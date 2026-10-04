/* Shared by every page: start a session, open the last report, small toast. */
(() => {
  const KEY = "unmute_sid";
  const toast = document.getElementById("toast");
  let tId;
  window.unmuteToast = (msg) => {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(tId);
    tId = setTimeout(() => toast.classList.remove("show"), 3200);
  };
  const store = {
    get() {
      try {
        return localStorage.getItem(KEY);
      } catch (e) {
        return null;
      }
    },
    set(v) {
      try {
        localStorage.setItem(KEY, v);
      } catch (e) {}
    },
  };

  async function startSession(btn) {
    const err = document.getElementById("err");
    if (err) err.hidden = true;
    const all = document.querySelectorAll("[data-start]");
    all.forEach((b) => (b.disabled = true));
    try {
      const r = await fetch(`${API_URL}/api/session/start`, { method: "POST" });
      let d = {};
      try {
        d = await r.json();
      } catch (e) {}
      if (!r.ok) throw new Error(d.message || "Could not start a session.");
      store.set(d.session_id);
      location.href = `chat.html?sid=${encodeURIComponent(d.session_id)}`;
    } catch (e) {
      all.forEach((b) => (b.disabled = false));
      const msg =
        e.name === "TypeError"
          ? "Could not reach the server. Is the backend running?"
          : e.message + " Please try again.";
      if (err) {
        err.textContent = msg;
        err.hidden = false;
      } else window.unmuteToast(msg);
    }
  }
  document.querySelectorAll("[data-start]").forEach((b) => b.addEventListener("click", () => startSession(b)));

  document.querySelectorAll("[data-report]").forEach((a) =>
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      const sid = store.get();
      if (!sid)
        return window.unmuteToast(
          "No report yet. Start a session first, and your report will appear here."
        );
      try {
        const r = await fetch(`${API_URL}/api/session/${encodeURIComponent(sid)}`);
        if (r.status === 404) {
          try {
            localStorage.removeItem(KEY);
          } catch (x) {}
          return window.unmuteToast(
            "That report was not found. Start a new session to get one."
          );
        }
        const d = await r.json();
        location.href =
          d.status === "active"
            ? `chat.html?sid=${encodeURIComponent(sid)}`
            : `report.html?sid=${encodeURIComponent(sid)}`;
      } catch (x) {
        window.unmuteToast("Could not open the report. Please try again.");
      }
    })
  );
})();
