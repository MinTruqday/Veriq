import { API_URL, authenticatedFetch, getAuthHeaders } from "@/shared/services/api-client";
export async function uploadAssetAPI(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await authenticatedFetch(`${API_URL}/tai-len/tap-tin`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.error?.message || body?.detail || body?.message;
    throw new Error(
      typeof detail === "string" && detail ? detail : "Không thể tải tệp lên. Vui lòng thử lại.",
    );
  }
  return body;
}
