import {
  agentReadRequest,
  agentRequest,
  downloadTestingFile,
  listQuery,
  testingRequest,
  testingStreamRequest,
} from "./testing.transport";

export const projectTestingApi = {
  listAgentCapabilities: (projectId) => agentReadRequest(`/du-an/${projectId}/nang-luc`),
  runAgent: (payload) =>
    agentRequest("/luot-chay", { method: "POST", body: JSON.stringify(payload) }),
  getAgentRun: (runId) => agentRequest(`/luot-chay/${runId}`),
  decideAgentRun: (runId, payload) =>
    agentRequest(`/luot-chay/${runId}/quyet-dinh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProjects: (query = "", status = "active") => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (status) params.set("status", status);
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
  listProjectTasks: (id, status = "") =>
    testingRequest(
      `/du-an/${id}/cong-viec${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  createProjectTask: (id, payload) =>
    testingRequest(`/du-an/${id}/cong-viec`, { method: "POST", body: JSON.stringify(payload) }),
  updateProjectTask: (id, taskId, payload) =>
    testingRequest(`/du-an/${id}/cong-viec/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteProjectTask: (id, taskId, payload) =>
    testingRequest(`/du-an/${id}/cong-viec/${taskId}`, {
      method: "DELETE",
      body: JSON.stringify(payload),
    }),
  getProjectSettings: (id) => testingRequest(`/du-an/${id}/cai-dat`),
  updateProjectSettings: (id, payload) =>
    testingRequest(`/du-an/${id}/cai-dat`, { method: "PATCH", body: JSON.stringify(payload) }),
  archiveProject: (id, payload) =>
    testingRequest(`/du-an/${id}/luu-tru`, { method: "POST", body: JSON.stringify(payload) }),
  restoreProject: (id, payload) =>
    testingRequest(`/du-an/${id}/khoi-phuc`, { method: "POST", body: JSON.stringify(payload) }),
  dashboard: (id) => testingRequest(`/du-an/${id}/tong-quan`),
  listTestStrategies: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/chien-luoc${query ? `?${query}` : ""}`);
  },
  createTestStrategy: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/chien-luoc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTestStrategy: (strategyId) => testingRequest(`/chien-luoc/${strategyId}`),
  updateTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  submitTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestTestStrategyChanges: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/yeu-cau-chinh-sua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  reviewTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  versionTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/tao-phien-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compareTestStrategyVersions: (strategyId, otherStrategyId) =>
    testingRequest(
      `/chien-luoc/${strategyId}/so-sanh?other_strategy_id=${encodeURIComponent(otherStrategyId)}`,
    ),
  cloneTestStrategy: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/chien-luoc/nhan-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  validateTestStrategy: (strategyId) =>
    testingRequest(`/chien-luoc/${strategyId}/kiem-tra`, { method: "POST" }),
  archiveTestStrategy: (strategyId, payload) =>
    testingRequest(`/chien-luoc/${strategyId}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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
  runTestAnalysisAi: (projectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/phan-tich-kiem-thu/ai`, {
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
  getTestConditionCoverage: (projectId) =>
    testingRequest(`/du-an/${projectId}/phan-tich-kiem-thu/truy-vet`),
  listMonitoringSnapshots: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/giam-sat-kiem-thu${query ? `?${query}` : ""}`);
  },
  createMonitoringSnapshot: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/giam-sat-kiem-thu/anh-chup`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMonitoringSnapshot: (snapshotId) =>
    testingRequest(`/giam-sat-kiem-thu/anh-chup/${snapshotId}`),
  overrideMonitoringCriterion: (snapshotId, payload) =>
    testingRequest(`/giam-sat-kiem-thu/anh-chup/${snapshotId}/ghi-de-tieu-chi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getQualityGate: (snapshotId) =>
    testingRequest(`/giam-sat-kiem-thu/anh-chup/${snapshotId}/danh-gia-chat-luong`),
  listQualityDecisions: (projectId, releaseId = "") =>
    testingRequest(
      `/du-an/${projectId}/quyet-dinh-chat-luong${releaseId ? `?release_id=${encodeURIComponent(releaseId)}` : ""}`,
    ),
  createQualityDecision: (snapshotId, payload) =>
    testingRequest(`/giam-sat-kiem-thu/anh-chup/${snapshotId}/quyet-dinh-chat-luong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportQualityGate: (snapshotId) =>
    testingRequest(`/giam-sat-kiem-thu/anh-chup/${snapshotId}/xuat-bang-chung`),
  listControlActions: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/hanh-dong-dieu-khien${query ? `?${query}` : ""}`);
  },
  createControlAction: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hanh-dong-dieu-khien`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateControlAction: (actionId, payload) =>
    testingRequest(`/hanh-dong-dieu-khien/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listTestStatusReports: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/bao-cao-trang-thai${query ? `?${query}` : ""}`);
  },
  generateTestStatusReport: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/bao-cao-trang-thai/tao-tu-anh-chup`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTestStatusReport: (reportId) => testingRequest(`/bao-cao-trang-thai/${reportId}`),
  updateTestStatusReport: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  draftTestStatusReportNarrative: (reportId, payload) =>
    testingStreamRequest(`/bao-cao-trang-thai/${reportId}/ai/ban-nhap`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  attachTestStatusReportEvidence: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/bang-chung`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitTestStatusReport: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestTestStatusReportChanges: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/yeu-cau-chinh-sua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveTestStatusReport: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  publishTestStatusReport: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/phat-hanh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  archiveTestStatusReport: (reportId, payload) =>
    testingRequest(`/bao-cao-trang-thai/${reportId}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compareTestStatusReports: (reportId, otherReportId) =>
    testingRequest(
      `/bao-cao-trang-thai/${reportId}/so-sanh?other_report_id=${encodeURIComponent(otherReportId)}`,
    ),
  exportTestStatusReport: (reportId, format) =>
    downloadTestingFile(
      `/bao-cao-trang-thai/${reportId}/xuat?format=${encodeURIComponent(format)}`,
      `test-status-report-${reportId}.${format}`,
    ),
  listTestCompletionReports: (projectId, filters = {}) => {
    const query = listQuery(filters);
    return testingRequest(`/du-an/${projectId}/hoan-tat-kiem-thu${query ? `?${query}` : ""}`);
  },
  createTestCompletionReport: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hoan-tat-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTestCompletionReport: (reportId) => testingRequest(`/hoan-tat-kiem-thu/${reportId}`),
  updateTestCompletionReport: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  draftTestCompletionNarrative: (reportId, payload) =>
    testingStreamRequest(`/hoan-tat-kiem-thu/${reportId}/ai/ban-nhap`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  clusterTestCompletionLessons: (reportId, payload) =>
    testingStreamRequest(`/hoan-tat-kiem-thu/${reportId}/ai/gom-bai-hoc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addTestCompletionResidualRisk: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/rui-ro`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addTestCompletionLesson: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/bai-hoc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  manageTestCompletionHandover: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/ban-giao`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  submitTestCompletionReport: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestTestCompletionChanges: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/yeu-cau-chinh-sua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  signOffTestCompletion: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/ky-xac-nhan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  decideTestCompletionResidualRisk: (reportId, riskId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/rui-ro/${riskId}/xu-ly`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveTestCompletionReport: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  closeTestCompletionReport: (reportId, payload) =>
    testingRequest(`/hoan-tat-kiem-thu/${reportId}/dong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportTestCompletionReport: (reportId, format) =>
    downloadTestingFile(
      `/hoan-tat-kiem-thu/${reportId}/xuat?format=${encodeURIComponent(format)}`,
      `test-completion-${reportId}.${format}`,
    ),
};
