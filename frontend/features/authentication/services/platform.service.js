import { API_URL, authenticatedFetch } from "@/shared/services/api-client";

async function platformRequest(path, options = {}) {
  const response = await authenticatedFetch(`${API_URL}/quan-tri${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      body?.detail ||
        body?.error?.message ||
        body?.message ||
        "Không thể hoàn tất thao tác quản trị",
    );
  }
  return body?.data;
}

async function downloadPlatformFile(path, filename) {
  const response = await authenticatedFetch(`${API_URL}/quan-tri${path}`);
  if (!response.ok) throw new Error("Không thể tải tệp quản trị");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const platformApi = {
  createUser: (payload) =>
    platformRequest("/tai-khoan", { method: "POST", body: JSON.stringify(payload) }),
  listUsers: (search = "") =>
    platformRequest(`/tai-khoan${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getUser: (id) => platformRequest(`/tai-khoan/${id}`),
  updateProfile: (id, payload) =>
    platformRequest(`/tai-khoan/${id}/ho-so`, { method: "PATCH", body: JSON.stringify(payload) }),
  enableUser: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/kich-hoat`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  disableUser: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/vo-hieu-hoa`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  lockUser: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/khoa`, { method: "POST", body: JSON.stringify({ reason }) }),
  unlockUser: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/mo-khoa`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  forcePasswordReset: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/bat-buoc-doi-mat-khau`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  updateSystemRole: (id, systemRole, reason) =>
    platformRequest(`/tai-khoan/${id}/vai-tro-he-thong`, {
      method: "PATCH",
      body: JSON.stringify({ system_role: systemRole, reason }),
    }),
  listSessions: (id) => platformRequest(`/tai-khoan/${id}/phien`),
  revokeSession: (id, sessionId) =>
    platformRequest(`/tai-khoan/${id}/phien/${sessionId}`, { method: "DELETE" }),
  revokeAllSessions: (id) => platformRequest(`/tai-khoan/${id}/phien`, { method: "DELETE" }),
  resendVerification: (id, reason) =>
    platformRequest(`/tai-khoan/${id}/gui-lai-xac-minh`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  deleteUser: (id, confirmation, reason) =>
    platformRequest(`/tai-khoan/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirmation, reason }),
    }),
  previewBulkUsers: (action, userIds, reason) =>
    platformRequest("/tai-khoan/hang-loat/xem-truoc", {
      method: "POST",
      body: JSON.stringify({ action, user_ids: userIds, reason }),
    }),
  confirmBulkUsers: (operationId) =>
    platformRequest(`/tai-khoan/hang-loat/${operationId}/xac-nhan`, {
      method: "POST",
      body: JSON.stringify({ confirmation: "CONFIRM" }),
    }),
  listMemberships: (id) => platformRequest(`/tai-khoan/${id}/vai-tro-du-an`),
  listUserAudit: (id) => platformRequest(`/tai-khoan/${id}/nhat-ky`),
  listProjects: (search = "") =>
    platformRequest(`/du-an${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getProject: (id) => platformRequest(`/du-an/${id}`),
  listProjectMemberships: (id) => platformRequest(`/du-an/${id}/vai-tro-du-an`),
  updateProjectStatus: (id, status, reason) =>
    platformRequest(`/du-an/${id}/trang-thai`, {
      method: "PATCH",
      body: JSON.stringify({ status, reason }),
    }),
  updateProjectQuota: (id, values, reason) =>
    platformRequest(`/du-an/${id}/han-muc`, {
      method: "PATCH",
      body: JSON.stringify({ ...values, reason }),
    }),
  deleteProject: (id, confirmation, reason) =>
    platformRequest(`/du-an/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirmation, reason }),
    }),
  getProjectPolicy: () => platformRequest("/nen-tang/chinh-sach-du-an"),
  updateProjectPolicy: (projectCreationPolicy, reason) =>
    platformRequest("/nen-tang/chinh-sach-du-an", {
      method: "PATCH",
      body: JSON.stringify({ project_creation_policy: projectCreationPolicy, reason }),
    }),
  listProviders: () => platformRequest("/ai/nha-cung-cap"),
  listModels: () => platformRequest("/ai/mo-hinh"),
  getAiDefaults: () => platformRequest("/ai/mac-dinh"),
  updateAiDefaults: (values, reason) =>
    platformRequest("/ai/mac-dinh", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  getAiVersions: () => platformRequest("/ai/phien-ban"),
  getAiLimits: () => platformRequest("/ai/gioi-han"),
  updateAiLimits: (values, reason) =>
    platformRequest("/ai/gioi-han", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  getAiRetrieval: () => platformRequest("/ai/truy-xuat"),
  updateAiRetrieval: (values, reason) =>
    platformRequest("/ai/truy-xuat", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  registerModel: (payload) =>
    platformRequest("/ai/mo-hinh", { method: "POST", body: JSON.stringify(payload) }),
  updateModel: (id, payload) =>
    platformRequest(`/ai/mo-hinh/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  getAuthPolicy: () => platformRequest("/bao-mat/chinh-sach-xac-thuc"),
  updateAuthPolicy: (values, reason) =>
    platformRequest("/bao-mat/chinh-sach-xac-thuc", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  getRateLimits: () => platformRequest("/bao-mat/gioi-han-tan-suat"),
  updateRateLimits: (values, reason) =>
    platformRequest("/bao-mat/gioi-han-tan-suat", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  listServiceIdentities: () => platformRequest("/bao-mat/danh-tinh-dich-vu"),
  createServiceIdentity: (payload) =>
    platformRequest("/bao-mat/danh-tinh-dich-vu", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  rotateServiceIdentity: (id, secretReference, reason) =>
    platformRequest(`/bao-mat/danh-tinh-dich-vu/${id}/xoay-vong`, {
      method: "POST",
      body: JSON.stringify({ secret_reference: secretReference, reason }),
    }),
  listBreakGlass: () => platformRequest("/bao-mat/truy-cap-khan-cap"),
  createBreakGlass: (payload) =>
    platformRequest("/bao-mat/truy-cap-khan-cap", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeBreakGlass: (id, reason) =>
    platformRequest(`/bao-mat/truy-cap-khan-cap/${id}/thu-hoi`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  getBreakGlassPolicy: () => platformRequest("/bao-mat/chinh-sach-truy-cap-khan-cap"),
  updateBreakGlassPolicy: (values, reason) =>
    platformRequest("/bao-mat/chinh-sach-truy-cap-khan-cap", {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  emergencyRevoke: (payload) =>
    platformRequest("/bao-mat/thu-hoi-khan-cap", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSecurityAudit: () => platformRequest("/bao-mat/nhat-ky"),
  getIntegrations: () => platformRequest("/tich-hop"),
  updateIntegrations: (values, reason) =>
    platformRequest("/tich-hop", { method: "PATCH", body: JSON.stringify({ values, reason }) }),
  getIntegrationHealth: () => platformRequest("/tich-hop/suc-khoe"),
  testSmtp: (recipient, reason) =>
    platformRequest("/tich-hop/smtp/kiem-tra", {
      method: "POST",
      body: JSON.stringify({ recipient, reason }),
    }),
  getStorage: () => platformRequest("/luu-tru"),
  updateStorage: (values, reason) =>
    platformRequest("/luu-tru", { method: "PATCH", body: JSON.stringify({ values, reason }) }),
  testStorage: () => platformRequest("/luu-tru/kiem-tra", { method: "POST" }),
  listSecrets: () => platformRequest("/bi-mat"),
  createSecret: (payload) =>
    platformRequest("/bi-mat", { method: "POST", body: JSON.stringify(payload) }),
  rotateSecret: (id, reference, reason) =>
    platformRequest(`/bi-mat/${id}/xoay-vong`, {
      method: "POST",
      body: JSON.stringify({ reference, reason }),
    }),
  deleteSecret: (id, reason) =>
    platformRequest(`/bi-mat/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ reason }),
    }),
  updateProvider: (id, payload) =>
    platformRequest(`/ai/nha-cung-cap/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  testProvider: (id) => platformRequest(`/ai/nha-cung-cap/${id}/kiem-tra`, { method: "POST" }),
  getHealth: () => platformRequest("/suc-khoe"),
  getMetrics: () => platformRequest("/van-hanh/so-lieu"),
  getQueue: () => platformRequest("/van-hanh/hang-doi"),
  getDlq: () => platformRequest("/van-hanh/dlq"),
  requeueDlq: (id, reason) =>
    platformRequest(`/van-hanh/dlq/${id}/dua-lai-hang-doi`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  discardDlq: (id, reason) =>
    platformRequest(`/van-hanh/dlq/${id}/loai-bo`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  cancelJob: (id) => platformRequest(`/van-hanh/tac-vu/${id}/huy`, { method: "POST" }),
  getRagOperations: () => platformRequest("/van-hanh/rag"),
  requestRagReindex: (payload) =>
    platformRequest("/van-hanh/rag/lap-chi-muc-lai", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCache: () => platformRequest("/van-hanh/bo-nho-dem"),
  clearCache: (scope, reason) =>
    platformRequest("/van-hanh/bo-nho-dem/don-sach", {
      method: "POST",
      body: JSON.stringify({ scope, confirmation: "CLEAR_SAFE_CACHE", reason }),
    }),
  getStorageUsage: () => platformRequest("/van-hanh/dung-luong-luu-tru"),
  getRuntimeVersions: () => platformRequest("/van-hanh/phien-ban-van-hanh"),
  getMaintenance: () => platformRequest("/cau-hinh/bao-tri"),
  updateMaintenance: (enabled, banner, reason) =>
    platformRequest("/cau-hinh/bao-tri", {
      method: "PATCH",
      body: JSON.stringify({ enabled, banner, reason }),
    }),
  getPlatformConfigGroup: (name) => platformRequest(`/cau-hinh/${name}`),
  updatePlatformConfigGroup: (name, values, reason) =>
    platformRequest(`/cau-hinh/${name}`, {
      method: "PATCH",
      body: JSON.stringify({ values, reason }),
    }),
  getAudit: () => platformRequest("/nhat-ky"),
  exportAudit: () => downloadPlatformFile("/nhat-ky/xuat", "veriq-global-audit.csv"),
  listJobs: (status = "") =>
    platformRequest(`/van-hanh/tac-vu${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  retryJob: (id) => platformRequest(`/van-hanh/tac-vu/${id}/thu-lai`, { method: "POST" }),
};
