"""make check T=1.1 · CH=1 · (nothing)  ·  verifies a task, a chapter or the whole lab.

Every check reads the real network: your answers are compared with what the hosts, the switch and the
routers say right now, and the things you change are tested by sending real traffic.

    python checks/check.py 1.1          one task
    python checks/check.py ch1          one chapter
    python checks/check.py all          everything
"""
import ipaddress
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "lab").as_posix())
import lab  # noqa: E402

GUIDE = "https://networkdoodles.com/labs/networking-101-lab"
TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
C = {k: (v if TTY else "") for k, v in dict(g="\033[32m", r="\033[31m", y="\033[33m", c="\033[36m", d="\033[2m",
                                              b="\033[1m", x="\033[0m").items()}


# ── reading your answers ───────────────────────────────────────────────────────
def answers(task):
    """answers/<task>.yml as a dict of strings. Read line by line, not as YAML: YAML would turn a MAC
    address made only of digits, like 02:42:11:22:33:44, into a number."""
    p = ROOT / "answers" / f"{task}.yml"
    doc = {}
    for line in (p.read_text().splitlines() if p.exists() else []):
        line = line.split(" #")[0].strip()
        if line and not line.startswith("#") and ":" in line:
            key, _, value = line.partition(":")
            doc[key.strip()] = value.strip().strip("'\"")
    return doc


def blank(v):
    return v is None or str(v).strip() == ""


def norm_mac(v):
    """aa:aa:aa:11:11:11, AA-AA-AA-11-11-11 and aaaa.aa11.1111 are all the same MAC address."""
    hexdigits = re.sub(r"[^0-9a-f]", "", str(v).lower())
    return ":".join(hexdigits[i:i + 2] for i in range(0, 12, 2)) if len(hexdigits) == 12 else None


def norm_prefix(v):
    """24, /24 and 255.255.255.0 are all the same prefix."""
    s = str(v).strip().lstrip("/")
    if s.isdigit():
        return int(s)
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{s}").prefixlen
    except ValueError:
        return None


def norm_ip(v):
    try:
        return str(ipaddress.IPv4Address(str(v).strip()))
    except ValueError:
        return None


def norm_port(v):
    """Gi3, gi3, GigabitEthernet3 and 3 are all the same switch port."""
    m = re.fullmatch(r"(?:gi(?:gabitethernet)?)?\s*(\d+)", str(v).strip().lower())
    return f"Gi{m.group(1)}" if m else None


def norm_int(v):
    s = str(v).strip()
    return int(s) if s.isdigit() else None


def norm_word(v):
    s = str(v).strip().lower()
    return s or None


NORM = {"mac": norm_mac, "prefix": norm_prefix, "ip": norm_ip, "port": norm_port, "int": norm_int, "word": norm_word}
WHAT = {"mac": "MAC address", "prefix": "prefix", "ip": "IPv4 address", "port": "switch port, like Gi1",
        "int": "whole number", "word": "name"}


def ask(doc, key, kind, want, label, hint="but that's not what the network says. Look again."):
    """One answer against the live value(s), with a message that says what's wrong without giving it away."""
    given = doc.get(key)
    if blank(given):
        return False, f"{label}: {key} is still blank in the answers file"
    value = NORM[kind](given)
    if value is None:
        return False, f"{label}: {given!r} isn't a {WHAT[kind]}"
    wants = want if isinstance(want, (set, list, tuple)) else {want}
    if value in wants:
        return True, f"{label}: {given}"
    return False, f"{label}: you wrote {given}, {hint}"


def iface(node):
    """A host's live address on eth1, as an ipaddress interface (or None if it has none)."""
    a = lab.addr(node)
    return ipaddress.IPv4Interface(a) if a else None


def pool_lease(cfg, pool):
    """A DHCP pool's lease time in seconds, from the router's running config (a day if it doesn't say)."""
    m = re.search(rf"^ip dhcp pool {pool}\n((?: .*\n)*)", cfg, re.M)
    lease = re.search(r"^ lease (\d+)(?: (\d+))?(?: (\d+))?", m.group(1), re.M) if m else None
    if not lease:
        return 86400
    d, h, mi = (int(x or 0) for x in lease.groups())
    return ((d * 24 + h) * 60 + mi) * 60


def need(*nodes):
    down = [n for n in nodes if not lab.ready(n)]
    if down:
        raise RuntimeError(f"{', '.join(down)} isn't running: is the lab up? (make status, make up)")


