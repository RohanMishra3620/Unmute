(() => {
  const params = new URLSearchParams(window.location.search);
  const sid = params.get("sid");
  if (!sid) {
    location.href = "index.html";
    return;
  }

  try {
    localStorage.setItem("unmute_sid", sid);
  } catch (e) {}

  const RISK_LABELS = {
    SAFE: "No safety concerns noticed",
    LOW_CONCERN: "Some everyday stress noticed",
    MODERATE_CONCERN: "Please look after yourself",
    HIGH_CONCERN: "Please reach out for help",
    CRISIS: "Please reach out for help now",
  };

  const main = document.getElementById("main");
  const loading = document.getElementById("report-loading");
  const errorEl = document.getElementById("report-error");

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function section(title, extraClass) {
    const s = el("section", "panel" + (extraClass ? " " + extraClass : ""));
    const h = el("h2");
    h.appendChild(el("span", "dot"));
    h.appendChild(document.createTextNode(title));
    s.appendChild(h);
    return s;
  }

  function listItems(items, ordered) {
    const ul = el(ordered ? "ol" : "ul", ordered ? "steps" : "list");
    items.forEach((item) => {
      const li = el("li");
      if (ordered) {
        const span = el("span", null, item);
        li.appendChild(span);
      } else {
        li.textContent = item;
      }
      ul.appendChild(li);
    });
    return ul;
  }

  function render(r) {
    main.innerHTML = "";
    const high = r.risk_level === "HIGH_CONCERN" || r.risk_level === "CRISIS";

    const h1 = el("h1", null, "Your Reflection");
    const meta = el(
      "p",
      "meta",
      "Session length: " +
        (r.session_duration || "") +
        " · Only you can see this page"
    );
    main.appendChild(h1);
    main.appendChild(meta);

    if (high && r.emergency) {
      const alert = el("div", "panel alert");
      alert.setAttribute("role", "alert");
      alert.appendChild(el("h2", null, "You do not have to handle this alone"));
      if (r.emergency.message) alert.appendChild(el("p", null, r.emergency.message));
      if (r.emergency.contacts && r.emergency.contacts.length) {
        const ul = el("ul", "list");
        r.emergency.contacts.forEach((c) => {
          const li = el("li");
          li.appendChild(document.createTextNode(c.label + ": "));
          const a = el("a");
          a.href = "tel:" + String(c.number).replace(/\s+/g, "");
          const strong = el("strong", null, c.number);
          a.appendChild(strong);
          li.appendChild(a);
          ul.appendChild(li);
        });
        alert.appendChild(ul);
      }
      main.appendChild(alert);
    }

    if (r.summary) {
      const s = section("In simple words");
      s.appendChild(el("p", "summary", r.summary));
      main.appendChild(s);
    }

    const grid1 = el("div", "grid2");
    if (r.overall_state) {
      const s = section("How you seemed to feel");
      s.appendChild(el("p", "state", r.overall_state));
      grid1.appendChild(s);
    }
    {
      const s = section("Safety check", "leaf");
      const p = el("p");
      let riskCls = "";
      if (high) riskCls = "high";
      else if (r.risk_level === "MODERATE_CONCERN") riskCls = "mid";
      const label =
        RISK_LABELS[r.risk_level] ||
        String(r.risk_level || "").replace(/_/g, " ");
      p.appendChild(el("span", "risk " + riskCls, label));
      s.appendChild(p);
      grid1.appendChild(s);
    }
    main.appendChild(grid1);

    if (r.emotion_scores && Object.keys(r.emotion_scores).length) {
      const s = section("Feelings I noticed");
      const ul = el("ul", "bars");
      Object.entries(r.emotion_scores).forEach(([emotion, score]) => {
        const li = el("li");
        const top = el("div", "top");
        top.appendChild(el("span", null, emotion));
        top.appendChild(el("span", null, score + " out of 10"));
        li.appendChild(top);
        const track = el("div", "track");
        const i = el("i");
        i.style.width = Math.min(100, Number(score) * 10) + "%";
        track.appendChild(i);
        li.appendChild(track);
        ul.appendChild(li);
      });
      s.appendChild(ul);
      main.appendChild(s);
    }

    const groups = [
      ["What was on your mind", r.main_topics],
      ["Good things I noticed", r.positive_signals],
      ["Things to keep an eye on", r.concerns],
    ];
    const grid2 = el("div", "grid2");
    let anyGroup = false;
    groups.forEach(([title, items]) => {
      if (items && items.length) {
        anyGroup = true;
        const s = section(title, "leaf");
        s.appendChild(listItems(items, false));
        grid2.appendChild(s);
      }
    });
    if (anyGroup) main.appendChild(grid2);

    if (r.suggested_next_steps && r.suggested_next_steps.length) {
      const s = section("Small steps you can try");
      s.appendChild(listItems(r.suggested_next_steps, true));
      main.appendChild(s);
    }

    if (r.disclaimer) {
      main.appendChild(el("p", "disclaimer", r.disclaimer));
    }

    const actions = el("div", "actions");
    const newLink = el("a", "btn primary", "Start a new session");
    newLink.href = "index.html";
    newLink.style.fontSize = "1rem";
    newLink.style.padding = "14px 28px";
    actions.appendChild(newLink);
    const delBtn = el("button", "btn danger-ghost", "Delete this session");
    delBtn.id = "del";
    delBtn.type = "button";
    actions.appendChild(delBtn);
    main.appendChild(actions);

    // Dialog already in HTML
    const dlg = document.getElementById("delDialog");
    delBtn.addEventListener("click", () => dlg.showModal());
    document.getElementById("delNo").addEventListener("click", () => dlg.close());
    document.getElementById("delYes").addEventListener("click", async () => {
      try {
        const r = await fetch(
          `${API_URL}/api/session/${encodeURIComponent(sid)}`,
          { method: "DELETE" }
        );
        if (r.ok || r.status === 404) {
          try {
            localStorage.removeItem("unmute_sid");
          } catch (e) {}
          location.href = "index.html";
        }
      } catch (e) {
        window.unmuteToast &&
          window.unmuteToast("Could not delete the session. Please try again.");
      }
    });
  }

  (async () => {
    try {
      const r = await fetch(
        `${API_URL}/api/session/${encodeURIComponent(sid)}/report`
      );
      let data = {};
      try {
        data = await r.json();
      } catch (e) {}
      if (r.status === 409 && data.error === "session_active") {
        location.href = `chat.html?sid=${encodeURIComponent(sid)}`;
        return;
      }
      if (!r.ok) {
        if (loading) loading.hidden = true;
        if (errorEl) {
          errorEl.hidden = false;
          errorEl.textContent =
            data.message ||
            "That session was not found or was deleted.";
        }
        setTimeout(() => {
          location.href = "index.html";
        }, 2500);
        return;
      }
      if (loading) loading.hidden = true;
      render(data);
    } catch (e) {
      if (loading) loading.hidden = true;
      if (errorEl) {
        errorEl.hidden = false;
        errorEl.textContent =
          "Could not reach the server. Please check your connection.";
      }
    }
  })();
})();
