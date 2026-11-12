"""The lab app's small backend: the config, task checks, progress, and starting a tab's service.

Caddy (port 8000, the one port the browser sees) sends /api/* here and everything else to the tabs' own
services. This listens on loopback only. Standard library only: it runs before any venv exists.

    python3 server.py               serve the API on 127.0.0.1:8001
    python3 server.py --caddyfile   print the Caddyfile for this lab's tabs
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # the lab repo
CONFIG = json.loads((HERE / "lab-ui.json").read_text())
if os.environ.get("LAB_GUIDE"):              # e.g. a local `hugo server` while writing the guide
    CONFIG["guide"] = os.environ["LAB_GUIDE"]
UI_PORT, API_PORT = 8000, 8001
STATE = pathlib.Path(os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local/state")) / "lab-ui"
PROGRESS = STATE / f"{ROOT.name}.json"
TASKS = {t[0] for ch in CONFIG["chapters"] for t in ch["tasks"]}
TABS = {t["id"]: t for t in CONFIG["tabs"]}
lock = threading.Lock()


def caddyfile():
    out = [f"# Made by {HERE.name}/server.py from lab-ui.json: the lab app on one port.",
           "{", "\tadmin off", "\tlog {", "\t\tlevel WARN", "\t}", "}", f":{UI_PORT} {{",
           f"\thandle /api/* {{\n\t\treverse_proxy 127.0.0.1:{API_PORT}\n\t}}"]
    if os.environ.get("LAB_GUIDE_DIR"):      # testing: a local build of the site, served at /guide/
        out.append(f"\thandle_path /guide/* {{\n\t\troot * {os.environ['LAB_GUIDE_DIR']}\n\t\tfile_server\n\t}}")
    for t in CONFIG["tabs"]:
        p = t["path"].rstrip("/")
        out.append(f"\tredir {p} {p}/")
        out.append(f"\t{'handle_path' if t.get('strip') else 'handle'} {p}/* {{\n"
                   f"\t\treverse_proxy 127.0.0.1:{t['port']}\n\t}}")
    out.append(f"\thandle {{\n\t\theader Cache-Control no-cache\n\t\troot * {HERE / 'www'}\n\t\tfile_server\n\t}}")
    out.append("}")
    return "\n".join(out) + "\n"


def up(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def network():
    """How far the lab's network has come: containerlab's running nodes, out of how many there should be.
    The app starts before the network does, so this is what it shows while you wait."""
    net = CONFIG.get("network")
    if not net:
        return None
    try:
        r = subprocess.run(["docker", "ps", "-q", "--filter", f"label=containerlab={net['name']}"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return {"docker": False, "running": 0, "total": net["nodes"]}
    if r.returncode != 0:                    # Docker inside the dev container is still starting
        return {"docker": False, "running": 0, "total": net["nodes"]}
    return {"docker": True, "running": len(r.stdout.split()), "total": net["nodes"]}


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
        if self.path == "/api/status":
            return self.send(200, {"progress": progress(), "network": network(),
                                   "services": {i: up(t["port"]) for i, t in TABS.items()}})
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
    else:
        ThreadingHTTPServer(("127.0.0.1", API_PORT), API).serve_forever()
