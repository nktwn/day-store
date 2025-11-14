import { fetchJSON, out, reflectAuthStatus, getAuthToken, cartAdd } from "./common.js";

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function cardHtml(p) {
  return `
    <div class="card hover-raise product-card" data-id="${p.id}">
      <div class="card-head">
        <h3 style="margin:0;font-size:18px">
          ${escapeHtml(p.brand || "?")} — ${escapeHtml(p.model || "?")}
        </h3>
      </div>
      <div class="mono">id: ${escapeHtml(p.id || "")}</div>
      <div>Category: <b>${escapeHtml(p.category || "-")}</b></div>
      <div>Price: <b class="price">${p.price ?? "-"}</b></div>

      <div class="actions">
        <button
          class="btn ghost action"
          data-act="like"
          data-id="${p.id}"
        >
          Like
        </button>

        <button
          class="btn outline action"
          data-act="unlike"
          data-id="${p.id}"
        >
          Unlike
        </button>

        <button
          class="btn success action"
          data-act="add"
          data-id="${p.id}"
          data-brand="${escapeHtml(p.brand || "")}"
          data-model="${escapeHtml(p.model || "")}"
          data-price="${p.price ?? ""}"
        >
          Add to Cart
        </button>
      </div>
    </div>
  `;
}



function renderProducts(items) {
  const wrap = document.getElementById("products");
  if (!wrap) return;
  if (!items.length) {
    wrap.innerHTML = `<div class="muted">Каталог пуст по текущим фильтрам</div>`;
    return;
  }
  wrap.innerHTML = items.map(cardHtml).join("");
}

function selectedCategories() {
  const w = document.getElementById("catFilters");
  if (!w) return [];
  return [...w.querySelectorAll('input[type="checkbox"]')]
    .filter((i) => i.checked)
    .map((i) => i.value.trim().toUpperCase());
}


async function reloadWithFilters() {
  const q = document.getElementById("searchInput")?.value.trim() || "";
  const cats = selectedCategories();

  try {
    let items = [];

    if (!q && !cats.length) {
      const data = await fetchJSON(`/api/v1/products`);
      items = Array.isArray(data) ? data : (data.items || []);
    }
    else if (q && cats.length) {
      const data = await fetchJSON(`/api/v1/search?q=${encodeURIComponent(q)}`);
      const all = data.items || [];
      const set = new Set(cats);
      items = all.filter(p => {
        const cat = (p.category || "").toString().toUpperCase();
        return !cat || set.has(cat);
      });
    }
    else if (q && !cats.length) {
      const data = await fetchJSON(`/api/v1/search?q=${encodeURIComponent(q)}`);
      items = data.items || [];
    }
    else if (!q && cats.length) {
      const csv = cats.join(",");
      const data = await fetchJSON(`/api/v1/products/by-category?category=${encodeURIComponent(csv)}`);
      items = data.items || [];
    }

    renderProducts(items);
    out({ search: q || null, categories: cats, count: items.length });

    await maybeLoadRecommendations();
  } catch (e) {
    out(e.message);
  }
}

async function maybeLoadRecommendations() {
  const list = document.getElementById("recoList");
  const hint = document.getElementById("recoHint");
  if (!list || !hint) return;

  list.innerHTML = `<div class="muted mono">Loading...</div>`;

  if (!getAuthToken()) {
    list.innerHTML = `<div class="muted">🔒 Нет данных для рекомендаций</div>`;
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
      hint.textContent = "Пока недостаточно действий для рекомендаций";
      list.innerHTML = `<div class="muted">Просматривайте и лайкайте товары, чтобы получить рекомендации</div>`;
      return;
    }

    list.innerHTML = items
      .map(
        (p) => `
        <div class="card fade-in">
          <div class="card-head">
            <div>
              <h4 style="margin:0">${escapeHtml(p.brand || "?")} — ${escapeHtml(p.model || "?")}</h4>
              <div class="mono" style="font-size:11px;margin-top:2px;">
                id: ${escapeHtml(p.id || "").slice(0,8)}...
              </div>
            </div>
            <a class="btn ghost" href="/product.html?id=${encodeURIComponent(p.id)}" style="padding:6px 10px;font-size:12px;">Open</a>
          </div>
          <div class="muted" style="font-size:12px;margin-top:4px;">
            Категория: <b>${escapeHtml(p.category || "-")}</b> · Цена: <b>${p.price ?? "-"}</b>
          </div>
        </div>`
      )
      .join("");

  } catch (e) {
    console.error("RECO ERROR:", e);
    hint.textContent = "Ошибка загрузки рекомендаций";
    list.innerHTML = `<div class="muted">Не удалось загрузить рекомендации</div>`;
  }
}

document.addEventListener("click", async (e) => {
  const btn = e.target.closest("button.action");
  if (!btn) return;
  const act = btn.dataset.act;
  const pid = btn.dataset.id;

  try {
    if (act === "like") {
      const data = await fetchJSON(`/api/v1/products/${pid}/like`, { method: "POST" });
      out(data);
    } else if (act === "unlike") {
      const data = await fetchJSON(`/api/v1/products/${pid}/like`, { method: "DELETE" });
      out(typeof data === "string" ? data : "unliked (204)");
    } else if (act === "add") {
      const brand = btn.dataset.brand || "";
      const model = btn.dataset.model || "";
      const priceRaw = btn.dataset.price || "";
      const price = priceRaw === "" ? null : Number(priceRaw);
      cartAdd({ id: pid, brand, model, price });
      out(`Added to cart: ${brand} — ${model}`);
    }
  } catch (err) {
    out(err.message);
  }
});

document.addEventListener("click", (e) => {
  if (e.target.closest("button.action")) return;

  const card = e.target.closest(".product-card");
  if (!card) return;

  const pid = card.dataset.id;
  if (!pid) return;

  window.location.href = `/product.html?id=${encodeURIComponent(pid)}`;
});


async function onSearch() {
  await reloadWithFilters();
}

async function applyCategoryFilter() {
  await reloadWithFilters();
}

function resetAllFilters() {
  const input = document.getElementById("searchInput");
  if (input) input.value = "";

  const w = document.getElementById("catFilters");
  if (w) w.querySelectorAll('input[type="checkbox"]').forEach((i) => (i.checked = false));

  reloadWithFilters().catch(console.error);
}


document.getElementById("btnSearch")?.addEventListener("click", onSearch);
document.getElementById("btnApplyCats")?.addEventListener("click", applyCategoryFilter);
document.getElementById("btnResetCats")?.addEventListener("click", resetAllFilters);

reflectAuthStatus();

reloadWithFilters().catch(console.error);
maybeLoadRecommendations().catch(console.error);
