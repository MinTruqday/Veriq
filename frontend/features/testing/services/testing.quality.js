import {
  downloadTestingFile,
  inferenceRequest,
  listQuery,
  testingRequest,
} from "./testing.transport";

export const qualityTestingApi = {
  listSyntheticTestabilityBenchmarkRuns: (limit = 20) =>
    inferenceRequest(
      `/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/tong-hop/lan-chay?limit=${encodeURIComponent(limit)}`,
    ),
  runSyntheticTestabilityBenchmark: () =>
    inferenceRequest("/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/tong-hop/chay-lap", {
      method: "POST",
    }),
  listReviewSessions: (projectId, filters = {}) =>
    testingRequest(`/du-an/${projectId}/phien-ra-soat?${listQuery(filters)}`),
  createReviewSession: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/phien-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getReviewSession: (reviewId) => testingRequest(`/phien-ra-soat/${reviewId}`),
  updateReviewSession: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  assignReviewSessionReviewers: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/nguoi-ra-soat`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  startReviewSession: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/bat-dau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createReviewFinding: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/ket-qua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  assignReviewFinding: (findingId, payload) =>
    testingRequest(`/phien-ra-soat/ket-qua/${findingId}/gan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolveReviewFinding: (findingId, payload) =>
    testingRequest(`/phien-ra-soat/ket-qua/${findingId}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyReviewFinding: (findingId, payload) =>
    testingRequest(`/phien-ra-soat/ket-qua/${findingId}/xac-minh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordReviewSessionDecision: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/quyet-dinh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  completeReviewSession: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/hoan-tat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  transitionReviewSessionTerminal: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/trang-thai-cuoi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getReviewSessionMetrics: (reviewId) => testingRequest(`/phien-ra-soat/${reviewId}/so-lieu`),
  createFollowUpReviewSession: (reviewId, payload) =>
    testingRequest(`/phien-ra-soat/${reviewId}/phien-tiep-theo`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportReviewSession: (reviewId) =>
    downloadTestingFile(`/phien-ra-soat/${reviewId}/xuat`, `formal-review-${reviewId}.csv`),
  listMeasurementDefinitions: (projectId) =>
    testingRequest(`/du-an/${projectId}/dinh-nghia-do-luong`),
  createMeasurementDefinition: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/dinh-nghia-do-luong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateMeasurementDefinition: (definitionId, payload) =>
    testingRequest(`/dinh-nghia-do-luong/${definitionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  versionMeasurementDefinition: (definitionId, payload) =>
    testingRequest(`/dinh-nghia-do-luong/${definitionId}/tao-phien-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  transitionMeasurementDefinition: (definitionId, payload) =>
    testingRequest(`/dinh-nghia-do-luong/${definitionId}/trang-thai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listMeasurementSnapshots: (projectId, filters = {}) =>
    testingRequest(`/du-an/${projectId}/anh-do-luong?${listQuery(filters)}`),
  createMeasurementSnapshot: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/anh-do-luong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getMeasurementTrend: (definitionId, releaseId = "") =>
    testingRequest(
      `/dinh-nghia-do-luong/${definitionId}/xu-huong${releaseId ? `?release_id=${encodeURIComponent(releaseId)}` : ""}`,
    ),
  compareMeasurementReleases: (projectId, releaseA, releaseB) =>
    testingRequest(
      `/du-an/${projectId}/do-luong/so-sanh-ban-phat-hanh?release_a=${encodeURIComponent(releaseA)}&release_b=${encodeURIComponent(releaseB)}`,
    ),
  listMeasurementThresholdAlerts: (projectId) =>
    testingRequest(`/du-an/${projectId}/do-luong/canh-bao`),
  validateMeasurementDefinition: (definitionId) =>
    testingRequest(`/dinh-nghia-do-luong/${definitionId}/xac-thuc`),
  pinMeasurementToDashboard: (definitionId, pinned) =>
    testingRequest(`/dinh-nghia-do-luong/${definitionId}/ghim`, {
      method: "PUT",
      body: JSON.stringify({ pinned }),
    }),
  exportMeasurementData: (definitionId, key) =>
    downloadTestingFile(`/dinh-nghia-do-luong/${definitionId}/xuat`, `metric-${key}.csv`),
  listQualityEvaluations: (projectId, releaseId = "") =>
    testingRequest(
      `/du-an/${projectId}/danh-gia-chat-luong${releaseId ? `?release_id=${encodeURIComponent(releaseId)}` : ""}`,
    ),
  createQualityEvaluation: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/danh-gia-chat-luong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getQualityEvaluation: (evaluationId) => testingRequest(`/danh-gia-chat-luong/${evaluationId}`),
  updateQualityEvaluation: (evaluationId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  submitQualityEvaluation: (evaluationId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  reviewQualityEvaluation: (evaluationId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}/ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createQualityWaiver: (evaluationId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}/mien-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  decideQualityWaiver: (evaluationId, waiverId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}/mien-tru/${waiverId}/quyet-dinh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveQualityEvaluation: (evaluationId, payload) =>
    testingRequest(`/danh-gia-chat-luong/${evaluationId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listCausalAnalyses: (projectId) => testingRequest(`/du-an/${projectId}/phan-tich-nguyen-nhan`),
  listCausalAnalysisCandidates: (projectId) =>
    testingRequest(`/du-an/${projectId}/phan-tich-nguyen-nhan/ung-vien`),
  createCausalAnalysis: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/phan-tich-nguyen-nhan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCausalAnalysis: (analysisId) => testingRequest(`/phan-tich-nguyen-nhan/${analysisId}`),
  getLatestCausalHypothesisResult: (analysisId) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/goi-y-tu-dong`),
  updateCausalAnalysis: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  linkCausalAnalysisDefects: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/lien-ket-loi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addCausalFiveWhy: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/nam-tai-sao`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordCausalRootCause: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/nguyen-nhan-goc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createCorrectiveAction: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/hanh-dong-khac-phuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createPreventiveAction: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/hanh-dong-phong-ngua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  assignPreventionAction: (actionId, payload) =>
    testingRequest(`/hanh-dong-phong-ngua/${actionId}/phan-cong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePreventionAction: (actionId, payload) =>
    testingRequest(`/hanh-dong-phong-ngua/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  submitCausalAnalysis: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveCausalAnalysis: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  reviewCausalEffectiveness: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/danh-gia-hieu-luc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  closeCausalAnalysis: (analysisId, payload) =>
    testingRequest(`/phan-tich-nguyen-nhan/${analysisId}/dong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listEnvironmentIncidents: (projectId, filters = {}) =>
    testingRequest(`/du-an/${projectId}/su-co-moi-truong?${listQuery(filters)}`),
  createEnvironmentIncident: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/su-co-moi-truong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateEnvironmentIncident: (incidentId, payload) =>
    testingRequest(`/su-co-moi-truong/${incidentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  transitionEnvironmentIncident: (incidentId, payload, close = false) =>
    testingRequest(`/su-co-moi-truong/${incidentId}/${close ? "ket-thuc" : "dieu-tra"}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listNonFunctionalTestPlans: (projectId, planType = "") =>
    testingRequest(
      `/du-an/${projectId}/ke-hoach-phi-chuc-nang${planType ? `?plan_type=${encodeURIComponent(planType)}` : ""}`,
    ),
  getNonFunctionalTestPlan: (planId) => testingRequest(`/ke-hoach-phi-chuc-nang/${planId}`),
  createNonFunctionalTestPlan: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/ke-hoach-phi-chuc-nang`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNonFunctionalTestPlan: (planId, payload) =>
    testingRequest(`/ke-hoach-phi-chuc-nang/${planId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  transitionNonFunctionalTestPlan: (planId, payload, approve = false) =>
    testingRequest(`/ke-hoach-phi-chuc-nang/${planId}/${approve ? "phe-duyet" : "gui-ra-soat"}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  importNonFunctionalEvidence: (planId, payload) =>
    testingRequest(`/ke-hoach-phi-chuc-nang/${planId}/bang-chung-ben-ngoai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProcessImprovements: (projectId) => testingRequest(`/du-an/${projectId}/cai-tien-quy-trinh`),
  getProcessImprovement: (proposalId) => testingRequest(`/cai-tien-quy-trinh/${proposalId}`),
  createProcessImprovement: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/cai-tien-quy-trinh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProcessImprovement: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  linkProcessImprovementSources: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/lien-ket-nguon`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveProcessImprovementExperiment: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/phe-duyet-thu-nghiem`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recordProcessImprovementBaseline: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/duong-co-so`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startProcessImprovementExperiment: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/bat-dau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  evaluateProcessImprovement: (proposalId, payload) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/danh-gia`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  decideProcessImprovement: (proposalId, payload, adopt = true) =>
    testingRequest(`/cai-tien-quy-trinh/${proposalId}/${adopt ? "ap-dung" : "tu-choi"}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listStatisticalQualityAnalyses: (projectId) =>
    testingRequest(`/du-an/${projectId}/kiem-soat-thong-ke`),
  getStatisticalQualityAnalysis: (analysisId) =>
    testingRequest(`/kiem-soat-thong-ke/${analysisId}`),
  calculateStatisticalQualityBaseline: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/kiem-soat-thong-ke`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  annotateStatisticalSpecialCause: (analysisId, payload) =>
    testingRequest(`/kiem-soat-thong-ke/${analysisId}/nguyen-nhan-dac-biet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compareStatisticalQuality: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/kiem-soat-thong-ke/so-sanh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
