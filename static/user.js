import { fetchJSON, makeBasic, setAuthToken, getAuthToken } from "./common.js";

function showHTML(html) {
  const box = document.getElementById("pretty");
  const panel = document.getElementById("messagesPanel");

  if (box) {
    box.innerHTML = html;
  }

  if (panel) {
    const hasContent = html && String(html).trim().length > 0;
    panel.style.display = hasContent ? "block" : "none";
  }
}


let IS_ADMIN = false;


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

    document.getElementById("regUser").value = "";
    document.getElementById("regPass").value = "";
    document.getElementById("regPass2").value = "";

  } catch (err) {
    showHTML(`<div class="error">❌ Ошибка регистрации: ${err.message}</div>`);
    console.error("Registration error:", err);
  }
}

async function loadAdminUsers() {
  const box = document.getElementById("adminUsersContent");
  const wrapper = document.getElementById("adminUsersBox");

  if (!box || !wrapper) return;

  if (!getAuthToken() || !IS_ADMIN) {
    wrapper.style.display = "none";
    return;
  }

  wrapper.style.display = "block";
  box.innerHTML = `<div class="muted mono">Загружаем пользователей…</div>`;

  try {
    const users = await fetchJSON(`/api/v1/users/admin/users`);

    if (!Array.isArray(users) || !users.length) {
      box.innerHTML = `<div class="muted">Пользователей не найдено</div>`;
      return;
    }

    const rows = users.map(u => `
      <tr>
        <td>${u.username}</td>
        <td class="mono">${u.id ? u.id.substring(0,8) + "..." : "-"}</td>
        <td>
          <button class="btn outline small btn-admin-pass" data-id="${u.id}" data-username="${u.username}">
            Update password
          </button>
          <button class="btn danger small btn-admin-del" data-id="${u.id}" data-username="${u.username}" style="margin-left:6px;">
            Delete
          </button>
        </td>
      </tr>
    `).join("");

    box.innerHTML = `
      <table class="table compact">
        <thead>
          <tr>
            <th>Username</th>
            <th>ID</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (e) {
    box.innerHTML = `<div class="error">❌ Ошибка загрузки пользователей: ${e.message}</div>`;
    console.error("Admin users load error:", e);
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
    IS_ADMIN = false;
    const adminBox = document.getElementById("adminUsersBox");
    if (adminBox) adminBox.style.display = "none";
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

    userInfoDiv.innerHTML = `
      <div class="kv">
        <div><span>Username</span><b>${data.username}</b></div>
      </div>
    `;

    IS_ADMIN = data.username === "admin";

    const adminBox = document.getElementById("adminUsersBox");
    if (adminBox) {
      adminBox.style.display = IS_ADMIN ? "block" : "none";
    }
    if (IS_ADMIN) {
      await loadAdminUsers();
    }

  } catch (e) {
    userInfoDiv.innerHTML = `<div class="error">❌ Ошибка: ${e.message}</div>`;
    IS_ADMIN = false;
    const adminBox = document.getElementById("adminUsersBox");
    if (adminBox) adminBox.style.display = "none";
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
  document.getElementById("btnUpdatePassword").addEventListener("click", onUpdatePassword);
  document.getElementById("btnReloadUsers")?.addEventListener("click", loadAdminUsers);

  document.getElementById("regPass2")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") onRegister();
  });

  document.getElementById("loginPass")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") onLogin();
  });

  document.getElementById("updNewPass2")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") onUpdatePassword();
  });

  if (getAuthToken()) {
    onWhoAmI();
    onHistory();
    onPurchases();
  }
});

document.addEventListener("click", async (e) => {
  const passBtn = e.target.closest(".btn-admin-pass");
  const delBtn = e.target.closest(".btn-admin-del");

  if (passBtn) {
    if (!IS_ADMIN || !getAuthToken()) {
      showHTML(`<div class="warn">⚠️ Доступ только для admin</div>`);
      return;
    }

    const userId = passBtn.dataset.id;
    const username = passBtn.dataset.username || "?";

    const newPass = prompt(`Введите новый пароль для пользователя "${username}":`);
    if (!newPass) return;
    const newPass2 = prompt(`Повторите новый пароль для "${username}":`);
    if (!newPass2) return;

    if (newPass !== newPass2) {
      showHTML(`<div class="error">❌ Пароли не совпадают</div>`);
      return;
    }

    if (newPass.length < 6) {
      showHTML(`<div class="warn">⚠️ Новый пароль должен быть не менее 6 символов</div>`);
      return;
    }

    try {
      const resp = await fetch(`/api/v1/users/admin/users/${encodeURIComponent(userId)}/password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": getAuthToken()
        },
        body: JSON.stringify({
          new_password: newPass,
          new_password_confirmation: newPass2
        })
      });

      if (!resp.ok) {
        const txt = await resp.text();
        let msg = "Не удалось обновить пароль";
        try {
          const j = JSON.parse(txt);
          if (j.detail) msg = j.detail;
        } catch (e2) {
          if (txt) msg = txt;
        }
        throw new Error(msg);
      }

      showHTML(`
        <div class="card success fade-in">
          <h3>✅ Пароль обновлён</h3>
          <p>Пароль пользователя <b>${username}</b> успешно изменён администратором.</p>
        </div>
      `);
    } catch (err) {
      showHTML(`<div class="error">❌ Ошибка смены пароля: ${err.message}</div>`);
      console.error("Admin update password error:", err);
    }

    return;
  }

  if (delBtn) {
    if (!IS_ADMIN || !getAuthToken()) {
      showHTML(`<div class="warn">⚠️ Доступ только для admin</div>`);
      return;
    }

    const userId = delBtn.dataset.id;
    const username = delBtn.dataset.username || "?";

    if (!confirm(`Вы уверены, что хотите удалить пользователя "${username}"?`)) {
      return;
    }

    try {
      const resp = await fetch(`/api/v1/users/admin/users/${encodeURIComponent(userId)}`, {
        method: "DELETE",
        headers: {
          "Authorization": getAuthToken()
        }
      });

      if (!resp.ok) {
        const txt = await resp.text();
        let msg = "Не удалось удалить пользователя";
        try {
          const j = JSON.parse(txt);
          if (j.detail) msg = j.detail;
        } catch (e2) {
          if (txt) msg = txt;
        }
        throw new Error(msg);
      }

      showHTML(`
        <div class="card success fade-in">
          <h3>✅ Пользователь удалён</h3>
          <p>Пользователь <b>${username}</b> был удалён администратором.</p>
        </div>
      `);

      await loadAdminUsers();
    } catch (err) {
      showHTML(`<div class="error">❌ Ошибка удаления пользователя: ${err.message}</div>`);
      console.error("Admin delete user error:", err);
    }
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


async function onUpdatePassword() {
  const oldPass = document.getElementById("updOldPass").value;
  const newPass = document.getElementById("updNewPass").value;
  const newPass2 = document.getElementById("updNewPass2").value;

  if (!getAuthToken()) {
    showHTML(`<div class="warn">⚠️ Для смены пароля необходимо войти в аккаунт</div>`);
    return;
  }

  if (!oldPass || !newPass || !newPass2) {
    showHTML(`<div class="warn">⚠️ Заполните все поля для смены пароля</div>`);
    return;
  }

  if (newPass.length < 6) {
    showHTML(`<div class="warn">⚠️ Новый пароль должен быть не менее 6 символов</div>`);
    return;
  }

  if (newPass !== newPass2) {
    showHTML(`<div class="error">❌ Новый пароль и подтверждение не совпадают</div>`);
    return;
  }

  if (newPass === oldPass) {
    showHTML(`<div class="warn">⚠️ Новый пароль не должен совпадать со старым</div>`);
    return;
  }

  try {
    const resp = await fetch(`/api/v1/users/me/update/password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": getAuthToken()
      },
      body: JSON.stringify({
        old_password: oldPass,
        new_password: newPass,
        new_password_confirmation: newPass2
      })
    });

    if (!resp.ok) {
      const txt = await resp.text();
      let msg = "Не удалось обновить пароль";
      try {
        const j = JSON.parse(txt);
        if (j.detail) msg = j.detail;
      } catch (e) {
        if (txt) msg = txt;
      }
      throw new Error(msg);
    }

    showHTML(`
      <div class="card success fade-in">
        <h3>✅ Пароль обновлён</h3>
        <p>Ваш пароль успешно изменён. Пожалуйста, войдите снова.</p>
      </div>
    `);

    document.getElementById("updOldPass").value = "";
    document.getElementById("updNewPass").value = "";
    document.getElementById("updNewPass2").value = "";

    setAuthToken("");

    if (window.reflectAuthStatus) {
      window.reflectAuthStatus();
    }

    document.getElementById("userInfo").innerHTML = `<div class="muted">Войдите, чтобы увидеть информацию</div>`;
    document.getElementById("historyContent").innerHTML = `<div class="muted">Войдите, чтобы увидеть историю</div>`;
    document.getElementById("purchasesContent").innerHTML = `<div class="muted">Войдите, чтобы увидеть историю покупок</div>`;

  } catch (err) {
    showHTML(`<div class="error">❌ Ошибка смены пароля: ${err.message}</div>`);
    console.error("Update password error:", err);
  }
}
