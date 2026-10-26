import {
  API_URL,
  authenticatedFetch,
  fetchWithNetworkError,
  getAuthHeaders,
  getToken,
} from "@/shared/services/api-client";
export { API_URL, getAuthHeaders, getToken };
export function removeToken(expectedToken) {
  if (typeof window !== "undefined") {
    const currentToken = getToken();
    if (expectedToken && currentToken !== expectedToken) return false;
    localStorage.removeItem("veriq_token");
    const cookieToken = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith("token="))
      ?.slice("token=".length);
    if (!expectedToken || cookieToken === expectedToken) {
      document.cookie = "token=; path=/; max-age=0; SameSite=Lax";
    }
    if (!expectedToken || userMePromise?.token === expectedToken) userMePromise = null;
    return true;
  }
  return false;
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
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/dang-nhap`, {
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
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/dang-ky`, {
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
  if (userMePromise?.token === token) return userMePromise.promise;
  const promise = (async () => {
    try {
      const res = await authenticatedFetch(`${API_URL}/xac-thuc/ca-nhan`, {
        method: "GET",
      });
      if (res.status === 401 || res.status === 403) {
        removeToken(token);
        return null;
      }
      if (!res.ok) throw new Error("Không thể xác minh phiên đăng nhập");
      const json = await res.json().catch(() => null);
      if (!json?.data) throw new Error("Không thể xác minh phiên đăng nhập");
      return json.data;
    } finally {
      if (userMePromise?.promise === promise) userMePromise = null;
    }
  })();
  userMePromise = { token, promise };
  return promise;
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
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/quen-mat-khau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể gửi yêu cầu khôi phục mật khẩu"));
  return data?.data || data;
};
export const resetPasswordAPI = async (token, newPassword) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/dat-lai-mat-khau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể cập nhật mật khẩu mới"));
  return data?.data || data;
};
export const verifyCodeAPI = async (token) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/xac-nhan-ma`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Mã xác thực không hợp lệ hoặc đã hết hạn"));
  return data?.data || data;
};
export const verifyEmailAPI = async (token) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/xac-minh-thu-dien-tu`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể xác minh địa chỉ thư điện tử"));
  return data?.data || data;
};
export const passkeyLoginBeginAPI = async (email) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/khoa-bao-mat/dang-nhap/bat-dau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể tạo luồng đăng nhập chứng thư số"));
  return data?.data || data;
};
export const passkeyLoginFinishAPI = async (email, credential) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/khoa-bao-mat/dang-nhap/hoan-tat`, {
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
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/khoa-bao-mat/dang-ky/bat-dau`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể tạo luồng đăng ký chứng thư số"));
  return data?.data || data;
};
export const passkeyRegisterFinishAPI = async (email, credential) => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/khoa-bao-mat/dang-ky/hoan-tat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, credential }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Lỗi hoàn tất luồng đăng ký chứng thư số"));
  return data?.data || data;
};
export const getGoogleLoginUrlAPI = async () => {
  const res = await fetchWithNetworkError(`${API_URL}/xac-thuc/google/dang-nhap`);
  const data = await res.json().catch(() => null);
  if (!res.ok || !data?.data?.url)
    throw new Error("Không thể tải điểm cuối xác thực định danh Google");
  return data.data.url;
};
export const completeGoogleLoginAPI = async (code, state) => {
  const res = await fetchWithNetworkError(
    `${API_URL}/xac-thuc/google/chuyen-huong?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    { credentials: "include" },
  );
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, "Không thể xác thực bằng Google"));
  return data?.data || data;
};