# ── chapter 1 · your computer ─────────────────────────────────────────────────
def t1_1():
    need("laptop", "printer")
    doc = answers("1.1")
    me, pr = iface("laptop"), iface("printer")
    if not me or not pr:
        yield False, "the laptop or the printer has no address: is the lab up? (make status)"
        return
    # The laptop's address changes in task 1.2's challenge, so the one it had before still counts.
    yield ask(doc, "laptop_mac", "mac", lab.mac("laptop"), "the laptop's MAC address (follow along)")
    yield ask(doc, "laptop_ip", "ip", {str(me.ip), "192.168.1.100"}, "the laptop's IP address (follow along)")
    yield ask(doc, "laptop_prefix", "prefix", me.network.prefixlen, "the laptop's prefix (follow along)")
    yield ask(doc, "printer_mac", "mac", lab.mac("printer"), "the printer's MAC address (challenge)")
    yield ask(doc, "printer_ip", "ip", str(pr.ip), "the printer's IP address (challenge)")
    yield ask(doc, "printer_prefix", "prefix", pr.network.prefixlen, "the printer's prefix (challenge)")
    worked = "which isn't right. Work it out from the IP address and the prefix."
    yield ask(doc, "printer_network", "ip", str(pr.network.network_address), "the printer's network address (challenge)", worked)
    yield ask(doc, "printer_broadcast", "ip", str(pr.network.broadcast_address), "the printer's broadcast address (challenge)", worked)


def t1_2():
    need("laptop", "r1")
    doc = answers("1.2")
    cfg = lab.show("r1", "show running-config")
    yield ask(doc, "dhcp_server", "ip", "192.168.1.1", "the DHCP server (follow along)")
    yield ask(doc, "gateway", "ip", "192.168.1.1", "the default gateway (follow along)")
    yield ask(doc, "dns_server", "ip", "192.168.2.53", "the DNS server (follow along)")
    yield ask(doc, "lease_seconds", "int", pool_lease(cfg, "HOME"), "the lease time, in seconds (follow along)",
              "but that's not the lease the laptop was given. udhcpc says it on its last line.")
    pools = dict(re.findall(r"^ip dhcp pool (\S+)\n((?: .*\n)*)", cfg, re.M))
    pool = next((name for name, body in pools.items() if " host 192.168.1.50 255.255.255.0" in body), None)
    body = pools.get(pool, "")
    # The laptop's udhcpc sends a Client-ID (01 + its MAC), so the reservation has to match on that.
    yield (bool(pool) and "client-identifier 01aa.aaaa.1111.11" in body,
           f"r1 has a pool that keeps 192.168.1.50 for the laptop's MAC address (challenge){': ' + pool if pool else ''}")
    me = iface("laptop")
    yield (bool(me) and str(me) == "192.168.1.50/24",
           f"the laptop has 192.168.1.50/24 (challenge): it has {me or 'no address'}"
           + ("" if me and str(me) == "192.168.1.50/24" else ". Did you ask for a new lease?"))
    gw, dns = lab.default_gw("laptop"), lab.nameservers("laptop")
    yield (bool(me) and str(me) == "192.168.1.50/24" and gw == "192.168.1.1" and "192.168.2.53" in dns,
           f"and still a gateway and a DNS server (challenge): gateway {gw or 'none'}, DNS {', '.join(dns) or 'none'}"
           + ("" if gw == "192.168.1.1" and "192.168.2.53" in dns else ". A reservation is a pool of its own: does it hand them out?"))


# ── chapter 2 · your network ──────────────────────────────────────────────────
def t2_1():
    need("laptop", "sw1", "r1")
    doc = answers("2.1")
    table = lab.mac_ports()
    r1_mac = lab.mac("r1")
    yield ask(doc, "laptop_port", "port", table.get(lab.mac("laptop")), "the laptop's port on sw1 (follow along)")
    yield ask(doc, "printer_port", "port", table.get(lab.mac("printer")), "the printer's port on sw1 (follow along)")
    yield ask(doc, "web_neighbor_ip", "ip", lab.default_gw("laptop") or "192.168.1.1",
              "the address the laptop asked ARP about, to reach web (challenge)",
              "but web isn't on the laptop's network. Who does the laptop hand the packet to?")
    yield ask(doc, "web_neighbor_mac", "mac", r1_mac, "the MAC address it learned for it (challenge)")
    yield ask(doc, "r1_port", "port", table.get(r1_mac), "r1's port on sw1 (challenge)")


