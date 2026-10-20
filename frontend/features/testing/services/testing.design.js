import {
  downloadTestingFile,
  listPage,
  listQuery,
  testingRequest,
  testingStreamRequest,
} from "./testing.transport";

export const designTestingApi = {
  listTestRepository: (projectId) => testingRequest(`/du-an/${projectId}/kho-ca-kiem-thu`),
  createTestRepositoryNode: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/kho-ca-kiem-thu`, {
      method: "POST",
      body: JSON.stringify({ ...payload, project_id: projectId }),
    }),
  updateTestRepositoryNode: (nodeId, payload) =>
    testingRequest(`/kho-ca-kiem-thu/${nodeId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listReusableTestSteps: (projectId) => testingRequest(`/du-an/${projectId}/buoc-dung-lai`),
  createReusableTestStep: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/buoc-dung-lai`, {
      method: "POST",
      body: JSON.stringify({ ...payload, project_id: projectId }),
    }),
  listRequirementClarifications: (requirementVersionId) =>
    testingRequest(`/phien-ban-yeu-cau/${requirementVersionId}/phieu-lam-ro`),
  createRequirementClarification: (requirementVersionId, payload) =>
    testingRequest(`/phien-ban-yeu-cau/${requirementVersionId}/phieu-lam-ro`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createClarificationsFromReview: (requirementVersionId) =>
    testingRequest(`/phien-ban-yeu-cau/${requirementVersionId}/phieu-lam-ro/tao-tu-ra-soat`, {
      method: "POST",
    }),
  answerRequirementClarification: (clarificationId, payload) =>
    testingRequest(`/phieu-lam-ro/${clarificationId}/tra-loi`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  resolveRequirementClarification: (clarificationId, payload) =>
    testingRequest(`/phieu-lam-ro/${clarificationId}/xac-nhan-giai-quyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  decideRequirementClarification: (clarificationId, payload) =>
    testingRequest(`/phieu-lam-ro/${clarificationId}/quyet-dinh`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getTestAdequacy: (requirementVersionId) =>
    testingRequest(`/phien-ban-yeu-cau/${requirementVersionId}/do-day-du-kiem-thu`),
  getTestAdequacyImpact: (requirementId) =>
    testingRequest(`/yeu-cau/${requirementId}/do-day-du-kiem-thu/tac-dong`),
  refreshTestAdequacy: (requirementVersionId, expectedRevision) =>
    testingRequest(`/phien-ban-yeu-cau/${requirementVersionId}/do-day-du-kiem-thu/lam-moi`, {
      method: "POST",
      body: JSON.stringify(expectedRevision ? { expected_revision: expectedRevision } : {}),
    }),
  submitTestAdequacy: (assessmentId, expectedRevision, note = "") =>
    testingRequest(`/do-day-du-kiem-thu/${assessmentId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision, note }),
    }),
  approveTestAdequacy: (assessmentId, expectedRevision, note = "") =>
    testingRequest(`/do-day-du-kiem-thu/${assessmentId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision, note }),
    }),
  decideTestAdequacyItem: (assessmentId, coverageItemId, payload) =>
    testingRequest(`/do-day-du-kiem-thu/${assessmentId}/hang-muc/${coverageItemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  addTestAdequacyExecutionFeedback: (assessmentId, coverageItemId, payload) =>
    testingRequest(
      `/do-day-du-kiem-thu/${assessmentId}/hang-muc/${coverageItemId}/phan-hoi-thuc-thi`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
  searchProject: (id, query) =>
    testingRequest(`/du-an/${id}/tim-kiem?q=${encodeURIComponent(query)}&limit=50`),
  listRequirementPage: (id, query = "") => listPage(`/du-an/${id}/yeu-cau`, query),
  listRequirements: (id, query = "") =>
    listPage(`/du-an/${id}/yeu-cau`, query).then((result) => result.items),
  createRequirement: (id, payload) =>
    testingRequest(`/du-an/${id}/yeu-cau`, { method: "POST", body: JSON.stringify(payload) }),
  updateRequirementDraft: (projectId, requirementId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/${requirementId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getRequirement: (id) => testingRequest(`/yeu-cau/${id}`),
  listRequirementVersions: (id) => testingRequest(`/yeu-cau/${id}/phien-ban`),
  createRequirementVersion: (id, payload) =>
    testingRequest(`/yeu-cau/${id}/phien-ban`, { method: "POST", body: JSON.stringify(payload) }),
  baselineRequirement: (id, revision) =>
    testingRequest(`/phien-ban-yeu-cau/${id}/chot-chuan`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: revision }),
    }),
  lintRequirement: (id, payload) =>
    testingStreamRequest(`/phien-ban-yeu-cau/${id}/ai/kiem-tra`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyRequirementAiSuggestion: (id, payload) =>
    testingRequest(`/phien-ban-yeu-cau/${id}/ai/ap-dung-de-xuat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compareRequirement: (id, fromId, toId) =>
    testingRequest(`/yeu-cau/${id}/so-sanh`, {
      method: "POST",
      body: JSON.stringify({ from_version_id: fromId, to_version_id: toId }),
    }),
  splitRequirement: (projectId, requirementId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/${requirementId}/tach`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  mergeRequirements: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/gop`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  findDuplicateRequirements: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/kiem-tra-trung-lap`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createRequirementImport: (id, payload) =>
    testingRequest(`/du-an/${id}/nhap-yeu-cau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listRequirementTemplates: (id) => testingRequest(`/du-an/${id}/mau-yeu-cau`),
  createRequirementTemplate: (id, payload) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau`, { method: "POST", body: JSON.stringify(payload) }),
  updateRequirementTemplate: (id, templateId, payload) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  synthesizeRequirementTemplate: (id, payload) =>
    testingStreamRequest(`/du-an/${id}/mau-yeu-cau/tong-hop`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewRequirementTemplate: (id, templateId) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau/${templateId}/xem-truoc`, { method: "POST" }),
  reviewRequirementTemplate: (id, templateId) =>
    testingStreamRequest(`/du-an/${id}/mau-yeu-cau/${templateId}/ai/kiem-tra`, { method: "POST" }),
  listRequirementFields: (id) => testingRequest(`/du-an/${id}/truong-yeu-cau`),
  createRequirementField: (id, payload) =>
    testingRequest(`/du-an/${id}/truong-yeu-cau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestRequirementTemplatePublication: (id, templateId, payload) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau/${templateId}/de-nghi-phat-hanh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  consentRequirementTemplatePublication: (id, templateId, payload) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau/${templateId}/dong-y`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveRequirementTemplatePublication: (id, templateId) =>
    testingRequest(`/du-an/${id}/mau-yeu-cau/${templateId}/duyet-phat-hanh`, { method: "POST" }),
  compareRequirementImport: (id) => testingRequest(`/nhap-yeu-cau/${id}/doi-chieu`),
  resolveRequirementImportCandidate: (id, candidateId, payload) =>
    testingRequest(`/nhap-yeu-cau/${id}/ung-vien/${candidateId}/doi-chieu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  confirmRequirementImport: (
    id,
    selectedIndexes,
    expectedRevision,
    separateIndexes = [],
    separateReasons = {},
  ) =>
    testingRequest(`/nhap-yeu-cau/${id}/xac-nhan`, {
      method: "POST",
      body: JSON.stringify({
        selected_indexes: selectedIndexes,
        separate_indexes: separateIndexes,
        separate_reasons: separateReasons,
        expected_revision: expectedRevision,
      }),
    }),
  updateRequirementImport: (id, payload) =>
    testingRequest(`/nhap-yeu-cau/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  mergeRequirementCandidates: (id, payload) =>
    testingRequest(`/nhap-yeu-cau/${id}/ung-vien/gop`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  splitRequirementCandidate: (id, candidateId, payload) =>
    testingRequest(`/nhap-yeu-cau/${id}/ung-vien/${candidateId}/tach`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  rejectRequirementCandidate: (id, candidateId, payload) =>
    testingRequest(`/nhap-yeu-cau/${id}/ung-vien/${candidateId}/tu-choi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  uploadRequirementImport: (id, file, format) => {
    const body = new FormData();
    body.append("format", format);
    body.append("file", file);
    return testingRequest(`/du-an/${id}/nhap-yeu-cau/tai-len`, { method: "POST", body });
  },
  createRequirementDocument: (id, payload) =>
    testingRequest(`/du-an/${id}/tai-lieu-yeu-cau`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  uploadRequirementDocument: (id, file, format, access = {}) => {
    const body = new FormData();
    body.append("format", format);
    body.append("file", file);
    body.append("visibility", access.visibility || "private");
    body.append("shared_with", JSON.stringify(access.shared_with || []));
    body.append("ai_enabled", String(Boolean(access.ai_enabled)));
    body.append("source_type", access.source_type || "REFERENCE");
    return testingRequest(`/du-an/${id}/tai-lieu-yeu-cau/tai-len`, { method: "POST", body });
  },
  listRequirementDocuments: (id, query = "") =>
    testingRequest(`/du-an/${id}/tai-lieu-yeu-cau${query ? `?${query}` : ""}`),
  createKnowledgeSource: (id, payload) =>
    testingRequest(`/du-an/${id}/nguon-tri-thuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listKnowledgeSources: (id, includeArchived = false) =>
    testingRequest(`/du-an/${id}/nguon-tri-thuc?include_archived=${includeArchived}`),
  archiveKnowledgeSource: (id, payload) =>
    testingRequest(`/nguon-tri-thuc/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  registerAttachment: (id, payload) =>
    testingRequest(`/du-an/${id}/tep-dinh-kem`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAttachments: (id, query = "") =>
    testingRequest(`/du-an/${id}/tep-dinh-kem${query ? `?${query}` : ""}`),
  deleteAttachment: (id) => testingRequest(`/tep-dinh-kem/${id}`, { method: "DELETE" }),
  moderateAttachment: (id, payload) =>
    testingRequest(`/tep-dinh-kem/${id}/kiem-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRequirementDocument: (id) => testingRequest(`/tai-lieu-yeu-cau/${id}`),
  updateRequirementDocument: (id, payload) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  updateRequirementDocumentAccess: (id, payload) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/quyen-truy-cap`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  updateRequirementDocumentAiRead: (id, payload) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/ai-doc`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  reindexRequirementDocument: (id) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/lap-chi-muc-lai`, { method: "POST" }),
  reindexKnowledgeSource: (id) =>
    testingRequest(`/nguon-tri-thuc/${id}/lap-chi-muc-lai`, { method: "POST" }),
  downloadRequirementDocument: (id, filename) =>
    downloadTestingFile(`/tai-lieu-yeu-cau/${id}/tai-xuong`, filename),
  archiveRequirementDocument: (id, payload) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  restoreRequirementDocument: (id, payload) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/khoi-phuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  retryRequirementDocumentParse: (id, revision) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/thu-lai-phan-tich`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: revision }),
    }),
  extractRequirementDocument: (id, idempotencyKey = crypto.randomUUID()) =>
    testingRequest(`/tai-lieu-yeu-cau/${id}/trich-xuat`, {
      method: "POST",
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    }),
  submitRequirementReview: (projectId, requirementId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/${requirementId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestRequirementChanges: (projectId, requirementId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/${requirementId}/yeu-cau-chinh-sua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveRequirement: (projectId, requirementId, payload) =>
    testingRequest(`/du-an/${projectId}/yeu-cau/${requirementId}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  obsoleteRequirement: (id, payload) =>
    testingRequest(`/yeu-cau/${id}/ngung-hieu-luc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  restoreRequirement: (id, payload) =>
    testingRequest(`/yeu-cau/${id}/khoi-phuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitTestCaseReview: (projectId, draftId, payload) =>
    testingRequest(`/du-an/${projectId}/ca-kiem-thu/${draftId}/gui-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestTestCaseChanges: (projectId, draftId, payload) =>
    testingRequest(`/du-an/${projectId}/ca-kiem-thu/${draftId}/yeu-cau-chinh-sua`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listScenarios: (id, query = "") => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/kich-ban-kiem-thu${value ? `?${value}` : ""}`);
  },
  listDataSets: (id, query = "") =>
    testingRequest(
      `/du-an/${id}/du-lieu-kiem-thu${query ? `?q=${encodeURIComponent(query)}` : ""}`,
    ),
  createDataSet: (id, payload) =>
    testingRequest(`/du-an/${id}/du-lieu-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listDataSetVersions: (id) => testingRequest(`/du-lieu-kiem-thu/${id}/phien-ban`),
  createDataSetVersion: (id, payload) =>
    testingRequest(`/du-lieu-kiem-thu/${id}/phien-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  bindDataSet: (projectId, dataSetId, payload) =>
    testingRequest(`/du-an/${projectId}/du-lieu-kiem-thu/${dataSetId}/gan-ca-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewDataSet: (projectId, dataSetId, payload) =>
    testingRequest(`/du-an/${projectId}/du-lieu-kiem-thu/${dataSetId}/xem-truoc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  archiveDataSet: (projectId, dataSetId, payload) =>
    testingRequest(`/du-an/${projectId}/du-lieu-kiem-thu/${dataSetId}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listTestCaseTemplates: (projectId, templateType = "") =>
    testingRequest(
      `/du-an/${projectId}/mau-ca-kiem-thu${templateType ? `?template_type=${encodeURIComponent(templateType)}` : ""}`,
    ),
  getTestCaseTemplate: (templateId) => testingRequest(`/mau-ca-kiem-thu/${templateId}`),
  createTestCaseTemplate: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/mau-ca-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTestCaseTemplate: (templateId, payload) =>
    testingRequest(`/mau-ca-kiem-thu/${templateId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveTestCaseTemplate: (templateId, payload) =>
    testingRequest(`/mau-ca-kiem-thu/${templateId}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createScenario: (id, payload) =>
    testingRequest(`/du-an/${id}/kich-ban-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateScenario: (id, payload) =>
    testingRequest(`/kich-ban-kiem-thu/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  cloneScenario: (id) => testingRequest(`/kich-ban-kiem-thu/${id}/nhan-ban`, { method: "POST" }),
  archiveScenario: (id, payload) =>
    testingRequest(`/kich-ban-kiem-thu/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  generateScenarios: (versionId, payload) =>
    testingStreamRequest(`/phien-ban-yeu-cau/${versionId}/ai/sinh-kich-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listTestDrafts: (id) => testingRequest(`/du-an/${id}/ban-nhap-ca-kiem-thu`),
  createTestDraft: (id, payload) =>
    testingRequest(`/du-an/${id}/ban-nhap-ca-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createGeneratedTestDrafts: (id, payload) =>
    testingRequest(`/du-an/${id}/ban-nhap-ca-kiem-thu/lo`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTestDraft: (id) => testingRequest(`/ban-nhap-ca-kiem-thu/${id}`),
  updateTestDraft: (id, payload) =>
    testingRequest(`/ban-nhap-ca-kiem-thu/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  lintTestDraft: (id) => testingRequest(`/ban-nhap-ca-kiem-thu/${id}/kiem-tra`, { method: "POST" }),
  freezeTestDraft: (id, revision, reason) =>
    testingRequest(`/ban-nhap-ca-kiem-thu/${id}/dong-bang`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: revision, change_reason: reason }),
    }),
  listTestCasePage: (id, query = "") => listPage(`/du-an/${id}/ca-kiem-thu`, query),
  listTestCases: (id, query = "") =>
    listPage(`/du-an/${id}/ca-kiem-thu`, query).then((result) => result.items),
  listTestVersions: (id) => testingRequest(`/ca-kiem-thu/${id}/phien-ban`),
  cloneTestCase: (id, payload) =>
    testingRequest(`/ca-kiem-thu/${id}/nhan-ban`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  obsoleteTestCase: (id, payload) =>
    testingRequest(`/ca-kiem-thu/${id}/ngung-hieu-luc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  restoreTestCase: (id, payload) =>
    testingRequest(`/ca-kiem-thu/${id}/khoi-phuc`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  generateTestCases: (versionId, payload) =>
    testingStreamRequest(`/phien-ban-yeu-cau/${versionId}/ai/sinh-ca-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recommendTestTechniques: (versionId, payload = {}) =>
    testingStreamRequest(`/phien-ban-yeu-cau/${versionId}/ai/de-xuat-ky-thuat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  generateProjectTestCases: (projectId, payload) =>
    testingStreamRequest(`/du-an/${projectId}/ca-kiem-thu/sinh`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  findDuplicates: (id) => testingRequest(`/du-an/${id}/ca-kiem-thu/trung-lap`),
  uploadTestImport: (id, file) => {
    const body = new FormData();
    const format = file.name.toLowerCase().endsWith(".xlsx") ? "xlsx" : "csv";
    body.append("format", format);
    body.append("file", file);
    return testingRequest(`/du-an/${id}/nhap-ca-kiem-thu/tai-len`, { method: "POST", body });
  },
  confirmTestImport: (id, payload) =>
    testingRequest(`/nhap-ca-kiem-thu/${id}/xac-nhan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportTestCases: (id, format = "csv") =>
    downloadTestingFile(
      `/du-an/${id}/ca-kiem-thu/xuat?format=${format}`,
      `test-cases-${id}.${format}`,
    ),
  importApiArtifact: (id, payload) =>
    testingRequest(`/du-an/${id}/dac-ta-giao-dien/nhap`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listApiArtifacts: (id) => testingRequest(`/du-an/${id}/dac-ta-giao-dien`),
  getApiArtifact: (id) => testingRequest(`/dac-ta-giao-dien/${id}`),
  reviewApiArtifact: (id, payload) =>
    testingRequest(`/dac-ta-giao-dien/${id}/ra-soat`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  confirmApiArtifact: (id, payload) =>
    testingRequest(`/dac-ta-giao-dien/${id}/xac-nhan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  archiveApiArtifact: (id, payload) =>
    testingRequest(`/dac-ta-giao-dien/${id}/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  diffApiArtifacts: (projectId, fromArtifactId, toArtifactId) =>
    testingRequest(
      `/du-an/${projectId}/dac-ta-giao-dien/khac-biet?from_artifact_id=${encodeURIComponent(fromArtifactId)}&to_artifact_id=${encodeURIComponent(toArtifactId)}`,
    ),
  analyzeApiArtifactImpact: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/dac-ta-giao-dien/phan-tich-anh-huong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listApiOperations: (id) => testingRequest(`/du-an/${id}/dac-ta-giao-dien/thao-tac`),
  generateApiTests: (id) =>
    testingRequest(`/dac-ta-giao-dien/thao-tac/${id}/sinh-ca-kiem-thu`, {
      method: "POST",
    }),
  traceability: (id) => testingRequest(`/du-an/${id}/truy-vet`),
  exportTraceability: (id) =>
    downloadTestingFile(`/du-an/${id}/truy-vet/xuat`, `traceability-${id}.csv`),
  coverage: (id, scope = {}) => {
    const query = listQuery(scope);
    return testingRequest(`/du-an/${id}/do-phu${query ? `?${query}` : ""}`);
  },
  listCoverageSnapshots: (id) => testingRequest(`/du-an/${id}/anh-chup-do-phu`),
  createCoverageSnapshot: (id, payload = {}) =>
    testingRequest(`/du-an/${id}/anh-chup-do-phu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  recoverTrace: (id) => testingRequest(`/du-an/${id}/khoi-phuc-truy-vet`, { method: "POST" }),
  createTrace: (payload) =>
    testingRequest("/lien-ket-truy-vet", { method: "POST", body: JSON.stringify(payload) }),
  confirmTrace: (id) => testingRequest(`/lien-ket-truy-vet/${id}/xac-nhan`, { method: "POST" }),
  rejectTrace: (id) => testingRequest(`/lien-ket-truy-vet/${id}/tu-choi`, { method: "POST" }),
  revokeTrace: (id) => testingRequest(`/lien-ket-truy-vet/${id}`, { method: "DELETE" }),
  listReviewComments: (projectId, query = "") =>
    testingRequest(`/du-an/${projectId}/nhan-xet-ra-soat${query ? `?${query}` : ""}`),
  createReviewComment: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/nhan-xet-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolveReviewComment: (id, reason = "") =>
    testingRequest(`/nhan-xet-ra-soat/${id}/giai-quyet`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  reopenReviewComment: (id, reason = "") =>
    testingRequest(`/nhan-xet-ra-soat/${id}/mo-lai`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  listChangeSets: (id, query = "") => {
    const value = listQuery(query);
    return testingRequest(`/du-an/${id}/bo-thay-doi${value ? `?${value}` : ""}`);
  },
  createChangeSet: (requirementId, payload) =>
    testingRequest(`/yeu-cau/${requirementId}/bo-thay-doi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getChangeSet: (id) => testingRequest(`/bo-thay-doi/${id}`),
  reviewChangeSet: (id, payload) =>
    testingRequest(`/bo-thay-doi/${id}/ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  analyzeImpact: (id) =>
    testingStreamRequest(`/bo-thay-doi/${id}/phan-tich-anh-huong`, { method: "POST" }),
  getChangeSetImpact: (id) => testingRequest(`/bo-thay-doi/${id}/phan-tich-anh-huong`),
  getImpact: (id) => testingRequest(`/phan-tich-anh-huong/${id}`),
  reviewImpact: (id, payload) =>
    testingRequest(`/phan-tich-anh-huong/${id}/ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  rerunImpact: (id, payload) =>
    testingStreamRequest(`/phan-tich-anh-huong/${id}/chay-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createProposals: (id) =>
    testingRequest(`/phan-tich-anh-huong/${id}/de-xuat-bao-tri`, { method: "POST" }),
  listProposals: (id, query = { status: "PENDING" }) => {
    const value = listQuery(typeof query === "string" ? { status: query } : query);
    return testingRequest(`/du-an/${id}/de-xuat-bao-tri${value ? `?${value}` : ""}`);
  },
  acceptProposal: (id, payload, edited = false) =>
    testingRequest(`/de-xuat-bao-tri/${id}/${edited ? "chap-nhan-co-chinh-sua" : "chap-nhan"}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  rejectProposal: (id, payload) =>
    testingRequest(`/de-xuat-bao-tri/${id}/tu-choi`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  regenerateProposal: (id, payload) =>
    testingRequest(`/de-xuat-bao-tri/${id}/sinh-lai`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  bulkTags: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/nhan`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkTags: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/nhan`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  bulkAddToSuite: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/ca-kiem-thu/them-vao-bo-kiem-thu`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkAddToSuite: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/ca-kiem-thu/them-vao-bo-kiem-thu`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  bulkMarkReviewRequired: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/ca-kiem-thu/danh-dau-can-ra-soat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkMarkReviewRequired: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/ca-kiem-thu/danh-dau-can-ra-soat`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  bulkArchive: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/luu-tru`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkArchive: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/luu-tru`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  bulkGenerateProposals: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/de-xuat-anh-huong`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkGenerateProposals: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/de-xuat-anh-huong`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  bulkApproveProposals: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/phe-duyet-de-xuat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  previewBulkApproveProposals: (projectId, payload) =>
    testingRequest(`/du-an/${projectId}/hang-loat/phe-duyet-de-xuat`, {
      method: "POST",
      body: JSON.stringify({ ...payload, preview: true }),
    }),
  regression: (id) =>
    testingStreamRequest(`/bo-thay-doi/${id}/de-xuat-hoi-quy`, { method: "POST" }),
  getChangeSetRegression: (id) => testingRequest(`/bo-thay-doi/${id}/de-xuat-hoi-quy`),
  approveRegression: (id, payload) =>
    testingRequest(`/de-xuat-hoi-quy/${id}/phe-duyet`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
