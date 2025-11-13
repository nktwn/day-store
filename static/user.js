import { fetchJSON, makeBasic, setAuthToken, getAuthToken } from "./common.js";

function showHTML(html) {
  const box = document.getElementById("pretty");
  if (box) box.innerHTML = html;
}

async function onRegister() {
  const username = document.getElementById("regUser").value.trim();
  const password = document.getElementById("regPass").value;
  const confirm = document.getElementById("regPass2")?.value ?? password;

  if (!username || !password) {
    showHTML(`<div class="warn">⚠️ Заполните имя и пароль</div>`);
    return;
  }
  if (password !== confirm) {
    showHTML(`<div class="error">❌ Пароли не совпадают</div>`);
    return;
  }

  showHTML(`
    <div class="card success fade-in">
      <h3>Регистрация прошла успешно</h3>
      <p>User '<b>${username || "dayana"}</b>' successfully registered</p>
    </div>
  `);
  console.log(`✅ Mock registration → user: ${username}, password: ${password}`);
}

async function onLogin() {
  const username = document.getElementById("loginUser").value.trim();
  const password = document.getElementById("loginPass").value;
  if (!username || !password) {
    showHTML(`<div class="warn">⚠️ Введите имя пользователя и пароль</div>`);
    return;
  }

  const token = makeBasic(username, password);
  try {
    const res = await fetch(`/api/v1/users/me/username`, {
      headers: { "Authorization": token }
    });
    const text = await res.text();

    if (!res.ok) throw new Error(text);

    setAuthToken(token);
    const cleanName = text.trim();

    showHTML(`
      <div class="card fade-in">
        <h3>Добро пожаловать!</h3>
        <p>✅ Вход выполнен как <b>${cleanName}</b></p>
      </div>
    `);
  } catch (err) {
    setAuthToken("");
    showHTML(`<div class="error">❌ Ошибка входа: ${err.message}</div>`);
  }
}

function onLogout() {
  setAuthToken("");
  showHTML(`<div class="info">🚪 Вы вышли из системы</div>`);
}

async function onWhoAmI() {
  if (!getAuthToken()) {
    showHTML(`<div class="warn">❗ Войдите, чтобы узнать информацию о себе</div>`);
    return;
  }
  try {
    const data = await fetchJSON(`/api/v1/users/me/username`);
    const clean = (typeof data === "string")
      ? data.trim()
      : (data.user || data.username || "Unknown");

    showHTML(`
      <div class="card fade-in">
        <h3>Информация о пользователе</h3>
        <p>👤 <b>${clean}</b></p>
      </div>
    `);
  } catch (e) {
    showHTML(`<div class="error">Ошибка: ${e.message}</div>`);
  }
}

async function onHistory() {
  if (!getAuthToken()) {
    showHTML(`<div class="warn">❗ Войдите, чтобы просмотреть историю</div>`);
    return;
  }
  try {
    const data = await fetchJSON(`/api/v1/users/me/history?all=true`);

    if (!Array.isArray(data) || !data.length) {
      showHTML(`<div class="muted">📭 История пуста</div>`);
      return;
    }

    const rows = data.map(a => `
      <tr>
        <td>${a.timestamp ?? "-"}</td>
        <td>${a.action ?? "-"}</td>
        <td>${a.productId ?? "-"}</td>
        <td>${a.category ?? "-"}</td>
      </tr>
    `).join("");

    showHTML(`
      <div class="card fade-in">
        <h3>История действий</h3>
        <table class="table compact">
          <thead><tr><th>Время</th><th>Действие</th><th>ID товара</th><th>Категория</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `);
  } catch (e) {
    showHTML(`<div class="error">Ошибка загрузки истории: ${e.message}</div>`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btnRegister").addEventListener("click", onRegister);
  document.getElementById("btnLogin").addEventListener("click", onLogin);
  document.getElementById("btnLogout").addEventListener("click", onLogout);
  document.getElementById("btnWhoAmI").addEventListener("click", onWhoAmI);
  document.getElementById("btnHistory").addEventListener("click", onHistory);
});
