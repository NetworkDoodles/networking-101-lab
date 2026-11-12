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

  async function check() {
    const id = $("#task").value, btn = $("#check"), out = $("#check-out");
    btn.disabled = true;
    btn.querySelector("span").textContent = "Checking " + id + " …";
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
    for (const x of cfg.tabs) {
      document.getElementById("tab-" + x.id).setAttribute("aria-selected", x === t);
      pane(x).classList.toggle("on", x === t);
    }
    $("#popout").href = t.path;
    load(t);
  }
  function reload() {
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
      document.querySelector("#tab-" + t.id + " .dot").classList.toggle("up", !!status.services[t.id]);
      // a service that stopped (make wireshark-stop) goes back to its start button
      if (t.start && !status.services[t.id] && pane(t).querySelector("iframe")) idle(t);
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
    el.hidden = false;
    let text, cls, title;
    if (!n.docker) {
      [text, cls] = ["setting up the lab …", "wait"];
      title = "Docker is starting and the lab's images are on their way. The VS Code tab's terminal shows the details.";
    } else if (n.running >= n.total) {
      [text, cls, title] = ["network up", "up", n.running + " nodes running"];
    } else {
      [text, cls] = ["network " + n.running + "/" + n.total, "wait"];
      title = n.running ? "Nodes are starting: the network is up when all " + n.total + " are running."
        : "The network isn't running yet. It starts by itself after the first setup; make up starts it by hand.";
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
    document.title = cfg.title + " · Network Doodles lab";
    $("#lab-title").textContent = "· " + cfg.title;
    for (const t of cfg.tabs) {
      const b = document.createElement("button");
      b.className = "tab";
      b.id = "tab-" + t.id;
      b.setAttribute("role", "tab");
      b.innerHTML = "<span class='dot'></span><span></span>";
      b.lastChild.textContent = t.name;
      b.onclick = () => select(t.id);
      $("#tabs").append(b);
      const p = document.createElement("div");
      p.className = "pane";
      p.id = "pane-" + t.id;
      $("#panes").append(p);
    }
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
    $("#reload").onclick = reload;
    $("#toggle-guide").onclick = () => toggleGuide();
    document.addEventListener("keydown", (e) => { if (e.ctrlKey && e.key === "\\") toggleGuide(); });
    splitter();
    setInterval(refresh, 10000);
    launcher();
  }
  main().catch((e) => { document.body.textContent = "The lab app couldn't load its config: " + e; });
})();
