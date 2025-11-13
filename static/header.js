function renderHeader() {
  const host = document.getElementById("site-header");
  if (!host) return;

  host.innerHTML = `
    <div class="topbar">
      <div class="topbar-inner">
        <div class="brand"><span class="logo"></span><a href="/" class="brand-link">DayStore</a></div>

        <nav class="topnav">
          <a href="/" data-nav="catalog">Browse</a>
          <a href="/user.html" data-nav="user">Account</a>
          <a href="/cart.html" data-nav="cart">Cart <span data-cart-count class="mono" style="margin-left:6px;background:rgba(255,255,255,.06);padding:2px 8px;border-radius:999px">0</span></a>
        </nav>
        <div class="status"><span class="dot"></span><span data-auth-status>anonymous</span></div>
      </div>
    </div>
  `;

  const map = {
    "/": "catalog",
    "/index.html": "catalog",
    "/product.html": "catalog",
    "/user.html": "user",
    "/cart.html": "cart",
  };
  const active = map[(location.pathname||"/").toLowerCase()] || "catalog";
  host.querySelectorAll(".topnav a").forEach(a=>{
    a.classList.toggle("active", a.dataset.nav===active);
  });
}
document.addEventListener("DOMContentLoaded", renderHeader);
