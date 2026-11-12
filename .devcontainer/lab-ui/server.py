"""The lab app's small backend: the config, task checks, progress, and starting a tab's service.

Caddy (port 8000, the one port the browser sees) sends /api/* here and everything else to the tabs' own
services. This listens on loopback only. Standard library only: it runs before any venv exists.

    python3 server.py               serve the API on 127.0.0.1:8001
    python3 server.py --caddyfile   print the Caddyfile for this lab's tabs
    python3 server.py --terminal    print the web terminal's port, if this lab has one (start.sh starts it)
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # the lab repo
CONFIG = json.loads((HERE / "lab-ui.json").read_text())
if os.environ.get("LAB_GUIDE"):              # e.g. a local `hugo server` while writing the guide
    CONFIG["guide"] = os.environ["LAB_GUIDE"]
UI_PORT, API_PORT, TERM_PORT = 8000, 8001, 7681
STATE = pathlib.Path(os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local/state")) / "lab-ui"
PROGRESS = STATE / f"{ROOT.name}.json"
TASKS = {t[0] for ch in CONFIG["chapters"] for t in ch["tasks"]}
TABS = {t["id"]: t for t in CONFIG["tabs"]}
TOPO = CONFIG.get("topology")
# The nodes you can open a terminal on: the Topology tab's, unless one says "shell": false.
SHELLS = [n["id"] for n in TOPO["nodes"] if n.get("shell", True)] if TOPO else []
# The files each task has you edit, shown under the guide so the lab needs no editor: "answers" is every task's
# answers file ("answers/{task}.yml" fills in the task's number), "edit" adds others for some tasks.
ANSWERS = CONFIG.get("answers")
EDIT = CONFIG.get("edit", {})
# Buttons that run one of the lab's make targets ("actions"), so a lab without the VS Code tab can still reset,
# solve or break things. "task": true adds T=<the task>; "tasks" limits one to those tasks.
ACTIONS = {a["id"]: a for a in CONFIG.get("actions", [])}
lock = threading.Lock()


def caddyfile():
    out = [f"# Made by {HERE.name}/server.py from lab-ui.json: the lab app on one port.",
           "{", "\tadmin off", "\tlog {", "\t\tlevel WARN", "\t}", "}", f":{UI_PORT} {{",
           f"\thandle /api/* {{\n\t\treverse_proxy 127.0.0.1:{API_PORT}\n\t}}"]
    if os.environ.get("LAB_GUIDE_DIR"):      # testing: a local build of the site, served at /guide/
        out.append(f"\thandle_path /guide/* {{\n\t\troot * {os.environ['LAB_GUIDE_DIR']}\n\t\tfile_server\n\t}}")
    if SHELLS:                               # the web terminal (ttyd), at /term/ itself
        out.append(f"\thandle /term/* {{\n\t\treverse_proxy 127.0.0.1:{TERM_PORT}\n\t}}")
    for t in CONFIG["tabs"]:
        if "port" not in t:                  # drawn by the app itself (the Topology tab)
            continue
        p = t["path"].rstrip("/")
        out.append(f"\tredir {p} {p}/")
        out.append(f"\t{'handle_path' if t.get('strip') else 'handle'} {p}/* {{\n"
                   f"\t\treverse_proxy 127.0.0.1:{t['port']}\n\t}}")
    out.append(f"\thandle {{\n\t\theader Cache-Control no-store\n\t\troot * {HERE / 'www'}\n\t\tfile_server\n\t}}")
    out.append("}")
    return "\n".join(out) + "\n"


def up(tab):
    if "port" not in tab:
        return True
    """Is the tab's service answering? A tab with "ready" asks that page over HTTP: a published Docker port accepts
    connections long before the app behind it is ready, so a plain connect would say yes too early."""
    if tab.get("ready"):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{tab['port']}{tab['ready']}", timeout=2)
            return True
        except urllib.error.HTTPError as e:
            return e.code < 500
        except OSError:
            return False
    try:
        with socket.create_connection(("127.0.0.1", tab["port"]), timeout=0.5):
            return True
    except OSError:
        return False


def network():
    """How far the lab's network has come: containerlab's running nodes, out of how many there should be.
    The app starts before the network does, so this is what it shows while you wait. "label" counts other
    containers instead (a Docker Compose project, say), and "what" is what the top bar calls them."""
    net = CONFIG.get("network")
    if not net:
        return None
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}", "--filter", "label=" + net.get("label", f"containerlab={net['name']}")],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return {"docker": False, "running": 0, "total": net["nodes"], "what": net.get("what")}
    if r.returncode != 0:                    # Docker inside the dev container is still starting
        return {"docker": False, "running": 0, "total": net["nodes"], "what": net.get("what")}
    # containerlab gives each SR Linux node a <name>-netns helper with the same label: it isn't a node
    running = [n for n in r.stdout.split() if not n.endswith("-netns")]
    return {"docker": True, "running": len(running), "total": net["nodes"], "what": net.get("what")}


def running():
    """The Topology tab's containers that are running, by name (containerlab names them after the nodes). The
    topology can name its own containerlab lab ("lab"), when the network the top bar counts is something else."""
    net = CONFIG.get("network")
    if TOPO and TOPO.get("lab"):
        label = f"containerlab={TOPO['lab']}"
    elif net:
        label = net.get("label", f"containerlab={net['name']}")
    else:
        return []
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}", "--filter", "label=" + label],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [n for n in r.stdout.split() if not n.endswith("-netns")] if r.returncode == 0 else []


def task_files(task):
    """The files a task has you edit, as paths in the repo: only these can be read or written through the API."""
    if task not in TASKS:
        return []
    names = ([ANSWERS.format(task=task)] if ANSWERS else []) + EDIT.get(task, [])
    out = []
    for n in names:
        f = (ROOT / n).resolve()
        if f.is_relative_to(ROOT) and f.is_file():
            out.append(f)
    return out


def progress():
    try:
        return json.loads(PROGRESS.read_text())
    except (OSError, ValueError):
        return {}


def save(task, ok):
    with lock:
        p = progress()
        p[task] = ok
        STATE.mkdir(parents=True, exist_ok=True)
        PROGRESS.write_text(json.dumps(p, indent=1, sort_keys=True))


def make(*args, timeout=300):
    env = dict(os.environ, NO_COLOR="1", TERM="dumb")
    r = subprocess.run(["make", "-s", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if not l.startswith("make: ***"))
    return r.returncode, out.strip()


class API(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/config":
            return self.send(200, CONFIG)
        if self.path == "/api/topology":
            return self.send(200, {"running": running()})
        if self.path.startswith("/api/files?task="):
            task = self.path.split("=", 1)[1]
            return self.send(200, {"task": task, "files": [{"path": str(f.relative_to(ROOT)), "text": f.read_text()}
                                                           for f in task_files(task)]})
        if self.path == "/api/status":
            return self.send(200, {"progress": progress(), "network": network(), "running": running() if SHELLS else [],
                                   "services": {i: up(t) for i, t in TABS.items()}})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        # Only the lab app's own page sends this header. A page on another site can't add it without a CORS
        # preflight, which this server never answers, so it can't make the lab run anything.
        if self.headers.get("X-Lab-UI") != "1":
            return self.send(403, {"error": "missing X-Lab-UI header"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send(400, {"error": "bad JSON"})
        if self.path == "/api/check":
            task = str(body.get("task", ""))
            if task not in TASKS:
                return self.send(400, {"error": f"no task {task!r}"})
            try:
                rc, out = make("check", f"T={task}")
            except subprocess.TimeoutExpired:
                return self.send(200, {"task": task, "ok": False, "output": "the check took too long"})
            save(task, rc == 0)
            return self.send(200, {"task": task, "ok": rc == 0, "output": out})
        if self.path == "/api/file":
            task, path, text = str(body.get("task", "")), str(body.get("path", "")), body.get("text")
            f = next((f for f in task_files(task) if str(f.relative_to(ROOT)) == path), None)
            if not f or not isinstance(text, str) or len(text) > 100_000:
                return self.send(400, {"error": f"task {task!r} doesn't edit {path!r}"})
            f.write_text(text)
            return self.send(200, {"task": task, "path": path, "saved": True})
        if self.path == "/api/action":
            a, task = ACTIONS.get(str(body.get("id", ""))), str(body.get("task", ""))
            if not a or ((a.get("task") or a.get("tasks")) and task not in TASKS) or (a.get("tasks") and task not in a["tasks"]):
                return self.send(400, {"error": "no such action for this task"})
            try:
                rc, out = make(a["make"], *([f"T={task}"] if a.get("task") or a.get("tasks") else []), timeout=600)
            except subprocess.TimeoutExpired:
                return self.send(200, {"ok": False, "output": "it took too long"})
            return self.send(200, {"ok": rc == 0, "output": out})
        if self.path == "/api/start":
            tab = TABS.get(str(body.get("tab", "")))
            if not tab or not tab.get("start"):
                return self.send(400, {"error": "that tab has nothing to start"})
            try:
                rc, out = make(tab["start"], timeout=600)
            except subprocess.TimeoutExpired:
                return self.send(200, {"ok": False, "output": "it took too long to start"})
            return self.send(200, {"ok": rc == 0, "output": out})
        self.send(404, {"error": "not found"})


if __name__ == "__main__":
    if sys.argv[1:] == ["--caddyfile"]:
        sys.stdout.write(caddyfile())
    elif sys.argv[1:] == ["--terminal"]:
        print(TERM_PORT if SHELLS else "")
    else:
        ThreadingHTTPServer(("127.0.0.1", API_PORT), API).serve_forever()
