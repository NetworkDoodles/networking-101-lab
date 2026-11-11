"""make status · what's running, and where to start.

The dev container runs this when the folder opens. It only reads. Safe to run any time.
"""
import os
import shutil
import sys
import time
import pathlib

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

GUIDE = "https://networkdoodles.com/labs/networking-101-lab"
TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
G, R, Y, D, B, X = (("\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m") if TTY else ("",) * 6)
WHAT = {
    "laptop": "a laptop (gets its address from DHCP)", "printer": "a printer", "broken-pc": "a PC someone set up by hand",
    "web": "a web server", "dns": "a DNS server", "sw1": "the switch", "r1": "router 1, the home gateway",
    "r2": "router 2, in front of the servers",
}


def row(ok, name, value):
    mark = f"{G}✓{X}" if ok else (f"{Y}·{X}" if ok is None else f"{R}✗{X}")
    print(f"  {mark} {name:<10} {value}")


def main():
    wait = "--wait" in sys.argv
    print(f"\n{B}Networking 101 · hands on{X}   {D}{GUIDE}{X}\n")
    if not shutil.which("docker"):
        row(False, "docker", "not found: open the lab in its dev container (Codespaces does this for you)")
        return 1
    deadline = time.time() + (300 if wait else 0)
    while True:
        up = {n: lab.ready(n) for n in lab.NETWORK + lab.HOSTS}
        if all(up.values()) or time.time() >= deadline:
            break
        print(f"  {D}starting: {', '.join(n for n, ok in up.items() if not ok)} ...{X}", flush=True)
        time.sleep(5)
    for n, ok in up.items():
        # No addresses here: finding them is task 1.1.
        row(ok, n, WHAT[n] if ok else f"{WHAT[n]}: not running yet (make up starts it)")
    if all(up.values()):
        print(f"\n  {G}Ready.{X} Open a terminal on the laptop with {B}make shell H=laptop{X}, then follow task 1.1.\n")
        return 0
    print(f"\n  Not everything is up. {B}make up{X} starts the network (about a minute).\n")
    return 1


sys.exit(main())
