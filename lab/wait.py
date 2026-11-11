"""Wait until the switch and routers have booted and the laptop has its address from DHCP."""
import sys
import time
import pathlib

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

deadline = time.time() + 240
while True:
    pending = [n for n in lab.NETWORK + lab.HOSTS if not lab.ready(n)]
    if not pending and not lab.addr("laptop"):
        pending = ["the laptop's DHCP address"]
    if not pending:
        break
    if time.time() > deadline:
        sys.exit(f"these didn't come up in 4 minutes: {', '.join(pending)}   (docker logs <name> says why)")
    print(f"  waiting for {', '.join(pending)} ...", flush=True)
    time.sleep(5)
print("\n  the network is up: a switch, two routers and five hosts. Start with task 1.1: make check T=1.1\n")
