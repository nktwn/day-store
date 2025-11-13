import { fetchJSON, makeBasic, setAuthToken, getAuthToken } from "./common.js";

function showHTML(html) {
  const box = document.getElementById("pretty");
  if (box) box.innerHTML = html;
}

function formatAction(action) {
  switch (action) {
    case "VIEW":
      return "Просмотр";
    case "LIKE":
      return "Лайк";
    case "PURCHASE":
      return "Покупка";
    default:
      return action || "-";
  }
}


async function onRegister() {
  const username = document.getElementById("regUser").value.trim();
  const password = document.getElementById("regPass").value;
  const confirm = document.getElementById("regPass2")?.value ?? password;

  // Валидация на клиенте
  if (!username || !password) {
    showHTML(`<div class="warn">⚠️ Заполните имя и пароль</div>`);
    return;
  }

  if (username.length < 3) {
    showHTML(`<div class="warn">⚠️ Имя пользователя должно быть не менее 3 символов</div>`);
    return;
  }

  if (password.length < 6) {
    showHTML(`<div class="warn">⚠️ Пароль должен быть не менее 6 символов</div>`);
    return;
  }

  if (password !== confirm) {
    showHTML(`<div class="error">❌ Пароли не совпадают</div>`);
    return;
  }

  try {
    // Отправка запроса на регистрацию
    const response = await fetch(`/api/v1/users/registration`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: username,
        password: password,
        passwordConfirmation: confirm
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMsg = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorMsg = errorJson.detail || errorText;
      } catch (e) {
        // Если не JSON, используем текст как есть
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();

    showHTML(`
      <div class="card success fade-in">
        <h3>✅ Регистрация прошла успешно</h3>
        <p>Пользователь '<b>${data.username}</b>' успешно зарегистрирован</p>
        <p class="muted">Теперь вы можете войти в систему</p>
      </div>
    `);

    // Очистка полей
    document.getElementById("regUser").value = "";
    document.getElementById("regPass").value = "";
    document.getElementById("regPass2").value = "";

  } catch (err) {
    showHTML(`<div class="error">❌ Ошибка регистрации: ${err.message}</div>`);
    console.error("Registration error:", err);
  }
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
    const response = await fetch(`/api/v1/users/me/username`, {
      headers: {
        "Authorization": token
      }
    });

    if (!response.ok) {
      let errorMsg = "Неверное имя пользователя или пароль";
      try {
        const errorText = await response.text();
        const errorJson = JSON.parse(errorText);
        errorMsg = errorJson.detail || errorMsg;
      } catch (e) {
        // Используем стандартное сообщение
      }
      throw new Error(errorMsg);
    }

    const usernameFromServer = await response.text();
    const cleanName = usernameFromServer.trim();

    setAuthToken(token);

    showHTML(`
      <div class="card success fade-in">
        <h3>🎉 Добро пожаловать!</h3>
        <p>✅ Вход выполнен как <b>${cleanName}</b></p>
        <p class="muted">Теперь вам доступны персональные рекомендации</p>
      </div>
    `);

    document.getElementById("loginPass").value = "";

    if (window.reflectAuthStatus) {
      window.reflectAuthStatus();
    }

    // Загружаем информацию о пользователе и историю после входа
    await onWhoAmI();
    await onHistory();
    await onPurchases();

  } catch (err) {
    setAuthToken("");
    showHTML(`<div class="error">❌ Ошибка входа: ${err.message}</div>`);
    console.error("Login error:", err);
  }
}

function onLogout() {
  setAuthToken("");
  showHTML(`
    <div class="info fade-in">
      <h3>👋 До свидания!</h3>
      <p>🚪 Вы успешно вышли из системы</p>
    </div>
  `);

  document.getElementById("loginUser").value = "";
  document.getElementById("loginPass").value = "";

  document.getElementById("userInfo").innerHTML = `<div class="muted">Войдите, чтобы увидеть информацию</div>`;
  document.getElementById("historyContent").innerHTML = `<div class="muted">Войдите, чтобы увидеть историю</div>`;
  document.getElementById("purchasesContent").innerHTML = `<div class="muted">Войдите, чтобы увидеть историю покупок</div>`;

  if (window.reflectAuthStatus) {
    window.reflectAuthStatus();
  }
}


