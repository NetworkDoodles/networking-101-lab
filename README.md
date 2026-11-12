# Networking 101, part 2: hands on

**[▶ Open the lab](https://labs.networkdoodles.com/open/networking-101-lab)**: one click, nothing to install

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

**Open the lab** (the link above, or the button on the [guide's page](https://networkdoodles.com/labs/networking-101-lab/)) and
sign in with GitHub. It creates your own codespace, on your GitHub account's free allowance, and opens the lab
app: the guide on the left, the **Topology** tab on the right. The first start takes a few minutes; the top bar
says **network up** when all eight devices are running. Then follow
[task 1.1](https://networkdoodles.com/labs/networking-101-lab/task-1-1/).

- **Topology tab**: the network, drawn. Hover over a device to see what it is, what it runs, where its ports
  are cabled and whether it's running. Click it to open a terminal on it, in a tab named after it (`laptop`,
  `r1` ...). Hosts give a Linux prompt (`laptop:~#`), sw1, r1 and r2 the CapeOS CLI (`r1#`). Close a tab
  with its ×.
- **Answers box**, under the guide: the current task's file (`answers/1.1.yml`; task 3.2 also has
  `lab/dns/lab.hosts`, picked with the switcher above the box). Type after the colons. It saves when you click
  away, with Ctrl+S, and always before a check.
- **Check task**, under the guide, checks your work. **Solve it for me**, next to it, does the task for you.
  **Break it**, on task 3.1, sets up that task's problem.
- **Reset network**, in the top bar, puts the network back how it started (it asks first; your answers stay).

On your own laptop instead: open the repo in its dev container (VS Code's *Reopen in Container*, or
`npx @devcontainers/cli up --workspace-folder .`), then the lab app is at http://localhost:8000.

## Commands

In the lab app, the buttons do all of this. Without it (a terminal in the dev container on your own laptop),
the same things are `make` commands:

| In the lab app | Command | What it does |
|---|---|---|
| click a device on **Topology** | `make shell H=laptop` | log in to a node: `laptop printer broken-pc web dns` are Linux hosts, `sw1 r1 r2` the switch and routers |
| **Check task** | `make check T=1.1` | check a task (`CH=1` checks a chapter, nothing checks them all) |
| **network up** in the top bar | `make status` | what's running |
| **Reset network** | `make reset` | put the whole network back how it started. Your answers files stay as they are |
| **Solve it for me** | `make solve T=1.2` | stuck, or skipped a task? does it for you on the network and fills in its answers, printing every command |
| **Break it** (task 3.1) | `make break T=3.1` | task 3.1's problem, on purpose |
| | `make help` | everything else |

The switch and routers run CapeOS Bolt, a lab network OS with an IOS-style CLI. The hosts are small Alpine
Linux containers with the everyday tools: `ip`, `ping`, `traceroute`, `arp`, `dig`, `nslookup`, `curl`.
