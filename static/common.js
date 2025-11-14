const LS_AUTH = "AUTH";

export function getAuthToken() {
  return localStorage.getItem(LS_AUTH) || "";
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(LS_AUTH, token);
  } else {
    localStorage.removeItem(LS_AUTH);
  }
  reflectAuthStatus();
}

export function makeBasic(u, p) {
  return "Basic " + btoa(`${u}:${p}`);
}

export function reflectAuthStatus() {
  const s = document.querySelector("[data-auth-status]");
  if (s) {
    const tok = getAuthToken();
    s.textContent = tok ? "authorized" : "anonymous";
    const dot = document.querySelector(".status .dot");
    if (dot) dot.style.background = tok ? "var(--success)" : "#ffd166";
  }
  document
    .querySelectorAll("[data-cart-count]")
    .forEach((e) => (e.textContent = String(cartCount())));
}

function attachAuth(opts = {}) {
  const headers = opts.headers || {};
  const tok = getAuthToken();
  if (tok && !headers["Authorization"]) {
    headers["Authorization"] = tok;
  }
  return { ...opts, headers };
}

export async function fetchJSON(url, opts = {}) {
  const r = await fetch(url, attachAuth(opts));
  if (!r.ok) {
    const txt = await r.text();
    if (r.status === 401 || r.status === 403) {
      setAuthToken("");
      throw new Error("Unauthorized: go to Account and log in.");
    }
    throw new Error(`HTTP ${r.status}: ${txt}`);
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("application/json") ? r.json() : r.text();
}

export function out(msg, id = "output") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent =
    typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
}

const LS_CART = "CART_V1";

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(LS_CART) || "[]");
  } catch {
    return [];
  }
}

function writeCart(items) {
  localStorage.setItem(LS_CART, JSON.stringify(items));
  reflectAuthStatus();
}

export function cartList() {
  return readCart();
}

export function cartCount() {
  return readCart().length;
}

export function cartAdd(item) {
  const xs = readCart();
  if (!xs.find((x) => x.id === item.id)) {
    xs.push(item);
    writeCart(xs);
  }
}

export function cartRemove(id) {
  writeCart(readCart().filter((x) => x.id !== id));
}

export function cartClear() {
  writeCart([]);
}

document.addEventListener("DOMContentLoaded", reflectAuthStatus);

