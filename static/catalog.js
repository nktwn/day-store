import { fetchJSON, out, reflectAuthStatus, getAuthToken } from "./common.js";

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function cardHtml(p) {
  return `
    <div class="card hover-raise">
      <div class="card-head">
        <h3 style="margin:0;font-size:18px">${escapeHtml(p.brand || "?")} — ${escapeHtml(p.model || "?")}</h3>
        <a class="btn ghost" href="/product.html?id=${encodeURIComponent(p.id)}">Open</a>
      </div>
      <div class="mono">id: ${escapeHtml(p.id || "")}</div>
      <div>Category: <b>${escapeHtml(p.category || "-")}</b></div>
      <div>Price: <b class="price">${p.price ?? "-"}</b></div>
      <div class="actions">
        <button class="btn outline action" data-act="view" data-id="${p.id}">View</button>
        <button class="btn action" data-act="like" data-id="${p.id}">Like</button>
        <button class="btn ghost action" data-act="unlike" data-id="${p.id}">Unlike</button>
        <button class="btn success action" data-act="buy" data-id="${p.id}">Buy</button>
      </div>
    </div>
  `;
}

function renderProducts(items) {
  const wrap = document.getElementById("products");
  if (!wrap) return;
  wrap.innerHTML = items.map(cardHtml).join("");
}

async function loadProducts({ useCache = false } = {}) {
  try {
    const data = await fetchJSON(`/api/v1/products?use_cache=${useCache ? "true" : "false"}`);
    renderProducts(data.items || []);
    await maybeLoadRecommendations();
  } catch (e) {
    out(e.message);
  }
}

document.addEventListener("click", async (e) => {
  const btn = e.target.closest("button.action");
  if (!btn) return;
  const act = btn.dataset.act;
  const pid = btn.dataset.id;
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
});

async function onSearch() {
  const q = document.getElementById("searchInput")?.value.trim() || "";
  try {
    const data = await fetchJSON(`/api/v1/search?q=${encodeURIComponent(q)}`);
    renderProducts(data.items || []);
    out({ search: q, count: data.count });
  } catch (e) {
    out(e.message);
  }
}

async function maybeLoadRecommendations() {
  const list = document.getElementById("recoList");
  const hint = document.getElementById("recoHint");
  const section = document.getElementById("recoSection");
  if (!list || !hint || !section) return;

  section.style.display = "";
  hint.textContent = "🔄 Загружаем персональные рекомендации...";
  list.innerHTML = `<div class="muted mono">Loading...</div>`;

  if (!getAuthToken()) {
    hint.textContent = "🔒 Войдите, чтобы получить рекомендации";
    list.innerHTML = `<div class="muted mono">Нет данных</div>`;
    return;
  }

  try {
    const data = await fetchJSON(`/api/v1/users/me/recommendation`);

    let items = [];
    if (Array.isArray(data)) items = data;
    else if (Array.isArray(data.items)) items = data.items;
    else if (Array.isArray(data.data)) items = data.data;
    else if (Array.isArray(data.recommendations)) items = data.recommendations;

    if (!items.length) {
      list.innerHTML = `<div class="muted">Пока нет персональных рекомендаций</div>`;
      hint.textContent = "Нет данных";
      section.style.display = "";
      return;
    }

    list.innerHTML = items
      .map(
        (p) => `
        <div class="card fade-in">
          <div class="card-head">
            <h4 style="margin:0">${escapeHtml(p.brand || "?")} — ${escapeHtml(p.model || "?")}</h4>
            <a class="btn ghost" href="/product.html?id=${encodeURIComponent(p.id)}">Open</a>
          </div>
          <div class="mono">id: ${escapeHtml(p.id || "")}</div>
          <div>Category: <b>${escapeHtml(p.category || "-")}</b></div>
          <div>Price: <b>${p.price ?? "-"}</b></div>
        </div>`
      )
      .join("");

    hint.textContent = "🎯 Персональные рекомендации";
    section.style.display = "";
  } catch (e) {
    console.error("RECO ERROR:", e);
    hint.textContent = "⚠️ Ошибка загрузки рекомендаций";
    list.innerHTML = `<div class="muted">Не удалось загрузить</div>`;
    section.style.display = "";
  }
}

function selectedCategories() {
  const w = document.getElementById("catFilters");
  if (!w) return [];
  return [...w.querySelectorAll('input[type="checkbox"]')]
    .filter((i) => i.checked)
    .map((i) => i.value.trim().toUpperCase());
}

async function applyCategoryFilter() {
  const cats = selectedCategories();
  if (!cats.length) {
    await loadProducts({ useCache: false });
    return;
  }
  const csv = cats.join(",");
  try {
    const data = await fetchJSON(`/api/v1/products/by-category?category=${encodeURIComponent(csv)}`);
    renderProducts(data.items || []);
    out({ filter: cats, count: data.count });
  } catch (e) {
    out(e.message);
  }
}

function resetCategoryFilter() {
  const w = document.getElementById("catFilters");
  if (w) w.querySelectorAll('input[type="checkbox"]').forEach((i) => (i.checked = false));
  loadProducts({ useCache: false }).catch(console.error);
}

document.getElementById("btnSearch")?.addEventListener("click", onSearch);
document.getElementById("btnApplyCats")?.addEventListener("click", applyCategoryFilter);
document.getElementById("btnResetCats")?.addEventListener("click", resetCategoryFilter);

reflectAuthStatus();
loadProducts({ useCache: false }).catch(console.error);

