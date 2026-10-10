const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const campusLocations = ["Hostel A", "Hostel B", "Hostel C", "Library", "Quad", "Gym", "Canteen", "Auditorium", "Sports Ground", "Science Block"];

let menuItems = [];
let cart = {};
let activeCategory = "All";
let session = readSession();
let toastTimer;
let currentBootId = null;
let isServerRestarting = false;

function readSession() {
  try {
    return JSON.parse(localStorage.getItem("hosteleats-session") || "null");
  } catch {
    return null;
  }
}

function saveSession(data) {
  try {
    if (data) {
      localStorage.setItem("hosteleats-session", JSON.stringify(data));
    } else {
      localStorage.removeItem("hosteleats-session");
    }
  } catch {}
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function showToast(message, isError = false) {
  const element = $("#toast");
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3200);
}

function headers(json = false) {
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
  };
}

async function api(path, options = {}) {
  try {
    const response = await fetch(`api/${path}`, {
      ...options,
      cache: "no-store",
      headers: { ...headers(Boolean(options.body)), ...(options.headers || {}) },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || `Request failed (${response.status})`);
    }
    return body;
  } catch (err) {
    throw err;
  }
}

function selectTab(name) {
  $$(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  $$(".panel").forEach((panel) => {
    const active = panel.id === `panel-${name}`;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });
  refreshActiveScreen();
}

function getActiveTab() {
  const activeBtn = $(".tab.active");
  return activeBtn ? activeBtn.dataset.tab : "menu";
}

function paintAccount() {
  const chip = $("#account-chip");
  if (chip) {
    chip.textContent = session ? `${session.name} · ${session.role}` : "Guest";
  }
  const loginBtn = $("#login-open");
  if (loginBtn) {
    loginBtn.textContent = session ? "Sign out" : "Sign in";
  }
  $$(".staff-tab").forEach((tab) => tab.classList.toggle("hidden", session?.role !== "staff"));
  if (session?.role !== "staff" && $("#panel-kitchen")?.classList.contains("active")) {
    selectTab("menu");
  }
  verifySessionStatus();
}

async function verifySessionStatus() {
  if (!session?.token) return;
  try {
    const result = await api("auth/session");
    const chip = $("#account-chip");
    if (chip && result.expires_in !== undefined) {
      chip.title = `Session expires in ${result.expires_in}s`;
    }
  } catch (err) {
    if (err.message.includes("401") || err.message.includes("expired") || err.message.includes("invalid")) {
      signOut(false);
      showToast("Session expired. Please sign in again.");
    }
  }
}

function renderMenu() {
  const visible = activeCategory === "All" ? menuItems : menuItems.filter((item) => item.category === activeCategory);
  const grid = $("#menu-grid");
  if (!grid) return;
  grid.innerHTML = visible.map((item) => `
    <article class="menu-card">
      <div class="food-icon">${escapeHtml(item.emoji)}</div>
      <div class="food-main">
        <div class="food-meta">
          <h4>${escapeHtml(item.name)}${item.popular ? '<span class="popular-label">POPULAR</span>' : ""}</h4>
          <span class="food-price">₹${item.price}</span>
        </div>
        <p class="food-desc">${escapeHtml(item.description)}</p>
        <div class="food-bottom">
          <span class="food-tag">${escapeHtml(item.category)}</span>
          <button class="add-button" data-add="${escapeHtml(item.id)}">＋ Add</button>
        </div>
      </div>
    </article>
  `).join("") || '<div class="empty-state">No items in this section today.</div>';
}

function renderCart() {
  const picked = menuItems.filter((item) => cart[item.id]);
  const count = picked.reduce((sum, item) => sum + cart[item.id], 0);
  const total = picked.reduce((sum, item) => sum + item.price * cart[item.id], 0);
  const countEl = $("#cart-count");
  if (countEl) countEl.textContent = count;
  const totalEl = $("#cart-total");
  if (totalEl) totalEl.textContent = `₹${total}`;
  const linesEl = $("#cart-lines");
  if (!linesEl) return;
  if (!picked.length) {
    linesEl.innerHTML = `
      <div class="empty-cart">
        <span class="empty-icon">🍱</span>
        <b>Your bag is empty</b>
        <p>Add tasty items from the menu to build your pre-order.</p>
      </div>`;
    return;
  }
  linesEl.innerHTML = picked.map((item) => `
    <div class="cart-line">
      <div class="cart-line-info">
        <b>${escapeHtml(item.name)}</b>
        <span>₹${item.price} each</span>
      </div>
      <div class="quantity-control">
        <button data-qty="${item.id}" data-delta="-1" aria-label="Remove one">−</button>
        <span>${cart[item.id]}</span>
        <button data-qty="${item.id}" data-delta="1" aria-label="Add one">＋</button>
      </div>
    </div>
  `).join("");
}

function renderOrders(orders, target) {
  const container = $(target);
  if (!container) return;
  if (!orders.length) {
    container.innerHTML = '<div class="empty-state">No orders in the queue right now.</div>';
    return;
  }
  container.innerHTML = orders.map((order) => {
    const itemText = order.items.map((item) => `${item.quantity} × ${escapeHtml(item.name)}`).join(", ");
    const ready = order.status === "Ready";
    return `
      <article class="order-card">
        <div class="order-top">
          <span class="order-id">${escapeHtml(order.id)}</span>
          <span class="status-pill ${ready ? "ready" : ""}">${escapeHtml(order.status)}</span>
        </div>
        <h4>${escapeHtml(order.student || "Your order")}</h4>
        <p class="order-details">${itemText}</p>
        <div class="order-bottom">
          <span>Pickup · ${escapeHtml(order.pickup_at)}</span>
          <b>₹${order.total}</b>
        </div>
      </article>`;
  }).join("");
}

async function loadMenu() {
  try {
    const result = await api("menu");
    menuItems = result.items;
    renderMenu();
    renderCart();
  } catch (error) {
    const grid = $("#menu-grid");
    if (grid) grid.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

async function loadLimiter() {
  try {
    const user = session ? session.username : "aarav";
    const res = await api(`limiter/status?user_id=${encodeURIComponent(user)}`);
    const statusCard = $("#limiter-status");
    if (statusCard) {
      statusCard.innerHTML = `
        <div class="limiter-badge ${res.can_order ? 'can-order' : 'rate-limited'}">
          <span class="limiter-dot"></span>
          <span>Order Limit: <b>${res.available} / ${res.max_orders}</b> orders available (${res.active_window_seconds}s window)</span>
        </div>`;
    }
  } catch {}
}

async function loadOrders() {
  if (!session) {
    const ordersEl = $("#my-orders");
    if (ordersEl) ordersEl.innerHTML = '<div class="empty-state">Sign in to view your orders.</div>';
    const queueEl = $("#kitchen-queue");
    if (queueEl) queueEl.innerHTML = '<div class="empty-state">Kitchen queue will appear here.</div>';
    return;
  }
  try {
    if (session.role === "student") {
      const result = await api("orders/mine");
      renderOrders(result.orders, "#my-orders");
    } else {
      const ordersEl = $("#my-orders");
      if (ordersEl) ordersEl.innerHTML = '<div class="empty-state">Staff accounts use the Kitchen Console to manage orders.</div>';
    }
  } catch (error) {
    if (error.message.includes("sign in")) signOut(false);
  }
  if (session?.role === "staff") {
    try {
      const result = await api("kitchen/queue");
      const queueEl = $("#kitchen-queue");
      if (!queueEl) return;
      if (!result.orders.length) {
        queueEl.innerHTML = '<div class="empty-state">The kitchen queue is clear. Nice work!</div>';
      } else {
        queueEl.innerHTML = result.orders.map((order) => `
          <article class="kitchen-order">
            <div>
              <span class="order-id">${escapeHtml(order.id)} · ${escapeHtml(order.pickup_at)}</span>
              <h4>${escapeHtml(order.student)}</h4>
              <p>${order.items.map((item) => `${item.quantity} × ${escapeHtml(item.name)}`).join(", ")} · ₹${order.total}</p>
            </div>
            <button class="primary-button" data-ready="${escapeHtml(order.id)}">Mark ready</button>
          </article>`).join("");
      }
    } catch (error) {
      if (error.message.includes("sign in")) signOut(false);
    }
  }
}

async function loadSlots() {
  const container = $("#busy-slots");
  if (!container) return;
  try {
    const result = await api("slots/busy");
    container.innerHTML = result.slots.map((slot) => `
      <div class="busy-slot">
        ${escapeHtml(slot.start_label)} – ${escapeHtml(slot.end_label)}
        <small>Reserved pickup window</small>
      </div>`).join("") || '<span class="muted-label">No reservations yet.</span>';
  } catch (error) {
    container.innerHTML = `<span class="muted-label">${escapeHtml(error.message)}</span>`;
  }
}

async function loadPeak() {
  const windowSelect = $("#rush-window");
  const windowSize = windowSelect ? Number(windowSelect.value) : 2;
  try {
    const result = await api(`analytics/peak-load?window=${windowSize}`);
    const peakWinEl = $("#peak-window");
    if (peakWinEl) peakWinEl.textContent = `${result.start_label || "—"} – ${result.end_label || "—"}`;
    const peakTotEl = $("#peak-total");
    if (peakTotEl) peakTotEl.textContent = result.total;
    const max = Math.max(...result.counts, 1);
    const chart = $("#rush-chart");
    if (chart) {
      chart.innerHTML = result.counts.map((count, index) => {
        const isPeak = index >= result.start && index < result.end;
        const height = Math.max(8, Math.round((count / max) * 100));
        return `
          <div class="rush-bar-col">
            <div class="rush-bar ${isPeak ? "peak" : ""}" style="height:${height}%">
              <span class="rush-bar-value">${count}</span>
            </div>
            <small class="rush-label">${escapeHtml(result.labels[index])}</small>
          </div>`;
      }).join("");
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

function setupLocations() {
  const options = campusLocations.map((name) => `<option>${escapeHtml(name)}</option>`).join("");
  const fromEl = $("#route-from");
  const toEl = $("#route-to");
  if (fromEl && toEl) {
    fromEl.innerHTML = options;
    toEl.innerHTML = options;
    fromEl.value = "Hostel A";
    toEl.value = "Canteen";
  }
}

async function loadRoute() {
  const fromEl = $("#route-from");
  const toEl = $("#route-to");
  const from = fromEl ? fromEl.value : "Hostel A";
  const to = toEl ? toEl.value : "Canteen";
  const resEl = $("#route-result");
  if (!resEl) return;
  try {
    const result = await api(`campus/route?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    resEl.innerHTML = `
      <div class="map-doodle">🧭</div>
      <span class="route-summary">${result.minutes} min walk</span>
      <b>Fastest path to ${escapeHtml(to)}</b>
      <div class="route-path">
        ${result.path.map((point, index) => `
          ${index ? '<span class="route-arrow">→</span>' : ""}
          <span class="route-node">${escapeHtml(point)}</span>
        `).join("")}
      </div>`;
  } catch (error) {
    resEl.innerHTML = `
      <div class="map-doodle">🧭</div>
      <b>Route unavailable</b>
      <p>${escapeHtml(error.message)}</p>`;
  }
}

async function buildCombo() {
  const budgetEl = $("#budget");
  const budget = Math.max(0, Number(budgetEl ? budgetEl.value : 60) || 60);
  const resultEl = $("#combo-result");
  if (!resultEl) return;
  try {
    const result = await api(`combo?budget=${budget}`);
    const rows = result.items.map((item) => `
      <div class="combo-line">
        <span>${escapeHtml(item.emoji)} &nbsp;${escapeHtml(item.name)}</span>
        <b>₹${item.price}</b>
      </div>`).join("");
    resultEl.innerHTML = `
      ${rows || '<div class="empty-state">Try a higher budget to unlock items.</div>'}
      <div class="combo-total">
        <span>Satisfaction Score · ${result.score} pts</span>
        <b>₹${result.total} / ₹${budget}</b>
      </div>`;
  } catch (error) {
    showToast(error.message, true);
  }
}

function signOut(showMessage = true) {
  session = null;
  saveSession(null);
  paintAccount();
  loadOrders();
  loadLimiter();
  if (showMessage) showToast("You’re signed out.");
}

async function signIn(event) {
  event.preventDefault();
  try {
    const username = $("#username").value;
    const password = $("#password").value;
    const result = await api("login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    session = result;
    saveSession(session);
    const modal = $("#login-modal");
    if (modal) modal.classList.add("hidden");
    paintAccount();
    await loadOrders();
    await loadLimiter();
    showToast(`Welcome, ${result.name.split(" ")[0]}!`);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function placeOrder() {
  if (!session) {
    const modal = $("#login-modal");
    if (modal) modal.classList.remove("hidden");
    return showToast("Sign in before placing an order.", true);
  }
  const items = Object.entries(cart)
    .filter(([, quantity]) => quantity > 0)
    .map(([item_id, quantity]) => ({ item_id, quantity }));
  if (!items.length) return showToast("Add something from the menu first.", true);
  const pickupEl = $("#order-pickup");
  const pickup_at = pickupEl ? pickupEl.value : "12:30 PM";
  try {
    const result = await api("orders", {
      method: "POST",
      body: JSON.stringify({ items, pickup_at }),
    });
    cart = {};
    renderCart();
    await loadOrders();
    await loadLimiter();
    showToast(`Order ${result.order.id} placed successfully!`);
  } catch (error) {
    showToast(error.message, true);
    await loadLimiter();
  }
}

async function bookSlot() {
  if (!session) {
    const modal = $("#login-modal");
    if (modal) modal.classList.remove("hidden");
    return showToast("Sign in to reserve a pickup slot.", true);
  }
  try {
    const start = Number($("#slot-start").value);
    const end = Number($("#slot-end").value);
    const result = await api("slots", {
      method: "POST",
      body: JSON.stringify({ start, end }),
    });
    showToast(result.message);
    await loadSlots();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function markReady(orderId) {
  try {
    await api("kitchen/ready", {
      method: "POST",
      body: JSON.stringify({ order_id: orderId }),
    });
    showToast(`${orderId} marked ready.`);
    await loadOrders();
  } catch (error) {
    showToast(error.message, true);
  }
}

function refreshActiveScreen() {
  const active = getActiveTab();
  if (active === "menu") {
    loadMenu();
    loadLimiter();
  } else if (active === "combo") {
    buildCombo();
  } else if (active === "slots") {
    loadSlots();
  } else if (active === "orders") {
    loadOrders();
  } else if (active === "rush") {
    loadPeak();
  } else if (active === "walk") {
    loadRoute();
  } else if (active === "kitchen") {
    loadOrders();
  }
}

function showReloadingBanner() {
  const banner = $("#reloading-banner");
  if (banner) banner.classList.remove("hidden");
  isServerRestarting = true;
}

function hideReloadingBanner() {
  const banner = $("#reloading-banner");
  if (banner) banner.classList.add("hidden");
  isServerRestarting = false;
}

function updateReloadChip(time) {
  const chip = $("#reload-chip");
  if (chip) chip.textContent = `Last reload: ${time}`;
}

async function checkReloadHealth() {
  try {
    const response = await fetch("api/health", { cache: "no-store" });
    if (!response.ok) {
      showReloadingBanner();
      return;
    }
    const data = await response.json();
    if (isServerRestarting) {
      hideReloadingBanner();
    }
    if (currentBootId === null) {
      currentBootId = data.boot_id;
      updateReloadChip(data.started_at);
    } else if (currentBootId !== data.boot_id) {
      currentBootId = data.boot_id;
      updateReloadChip(data.started_at);
      showToast(`Changes applied, reloaded at ${data.started_at}`);
      hideReloadingBanner();
      refreshActiveScreen();
    }
  } catch {
    showReloadingBanner();
  }
}

// Event Delegation
document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab]");
  if (tab) selectTab(tab.dataset.tab);
  const go = event.target.closest("[data-go]");
  if (go) {
    selectTab(go.dataset.go);
    document.querySelector(".tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  const category = event.target.closest("[data-category]");
  if (category) {
    activeCategory = category.dataset.category;
    $$(".category").forEach((button) => button.classList.toggle("active", button === category));
    renderMenu();
  }
  const add = event.target.closest("[data-add]");
  if (add) {
    cart[add.dataset.add] = Math.min(10, (cart[add.dataset.add] || 0) + 1);
    renderCart();
  }
  const quantity = event.target.closest("[data-qty]");
  if (quantity) {
    const id = quantity.dataset.qty;
    cart[id] = Math.max(0, (cart[id] || 0) + Number(quantity.dataset.delta));
    if (!cart[id]) delete cart[id];
    renderCart();
  }
  const ready = event.target.closest("[data-ready]");
  if (ready) markReady(ready.dataset.ready);
});

$("#login-open")?.addEventListener("click", () => {
  if (session) signOut();
  else $("#login-modal")?.classList.remove("hidden");
});
$("#login-close")?.addEventListener("click", () => $("#login-modal")?.classList.add("hidden"));
$("#login-modal")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.classList.add("hidden");
});
$("#login-form")?.addEventListener("submit", signIn);
$("#place-order")?.addEventListener("click", placeOrder);
$("#book-slot")?.addEventListener("click", bookSlot);
$("#build-combo")?.addEventListener("click", buildCombo);
$("#rush-window")?.addEventListener("change", loadPeak);
$("#find-route")?.addEventListener("click", loadRoute);

// Initialization & Seeded Scenarios
paintAccount();
setupLocations();
loadMenu();
loadLimiter();
loadSlots();
loadPeak();
loadRoute();
loadOrders();
buildCombo();

// Poll health endpoint every 1.5s for instant reload detection
window.setInterval(checkReloadHealth, 1500);

// Live update orders and slots every 3s
window.setInterval(() => {
  if (!isServerRestarting) {
    loadOrders();
    loadSlots();
    loadLimiter();
  }
}, 3000);
