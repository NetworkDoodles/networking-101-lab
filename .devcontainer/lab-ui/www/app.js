// The lab app: the guide on the left, one tab per service, every tab behind this same address.
(() => {
  const $ = (s) => document.querySelector(s);
  const store = {
    get: (k, d) => { try { return localStorage.getItem("lab-ui:" + k) ?? d; } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem("lab-ui:" + k, v); } catch {} },
  };
  const api = (path, body) => fetch("/api/" + path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Lab-UI": "1" }, body: JSON.stringify(body),
  }).then((r) => r.json());

  let cfg, tasks = [], status = { progress: {}, services: {} }, active;

  // ── guide ────────────────────────────────────────────────────────────────
  const guideUrl = (id) => cfg.guide + (id === "overview" ? "" : "task-" + id.replace(".", "-") + "/");
  // navigate = false when the guide itself moved (a link clicked in it): only the picker follows
  function showTask(id, navigate = true) {
    if (id !== "overview" && !tasks.includes(id)) id = "overview";
    $("#task").value = id;
    store.set("task", id);
    if (navigate) $("#guide-frame").src = guideUrl(id);
    $("#prev").disabled = id === "overview";
    $("#next").disabled = id === tasks[tasks.length - 1];
    const btn = $("#check");
    btn.hidden = id === "overview";
    btn.querySelector("span").textContent = "Check task " + id;
    $("#check-out").hidden = true;
    actionButtons(id);
    loadAnswers(id);
  }

  // ── files ────────────────────────────────────────────────────────────────
  // The files a task has you edit (its answers file, and any others: "answers" and "edit" in lab-ui.json) are
  // edited here, under the guide, so a lab can do without the VS Code tab. A check saves them first.
  let files = [], fileTask = null, cur = -1;
  async function loadAnswers(id) {
    const box = $("#answers");
    if (!(cfg.answers || cfg.edit) || id === "overview") { await saveAnswers(); box.hidden = true; files = []; cur = -1; return; }
    await saveAnswers();
    const r = await api("files?task=" + encodeURIComponent(id)).catch(() => null);
    files = (r && r.files || []).map((f) => ({ ...f, saved: f.text }));
    fileTask = id;
    cur = -1;
    box.hidden = !files.length;
    const pick = $("#answers-pick");
    pick.innerHTML = "";
    files.forEach((f, i) => {
      const b = document.createElement("button");
      b.textContent = f.path;
      b.onclick = () => showFile(i);
      pick.append(b);
    });
    if (files.length) showFile(0);
  }
  function showFile(i) {
    if (cur >= 0) files[cur].text = $("#answers-text").value;
    cur = i;
    [...$("#answers-pick").children].forEach((b, j) => b.setAttribute("aria-pressed", i === j));
    $("#answers-text").value = files[i].text;
    $("#answers-state").textContent = files[i].text === files[i].saved ? "" : "not saved yet";
  }
  async function saveAnswers() {
    if (cur < 0) return;
    files[cur].text = $("#answers-text").value;
    for (const f of files) {
      if (f.text === f.saved) continue;
      const r = await api("file", { task: fileTask, path: f.path, text: f.text }).catch(() => null);
      if (r && r.saved) f.saved = f.text;
      else { $("#answers-state").textContent = "not saved: " + ((r && r.error) || "no answer"); return; }
    }
    $("#answers-state").textContent = "saved";
  }
  function step(d) {
    const order = ["overview", ...tasks], i = order.indexOf($("#task").value);
    showTask(order[Math.min(order.length - 1, Math.max(0, i + d))]);
  }
  function taskLabel(id, title) {
    const p = status.progress[id];
    return (p === true ? "✓ " : p === false ? "✗ " : "   ") + id + "  " + title;
  }
  function fillTasks() {
    const sel = $("#task"), keep = sel.value;
    sel.innerHTML = '<option value="overview">Overview</option>';
    for (const ch of cfg.chapters) {
      const g = document.createElement("optgroup");
      g.label = ch.n + " · " + ch.title;
      for (const [id, title] of ch.tasks) g.append(new Option(taskLabel(id, title), id));
      sel.append(g);
    }
    if (keep) sel.value = keep;
  }

  // ── actions ──────────────────────────────────────────────────────────────
  // "actions" in lab-ui.json: buttons for the lab's make targets. "bar": true puts one in the top bar (Reset);
  // the rest sit by Check task, for every task ("task": true) or only some ("tasks": ["3.1"]).
  function actionButtons(id) {
    const box = $("#acts");
    box.innerHTML = "";
    for (const a of cfg.actions || []) {
      if (a.bar || id === "overview" || (a.tasks && !a.tasks.includes(id))) continue;
      box.append(actionButton(a, () => id));
    }
  }
  function actionButton(a, task) {
    const b = document.createElement("button");
    b.className = "act";
    b.textContent = a.label;
    if (a.title) b.title = a.title;
    b.onclick = async () => {
      if (a.confirm && !confirm(a.confirm)) return;
      const t = task(), out = $("#check-out");
      b.disabled = true;
      const label = b.textContent;
      b.textContent = (a.busy || "Working") + " …";
      const r = await api("action", { id: a.id, task: t }).catch((e) => ({ ok: false, output: String(e) }));
      out.className = "check-out " + (r.ok ? "ok" : "bad");
      out.querySelector("pre").textContent = r.output || r.error || (r.ok ? "Done." : "It didn't work.");
      out.hidden = false;
      b.disabled = false;
      b.textContent = label;
      if (t && t !== "overview") loadAnswers(t);   // solve fills in the answers: show them
      refresh();
      if (active && active.kind === "topology") topoState();
    };
    return b;
  }

  async function check() {
    const id = $("#task").value, btn = $("#check"), out = $("#check-out");
    btn.disabled = true;
    btn.querySelector("span").textContent = "Checking " + id + " …";
    await saveAnswers();
    try {
      const r = await api("check", { task: id });
      out.className = "check-out " + (r.ok ? "ok" : "bad");
      out.querySelector("pre").textContent = r.output || r.error || "";
      if (launched && r.task) nd("progress", { task: r.task, ok: !!r.ok }).catch(() => {});
    } catch (e) {
      out.className = "check-out bad";
      out.querySelector("pre").textContent = "The check didn't run: " + e;
    }
    out.hidden = false;
    btn.disabled = false;
    btn.querySelector("span").textContent = "Check task " + id;
    refresh();
  }

  // ── tabs ─────────────────────────────────────────────────────────────────
  function pane(t) { return document.getElementById("pane-" + t.id); }
  function load(t) {
    const p = pane(t);
    if (t.kind === "topology") return topology(p);
    if (t.start && !status.services[t.id]) return idle(t);
    if (!p.querySelector("iframe")) {
      p.innerHTML = "";
      const f = document.createElement("iframe");
      f.title = t.name;
      f.src = t.path;
      f.allow = "clipboard-read; clipboard-write; fullscreen";
      p.append(f);
    }
  }
  function idle(t, msg) {
    const p = pane(t);
    p.innerHTML = "";
    const box = document.createElement("div");
    box.className = "idle";
    box.innerHTML = "<p></p><button class='btn'></button><pre hidden></pre>";
    box.querySelector("p").textContent = msg || t.idle || t.name + " isn't running.";
    const b = box.querySelector("button");
    b.textContent = t.startLabel || "Start " + t.name;
    b.onclick = async () => {
      b.disabled = true;
      b.textContent = "Starting " + t.name + " …";
      const r = await api("start", { tab: t.id }).catch((e) => ({ ok: false, output: String(e) }));
      if (!r.ok) {
        const pre = box.querySelector("pre");
        pre.hidden = false;
        pre.textContent = r.output || r.error;
        b.disabled = false;
        b.textContent = "Try again";
        return;
      }
      // the container is up; wait for the app inside it to answer through the proxy
      for (let i = 0; i < 90; i++) {
        const ok = await fetch(t.path, { cache: "no-store" }).then((x) => x.ok).catch(() => false);
        if (ok) break;
        await new Promise((res) => setTimeout(res, 1000));
      }
      status.services[t.id] = true;
      p.innerHTML = "";
      load(t);
      refresh();
    };
    p.append(box);
  }
  function select(id) {
    const t = cfg.tabs.find((x) => x.id === id) || cfg.tabs[0];
    active = t;
    store.set("tab", t.id);
    if (!t.node) store.set("lasttab", t.id);
    for (const x of cfg.tabs) {
      document.getElementById("tab-" + x.id).setAttribute("aria-selected", x === t);
      pane(x).classList.toggle("on", x === t);
    }
    $("#popout").href = t.path || "";
    $("#popout").hidden = !t.path;
    load(t);
  }
  function addTab(t, at) {
    const b = document.createElement("button");
    b.className = "tab" + (t.node ? " term" : "");
    b.id = "tab-" + t.id;
    b.setAttribute("role", "tab");
    b.innerHTML = "<span class='dot'></span><span></span>";
    b.children[1].textContent = t.name;
    b.onclick = () => select(t.id);
    if (t.node) {
      const x = document.createElement("span");
      x.className = "x";
      x.title = "Close " + t.name + "'s terminal";
      x.textContent = "×";
      x.onclick = (e) => { e.stopPropagation(); closeTerminal(t); };
      b.append(x);
    }
    $("#tabs").append(b);
    const p = document.createElement("div");
    p.className = "pane";
    p.id = "pane-" + t.id;
    $("#panes").append(p);
  }

  // ── terminals ────────────────────────────────────────────────────────────
  // Clicking a node on the Topology tab opens a terminal on it, in a tab of its own (or goes back to it).
  const termIds = () => cfg.tabs.filter((t) => t.node).map((t) => t.node);
  function openTerminal(node, show = true) {
    let t = cfg.tabs.find((x) => x.node === node);
    if (!t) {
      t = { id: "term-" + node, name: node, node, path: "/term/?arg=" + encodeURIComponent(node) };
      cfg.tabs.push(t);
      addTab(t);
      store.set("terms", termIds().join(" "));
    }
    if (show) select(t.id);
  }
  function closeTerminal(t) {
    cfg.tabs = cfg.tabs.filter((x) => x !== t);
    document.getElementById("tab-" + t.id).remove();
    pane(t).remove();
    store.set("terms", termIds().join(" "));
    if (active === t) select(store.get("lasttab", cfg.tabs[0].id));
  }

  // ── topology ─────────────────────────────────────────────────────────────
  // The lab's network, drawn like the guide's animations. Hover a node for what it is and what its ports
  // connect to; click it for a terminal on it.
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.append(e);
    return e;
  };
  // the same icons as the guide's animations (the site's netsim.js), drawn around (0,0); each returns its label's y
  const ICONS = {
    pc(g) { el("rect", { class: "ico", x: -24, y: -22, width: 48, height: 32, rx: 4 }, g); el("rect", { class: "scr", x: -19, y: -17, width: 38, height: 22, rx: 2 }, g); el("path", { class: "ico", d: "M-7 10h14l3 8h-20z" }, g); return 32; },
    laptop(g) { el("rect", { class: "ico", x: -20, y: -20, width: 40, height: 26, rx: 3 }, g); el("rect", { class: "scr", x: -16, y: -16, width: 32, height: 18, rx: 2 }, g); el("path", { class: "ico", d: "M-27 7h54l-5 8h-44z" }, g); return 30; },
    printer(g) { el("rect", { class: "scr", x: -14, y: -22, width: 28, height: 12 }, g); el("rect", { class: "ico", x: -24, y: -12, width: 48, height: 22, rx: 4 }, g); el("rect", { class: "scr", x: -14, y: 4, width: 28, height: 14 }, g); return 32; },
    server(g) { for (let i = 0; i < 3; i++) { el("rect", { class: "ico", x: -20, y: -24 + i * 15, width: 40, height: 13, rx: 2 }, g); el("circle", { class: "dot", cx: -13, cy: -17.5 + i * 15, r: 2 }, g); el("path", { class: "scr-line", d: `M-4 ${-17.5 + i * 15}h17` }, g); } return 34; },
    switch(g) { el("rect", { class: "ico", x: -30, y: -13, width: 60, height: 26, rx: 5 }, g); el("path", { class: "arw", d: "M-16 -4h30m-5 -4 5 4-5 4M16 5h-30m5 -4-5 4 5 4" }, g); return 27; },
    router(g) { el("ellipse", { class: "ico", cx: 0, cy: 5, rx: 26, ry: 10 }, g); el("path", { class: "ico", d: "M-26 -5v10a26 10 0 0 0 52 0v-10" }, g); el("ellipse", { class: "ico top", cx: 0, cy: -5, rx: 26, ry: 10 }, g); el("path", { class: "arw", d: "M-14 -9l7 3M14 -1l-7 -3M-3 -12l4 -2M3 2l-4 2" }, g); return 28; },
    db(g) { el("path", { class: "ico", d: "M-22 -14v28a22 7 0 0 0 44 0v-28" }, g); el("path", { class: "scr-line", d: "M-22 0a22 7 0 0 0 44 0" }, g); el("ellipse", { class: "ico top", cx: 0, cy: -14, rx: 22, ry: 7 }, g); return 30; },
  };
  let topoRunning = [], topoTimer;
  function ports(id) {
    // "eth2 → laptop eth1", from the links
    const out = [];
    for (const [a, b] of cfg.topology.links) {
      const [an, ap] = a.split(":"), [bn, bp] = b.split(":");
      if (an === id) out.push([ap, bn + " " + bp]);
      else if (bn === id) out.push([bp, an + " " + ap]);
    }
    return out.sort((x, y) => x[0].localeCompare(y[0], undefined, { numeric: true }));
  }
  function topology(p) {
    if (p.querySelector(".topo")) return topoState();
    const T = cfg.topology;
    p.innerHTML = "<div class='topo'><svg></svg><div class='topo-tip' hidden></div><p class='topo-hint'></p></div>";
    p.querySelector(".topo-hint").textContent = T.hint || "Click a device to open a terminal on it. Hover for its details.";
    const svg = p.querySelector("svg"), tip = p.querySelector(".topo-tip");
    const xs = T.nodes.map((n) => n.x), ys = T.nodes.map((n) => n.y);
    svg.setAttribute("viewBox", [Math.min(...xs) - 90, Math.min(...ys) - 70, Math.max(...xs) - Math.min(...xs) + 180,
      Math.max(...ys) - Math.min(...ys) + 150].join(" "));
    const at = Object.fromEntries(T.nodes.map((n) => [n.id, n]));
    const links = el("g", {}, svg), nodes = el("g", {}, svg);
    for (const [a, b] of T.links) {
      const na = at[a.split(":")[0]], nb = at[b.split(":")[0]];
      const g = el("g", { class: "ns-link" }, links);
      el("line", { x1: na.x, y1: na.y, x2: nb.x, y2: nb.y }, g);
      el("line", { class: "hit", x1: na.x, y1: na.y, x2: nb.x, y2: nb.y }, g);
      // "linkTip": a line for each cable's hover card, with {a} and {b} for its two ends (e.g. how to capture on it)
      const lt = T.linkTip ? "<p class='tt-foot'>" + escHtml(T.linkTip.replaceAll("{a}", a).replaceAll("{b}", b)) + "</p>" : "";
      g.addEventListener("pointerenter", (e) => showTip(e, "<b>" + a.replace(":", " ") + "</b> ↔ <b>" + b.replace(":", " ") + "</b>" + lt));
      g.addEventListener("pointermove", moveTip);
      g.addEventListener("pointerleave", () => { tip.hidden = true; });
    }
    for (const n of T.nodes) {
      const g = el("g", { class: "ns-node k-" + n.icon + (n.shell === false ? "" : " clickable"), transform: `translate(${n.x} ${n.y})`, "data-id": n.id,
        tabindex: n.shell === false ? -1 : 0, role: "button", "aria-label": n.id + ": " + (n.what || "") }, nodes);
      el("rect", { class: "hit", x: -40, y: -36, width: 80, height: 92, rx: 10 }, g);
      const ly = (ICONS[n.icon] || ICONS.pc)(g);
      el("text", { class: "lbl", y: ly + 6 }, g).textContent = n.id;
      if (n.sub) el("text", { class: "sub", y: ly + 23 }, g).textContent = n.sub;
      g.addEventListener("pointerenter", (e) => showTip(e, nodeTip(n)));
      g.addEventListener("pointermove", moveTip);
      g.addEventListener("pointerleave", () => { tip.hidden = true; });
      if (n.shell !== false) {
        g.addEventListener("click", () => { tip.hidden = true; openTerminal(n.id); });
        g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openTerminal(n.id); } });
      }
    }
    function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; moveTip(e); }
    function moveTip(e) {
      const r = p.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
      let x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
      if (x + w > r.width - 8) x = e.clientX - r.left - w - 16;
      if (y + h > r.height - 8) y = e.clientY - r.top - h - 16;
      tip.style.left = Math.max(8, x) + "px";
      tip.style.top = Math.max(8, y) + "px";
    }
    topoState();
  }
  const escHtml = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function nodeTip(n) {
    const up = topoRunning.includes(n.id);
    let h = "<div class='tt-head'><b>" + escHtml(n.id) + "</b><span class='" + (up ? "up" : "down") + "'>" +
      (up ? "running" : "not running") + "</span></div>";
    if (n.what) h += "<p>" + escHtml(n.what) + "</p>";
    const rows = [...(n.details || [])];
    const ps = ports(n.id);
    if (ps.length) rows.push(["ports", ps.map(([a, b]) => escHtml(a) + " → " + escHtml(b)).join("<br>"), true]);
    if (rows.length) h += "<table>" + rows.map(([k, v, raw]) => "<tr><th>" + escHtml(k) + "</th><td>" + (raw ? v : escHtml(v)) + "</td></tr>").join("") + "</table>";
    if (n.shell !== false) h += "<p class='tt-foot'>Click for a terminal on " + escHtml(n.id) + ".</p>";
    return h;
  }
  async function topoState() {
    const r = await api("topology").catch(() => null);
    if (r) topoRunning = r.running;
    for (const g of document.querySelectorAll(".topo .ns-node")) g.classList.toggle("down", !topoRunning.includes(g.dataset.id));
    clearTimeout(topoTimer);
    if (active && active.kind === "topology") topoTimer = setTimeout(topoState, topoRunning.length < cfg.topology.nodes.length ? 3000 : 15000);
  }
  function reload() {
    if (active.kind === "topology") return topoState();
    const f = pane(active).querySelector("iframe");
    if (f) f.src = active.path; else load(active);
  }

  // ── status ───────────────────────────────────────────────────────────────
  async function refresh() {
    try { status = await api("status"); } catch { return; }
    netStatus(status.network);
    const done = tasks.filter((id) => status.progress[id] === true).length;
    $("#progress").innerHTML = "<b>" + done + "</b>/" + tasks.length + " tasks checked";
    for (const t of cfg.tabs) {
      if (t.node) { document.querySelector("#tab-" + t.id + " .dot").classList.toggle("up", (status.running || []).includes(t.node)); continue; }
      document.querySelector("#tab-" + t.id + " .dot").classList.toggle("up", !!status.services[t.id]);
      // a service that stopped (make wireshark-stop) goes back to its start button, and one that came up
      // (started from a terminal, or still starting when the tab opened) replaces it
      if (t.start && !status.services[t.id] && pane(t).querySelector("iframe")) idle(t);
      else if (t.start && status.services[t.id] && t === active && !pane(t).querySelector("iframe")
        && !pane(t).querySelector("button:disabled")) { pane(t).innerHTML = ""; load(t); }
    }
    // rebuild the picker only when a result changed: rebuilding closes it if it's open
    const p = JSON.stringify(status.progress);
    if (p !== lastProgress) { lastProgress = p; fillTasks(); }
  }
  let lastProgress;

  // The app is up before the lab is: say how far the start has got, and check again soon until it's done.
  let netTimer;
  function netStatus(n) {
    const el = $("#net");
    if (!n) return;
    const what = n.what || "network", units = n.what ? " containers" : " nodes";
    el.hidden = false;
    let text, cls, title;
    if (!n.docker) {
      [text, cls] = ["setting up the lab …", "wait"];
      title = "Docker is starting and the lab's images are on their way. The VS Code tab's terminal shows the details.";
    } else if (n.running >= n.total) {
      [text, cls, title] = [what + " up", "up", n.running + units + " running"];
    } else {
      [text, cls] = [what + " " + n.running + "/" + n.total, "wait"];
      title = n.running ? "Starting: " + what + " is up when all " + n.total + units + " are running."
        : what + " isn't running yet. It starts by itself after the first setup; make up starts it by hand.";
    }
    el.textContent = text;
    el.className = "net " + cls;
    el.title = title;
    clearTimeout(netTimer);
    if (cls === "wait") netTimer = setTimeout(refresh, 3000);
  }

  // ── opened from the site ─────────────────────────────────────────────────
  // At its own address on the site, the launcher in front answers /__nd/*: who you are, activity, finishing.
  // Anywhere else (Codespaces' port, a laptop) /__nd/info is a 404 and none of this runs.
  let launched = null, lastInput = Date.now();
  const touched = () => { lastInput = Date.now(); };
  const INPUT = ["keydown", "pointerdown", "pointermove", "wheel", "touchstart"];
  function watch(win) { try { for (const ev of INPUT) win.addEventListener(ev, touched, { passive: true, capture: true }); } catch {} }
  function watchFrames() {
    // every tab is on this same address, so their input can be seen from here
    for (const f of document.querySelectorAll("iframe")) {
      if (f.dataset.watched) continue;
      f.dataset.watched = "1";
      f.addEventListener("load", () => { try { watch(f.contentWindow); } catch {} });
      try { if (f.contentDocument && f.contentDocument.readyState === "complete") watch(f.contentWindow); } catch {}
    }
  }
  const nd = (path, body) => fetch("/__nd/" + path, body === undefined ? { cache: "no-store" } : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Lab-UI": "1" }, body: JSON.stringify(body),
  });
  async function launcher() {
    const r = await fetch("/__nd/info", { cache: "no-store" }).catch(() => null);
    if (!r || !r.ok || !(r.headers.get("Content-Type") || "").includes("json")) return;
    launched = await r.json();
    watch(window);
    new MutationObserver(watchFrames).observe($("#panes"), { childList: true, subtree: true });
    watchFrames();
    // "still here", once a minute, but only while someone is actually using the lab: the site stops the
    // codespace when these stop, so an open tab nobody is using doesn't burn your Codespaces hours.
    setInterval(() => { if (Date.now() - lastInput < 5 * 60000) nd("beat", {}).catch(() => {}); }, 60000);
    nd("beat", {}).catch(() => {});
    const b = $("#finish");
    b.hidden = false;
    b.title = "Signed in as " + launched.login + ". Delete this lab's codespace: you're done with it.";
    b.onclick = finish;
  }
  async function finish() {
    const ok = confirm("Finish " + (launched.title || "this lab") + "?\n\nThis deletes its codespace and everything in it: " +
      "your captures, your answers and any files you changed. Opening the lab again later starts a fresh copy.");
    if (!ok) return;
    const b = $("#finish");
    b.disabled = true;
    b.textContent = "Deleting …";
    const r = await nd("finish", {}).then((x) => x.json()).catch((e) => ({ error: String(e) }));
    if (!r.ok) { alert("It didn't finish: " + (r.error || "no answer")); b.disabled = false; b.textContent = "Finish lab"; return; }
    // back to the lab's page on networkdoodles.com
    document.body.innerHTML = "<div class='idle'><p>Done. The codespace is deleted. Taking you back to networkdoodles.com …</p></div>";
    setTimeout(() => { location.href = r.next; }, 1500);
  }

  // ── layout ───────────────────────────────────────────────────────────────
  function toggleGuide(force) {
    const hide = force ?? !document.body.classList.contains("no-guide");
    document.body.classList.toggle("no-guide", hide);
    $("#toggle-guide").setAttribute("aria-pressed", !hide);
    store.set("guide", hide ? "hidden" : "shown");
  }
  function splitter() {
    const s = $("#split");
    s.onpointerdown = (e) => {
      s.setPointerCapture(e.pointerId);
      s.classList.add("drag");
      document.body.classList.add("dragging");
      s.onpointermove = (m) => {
        const w = Math.max(280, Math.min(window.innerWidth * 0.7, m.clientX));
        document.documentElement.style.setProperty("--guide", w + "px");
      };
      s.onpointerup = () => {
        s.onpointermove = null;
        s.classList.remove("drag");
        document.body.classList.remove("dragging");
        store.set("width", getComputedStyle(document.documentElement).getPropertyValue("--guide"));
      };
    };
  }

  async function main() {
    cfg = await api("config");
    tasks = cfg.chapters.flatMap((c) => c.tasks.map((t) => t[0]));
    // "hidden": true keeps a tab's address working but leaves it out of the bar (a lab that needs no editor)
    cfg.tabs = cfg.tabs.filter((t) => !t.hidden);
    document.title = cfg.title + " · Network Doodles lab";
    $("#lab-title").textContent = "· " + cfg.title;
    $("#home").href = cfg.guide;   // back to the lab's page on networkdoodles.com, in a new tab
    for (const t of cfg.tabs) addTab(t);
    // the terminals you had open, and any the lab opens to start with ("terminals": ["laptop"])
    const nodes = new Set((cfg.topology?.nodes || []).filter((n) => n.shell !== false).map((n) => n.id));
    for (const n of (store.get("terms", null) ?? (cfg.terminals || []).join(" ")).split(" ")) if (nodes.has(n)) openTerminal(n, false);
    const w = store.get("width");
    if (w) document.documentElement.style.setProperty("--guide", w);
    toggleGuide(store.get("guide") === "hidden");
    await refresh();
    showTask(store.get("task", "overview"));
    select(store.get("tab", cfg.tabs[0].id));

    $("#task").onchange = (e) => showTask(e.target.value);
    // the guide's pages say which task they are (the site's head.html, when embedded)
    const guideOrigin = new URL(cfg.guide, location.href).origin;
    window.addEventListener("message", (e) => {
      if (e.origin !== guideOrigin || e.source !== $("#guide-frame").contentWindow || !e.data || !e.data.ndLab) return;
      const t = String(e.data.ndLab.task || "");
      const id = tasks.includes(t) ? t : "overview";
      if (id !== $("#task").value) showTask(id, false);
    });
    $("#prev").onclick = () => step(-1);
    $("#next").onclick = () => step(1);
    $("#check").onclick = check;
    for (const a of (cfg.actions || []).filter((x) => x.bar)) $("#bar-acts").append(actionButton(a, () => $("#task").value));
    $("#answers-text").addEventListener("input", () => { $("#answers-state").textContent = "not saved yet"; });
    $("#answers-text").addEventListener("blur", saveAnswers);
    $("#answers-text").addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveAnswers(); } });
    $("#reload").onclick = reload;
    $("#toggle-guide").onclick = () => toggleGuide();
    document.addEventListener("keydown", (e) => { if (e.ctrlKey && e.key === "\\") toggleGuide(); });
    splitter();
    setInterval(refresh, 10000);
    launcher();
  }
  main().catch((e) => { document.body.textContent = "The lab app couldn't load its config: " + e; });
})();
