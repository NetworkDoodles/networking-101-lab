# Networking 101, part 2: hands on

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/NetworkDoodles/networking-101-lab?quickstart=1)

The hands-on half of [Networking 101](https://networkdoodles.com/labs/networking-101/). You log in to real
computers, a switch and two routers, run the commands network engineers use every day, and match what they
print to the ideas from the lessons: MAC and IP addresses, prefixes, DHCP, ARP, the switch's MAC table,
routing and DNS.

**The guide:** https://networkdoodles.com/labs/networking-101-lab/

```
  laptop ────┐
  printer ───┼── sw1 ── r1 ════ 10.0.0.0/30 ════ r2 ──┬── web  192.168.2.10/28
  broken-pc ─┘     192.168.1.0/24                     └── dns  192.168.2.53/28
```

## Start

The easy way: **Open the lab** on the [guide's page](https://networkdoodles.com/labs/networking-101-lab/), and
sign in with GitHub. It creates your codespace and opens the lab app: the guide on the left, VS Code on the
right. The first start takes a few minutes.

Or from here, in GitHub's own editor:

1. Click **Open in GitHub Codespaces** above, then **Create codespace**. If VS Code asks whether you trust
   the folder, click **Trust Folder & Continue**.
2. The lab app opens in a new browser tab (port 8000, **Lab** in the PORTS tab). Wait for it to say
   **network up**: the first start takes a few minutes.
3. Follow [task 1.1](https://networkdoodles.com/labs/networking-101-lab/task-1-1/). **Check task**, under the
   guide, checks your work.

## Commands

| Command | What it does |
|---|---|
| `make shell H=laptop` | log in to a node: `laptop printer broken-pc web dns` are Linux hosts, `sw1 r1 r2` the switch and routers |
| `make check T=1.1` | check a task (`CH=1` checks a chapter, nothing checks them all) |
| `make status` | what's running |
| `make reset` | put the whole network back how it started. Your answers files stay as they are |
| `make solve T=1.2` | stuck, or skipped a task? does it for you on the network and fills in its answers, printing every command |
| `make break T=3.1` | task 3.1's problem, on purpose |
| `make help` | everything else |

The switch and routers run CapeOS Bolt, a lab network OS with an IOS-style CLI. The hosts are small Alpine
Linux containers with the everyday tools: `ip`, `ping`, `traceroute`, `arp`, `dig`, `nslookup`, `curl`.
