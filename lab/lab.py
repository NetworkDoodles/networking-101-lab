"""Small helpers the checker and the status page share: run a command on a lab node and read the answer."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOSTS = ["laptop", "printer", "broken-pc", "web", "dns"]
NETWORK = ["sw1", "r1", "r2"]          # CapeOS Bolt: an IOS-style CLI


def sh(node, cmd, timeout=20):
    """Run a shell command on a host; return (exit code, output)."""
    try:
        p = subprocess.run(["docker", "exec", node, "sh", "-c", cmd], capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 127, str(e)


def show(node, cmd, timeout=20):
    """Run a CLI command on the switch or a router; return its output ('' if it can't)."""
    try:
        p = subprocess.run(["docker", "exec", "-i", node, "capeos-cli", "-c", cmd], capture_output=True,
                           text=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def running(node):
    p = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", node], capture_output=True, text=True)
    return p.stdout.strip() == "true"


def ready(node):
    if not running(node):
        return False
    if node in NETWORK:
        return sh(node, "test -e /run/capeos/ready")[0] == 0
    return True


def addr(node, dev="eth1"):
    """A host's IPv4 address and prefix on eth1, like '192.168.1.20/24' (or None)."""
    code, out = sh(node, f"ip -4 -o addr show dev {dev}")
    for word in out.split():
        if "/" in word and word[0].isdigit():
            return word
    return None


def mac(node, dev="eth1"):
    code, out = sh(node, f"cat /sys/class/net/{dev}/address")
    return out.lower() if code == 0 else None


def config(node, *lines):
    """Type configuration commands on the switch or a router, as you would: configure terminal ... end."""
    text = "\n".join(["configure terminal", *lines, "end", ""])
    p = subprocess.run(["docker", "exec", "-i", node, "capeos-cli"], input=text, capture_output=True, text=True,
                       timeout=30)
    return p.stdout


def mac_ports(switch="sw1"):
    """The switch's MAC address table as {mac (aa:bb:..): port (Gi3)}."""
    table = {}
    for line in show(switch, "show mac address-table").splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit() and parts[1].count(".") == 2:
            hexdigits = parts[1].replace(".", "").lower()
            table[":".join(hexdigits[i:i + 2] for i in range(0, 12, 2))] = parts[-1]
    return table


def default_gw(node):
    code, out = sh(node, "ip -4 route show default")
    words = out.split()
    return words[words.index("via") + 1] if "via" in words else None


def nameservers(node):
    code, out = sh(node, "cat /etc/resolv.conf")
    return [l.split()[1] for l in out.splitlines() if l.startswith("nameserver") and len(l.split()) > 1]


def pings(node, target, count=2):
    return sh(node, f"ping -c {count} -W 1 {target}", timeout=15)[0] == 0
