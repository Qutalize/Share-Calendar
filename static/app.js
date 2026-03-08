/* ===== CalSync - app.js ===== */
"use strict";

// ===== State =====
let currentUser = null;
let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1;
let allEvents = [];
let currentEventId = null;

// ===== API Helper =====
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "エラーが発生しました");
  return data;
}

// ===== Toast =====
function toast(msg, type = "info") {
  const icons = { info: "ℹ️", success: "✅", warning: "⚠️", error: "❌" };
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ===== Auth =====
function showAuthTab(tab) {
  document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
  document.getElementById("register-form").classList.toggle("hidden", tab !== "register");
  document.querySelectorAll(".tab-btn").forEach((b, i) => {
    b.classList.toggle("active", (i === 0) === (tab === "login"));
  });
  document.getElementById("auth-error").classList.add("hidden");
}

async function doLogin() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    const data = await api("POST", "/api/login", { username, password });
    currentUser = data.user;
    enterApp();
  } catch (e) {
    showAuthError(e.message);
  }
}

async function doRegister() {
  const username = document.getElementById("reg-username").value.trim();
  const display_name = document.getElementById("reg-displayname").value.trim();
  const password = document.getElementById("reg-password").value;
  try {
    const data = await api("POST", "/api/register", { username, display_name, password });
    currentUser = data.user;
    enterApp();
  } catch (e) {
    showAuthError(e.message);
  }
}

