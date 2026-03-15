/**
 * api.js — 前端统一 API 请求封装
 * 所有与后端的通信都通过这里
 */

const BASE_URL = "http://localhost:8000";

// ── Token 管理 ─────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem("token"),
  setToken: (t) => localStorage.setItem("token", t),
  removeToken: () => localStorage.removeItem("token"),
  getUser: () => JSON.parse(localStorage.getItem("user") || "null"),
  setUser: (u) => localStorage.setItem("user", JSON.stringify(u)),
  removeUser: () => localStorage.removeItem("user"),
  isLoggedIn: () => !!localStorage.getItem("token"),
  isAdmin: () => {
    const u = Auth.getUser();
    return u && u.is_admin;
  },
  logout: () => {
    Auth.removeToken();
    Auth.removeUser();
    window.location.href = "login.html";
  },
};

// ── 通用请求 ────────────────────────────────────────
async function request(path, options = {}) {
  const token = Auth.getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg = data.detail || `请求失败 (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

const get  = (path, params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ""))
  ).toString();
  return request(qs ? `${path}?${qs}` : path);
};
const post   = (path, body) => request(path, { method: "POST",   body: JSON.stringify(body) });
const put    = (path, body) => request(path, { method: "PUT",    body: JSON.stringify(body) });
const del    = (path)       => request(path, { method: "DELETE" });

// ── Auth API ────────────────────────────────────────
const AuthAPI = {
  register: (data) => post("/api/auth/register", data),
  login:    (data) => post("/api/auth/login", data),
  me:       ()     => get("/api/auth/me"),
};

// ── 餐厅 API ────────────────────────────────────────
const RestaurantAPI = {
  list: (params) => get("/api/restaurants", params),
  detail: (id)   => get(`/api/restaurants/${id}`),
  featured: ()   => get("/api/restaurants/featured"),
  ranking: ()    => get("/api/restaurants/ranking"),
  create: (data) => post("/api/restaurants", data),
  update: (id, data) => put(`/api/restaurants/${id}`, data),
  delete: (id)   => del(`/api/restaurants/${id}`),
  toggleFav: (id) => post(`/api/restaurants/${id}/favorite`),
  isFavorited: (id) => get(`/api/restaurants/${id}/is_favorited`),
};

// ── 评价 API ────────────────────────────────────────
const ReviewAPI = {
  list:   (restaurant_id, page = 1) => get("/api/reviews", { restaurant_id, page }),
  create: (data) => post("/api/reviews", data),
  delete: (id)   => del(`/api/reviews/${id}`),
};

// ── AI 推荐 API ─────────────────────────────────────
const AIAPI = {
  recommend: (message, campus = "", budget = null) =>
    post("/api/ai/recommend", { message, campus, budget }),
};

// ── 管理后台 API ─────────────────────────────────────
const AdminAPI = {
  stats:         ()     => get("/api/admin/stats"),
  users:         ()     => get("/api/admin/users"),
  toggleUser:    (id)   => put(`/api/admin/users/${id}/toggle`),
  deleteReview:  (id)   => del(`/api/admin/reviews/${id}`),
  createDeal:    (data) => post("/api/admin/deals", data),
  deleteDeal:    (id)   => del(`/api/admin/deals/${id}`),
  createMenuItem:(data) => post("/api/admin/menu-items", data),
  deleteMenuItem:(id)   => del(`/api/admin/menu-items/${id}`),
};

// ── 积分 API ────────────────────────────────────────────────
const PointsAPI = {
  me:      ()                  => get("/api/points/me"),
  logs:    (page=1)            => get("/api/points/logs", {page}),
  today:   ()                  => get("/api/points/today"),
  ranking: (limit=10)          => get("/api/points/ranking", {limit}),
  earn:    (action, note="")   => post("/api/points/earn", {action, note}),
  redeem:  (points, note)      => post("/api/points/redeem", {points, note}),
};

// 积分浮动动画
function showPointsFloat(pts, msg="") {
  if (!Auth.isLoggedIn()) return;
  const el = document.createElement("div");
  el.textContent = `+${pts} 积分${msg ? " · "+msg : ""}`;
  el.style.cssText = "position:fixed;top:72px;right:16px;background:linear-gradient(135deg,#f4b942,#e85d26);color:white;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:500;z-index:9999;pointer-events:none;font-family:'Noto Sans SC',sans-serif;box-shadow:0 4px 16px rgba(244,185,66,.4);animation:ptsFly 2s ease forwards;";
  if (!document.getElementById("_pts_style")) {
    const s = document.createElement("style");
    s.id = "_pts_style";
    s.textContent = "@keyframes ptsFly{0%{opacity:1;transform:translateY(0)}70%{opacity:1;transform:translateY(-40px)}100%{opacity:0;transform:translateY(-70px)}}";
    document.head.appendChild(s);
  }
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2100);
}

// ── UI 工具 ─────────────────────────────────────────
function showToast(msg, type = "info") {
  let t = document.getElementById("_toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "_toast";
    t.style.cssText = `
      position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);
      padding:12px 20px;border-radius:12px;font-size:14px;z-index:9999;
      transition:transform .35s cubic-bezier(.16,1,.3,1);white-space:nowrap;
      font-family:'Noto Sans SC',sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.2);
    `;
    document.body.appendChild(t);
  }
  const colors = { info: "#1a1209", success: "#2d7a4f", error: "#e85d26" };
  t.style.background = colors[type] || colors.info;
  t.style.color = "#fdf6e3";
  t.textContent = msg;
  t.style.transform = "translateX(-50%) translateY(0)";
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.style.transform = "translateX(-50%) translateY(80px)"; }, 2500);
}

function requireLogin() {
  if (!Auth.isLoggedIn()) {
    showToast("请先登录", "error");
    setTimeout(() => { window.location.href = "login.html"; }, 800);
    return false;
  }
  return true;
}

// 渲染评分星星
function renderStars(rating) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  let s = "";
  for (let i = 0; i < 5; i++) {
    if (i < full) s += "★";
    else if (i === full && half) s += "☆";
    else s += "☆";
  }
  return s;
}

// 价格范围显示
function priceRange(r) {
  if (r.price_min && r.price_max) return `¥${r.price_min}-${r.price_max}`;
  if (r.price_min) return `¥${r.price_min}起`;
  return "价格待更新";
}
