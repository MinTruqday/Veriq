import {
  downloadTestingFile,
  listPage,
  listQuery,
  testingRequest,
  testingStreamRequest,
} from "./testing.transport";

export const executionTestingApi = {
  listJUnitResultImports: (projectId) =>
    testingRequest(`/du-an/${projectId}/ket-qua-tu-dong/junit`),
  importJUnitResult: (projectId, testRunId, file) => {
    const body = new FormData();
    body.append("test_run_id", testRunId);
    body.append("file", file);
    return testingRequest(`/du-an/${projectId}/ket-qua-tu-dong/junit`, { method: "POST", body });
  },
  resolveJUnitResultMapping: (importId, payload) =>
    testingRequest(`/ket-qua-tu-dong/junit/${importId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listPlans: (id, query = "") => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/ke-hoach-kiem-thu${value ? `?${value}` : ""}`);
  },
  createPlan: (payload) =>
    testingRequest("/ke-hoach-kiem-thu", { method: "POST", body: JSON.stringify(payload) }),
  updatePlan: (id, payload) =>
    testingRequest(`/ke-hoach-kiem-thu/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  validatePlan: (id) => testingRequest(`/ke-hoach-kiem-thu/${id}/kiem-tra`, { method: "POST" }),
  submitPlan: (id, payload) =>
    testingRequest(`/ke-hoach-kiem-thu/${id}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approvePlan: (id, payload) =>
    testingRequest(`/ke-hoach-kiem-thu/${id}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  archivePlan: (id, payload) =>
    testingRequest(`/ke-hoach-kiem-thu/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  clonePlan: (id) => testingRequest(`/ke-hoach-kiem-thu/${id}/nhan-ban`, { method: "POST" }),
  listSuites: (id, query = "") => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/bo-kiem-thu${value ? `?${value}` : ""}`);
  },
  listReleases: (id, query = {}) => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/ban-phat-hanh${value ? `?${value}` : ""}`);
  },
  createRelease: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/ban-phat-hanh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  activateRelease: (releaseId, payload) =>
    testingRequest(`/ban-phat-hanh/${releaseId}/kich-hoat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  closeRelease: (releaseId, payload) =>
    testingRequest(`/ban-phat-hanh/${releaseId}/dong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listBuilds: (id, query = {}) => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/ban-dung${value ? `?${value}` : ""}`);
  },
  listEnvironments: (id) => testingRequest(`/du-an/${id}/moi-truong`),
  listDeviceMatrices: (id, includeArchived = false) =>
    testingRequest(`/du-an/${id}/ma-tran-thiet-bi?include_archived=${includeArchived}`),
  getDeviceMatrix: (id) => testingRequest(`/ma-tran-thiet-bi/${id}`),
  createDeviceMatrix: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/ma-tran-thiet-bi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateDeviceMatrix: (id, payload) =>
    testingRequest(`/ma-tran-thiet-bi/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveDeviceMatrix: (id, payload) =>
    testingRequest(`/ma-tran-thiet-bi/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  assignDeviceMatrix: (id, payload) =>
    testingRequest(`/ma-tran-thiet-bi/${id}/gan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProjectNotificationWatches: (projectId, artifactType = "") =>
    testingRequest(
      `/du-an/${projectId}/thong-bao/theo-doi${artifactType ? `?artifact_type=${encodeURIComponent(artifactType)}` : ""}`,
    ),
  setProjectNotificationWatch: (projectId, artifactType, artifactId, watching) =>
    testingRequest(`/du-an/${projectId}/thong-bao/theo-doi/${artifactType}/${artifactId}`, {
      method: "PUT",
      body: JSON.stringify({ watching }),
    }),
  getProjectNotificationRules: (projectId) =>
    testingRequest(`/du-an/${projectId}/thong-bao/quy-tac`),
  updateProjectNotificationRules: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/thong-bao/quy-tac`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getProjectNotificationPreferences: (projectId) =>
    testingRequest(`/du-an/${projectId}/thong-bao/tuy-chon`),
  updateProjectNotificationPreferences: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/thong-bao/tuy-chon`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listSecurityTestSuggestions: (projectId) =>
    testingRequest(`/du-an/${projectId}/ai/goi-y-kiem-thu-bao-mat`),
  generateSecurityTestSuggestions: (projectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/ai/goi-y-kiem-thu-bao-mat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listPerformancePlanDrafts: (projectId) =>
    testingRequest(`/du-an/${projectId}/ai/ke-hoach-hieu-nang`),
  generatePerformancePlanDraft: (projectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/ai/ke-hoach-hieu-nang`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAutomationScriptDrafts: (projectId) =>
    testingRequest(`/du-an/${projectId}/ban-nhap-kich-ban-tu-dong`),
  getAutomationScriptDraft: (draftId) => testingRequest(`/ban-nhap-kich-ban-tu-dong/${draftId}`),
  generateAutomationScriptDraft: (projectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/ai/ban-nhap-kich-ban-tu-dong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateAutomationScriptDraft: (draftId, payload) =>
    testingRequest(`/ban-nhap-kich-ban-tu-dong/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  approveAutomationScriptDraft: (draftId, payload) =>
    testingRequest(`/ban-nhap-kich-ban-tu-dong/${draftId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportAutomationScriptDraft: (draftId, filename) =>
    downloadTestingFile(`/ban-nhap-kich-ban-tu-dong/${draftId}/xuat`, filename),
  listProjectConnectors: (projectId) => testingRequest(`/du-an/${projectId}/ket-noi`),
  bindProjectConnector: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-noi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProjectConnector: (projectId, connectorId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-noi/${connectorId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  unbindProjectConnector: (projectId, connectorId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-noi/${connectorId}/ngat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startProjectConnectorSync: (projectId, connectorId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-noi/${connectorId}/dong-bo`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProjectConnectorSyncLog: (projectId) => testingRequest(`/du-an/${projectId}/ket-noi/nhat-ky`),
  listProjectConnectorConflicts: (projectId) =>
    testingRequest(`/du-an/${projectId}/ket-noi/xung-dot`),
  resolveProjectConnectorConflict: (projectId, conflictId, payload) =>
    testingRequest(`/du-an/${projectId}/ket-noi/xung-dot/${conflictId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAutomationExecutions: (projectId) => testingRequest(`/du-an/${projectId}/thuc-thi-tu-dong`),
  getAutomationExecution: (executionId) => testingRequest(`/thuc-thi-tu-dong/${executionId}`),
  createAutomationExecution: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/thuc-thi-tu-dong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startAutomationExecution: (executionId, payload) =>
    testingRequest(`/thuc-thi-tu-dong/${executionId}/bat-dau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cancelAutomationExecution: (executionId, payload) =>
    testingRequest(`/thuc-thi-tu-dong/${executionId}/huy`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAutomationEvidence: (executionId) =>
    testingRequest(`/thuc-thi-tu-dong/${executionId}/bang-chung`),
  getCicdState: (projectId) => testingRequest(`/du-an/${projectId}/tich-hop-trien-khai-lien-tuc`),
  createCicdBinding: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/tich-hop-trien-khai-lien-tuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCicdBinding: (projectId, bindingId, payload) =>
    testingRequest(`/du-an/${projectId}/tich-hop-trien-khai-lien-tuc/${bindingId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  retryCicdRun: (projectId, runId, payload) =>
    testingRequest(`/du-an/${projectId}/tich-hop-trien-khai-lien-tuc/lan-chay/${runId}/thu-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCollaborationPresence: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/cong-tac/phien`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listCollaborationPresence: (projectId, artifactType, artifactId) =>
    testingRequest(
      `/du-an/${projectId}/cong-tac/hien-dien?artifact_type=${encodeURIComponent(artifactType)}&artifact_id=${encodeURIComponent(artifactId)}`,
    ),
  applyRequirementCollaborationOperation: (projectId, artifactId, payload) =>
    testingRequest(`/du-an/${projectId}/cong-tac/yeu-cau/${artifactId}/thao-tac`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyTestCaseCollaborationOperation: (projectId, artifactId, payload) =>
    testingRequest(`/du-an/${projectId}/cong-tac/ca-kiem-thu/${artifactId}/thao-tac`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listCollaborationConflicts: (projectId) =>
    testingRequest(`/du-an/${projectId}/cong-tac/xung-dot`),
  resolveCollaborationConflict: (projectId, conflictId, payload) =>
    testingRequest(`/du-an/${projectId}/cong-tac/xung-dot/${conflictId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listWebhookSubscriptions: (projectId, includeDisabled = true) =>
    testingRequest(`/du-an/${projectId}/moc-goi?include_disabled=${includeDisabled}`),
  createWebhookSubscription: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/moc-goi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateWebhookSubscription: (projectId, subscriptionId, payload) =>
    testingRequest(`/du-an/${projectId}/moc-goi/${subscriptionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listWebhookDeliveries: (projectId, status = "") =>
    testingRequest(
      `/du-an/${projectId}/moc-goi/giao-hang${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  replayWebhookDelivery: (projectId, deliveryId, payload) =>
    testingRequest(`/du-an/${projectId}/moc-goi/giao-hang/${deliveryId}/phat-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createSuite: (payload) =>
    testingRequest("/bo-kiem-thu", { method: "POST", body: JSON.stringify(payload) }),
  updateSuite: (id, payload) =>
    testingRequest(`/bo-kiem-thu/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  cloneSuite: (id) => testingRequest(`/bo-kiem-thu/${id}/nhan-ban`, { method: "POST" }),
  archiveSuite: (id, payload) =>
    testingRequest(`/bo-kiem-thu/${id}/luu-tru`, { method: "POST", body: JSON.stringify(payload) }),
  listRunPage: (id, query = "") => listPage(`/du-an/${id}/lan-chay-kiem-thu`, query),
  listRuns: (id, query = "") =>
    listPage(`/du-an/${id}/lan-chay-kiem-thu`, query).then((result) => result.items),
  listResults: (id, status = "") =>
    testingRequest(
      `/du-an/${id}/ket-qua-kiem-thu${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  createRun: (payload) =>
    testingRequest("/lan-chay-kiem-thu", { method: "POST", body: JSON.stringify(payload) }),
  getRun: (id) => testingRequest(`/lan-chay-kiem-thu/${id}`),
  startRun: (id) => testingRequest(`/lan-chay-kiem-thu/${id}/bat-dau`, { method: "POST" }),
  resumeRun: (projectId, runId, payload) =>
    testingRequest(`/du-an/${projectId}/lan-chay-kiem-thu/${runId}/tiep-tuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordResult: (runId, versionId, payload) =>
    testingRequest(`/lan-chay-kiem-thu/${runId}/ket-qua/${versionId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateExecution: (projectId, executionId, payload) =>
    testingRequest(`/du-an/${projectId}/thuc-thi-kiem-thu/${executionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  completeRun: (id) => testingRequest(`/lan-chay-kiem-thu/${id}/hoan-tat`, { method: "POST" }),
  abortRun: (id, reason) =>
    testingRequest(`/lan-chay-kiem-thu/${id}/huy`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  exportRunReport: (id) =>
    downloadTestingFile(`/lan-chay-kiem-thu/${id}/bao-cao`, `test-run-${id}.csv`),
  listDefectPage: (id, query = "") => listPage(`/du-an/${id}/loi`, query),
  listDefects: (id, query = "") =>
    listPage(`/du-an/${id}/loi`, query).then((result) => result.items),
  findDuplicateDefects: (id) => testingRequest(`/du-an/${id}/loi/trung-lap`),
  suggestDefectTrace: (projectId, defectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/ai/loi/${defectId}/goi-y-truy-vet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateDefectTrace: (projectId, defectId, payload) =>
    testingRequest(`/du-an/${projectId}/loi/${defectId}/truy-vet`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  exportDefects: (id) => downloadTestingFile(`/du-an/${id}/loi/xuat`, `defects-${id}.csv`),
  createDefect: (id, payload) =>
    testingRequest(`/du-an/${id}/loi`, { method: "POST", body: JSON.stringify(payload) }),
  updateDefect: (id, payload) =>
    testingRequest(`/loi/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  transitionDefect: (id, payload) =>
    testingRequest(`/loi/${id}/chuyen-trang-thai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  retestDefect: (projectId, defectId, payload) =>
    testingRequest(`/du-an/${projectId}/loi/${defectId}/kiem-thu-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  searchKnowledge: (id, payload) =>
    testingRequest(`/du-an/${id}/tri-thuc/tim-kiem`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  askProject: (id, payload) =>
    testingStreamRequest(`/du-an/${id}/ai/hoi-dap`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  audit: (id) => testingRequest(`/du-an/${id}/nhat-ky`),
  maintenanceAnalytics: (id) => testingRequest(`/du-an/${id}/phan-tich-bao-tri`),
  aiAnalytics: (id) => testingRequest(`/du-an/${id}/phan-tich-ai`),
  executionReport: (id, scope = {}) =>
    testingRequest(`/du-an/${id}/bao-cao/thuc-thi?${listQuery(scope)}`),
  defectReport: (id, scope = {}) => testingRequest(`/du-an/${id}/bao-cao/loi?${listQuery(scope)}`),
  projectActivity: (id) => testingRequest(`/du-an/${id}/hoat-dong`),
  operations: (query = "") => testingRequest(`/van-hanh${query ? `?${query}` : ""}`),
  retryOperationJob: (jobId) =>
    testingRequest(`/van-hanh/tac-vu/${jobId}/thu-lai`, { method: "POST" }),
};
