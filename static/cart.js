import { cartList, cartRemove, cartClear, reflectAuthStatus, fetchJSON, getAuthToken, out } from "./common.js";

function render(){
  reflectAuthStatus();
  const items = cartList();
  const wrap = document.getElementById("cartList");
  if(!wrap) return;
  if(!items.length){ wrap.innerHTML = `<div class="muted">Your cart is empty</div>`; return; }
  wrap.innerHTML = `
    <table class="table">
      <thead><tr><th>Item</th><th>Price</th><th></th></tr></thead>
      <tbody>
        ${items.map(it=>`
          <tr>
            <td>${it.brand||"?"} — ${it.model||"?"}<div class="mono">id: ${it.id}</div></td>
            <td>${it.price ?? "-"}</td>
            <td><button class="btn ghost rm" data-id="${it.id}">Remove</button></td>
          </tr>`).join("")}
      </tbody>
    </table>
  `;
}

async function checkout(){
  const items = cartList(); if(!items.length) return out("Cart is empty");
  if(!getAuthToken()) return out("Login required (Account page)");
  let ok=0, fail=0;
  for(const it of items){
    try{ await fetchJSON(`/api/v1/products/${it.id}/buy`, {method:"POST"}); ok++; }
    catch(e){ fail++; out(`Error ${it.id}: ${e.message}`); }
  }
  out(`Purchased: ${ok}, errors: ${fail}`);
  render();
}

document.addEventListener("click", e=>{
  const rm = e.target.closest("button.rm"); if(rm){ cartRemove(rm.dataset.id); render(); }
});
document.addEventListener("DOMContentLoaded", ()=>{
  render();
  document.getElementById("btnCheckout").addEventListener("click", checkout);
  document.getElementById("btnClear").addEventListener("click", ()=>{ cartClear(); render(); });
});
