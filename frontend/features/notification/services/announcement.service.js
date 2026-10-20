import { API_URL, authenticatedFetch, getToken } from "@/shared/services/api-client";
export const getAnnouncementsAPI = async () => {
  const token = getToken();
  if (!token) throw new Error("Yêu cầu xác thực tài khoản để thực hiện thao tác");
  const res = await authenticatedFetch(`${API_URL}/thong-bao`);
  const resultData = await res.json();
  if (!res.ok) throw new Error(resultData.message || "Không thể tải dữ liệu thông báo");
  return resultData;
};
export const markAnnouncementReadAPI = async (id) => {
  const res = await authenticatedFetch(`${API_URL}/thong-bao/${id}/doc-hieu`, {
    method: "PATCH",
  });
  const resultData = await res.json();
  if (!res.ok) throw new Error(resultData.message || "Không thể cập nhật trạng thái thông báo");
  return resultData;
};
export const markAllAnnouncementsReadAPI = async () => {
  const res = await authenticatedFetch(`${API_URL}/thong-bao/doc-tat-ca`, {
    method: "PATCH",
  });
  const resultData = await res.json();
  if (!res.ok) throw new Error(resultData.message || "Không thể cập nhật trạng thái hàng loạt");
  return resultData;
};
export const deleteAnnouncementAPI = async (id) => {
  const res = await authenticatedFetch(`${API_URL}/thong-bao/${id}`, {
    method: "DELETE",
  });
  const resultData = await res.json();
  if (!res.ok) throw new Error(resultData.message || "Không thể xóa thông báo");
  return resultData;
};
export const getAnnouncementSettingsAPI = async () => {
  if (!getToken()) throw new Error("Yêu cầu xác thực tài khoản để thực hiện thao tác");
  const res = await authenticatedFetch(`${API_URL}/thong-bao/cai-dat`);
  if (!res.ok) throw new Error("Không thể tải cấu hình hệ thống thông báo");
  return await res.json();
};
export const updateAnnouncementSettingsAPI = async (settings) => {
  if (!getToken()) throw new Error("Yêu cầu xác thực tài khoản để thực hiện thao tác");
  const res = await authenticatedFetch(`${API_URL}/thong-bao/cai-dat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Không thể lưu cấu hình hệ thống thông báo");
  return await res.json();
};