function showAuthError(msg) {
  const el = document.getElementById("auth-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function doLogout() {
  await api("POST", "/api/logout");
  currentUser = null;
  document.getElementById("auth-screen").classList.remove("hidden");
  document.getElementById("app-screen").classList.add("hidden");
}

function enterApp() {
  document.getElementById("auth-screen").classList.add("hidden");
  document.getElementById("app-screen").classList.remove("hidden");

  // サイドバー情報更新
  document.getElementById("sidebar-name").textContent = currentUser.display_name;
  document.getElementById("sidebar-username").textContent = "@" + currentUser.username;
  document.getElementById("sidebar-avatar").textContent =
    currentUser.display_name.charAt(0).toUpperCase();

  showView("calendar");
  loadNotifications();
}

// ===== View Navigation =====
function showView(name) {
  document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  document.getElementById(`view-${name}`).classList.remove("hidden");
  document.querySelector(`[data-view="${name}"]`).classList.add("active");

  if (name === "calendar") loadCalendar();
  if (name === "friends") loadFriends();
  if (name === "notifications") loadNotifications();
}

// ===== Calendar =====
async function loadCalendar() {
  try {
    const data = await api("GET", `/api/events?year=${currentYear}&month=${currentMonth}`);
    allEvents = data.events;
    renderCalendar();
    renderEventList();
  } catch (e) {
    toast(e.message, "error");
  }
}

function changeMonth(delta) {
  currentMonth += delta;
  if (currentMonth > 12) { currentMonth = 1; currentYear++; }
  if (currentMonth < 1) { currentMonth = 12; currentYear--; }
  loadCalendar();
}

function renderCalendar() {
  const title = document.getElementById("month-title");
  title.textContent = `${currentYear}年${currentMonth}月`;

  const grid = document.getElementById("calendar-grid");
  // ヘッダー行を残してリセット
  const headers = Array.from(grid.querySelectorAll(".cal-header"));
  grid.innerHTML = "";
  headers.forEach(h => grid.appendChild(h));

  const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  const prevDays = new Date(currentYear, currentMonth - 1, 0).getDate();

  const today = new Date();
  const conflicts = new Set(allEvents.filter(e => e.is_conflict).map(e => {
    return new Date(e.start_time).getDate();
  }));

  // イベントを日付ごとにグループ化
  const eventsByDay = {};
  allEvents.forEach(ev => {
    const d = new Date(ev.start_time).getDate();
    const m = new Date(ev.start_time).getMonth() + 1;
    const y = new Date(ev.start_time).getFullYear();
    if (m === currentMonth && y === currentYear) {
      if (!eventsByDay[d]) eventsByDay[d] = [];
      eventsByDay[d].push(ev);
    }
  });

  // 前月の余白
  for (let i = 0; i < firstDay; i++) {
    const day = document.createElement("div");
    day.className = "cal-day other-month";
    const num = prevDays - firstDay + 1 + i;
    day.innerHTML = `<span class="day-num">${num}</span>`;
    grid.appendChild(day);
  }

  // 当月の日
  for (let d = 1; d <= daysInMonth; d++) {
    const day = document.createElement("div");
    const isToday = d === today.getDate() &&
      currentMonth === today.getMonth() + 1 &&
      currentYear === today.getFullYear();
    const hasConflict = (eventsByDay[d] || []).some(e => e.is_conflict);

    day.className = `cal-day${isToday ? " today" : ""}${hasConflict ? " has-conflict" : ""}`;
    day.onclick = () => onDayClick(d);

    const numEl = document.createElement("span");
    numEl.className = "day-num";
    numEl.textContent = d;
    day.appendChild(numEl);

    // イベントドット（最大3件）
    const dayEvs = eventsByDay[d] || [];
    dayEvs.slice(0, 3).forEach(ev => {
      const dot = document.createElement("div");
      const cls = ev.is_conflict ? "conflict" : (ev.is_mine ? "mine" : "friend");
      dot.className = `cal-event-dot ${cls}`;
      dot.textContent = ev.title;
      dot.onclick = (e) => { e.stopPropagation(); openDetailModal(ev); };
      day.appendChild(dot);
    });
    if (dayEvs.length > 3) {
      const more = document.createElement("div");
      more.style.cssText = "font-size:10px;color:var(--text-dim);padding:1px 4px;";
      more.textContent = `+${dayEvs.length - 3}件`;
      day.appendChild(more);
    }

    grid.appendChild(day);
  }

  // ダブルブッキングバナー
  const conflictEvents = allEvents.filter(e => e.is_conflict);
  const banner = document.getElementById("conflict-banner");
  if (conflictEvents.length > 0) {
    const names = [...new Set(conflictEvents.map(e => e.title))].join("、");
    document.getElementById("conflict-text").textContent =
      `⚠️ ダブルブッキング: 「${names}」に重複があります`;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

function onDayClick(day) {
  // その日の日時をデフォルトセットしてモーダル開く
  const y = currentYear;
  const m = String(currentMonth).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  document.getElementById("ev-start").value = `${y}-${m}-${d}T10:00`;
  document.getElementById("ev-end").value = `${y}-${m}-${d}T11:00`;
  openEventModal();
}

function renderEventList() {
  const list = document.getElementById("event-list");
  list.innerHTML = "";

  const sorted = [...allEvents].sort(
    (a, b) => new Date(a.start_time) - new Date(b.start_time)
  );

  if (sorted.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📭</div>
      <p>今月の予定はありません</p>
    </div>`;
    return;
  }

  sorted.forEach(ev => {
    const card = document.createElement("div");
    card.className = `event-card${ev.is_conflict ? " conflict" : ""}${!ev.is_mine ? " friend-event" : ""}`;
    card.onclick = () => openDetailModal(ev);

    const start = formatDt(ev.start_time);
    const end = formatDt(ev.end_time);
    const location = ev.location ? `📍 ${ev.location}` : "";
    const train = ev.train? `🚃 ${ev.train}` : "";
    const owner = ev.is_mine ? "" : (ev.owner_name ? `👤 ${ev.owner_name}` : "");

    card.innerHTML = `
      <div class="event-color-bar"></div>
      <div class="event-card-content">
        <div class="event-card-title">
          ${ev.title}
          ${ev.is_conflict ? '<span class="conflict-tag">⚠️ 重複</span>' : ""}
        </div>
        <div class="event-card-meta">
          <span>🕐 ${start} 〜 ${end}</span>
          ${location ? `<span>${location}</span>` : ""}
          ${train ? `<span>${train}</span>` : ""}
          ${owner ? `<span>${owner}</span>` : ""}
        </div>
      </div>
    `;
    list.appendChild(card);
  });
}

// ===== Event Modal =====
function openEventModal() {
  document.getElementById("event-modal").classList.remove("hidden");
  document.getElementById("ev-title").focus();
}

function closeEventModal() {
  document.getElementById("event-modal").classList.add("hidden");
  document.getElementById("conflict-preview").classList.add("hidden");
  document.getElementById("ev-title").value = "";
  document.getElementById("ev-location").value = "";
  document.getElementById("ev-train").value = "";
  document.getElementById("ev-description").value = "";
  document.getElementById("ev-public").checked = false;
}

async function checkConflictPreview() {
  const start = document.getElementById("ev-start").value;
  const end = document.getElementById("ev-end").value;
  if (!start || !end) return;

  const startDt = new Date(start);
  const endDt = new Date(end);

  const conflicts = allEvents.filter(ev => {
    if (!ev.is_mine) return false;
    const s = new Date(ev.start_time);
    const e = new Date(ev.end_time);
    return startDt < e && endDt > s;
  });

  const preview = document.getElementById("conflict-preview");
  if (conflicts.length > 0) {
    const names = conflicts.map(e => `「${e.title}」(${formatDt(e.start_time)}〜)`).join("、");
    document.getElementById("conflict-preview-text").textContent =
      `${names} と重複しています`;
    preview.classList.remove("hidden");
  } else {
    preview.classList.add("hidden");
  }
}

async function submitEvent() {
  const title = document.getElementById("ev-title").value.trim();
  const start_time = document.getElementById("ev-start").value;
  const end_time = document.getElementById("ev-end").value;
  const location = document.getElementById("ev-location").value.trim();
  const train = document.getElementById("ev-train").value.trim();
  const description = document.getElementById("ev-description").value.trim();
  const is_public = document.getElementById("ev-public").checked;

  if (!title || !start_time || !end_time) {
    toast("タイトルと日時は必須です", "error");
    return;
  }
  if (new Date(start_time) >= new Date(end_time)) {
    toast("終了時刻は開始時刻より後にしてください", "error");
    return;
  }

  try {
    const data = await api("POST", "/api/events",
      { title, start_time, end_time, location,train, description, is_public });

    if (data.warning) {
      toast(data.warning, "warning");
    } else {
      toast("予定を追加しました", "success");
    }
    closeEventModal();
    loadCalendar();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ===== Event Detail Modal =====
async function openDetailModal(ev) {
  currentEventId = ev.id;

  document.getElementById("detail-title").textContent = ev.title;
  document.getElementById("detail-time").textContent =
    `${formatDt(ev.start_time)} 〜 ${formatDt(ev.end_time)}`;

  const locRow = document.getElementById("detail-location-row");
  if (ev.location) {
    document.getElementById("detail-location").textContent = ev.location;
    locRow.classList.remove("hidden");
  } else {
    locRow.classList.add("hidden");
  }

  const traRow = document.getElementById("detail-train-row");
  if (ev.train) {
    document.getElementById("detail-train").textContent = ev.train;
    traRow.classList.remove("hidden");
  } else {
    traRow.classList.add("hidden");
  }

  const descRow = document.getElementById("detail-desc-row");
  if (ev.description) {
    document.getElementById("detail-description").textContent = ev.description;
    descRow.classList.remove("hidden");
  } else {
    descRow.classList.add("hidden");
  }

  // 削除ボタン（自分のイベントのみ）
  document.getElementById("delete-btn").style.display = ev.is_mine ? "" : "none";

  // 参加状況（公開イベントのみ）
  const participationSection = document.getElementById("participation-section");
  if (ev.is_public || !ev.is_mine) {
    participationSection.classList.remove("hidden");
    try {
      const pData = await api("GET", `/api/events/${ev.id}/participants`);
      renderParticipants(pData.participants);
    } catch (e) {}

    // 自分のイベントなら参加ボタン非表示
    document.getElementById("participation-actions").style.display =
      ev.is_mine ? "none" : "";
  } else {
    participationSection.classList.add("hidden");
  }

  document.getElementById("event-detail-modal").classList.remove("hidden");
}

function renderParticipants(participants) {
  const list = document.getElementById("participants-list");
  if (participants.length === 0) {
    list.innerHTML = `<div style="font-size:13px;color:var(--text-muted)">まだ回答者はいません</div>`;
    return;
  }
  list.innerHTML = participants.map(p => {
    const cls = p.response === "accepted" ? "resp-accepted" :
                p.response === "declined" ? "resp-declined" : "resp-pending";
    const label = p.response === "accepted" ? "✓ 参加" :
                  p.response === "declined" ? "✗ 不参加" : "— 未回答";
    return `<div class="participant-item">
      <span>${p.display_name}</span>
      <span class="${cls}">${label}</span>
    </div>`;
  }).join("");
}

function closeDetailModal() {
  document.getElementById("event-detail-modal").classList.add("hidden");
  currentEventId = null;
}

async function deleteCurrentEvent() {
  if (!currentEventId) return;
  if (!confirm("この予定を削除しますか？")) return;
  try {
    await api("DELETE", `/api/events/${currentEventId}`);
    toast("予定を削除しました", "success");
    closeDetailModal();
    loadCalendar();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function respond(response) {
  if (!currentEventId) return;
  try {
    const data = await api("POST", `/api/events/${currentEventId}/participate`, { response });
    toast(data.message, "success");
    closeDetailModal();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ===== Friends =====
async function loadFriends() {
  try {
    const data = await api("GET", "/api/friends");
    renderFriendList(data.friends);
  } catch (e) {
    toast(e.message, "error");
  }
}

function renderFriendList(friends) {
  const list = document.getElementById("friend-list");
  if (friends.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon">👥</div>
      <p>フレンドがいません。上の検索でフレンドを追加しましょう！</p>
    </div>`;
    return;
  }
  list.innerHTML = friends.map(f => `
    <div class="friend-card">
      <div class="search-avatar">${f.display_name.charAt(0).toUpperCase()}</div>
      <div>
        <div style="font-weight:600;font-size:14px">${f.display_name}</div>
        <div style="font-size:12px;color:var(--text-muted);font-family:var(--font-mono)">@${f.username}</div>
      </div>
      <span class="friend-status status-${f.status}">
        ${f.status === "accepted"}
      </span>
    </div>
  `).join("");
}

let searchTimeout = null;
function searchUsers(q) {
  clearTimeout(searchTimeout);
  const dropdown = document.getElementById("search-results");
  if (!q) { dropdown.classList.add("hidden"); return; }

  searchTimeout = setTimeout(async () => {
    try {
      const data = await api("GET", `/api/friends/search?q=${encodeURIComponent(q)}`);
      if (data.users.length === 0) {
        dropdown.classList.add("hidden");
        return;
      }
      dropdown.innerHTML = data.users.map(u => `
        <div class="search-result-item">
          <div class="search-avatar">${u.display_name.charAt(0).toUpperCase()}</div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:600">${u.display_name}</div>
            <div style="font-size:12px;color:var(--text-muted);font-family:var(--font-mono)">@${u.username}</div>
          </div>
          <button class="btn-add-friend" onclick="sendFriendRequest(${u.id}, '${u.display_name}')">
            ＋ 追加
          </button>
        </div>
      `).join("");
      dropdown.classList.remove("hidden");
    } catch (e) {}
  }, 300);
}

async function sendFriendRequest(friendId, name) {
  try {
    await api("POST", "/api/friends/request", { friend_id: friendId });
    toast(`${name}さんにフレンド申請を送りました`, "success");
    document.getElementById("search-results").classList.add("hidden");
    document.getElementById("friend-search-input").value = "";
    loadFriends();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ===== Notifications =====
async function loadNotifications() {
  try {
    const data = await api("GET", "/api/notifications");
    renderNotifications(data.notifications);

    // バッジ更新
    const badge = document.getElementById("notif-badge");
    if (data.unread_count > 0) {
      badge.textContent = data.unread_count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  } catch (e) {}
}

function renderNotifications(notifications) {
  const list = document.getElementById("notification-list");
  if (notifications.length === 0) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🔔</div>
      <p>通知はありません</p>
    </div>`;
    return;
  }

  const icons = {
    double_booking: "⚠️",
    event_invite: "📩",
    friend_request: "👋",
    participation_update: "✅",
  };

  list.innerHTML = notifications.map(n => `
    <div class="notif-card ${n.is_read ? "" : "unread"} ${n.type}"
         onclick="markRead(${n.id}, this)">
      <div class="notif-icon">${icons[n.type] || "🔔"}</div>
      <div class="notif-body">
        <div class="notif-message">${n.message}</div>
        <div class="notif-time">${formatRelative(n.created_at)}</div>
      </div>
      ${!n.is_read ? '<div style="width:8px;height:8px;background:var(--primary);border-radius:50%;flex-shrink:0;margin-top:6px"></div>' : ""}
    </div>
  `).join("");
}

async function markRead(id, el) {
  try {
    await api("POST", `/api/notifications/${id}/read`);
    el.classList.remove("unread");
    const dot = el.querySelector("div[style*='background:var(--primary)']");
    if (dot) dot.remove();
    loadNotifications(); // バッジ更新
  } catch (e) {}
}

async function markAllRead() {
  try {
    await api("POST", "/api/notifications/read-all");
    toast("全て既読にしました", "success");
    loadNotifications();
  } catch (e) {}
}

// ===== Helpers =====
function formatDt(isoStr) {
  const d = new Date(isoStr);
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${m}/${day} ${h}:${min}`;
}

function formatRelative(isoStr) {
  const d = new Date(isoStr);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return "たった今";
  if (diff < 3600) return `${Math.floor(diff / 60)}分前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
  return `${Math.floor(diff / 86400)}日前`;
}

// ===== Keyboard shortcuts =====
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    closeEventModal();
    closeDetailModal();
  }
  if (e.key === "Enter" && document.getElementById("auth-screen").style.display !== "none") {
    const activeForm = document.getElementById("login-form").classList.contains("hidden")
      ? "register" : "login";
    if (activeForm === "login") doLogin();
    else doRegister();
  }
});

// Enter キーでログイン
document.getElementById("login-password").addEventListener("keydown", e => {
  if (e.key === "Enter") doLogin();
});

// ===== Init =====
(async () => {
  try {
    const data = await api("GET", "/api/me");
    currentUser = data.user;
    enterApp();
  } catch {
    // 未ログイン → ログイン画面のまま
  }
})();