async function onWhoAmI() {
  const userInfoDiv = document.getElementById("userInfo");

  if (!getAuthToken()) {
    userInfoDiv.innerHTML = `<div class="muted">Войдите, чтобы увидеть информацию</div>`;
    return;
  }

  try {
    const response = await fetch(`/api/v1/users/me`, {
      headers: {
        "Authorization": getAuthToken()
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    // БЕЗ ID, только username
    userInfoDiv.innerHTML = `
      <div class="kv">
        <div><span>Username</span><b>${data.username}</b></div>
      </div>
    `;
  } catch (e) {
    userInfoDiv.innerHTML = `<div class="error">❌ Ошибка: ${e.message}</div>`;
    console.error("WhoAmI error:", e);
  }
}


async function onHistory() {
  const historyDiv = document.getElementById("historyContent");

  if (!getAuthToken()) {
    historyDiv.innerHTML = `<div class="muted">Войдите, чтобы увидеть историю</div>`;
    return;
  }

  try {
    const data = await fetchJSON(`/api/v1/users/me/history?all=true`);

    if (!Array.isArray(data) || !data.length) {
      historyDiv.innerHTML = `<div class="muted">📭 История действий пуста</div>`;
      return;
    }

    const rows = data.map(a => {
      const date = new Date(a.timestamp);
      const formattedDate = date.toLocaleString('ru-RU');

      return `
        <tr>
          <td>${formattedDate}</td>
          <td><span class="badge-inline">${formatAction(a.action)}</span></td>
          <td class="mono">${a.productId ? a.productId.substring(0, 8) + '...' : '-'}</td>
          <td>${a.category ?? "-"}</td>
        </tr>
      `;
    }).join("");


    historyDiv.innerHTML = `
      <p class="muted" style="margin-bottom:12px;">Всего записей: ${data.length}</p>
      <table class="table compact">
        <thead>
          <tr>
            <th>Время</th>
            <th>Действие</th>
            <th>ID товара</th>
            <th>Категория</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (e) {
    historyDiv.innerHTML = `<div class="error">❌ Ошибка загрузки истории: ${e.message}</div>`;
    console.error("History error:", e);
  }
}


document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btnRegister").addEventListener("click", onRegister);
  document.getElementById("btnLogin").addEventListener("click", onLogin);
  document.getElementById("btnLogout").addEventListener("click", onLogout);
  document.getElementById("btnHistory").addEventListener("click", onHistory);
  document.getElementById("btnPurchases").addEventListener("click", onPurchases);

  // Enter
  document.getElementById("regPass2")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") onRegister();
  });

  document.getElementById("loginPass")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") onLogin();
  });

  if (getAuthToken()) {
    onWhoAmI();
    onHistory();
    onPurchases();
  }
});


async function onPurchases() {
  const box = document.getElementById("purchasesContent");

  if (!getAuthToken()) {
    box.innerHTML = `<div class="muted">Войдите, чтобы увидеть историю покупок</div>`;
    return;
  }

  try {
    const data = await fetchJSON(`/api/v1/users/me/purchases`);

    if (!Array.isArray(data) || !data.length) {
      box.innerHTML = `<div class="muted">🛒 Пока нет покупок</div>`;
      return;
    }

    const rows = data.map(p => {
      const date = new Date(p.timestamp);
      const formattedDate = date.toLocaleString('ru-RU');
      const prod = p.product || {};

      return `
        <tr>
          <td>${formattedDate}</td>
          <td>${prod.brand || "?"}</td>
          <td>${prod.model || "?"}</td>
          <td>${prod.category ?? "-"}</td>
          <td>${prod.price ?? "-"}</td>
          <td class="mono">${prod.id ? prod.id.substring(0, 8) + "..." : "-"}</td>
        </tr>
      `;
    }).join("");

    box.innerHTML = `
      <p class="muted" style="margin-bottom:12px;">Всего покупок: ${data.length}</p>
      <table class="table compact">
        <thead>
          <tr>
            <th>Время</th>
            <th>Бренд</th>
            <th>Модель</th>
            <th>Категория</th>
            <th>Цена</th>
            <th>ID товара</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (e) {
    box.innerHTML = `<div class="error">❌ Ошибка загрузки покупок: ${e.message}</div>`;
    console.error("Purchases error:", e);
  }
}

