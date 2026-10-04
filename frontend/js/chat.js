(() => {
  const params = new URLSearchParams(window.location.search);
  const sid = params.get("sid");
  if (!sid) {
    location.href = "index.html";
    return;
  }

  const root = document.getElementById("chat-root");
  root.dataset.sid = sid;
  const total = Number(root.dataset.total) || 300;
  const $ = (id) => document.getElementById(id);
  const box = $("messages"),
    form = $("form"),
    input = $("input"),
    send = $("send"),
    timer = $("timer"),
    bar = $("bar"),
    helplines = $("helplines"),
    helpBtn = $("help"),
    status = $("status"),
    endBtn = $("end"),
    chips = $("chips"),
    dlg = $("endDialog");
  const OPEN_CHIPS = [
    "I am feeling stressed",
    "I am worried about my case",
    "I cannot sleep properly",
    "I feel scared or alone",
    "I am doing okay today",
  ];
  const LEAF = document.querySelector(".avatar").innerHTML;
  let deadline = 0,
    ended = false,
    busy = false;
  try {
    localStorage.setItem("unmute_sid", sid);
  } catch (e) {}

  const fmt = (s) => Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  const isHigh = (r) => r === "HIGH_CONCERN" || r === "CRISIS";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const down = () =>
    box.scrollTo({ top: box.scrollHeight, behavior: reduce ? "auto" : "smooth" });

  function add(role, text, animate = true) {
    const row = document.createElement("div");
    row.className =
      "row " + (role === "user" ? "user" : "bot") + (animate ? " pop" : "");
    if (role !== "user") {
      const a = document.createElement("span");
      a.className = "avatar";
      a.innerHTML = LEAF;
      row.appendChild(a);
    }
    const b = document.createElement("div");
    b.className = "bubble";
    b.textContent = text;
    row.appendChild(b);
    box.appendChild(row);
    down();
    return row;
  }
  function typing() {
    const row = document.createElement("div");
    row.className = "row bot typing";
    row.innerHTML =
      '<span class="avatar">' +
      LEAF +
      '</span><div class="bubble" aria-label="Unmute is typing"><i></i><i></i><i></i></div>';
    box.appendChild(row);
    down();
    return row;
  }
  function setChips(list) {
    chips.innerHTML = "";
    (list || []).forEach((t) => {
      const c = document.createElement("button");
      c.type = "button";
      c.className = "chip";
      c.textContent = t;
      c.addEventListener("click", () => submit(t));
      chips.appendChild(c);
    });
  }
  function setRemaining(s) {
    deadline = Date.now() + s * 1000;
    tick();
  }
  function tick() {
    const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    timer.textContent = fmt(left);
    bar.style.width = Math.min(100, (left / total) * 100) + "%";
    if (left <= 0 && !ended) finish();
  }
  async function api(path, opts = {}) {
    const r = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    let data = {};
    try {
      data = await r.json();
    } catch (e) {}
    return { ok: r.ok, status: r.status, data };
  }
  function lock() {
    input.disabled = true;
    send.disabled = true;
    endBtn.disabled = true;
    chips.innerHTML = "";
  }
  function showHelp(open) {
    helplines.hidden = !open;
    helpBtn.setAttribute("aria-expanded", String(open));
  }
  async function finish() {
    if (ended) return;
    ended = true;
    lock();
    status.textContent = "Session complete. Preparing your reflection...";
    try {
      await api("/api/session/end", {
        method: "POST",
        body: JSON.stringify({ session_id: sid }),
      });
    } catch (e) {}
    location.href = `report.html?sid=${encodeURIComponent(sid)}`;
  }
  async function submit(text) {
    text = (text || "").trim();
    if (!text || ended || busy) return;
    busy = true;
    setChips([]);
    add("user", text);
    input.value = "";
    autosize();
    send.disabled = true;
    status.textContent = "";
    const t = typing();
    let res;
    try {
      [res] = await Promise.all([
        api("/api/chat", {
          method: "POST",
          body: JSON.stringify({ session_id: sid, message: text }),
        }),
        new Promise((r) => setTimeout(r, reduce ? 0 : 700)),
      ]);
    } catch (e) {
      t.remove();
      busy = false;
      send.disabled = false;
      status.textContent =
        "Could not reach the server. Please check your connection and try again.";
      return;
    }
    t.remove();
    busy = false;
    send.disabled = false;
    if (res.status === 410 || res.status === 409) return finish();
    if (!res.ok) {
      status.textContent =
        res.data.message || "Something went wrong. Please try again.";
      return;
    }
    add("assistant", res.data.reply);
    setChips(res.data.suggestions);
    requestAnimationFrame(down);
    if (res.data.emergency) showHelp(true);
    setRemaining(res.data.remaining_seconds);
    input.focus();
  }
  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submit(input.value);
  });
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input.value);
    }
  });
  helpBtn.addEventListener("click", () => showHelp(helplines.hidden));
  endBtn.addEventListener("click", () => dlg.showModal());
  $("keep").addEventListener("click", () => dlg.close());
  $("confirmEnd").addEventListener("click", () => {
    dlg.close();
    finish();
  });

  (async () => {
    let res;
    try {
      res = await api("/api/session/" + encodeURIComponent(sid));
    } catch (e) {
      status.textContent = "Could not reach the server.";
      return;
    }
    if (!res.ok) {
      location.href = "index.html";
      return;
    }
    if (res.data.status !== "active") {
      location.href = `report.html?sid=${encodeURIComponent(sid)}`;
      return;
    }
    res.data.messages.forEach((m) => add(m.role, m.message, false));
    if (isHigh(res.data.risk_level)) showHelp(true);
    if (res.data.messages.filter((m) => m.role === "user").length === 0) {
      setChips(OPEN_CHIPS);
      requestAnimationFrame(down);
    }
    setRemaining(res.data.remaining_seconds);
    setInterval(tick, 500);
    input.focus();
  })();
})();