def t2_2():
    need("broken-pc")
    me = iface("broken-pc")
    yield (bool(me) and str(me) == "192.168.1.30/24",
           f"broken-pc's address is 192.168.1.30/24 (follow along): it's {me or 'not set'}")
    gw = lab.default_gw("broken-pc")
    yield gw == "192.168.1.1", f"broken-pc's default gateway is r1, 192.168.1.1 (challenge): it's {gw or 'not set'}"
    yield lab.pings("broken-pc", "192.168.1.20"), "broken-pc reaches the printer, on its own network (challenge)"
    yield lab.pings("broken-pc", "192.168.2.10"), "broken-pc reaches web, two routers away (challenge)"


# ── chapter 3 · other networks ────────────────────────────────────────────────
def t3_1():
    need("laptop", "r1", "r2")
    doc = answers("3.1")
    yield ask(doc, "r1_next_hop", "ip", "10.0.0.2", "where r1 sends packets for 192.168.2.0/24 (follow along)",
              "but that's not what r1's routing table says. Look for the S line.")
    yield ask(doc, "hops_to_web", "int", 3, "how many hops traceroute counts to web (follow along)")
    yield ask(doc, "broken_router", "word", "r2", "which router was missing a route (challenge)",
              "but its routing table has everything it needs. Which router has to send the answers back?")
    cfg = lab.show("r2", "show running-config")
    yield ("ip route 192.168.1.0 255.255.255.0 10.0.0.1" in cfg,
           "r2 has a route back to the home network, 192.168.1.0/24 via r1 (challenge)")
    code, out = lab.sh("laptop", "traceroute -n -w 1 -q 1 -m 5 192.168.2.10", timeout=30)
    hops = [l.split()[1] for l in out.splitlines()[1:] if len(l.split()) > 1]
    yield (hops[:3] == ["192.168.1.1", "10.0.0.2", "192.168.2.10"],
           f"traceroute from the laptop goes r1, r2, web (challenge): {' → '.join(hops) or 'no answer'}")


def t3_2():
    need("laptop", "dns")
    doc = answers("3.2")
    yield ask(doc, "dns_server", "ip", lab.nameservers("laptop")[:1] or "192.168.2.53", "the laptop's DNS server (follow along)")
    yield ask(doc, "web_ip", "ip", "192.168.2.10", "web.lab's address, from dig (follow along)")
    code, out = lab.sh("laptop", "dig +short +time=2 +tries=1 printer.lab")
    yield out.strip() == "192.168.1.20", f"dig printer.lab answers 192.168.1.20 (challenge): {out.strip() or 'no answer'}"
    yield lab.pings("laptop", "printer.lab", 1), "ping printer.lab works from the laptop (challenge)"


# ── the tasks ──────────────────────────────────────────────────────────────────
TASKS = {
    "1.1": "meet your computer",
    "1.2": "get an address",
    "2.1": "who's next door?",
    "2.2": "one wrong number",
    "3.1": "across two routers",
    "3.2": "names for addresses",
}
CHAPTERS = {1: "your computer", 2: "your network", 3: "other networks"}


def report(t):
    print(f"{C['c']}╭─{C['x']} {C['b']}task {t}{C['x']} {C['d']}·{C['x']} {TASKS[t]}", flush=True)
    results = []
    try:
        for ok, msg in globals()[f"t{t.replace('.', '_')}"]():
            ok = bool(ok)
            results.append(ok)
            print(f"{C['c']}│{C['x']}  {C['g'] + '✓' if ok else C['r'] + '✗'}{C['x']} {msg}", flush=True)
    except Exception as e:  # a half-finished task shouldn't crash the checker
        results.append(False)
        print(f"{C['c']}│{C['x']}  {C['r']}✗{C['x']} {str(e).splitlines()[0][:160] if str(e) else type(e).__name__}")
    passed = sum(results)
    done = passed == len(results)
    tail = (f"{C['g']}verified{C['x']}" if done else
            f"{C['y']}stuck?{C['x']} the hints and the answer are on the guide page  "
            f"{C['d']}{GUIDE}/task-{t.replace('.', '-')}/{C['x']}")
    print(f"{C['c']}╰─{C['x']} {passed}/{len(results)} checks passed  {tail}\n")
    return done


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg.startswith("ch"):
        n = int(arg[2:])
        print(f"{C['b']}chapter {n} · {CHAPTERS.get(n, '')}{C['x']}\n")
        sys.exit(0 if all([report(t) for t in TASKS if t.startswith(f"{n}.")]) else 1)
    if arg == "all":
        done = [t for t in TASKS if report(t)]
        print(f"{C['b']}{len(done)}/{len(TASKS)} tasks verified{C['x']}")
        sys.exit(0 if len(done) == len(TASKS) else 1)
    if arg not in TASKS:
        sys.exit(f"no task {arg}: tasks are {', '.join(TASKS)}")
    sys.exit(0 if report(arg) else 1)
