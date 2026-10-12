import {
  API_URL,
  authenticatedFetch,
  getAuthHeaders,
  getToken,
} from "@/shared/services/api-client";
export { API_URL, getAuthHeaders, getToken };
export function setToken(token) {
  if (typeof window !== "undefined") {
    localStorage.setItem("veriq_token", token);
    userMePromise = null;
  }
}
export function removeToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("veriq_token");
    userMePromise = null;
  }
}
export function getUserFromToken(token = getToken()) {
  if (!token) return null;
  try {
    const encodedPayload = token.split(".")[1];
    if (!encodedPayload) return null;
    const normalized = encodedPayload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
    const payload = JSON.parse(
      decodeURIComponent(
        Array.from(atob(padded))
          .map((character) => `%${character.charCodeAt(0).toString(16).padStart(2, "0")}`)
          .join(""),
      ),
    );
    const userId = payload.uid || payload.user_id || payload.id;
    if (!payload.sub || !userId) return null;
    if (payload.exp && payload.exp * 1000 <= Date.now()) return null;
    return {
      _id: userId,
      email: payload.sub,
      full_name: payload.full_name || payload.sub,
      slug: payload.slug || "",
      system_role: payload.system_role || "USER",
    };
  } catch {
    return null;
  }
}
function errorMessage(data, fallback) {
  const detail = data?.detail ?? data?.message;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item === "string" ? item : item?.msg || item?.message))
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (detail && typeof detail === "object") {
    const message = detail.message || detail.msg || detail.code;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}
export async function logoutAPI(allDevices = false) {
  const token = getToken();
  if (!token) return;
  const endpoint = allDevices ? "dang-xuat-tat-ca" : "dang-xuat";
  await authenticatedFetch(`${API_URL}/xac-thuc/${endpoint}`, {
    method: "POST",
  });
}
let userMePromise = null;
export async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);
  const res = await fetch(`${API_URL}/xac-thuc/dang-nhap`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
    credentials: "include",
  });
  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.data) {
    throw new Error(errorMessage(json, "Lỗi xác thực thông tin đăng nhập"));
  }
  return json.data;
}
export async function register(email, password, full_name, slug, agreed_to_terms) {
  const res = await fetch(`${API_URL}/xac-thuc/dang-ky`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, full_name, slug, agreed_to_terms }),
  });
  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.data) {
    throw new Error(errorMessage(json, "Không thể tạo hồ sơ người dùng mới"));
  }
  return json.data;
}
export async function getUserMe() {
  const token = getToken();
  if (!token) return null;
  if (userMePromise) return userMePromise;
  userMePromise = (async () => {
    try {
      const res = await authenticatedFetch(`${API_URL}/xac-thuc/ca-nhan`, {
        method: "GET",
      });
      if (res.status === 401 || res.status === 403) {
        removeToken();
        return null;
      }
      if (!res.ok) throw new Error("Không thể xác minh phiên đăng nhập");
      const json = await res.json().catch(() => null);
      if (!json?.data) throw new Error("Không thể xác minh phiên đăng nhập");
      return json.data;
    } finally {
      userMePromise = null;
    }
  })();
  return userMePromise;
}
async function authenticatedJson(path, options = {}, fallback = "Yêu cầu không thành công") {
  const response = await authenticatedFetch(`${API_URL}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(errorMessage(body, fallback));
  return body.data ?? body;
}
export function updateMyProfile(payload) {
  return authenticatedJson(
    "/xac-thuc/ca-nhan",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể cập nhật thông tin cá nhân",
  );
}
export function changeMyPassword(payload) {
  return authenticatedJson(
    "/xac-thuc/doi-mat-khau",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể đổi mật khẩu",
  );
}
export function changeMyEmail(payload) {
  return authenticatedJson(
    "/xac-thuc/doi-thu-dien-tu",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể đổi email",
  );
}
export function getMySettings() {
  return authenticatedJson("/xac-thuc/cai-dat", {}, "Không thể tải cài đặt cá nhân");
}
export function updateMySettings(payload) {
  return authenticatedJson(
    "/xac-thuc/cai-dat",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể cập nhật cài đặt cá nhân",
  );
}
export function updateMyNotifications(payload) {
  return authenticatedJson(
    "/xac-thuc/thong-bao",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    "Không thể cập nhật cài đặt thông báo",
  );
}
export function listMySessions() {
  return authenticatedJson("/xac-thuc/phien", {}, "Không thể tải danh sách phiên đăng nhập");
}
export function revokeMySession(sessionId) {
  return authenticatedJson(
    `/xac-thuc/phien/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
    },
    "Không thể thu hồi phiên đăng nhập",
  );
}
export const forgotPasswordAPI = async (email) => {
  const res = await fetch(`${API_URL}/xac-thuc/quen-mat-khau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể tạo tiến trình khôi phục mật khẩu"));
  return data?.data || data;
};
export const resetPasswordAPI = async (token, newPassword) => {
  const res = await fetch(`${API_URL}/xac-thuc/dat-lai-mat-khau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể cập nhật cấu trúc mật khẩu mới"));
  return data?.data || data;
};
export const verifyCodeAPI = async (token) => {
  const res = await fetch(`${API_URL}/xac-thuc/xac-nhan-ma`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Lỗi sai lệch mã thông báo xác thực"));
  return data?.data || data;
};
export const passkeyLoginBeginAPI = async (email) => {
  const res = await fetch(`${API_URL}/xac-thuc/khoa-bao-mat/dang-nhap/bat-dau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể tạo luồng đăng nhập chứng thư số"));
  return data?.data || data;
};
export const passkeyLoginFinishAPI = async (email, credential) => {
  const res = await fetch(`${API_URL}/xac-thuc/khoa-bao-mat/dang-nhap/hoan-tat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, credential }),
    credentials: "include",
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Lỗi hoàn tất luồng đăng nhập chứng thư số"));
  return data?.data || data;
};
export const passkeyRegisterBeginAPI = async (email) => {
  const res = await fetch(`${API_URL}/xac-thuc/khoa-bao-mat/dang-ky/bat-dau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể tạo luồng đăng ký chứng thư số"));
  return data?.data || data;
};
export const passkeyRegisterFinishAPI = async (email, credential) => {
  const res = await fetch(`${API_URL}/xac-thuc/khoa-bao-mat/dang-ky/hoan-tat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, credential }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Lỗi hoàn tất luồng đăng ký chứng thư số"));
  return data?.data || data;
};
export const getGoogleLoginUrlAPI = async () => {
  const res = await fetch(`${API_URL}/xac-thuc/google/dang-nhap`);
  const data = await res.json().catch(() => null);
  if (!res.ok || !data?.data?.url)
    throw new Error("Không thể tải điểm cuối xác thực định danh Google");
  return data.data.url;
};
export const completeGoogleLoginAPI = async (code, state) => {
  const res = await fetch(
    `${API_URL}/xac-thuc/google/chuyen-huong?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    { credentials: "include" },
  );
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể xác thực bằng Google"));
  return data?.data || data;
};
