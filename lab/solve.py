"""make solve T=1.2 · make break T=3.1

solve: stuck, or skipped a task? This does the task for you on the running network, the same way the guide's
solution does, and fills in that task's answers file. It prints every command it runs, so you can read them.

break: sets up a task's problem on purpose (only task 3.1 has one).
"""
import pathlib
import re
import sys

sys.path.insert(0, pathlib.Path(__file__).resolve().parent.as_posix())
import lab  # noqa: E402

ANSWERS = lab.ROOT / "answers"
HOSTS_FILE = lab.ROOT / "lab" / "dns" / "lab.hosts"


def say(where, cmd):
    print(f"  {where:<10} {cmd}")


def run(node, cmd):
    say(node, cmd)
    return lab.sh(node, cmd, timeout=40)[1]


def configure(node, *lines):
    for line in ("configure terminal", *lines, "end"):
        say(node, line)
    lab.config(node, *lines)


def fill(task, values):
    """Write values into answers/<task>.yml after their keys, keeping every comment."""
    path = ANSWERS / f"{task}.yml"
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        key = line.split(":")[0].strip()
        if key in values and not line.lstrip().startswith("#"):
            lines[i] = f"{key}: {values[key]}"
    path.write_text("\n".join(lines) + "\n")
    print(f"  {'answers':<10} filled in answers/{task}.yml")


def port(mac):
    return lab.mac_ports().get(mac, "")


def solve_1_1():
    me, pr = lab.addr("laptop"), lab.addr("printer")
    ip, plen = pr.split("/")
    import ipaddress
    net = ipaddress.IPv4Interface(pr).network
    fill("1.1", {"laptop_mac": lab.mac("laptop"), "laptop_ip": me.split("/")[0], "laptop_prefix": me.split("/")[1],
                 "printer_mac": lab.mac("printer"), "printer_ip": ip, "printer_prefix": plen,
                 "printer_network": net.network_address, "printer_broadcast": net.broadcast_address})


def solve_1_2():
    configure("r1", "ip dhcp pool LAPTOP", " host 192.168.1.50 255.255.255.0", " client-identifier 01aa.aaaa.1111.11",
              " default-router 192.168.1.1", " dns-server 192.168.2.53", " domain-name lab")
    run("laptop", "pkill udhcpc; sleep 1")
    print("             " + run("laptop", "udhcpc -i eth1 -q").replace("\n", "\n             "))
    cfg = lab.show("r1", "show running-config")
    m = re.search(r"^ip dhcp pool HOME\n(?: .*\n)*? lease (\d+)(?: (\d+))?(?: (\d+))?", cfg, re.M)
    d, h, mi = (int(x or 0) for x in m.groups()) if m else (1, 0, 0)
    fill("1.2", {"dhcp_server": "192.168.1.1", "gateway": "192.168.1.1", "dns_server": "192.168.2.53",
                 "lease_seconds": ((d * 24 + h) * 60 + mi) * 60})


def solve_2_1():
    run("laptop", "ping -c 2 192.168.1.20 >/dev/null; ping -c 2 192.168.2.10 >/dev/null")
    r1 = lab.mac("r1")
    fill("2.1", {"laptop_port": port(lab.mac("laptop")), "printer_port": port(lab.mac("printer")),
                 "web_neighbor_ip": "192.168.1.1", "web_neighbor_mac": r1, "r1_port": port(r1)})


def solve_2_2():
    run("broken-pc", "ip addr flush dev eth1")
    run("broken-pc", "ip addr add 192.168.1.30/24 dev eth1")
    run("broken-pc", "ip route replace default via 192.168.1.1")


def solve_3_1():
    configure("r2", "ip route 192.168.1.0 255.255.255.0 10.0.0.1")
    fill("3.1", {"r1_next_hop": "10.0.0.2", "hops_to_web": 3, "broken_router": "r2"})


def solve_3_2():
    text = HOSTS_FILE.read_text()
    if not re.search(r"^\s*192\.168\.1\.20\s+printer\.lab\b", text, re.M):
        HOSTS_FILE.write_text(text.rstrip("\n") + "\n192.168.1.20  printer.lab\n")
        print(f"  {'file':<10} added '192.168.1.20  printer.lab' to lab/dns/lab.hosts")
    fill("3.2", {"dns_server": "192.168.2.53", "web_ip": "192.168.2.10"})


def solve_3_3():
    out = run("laptop", "curl -s -o /dev/null -w '%{local_port}' http://web.lab/")
    run("web", "httpd -p 8080 -h /srv/www")
    fill("3.3", {"web_port": 80, "dns_port": 53, "laptop_port": out.strip(), "port_22": "refused"})


def break_3_1():
    configure("r2", "no ip route 192.168.1.0 255.255.255.0 10.0.0.1")
    print("\n  Something on the way to web is broken now. From the laptop: traceroute -n 192.168.2.10\n")


if __name__ == "__main__":
    action, task = sys.argv[1], sys.argv[2]
    fn = globals().get(f"{action}_{task.replace('.', '_')}")
    if not fn:
        sys.exit(f"no {action} for task {task}" + ("   (only task 3.1 has one)" if action == "break" else ""))
    print(f"\n  {action} task {task}:\n")
    fn()
    if action == "solve":
        print(f"\n  done. Now: make check T={task}\n")
