const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
if (!configuredApiUrl) throw new Error("NEXT_PUBLIC_API_URL is required");
export const API_URL = configuredApiUrl;
export function getToken() {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("veriq_token");
  return token && token !== "null" && token !== "undefined" ? token : null;
}
export function getAuthHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
export async function fetchWithNetworkError(input, init) {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Không thể kết nối đến máy chủ Veriq. Vui lòng thử lại sau", {
        cause: error,
      });
    }
    throw error;
  }
}
let refreshPromise = null;
function applyToken(token) {
  localStorage.setItem("veriq_token", token);
  document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
}
export async function refreshAccessToken(expectedToken) {
  if (typeof window === "undefined") return null;
  if (!refreshPromise) {
    refreshPromise = fetchWithNetworkError(`${API_URL}/xac-thuc/lam-moi-phien`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (response.status === 401 || response.status === 403) return null;
        if (!response.ok) {
          throw new Error("Không thể làm mới phiên đăng nhập. Vui lòng thử lại.");
        }
        let body;
        try {
          body = await response.json();
        } catch (error) {
          throw new Error("Máy chủ trả về phiên đăng nhập không hợp lệ", { cause: error });
        }
        const token = body?.data?.access_token;
        if (typeof token !== "string" || !token) {
          throw new Error("Máy chủ không trả về phiên đăng nhập mới");
        }
        if (expectedToken && getToken() !== expectedToken) return getToken();
        applyToken(token);
        return token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}
export async function authenticatedFetch(input, init = {}) {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const request = {
    ...init,
    headers,
    credentials: init.credentials || "include",
  };
  const response = await fetchWithNetworkError(input, request);
  if (response.status !== 401) return response;
  const replacement = await refreshAccessToken(token);
  if (!replacement) {
    if (token && getToken() === token && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("veriq-session-expired"));
    }
    return response;
  }
  headers.set("Authorization", `Bearer ${replacement}`);
  return fetchWithNetworkError(input, {
    ...request,
    headers,
  });
}
