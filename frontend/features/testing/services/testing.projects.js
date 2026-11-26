import { aiRunRequest, listQuery, testingRequest } from "./testing.transport";

export const projectTestingApi = {
  getProjectRolePermissions: () => testingRequest("/quan-tri/vai-tro-du-an"),
  updateProjectRolePermissions: (payload) =>
    testingRequest("/quan-tri/vai-tro-du-an", { method: "PUT", body: JSON.stringify(payload) }),
  getProjectCapabilities: () => testingRequest("/du-an/kha-nang"),
  listEffectiveAccess: (projectId) =>
    testingRequest(`/du-an/${encodeURIComponent(projectId)}/quyen-hieu-luc`),
  listAIRunCapabilities: (projectId) =>
    aiRunRequest(`/du-an/${encodeURIComponent(projectId)}/nang-luc`),
  createAIRun: (payload) =>
    aiRunRequest("/luot-chay", { method: "POST", body: JSON.stringify(payload) }),
  getAIRun: (runId) => aiRunRequest(`/luot-chay/${runId}`),
  getAIRunEvidence: (runId) => aiRunRequest(`/luot-chay/${runId}/bang-chung`),
  listAIRuns: (projectId) => aiRunRequest(`/du-an/${projectId}/luot-chay`),
  resumeAIRun: (runId, payload) =>
    aiRunRequest(`/luot-chay/${runId}/uy-quyen-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cancelAIRun: (runId, payload) =>
    aiRunRequest(`/luot-chay/${runId}/huy`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProjects: (query = "", status = "active", limit = 200) => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (status) params.set("status", status);
    params.set("limit", String(limit));
    return testingRequest(`/du-an?${params.toString()}`);
  },
  createProject: (payload) =>
    testingRequest("/du-an", { method: "POST", body: JSON.stringify(payload) }),
  getProject: (id) => testingRequest(`/du-an/${id}`),
  listMembers: (id) => testingRequest(`/du-an/${id}/thanh-vien`),
  listInvitations: () => testingRequest("/loi-moi-du-an"),
  addMember: (id, payload) =>
    testingRequest(`/du-an/${id}/thanh-vien`, { method: "POST", body: JSON.stringify(payload) }),
  inviteMember: (id, payload) =>
    testingRequest(`/du-an/${id}/loi-moi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  acceptInvitation: (invitationId) =>
    testingRequest(`/loi-moi-du-an/${invitationId}/chap-nhan`, { method: "POST" }),
  declineInvitation: (invitationId) =>
    testingRequest(`/loi-moi-du-an/${invitationId}/tu-choi`, { method: "POST" }),
  leaveProject: (id) => testingRequest(`/du-an/${id}/roi-du-an`, { method: "POST" }),
  resendMemberInvite: (id, userId) =>
    testingRequest(`/du-an/${id}/thanh-vien/${userId}/gui-lai-loi-moi`, { method: "POST" }),
  cancelMemberInvite: (id, userId) =>
    testingRequest(`/du-an/${id}/thanh-vien/${userId}/huy-loi-moi`, { method: "POST" }),
  updateMember: (id, userId, payload) =>
    testingRequest(`/du-an/${id}/thanh-vien/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  removeMember: (id, userId) =>
    testingRequest(`/du-an/${id}/thanh-vien/${userId}`, { method: "DELETE" }),
  updateProject: (id, payload) =>
    testingRequest(`/du-an/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  updateProjectProgress: (id, payload) =>
    testingRequest(`/du-an/${id}/tien-do`, { method: "PATCH", body: JSON.stringify(payload) }),
  getProjectSettings: (id) => testingRequest(`/du-an/${id}/cai-dat`),
  updateProjectSettings: (id, payload) =>
    testingRequest(`/du-an/${id}/cai-dat`, { method: "PATCH", body: JSON.stringify(payload) }),
  archiveProject: (id, payload) =>
    testingRequest(`/du-an/${id}/luu-tru`, { method: "POST", body: JSON.stringify(payload) }),
  restoreProject: (id, payload) =>
    testingRequest(`/du-an/${id}/khoi-phuc`, { method: "POST", body: JSON.stringify(payload) }),
  dashboard: (id) => testingRequest(`/du-an/${id}/tong-quan`),
  getDefectClassificationOptions: (projectId) =>
    testingRequest(`/du-an/${projectId}/phan-loai-loi`),
  listTestConditions: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/dieu-kien-kiem-thu${query ? `?${query}` : ""}`);
  },
  createTestCondition: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/dieu-kien-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTestCondition: (conditionId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  submitTestCondition: (conditionId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  reviewTestCondition: (conditionId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}/ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveTestCondition: (conditionId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  archiveTestCondition: (conditionId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolveTestAnalysisFinding: (conditionId, findingId, payload) =>
    testingRequest(`/dieu-kien-kiem-thu/${conditionId}/ket-qua/${findingId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listTestAnalysisBasis: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(
      `/du-an/${projectId}/phan-tich-kiem-thu/co-so${query ? `?${query}` : ""}`,
    );
  },
  runDeterministicTestAnalysis: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/phan-tich-kiem-thu/kiem-tra`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listTestAnalysisFindings: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/ket-qua-phan-tich${query ? `?${query}` : ""}`);
  },
  createTestAnalysisFinding: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-qua-phan-tich`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  assignTestAnalysisFinding: (findingId, payload) =>
    testingRequest(`/ket-qua-phan-tich/${findingId}/phan-cong`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  resolveStandaloneTestAnalysisFinding: (findingId, payload) =>
    testingRequest(`/ket-qua-phan-tich/${findingId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyTestAnalysisFinding: (findingId, payload) =>
    testingRequest(`/ket-qua-phan-tich/${findingId}/xac-minh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  bulkPrioritizeTestConditions: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/dieu-kien-kiem-thu/uu-tien`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getLivePlanProgress: (projectId, planId) =>
    testingRequest(`/du-an/${projectId}/ke-hoach-kiem-thu/${planId}/tien-do`),
};
