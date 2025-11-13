(function () {

  const out = (msg) => {
    const el = document.getElementById("output");
    el.textContent = (typeof msg === "string") ? msg : JSON.stringify(msg, null, 2);
  };


  function getAuthToken() { return localStorage.getItem("AUTH") || ""; }
  function setAuthToken(token) {
    if (token) localStorage.setItem("AUTH", token);
    else localStorage.removeItem("AUTH");
    reflectAuthStatus();
    updateControlsState();
  }
  function makeBasic(u, p) { return "Basic " + btoa(`${u}:${p}`); }

  function reflectAuthStatus() {
    const span = document.getElementById("authStatus");
    const tok = getAuthToken();
    if (!span) return;
    if (!tok) { span.textContent = "anonymous"; span.style.color = "#ffd166"; }
    else { span.textContent = "authorized"; span.style.color = "#06d6a0"; }
  }

  function updateControlsState() {
    const authed = !!getAuthToken();
    const btnWho = document.getElementById("btnWhoAmI");
    const btnHist = document.getElementById("btnHistory");
    const actions = document.querySelectorAll("button.action");

    if (btnWho) btnWho.disabled = !authed;
    if (btnHist) btnHist.disabled = !authed;

    actions.forEach(b => {
      const act = b.dataset.act;
      b.disabled = (act !== "view" && !authed);
    });
  }


  async function fetchJSON(url, opts = {}) {
    opts.headers = opts.headers || {};
    const auth = getAuthToken();
    if (auth && !opts.headers["Authorization"]) {
      opts.headers["Authorization"] = auth;
    }
    const r = await fetch(url, opts);
    if (!r.ok) {
      const txt = await r.text();
      if (r.status === 401 || r.status === 403) {
        throw new Error("Unauthorized: введите логин и пароль (Basic)");
      }
      throw new Error(`HTTP ${r.status}: ${txt}`);
    }
    const ct = r.headers.get("content-type") || "";
    return ct.includes("application/json") ? r.json() : r.text();
  }

  async function loadProducts() {
    try {
      const useCache = getAuthToken() ? "false" : "true";
      const data = await fetchJSON(`/api/v1/products?use_cache=${useCache}`);
      renderProducts(data.items || []);
      updateControlsState();
    } catch (e) {
      out(e.message);
    }
  }

  function renderProducts(items) {
    const wrap = document.getElementById("products");
    if (!wrap) return;
    wrap.innerHTML = "";
    items.forEach(p => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${p.brand || "?"} — ${p.model || "?"}</h3>
        <div class="mono">id: ${p.id}</div>
        <div>Категория: <b>${p.category || "-"}</b></div>
        <div>Цена: <b>${p.price ?? "-"}</b></div>
        <div class="actions">
          <button class="action" data-act="view" data-id="${p.id}">Открыть</button>
          <button class="action" data-act="like" data-id="${p.id}">Like</button>
          <button class="action" data-act="unlike" data-id="${p.id}">Unlike</button>
          <button class="action" data-act="buy" data-id="${p.id}">Buy</button>
        </div>
      `;
      wrap.appendChild(card);
    });
  }

  async function onAction(e) {
    const btn = e.target.closest("button.action");
    if (!btn) return;
    const act = btn.dataset.act;
    const pid = btn.dataset.id;

    if ((act === "like" || act === "unlike" || act === "buy") && !getAuthToken()) {
      out("Unauthorized: сначала войдите (Basic)");
      return;
    }

    try {
      if (act === "view") {
        const data = await fetchJSON(`/api/v1/products/${pid}`);
        out(data);
      } else if (act === "like") {
        const data = await fetchJSON(`/api/v1/products/${pid}/like`, { method: "POST" });
        out(data);
      } else if (act === "unlike") {
        const data = await fetchJSON(`/api/v1/products/${pid}/like`, { method: "DELETE" });
        out(data);
      } else if (act === "buy") {
        const data = await fetchJSON(`/api/v1/products/${pid}/buy`, { method: "POST" });
        out(data);
      }
    } catch (err) {
      out(err.message);
    }
  }

  async function onSearch() {
    const inp = document.getElementById("searchInput");
    const q = inp ? inp.value.trim() : "";
    try {
      const data = await fetchJSON(`/api/v1/search?q=${encodeURIComponent(q)}`);
      renderProducts(data.items || []);
      out({ search: q, count: data.count });
      updateControlsState();
    } catch (e) {
      out(e.message);
    }
  }


  async function onRegister() {
    const u = document.getElementById("authUser")?.value.trim();
    const p = document.getElementById("authPass")?.value;
    if (!u || !p) return out("Введите username и password для регистрации");
    try {
      const res = await fetchJSON(`/api/v1/users/registration`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p, passwordConfirmation: p })
      });
      out(res);
    } catch (e) {
      out(e.message);
    }
  }

  async function onLogin() {
    const u = document.getElementById("authUser")?.value.trim();
    const p = document.getElementById("authPass")?.value;
    if (!u || !p) return out("Введите username и password для логина");
    const token = makeBasic(u, p);
    try {
      const r = await fetch(`/api/v1/users/me/username`, { headers: { "Authorization": token } });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(`Login failed: HTTP ${r.status}: ${txt}`);
      }
      const txt = await r.text();
      setAuthToken(token);
      out({ login: "ok", whoami: txt.trim() });
      await loadProducts();
    } catch (e) {
      setAuthToken("");
      out(e.message);
    }
  }

  function onLogout() {
    setAuthToken("");
    out("logged out");
    updateControlsState();
  }

  async function whoAmI() {
    if (!getAuthToken()) { out("Unauthorized: войдите (Basic)"); return; }
    try {
      const data = await fetchJSON(`/api/v1/users/me/username`);
      out(data);
    } catch (e) {
      out(e.message);
    }
  }

  async function myHistory() {
    if (!getAuthToken()) { out("Unauthorized: войдите (Basic)"); return; }
    try {
      const data = await fetchJSON(`/api/v1/users/me/history?all=true`);
      out(data);
    } catch (e) {
      out(e.message);
    }
  }


  document.addEventListener("DOMContentLoaded", () => {

    document.addEventListener("click", onAction);

    document.getElementById("btnSearch")?.addEventListener("click", onSearch);
    document.getElementById("btnRegister")?.addEventListener("click", onRegister);
    document.getElementById("btnLogin")?.addEventListener("click", onLogin);
    document.getElementById("btnLogout")?.addEventListener("click", onLogout);
    document.getElementById("btnWhoAmI")?.addEventListener("click", whoAmI);
    document.getElementById("btnHistory")?.addEventListener("click", myHistory);

    reflectAuthStatus();
    loadProducts().finally(updateControlsState);
  });

})();
