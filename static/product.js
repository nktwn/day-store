import { fetchJSON, out, getAuthToken, cartAdd } from "./common.js";

function isLoggedIn(){ return !!getAuthToken(); }
function getId(){ return new URL(location.href).searchParams.get("id") || ""; }

function skeleton(id){
  const box = document.getElementById("productBox");
  box.innerHTML = `
    <div class="big card">
      <div class="card-head">
        <h2 id="pTitle" style="margin:0">Loading…</h2>
        <div class="mono">id: ${id}</div>
      </div>
      <div id="pInfo" class="kv" style="margin-top:10px">
        <div><span>Category</span><b>—</b></div>
        <div><span>Price</span><b>—</b></div>
        <div><span>Status</span><b id="pStatus" class="muted">Waiting server…</b></div>
      </div>
      <div class="actions" style="margin-top:14px">
        <button class="btn" data-act="view">View</button>
        <button class="btn ${isLoggedIn()?"":"ghost"} need-auth" data-act="like">Like</button>
        <button class="btn ghost need-auth" data-act="unlike">Unlike</button>
        <button class="btn outline" data-act="cart" data-brand="" data-model="" data-price="">Add to Cart</button>
        <button class="btn success need-auth" data-act="buy">Buy</button>
      </div>
    </div>
  `;
  reflectAuth();
}
function reflectAuth(){
  document.querySelectorAll(".need-auth").forEach(b=>{
    if(isLoggedIn()){ b.removeAttribute("disabled"); b.classList.remove("ghost"); }
    else { b.setAttribute("disabled","disabled"); b.classList.add("ghost"); }
  });
}

function hydrate(p){
  document.getElementById("pTitle").textContent = `${p.brand||"?"} — ${p.model||"?"}`;
  document.getElementById("pInfo").innerHTML = `
    <div><span>Category</span><b>${p.category || "-"}</b></div>
    <div><span>Price</span><b>${p.price ?? "-"}</b></div>
    <div><span>Status</span><b class="muted">Ready</b></div>
  `;
  const btnCart = document.querySelector('button[data-act="cart"]');
  if(btnCart){ btnCart.dataset.brand = p.brand||""; btnCart.dataset.model = p.model||""; btnCart.dataset.price = p.price ?? ""; }
}
function notFound(){
  document.getElementById("pTitle").textContent = "Product not found";
  const s = document.getElementById("pStatus"); if(s) s.textContent="Check product id";
}

async function load(){
  const id = getId(); if(!id){ out("No product id specified"); return; }
  skeleton(id);
  try{ const data = await fetchJSON(`/api/v1/java/products/${encodeURIComponent(id)}`); hydrate(data); }
  catch(e){ notFound(); out(e.message); }
}

document.addEventListener("click", async (e)=>{
  const btn = e.target.closest("button.btn"); if(!btn) return;
  const act = btn.dataset.act; const id = getId();
  try{
    if(act==="view"){
      const data = await fetchJSON(`/api/v1/java/products/${id}`); out(data);
    }else if(act==="like"){
      if(!isLoggedIn()) return out("Login required");
      const data = await fetchJSON(`/api/v1/java/products/${id}/like`, {method:"POST"}); out(data);
    }else if(act==="unlike"){
      if(!isLoggedIn()) return out("Login required");
      const res = await fetchJSON(`/api/v1/java/products/${id}/like`, {method:"DELETE"});
      out(typeof res==="string"?res:"unliked (204)");
    }else if(act==="cart"){
      cartAdd({id, brand:btn.dataset.brand||"", model:btn.dataset.model||"", price: btn.dataset.price?Number(btn.dataset.price):null});
      out("Added to cart");
    }else if(act==="buy"){
      if(!isLoggedIn()) return out("Login required");
      const data = await fetchJSON(`/api/v1/java/products/${id}/buy`, {method:"POST"}); out(data);
    }
  }catch(err){ out(err.message); }
});

window.addEventListener("storage", ev=>{ if(ev.key==="AUTH"){ reflectAuth(); } });

document.addEventListener("DOMContentLoaded", load);
