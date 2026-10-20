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
export async function refreshAccessToken() {
  if (typeof window === "undefined") return null;
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_URL}/xac-thuc/lam-moi-phien`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) return null;
        const body = await response.json();
        const token = body?.data?.access_token;
        if (typeof token !== "string" || !token) return null;
        applyToken(token);
        return token;
      })
      .catch(() => null)
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
  const replacement = await refreshAccessToken();
  if (!replacement) return response;
  headers.set("Authorization", `Bearer ${replacement}`);
  return fetchWithNetworkError(input, {
    ...request,
    headers,
  });
}
