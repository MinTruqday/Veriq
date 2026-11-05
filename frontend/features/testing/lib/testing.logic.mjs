export function emptyDoc() {
  return { type: "doc", content: [] };
}

export function textDoc(text) {
  return {
    type: "doc",
    content: text ? [{ type: "paragraph", content: [{ type: "text", text: String(text) }] }] : [],
  };
}

export function docText(document) {
  const values = [];
  const visit = (node) => {
    if (Array.isArray(node)) return node.forEach(visit);
    if (!node || typeof node !== "object") return;
    if (typeof node.text === "string") values.push(node.text);
    if (node.content) visit(node.content);
  };
  visit(document);
  return values.join(" ").trim();
}

const labels = {
  ACCEPTED: "Đã chấp nhận",
  ACCEPTED_WITH_ACTIONS: "Chấp nhận kèm hành động",
  ACTIVE: "Đang hoạt động",
  ADOPTED: "Đã áp dụng",
  APPLY_PARTIAL: "Áp dụng một phần",
  ANALYZED: "Đã phân tích",
  APPROVED: "Đã phê duyệt",
  ASSURED: "Đã có hồ sơ đảm bảo",
  AWAITING_AUTHORIZATION: "Cần kiểm tra quyền truy cập",
  AWAITING_INPUT: "Cần bổ sung thông tin",
  ACTION_STARTED: "Đang thực hiện tác vụ",
  ACTIONS_EXECUTED: "Đã thực hiện tác vụ",
  ACTIONS_VERIFIED: "Đã kiểm tra kết quả",
  ARCHIVED: "Đã lưu trữ",
  AUTHENTICATED: "Tài khoản đã xác thực",
  BASELINED: "Đã đặt làm phiên bản chuẩn",
  BACKLOG: "Danh sách chờ",
  BLOCKED: "Bị chặn",
  BOUND: "Đã liên kết",
  CHANGED: "Đã thay đổi",
  CLOSED: "Đã đóng",
  COMPLETED: "Đã hoàn tất",
  CONDITIONAL: "Đảm bảo có điều kiện",
  CONFIRMED: "Đã xác nhận",
  CREATED: "Đã tạo",
  CRITICAL: "Nghiêm trọng",
  DEGRADED: "Hoạt động giới hạn",
  DEGRADED_AI: "AI hoạt động giới hạn",
  DEGRADED_KNOWLEDGE: "dữ liệu tham chiếu chưa sẵn sàng",
  DUPLICATE: "Trùng lặp",
  DRAFT: "Bản nháp",
  DISABLED: "Đã vô hiệu hóa",
  EDITED_ACCEPTED: "Đã chấp nhận sau chỉnh sửa",
  EXPIRED: "Đã hết hạn",
  FAIL: "Thất bại",
  FAILED: "Không thành công",
  FACTS_EXTRACTED: "Đã trích xuất thông tin có nguồn",
  FINALIZED: "Đã ghi nhận kết quả",
  FRESH: "Còn hiệu lực",
  GO: "Phát hành",
  GO_WITH_RISK: "Phát hành kèm rủi ro",
  HISTORICAL: "Lịch sử",
  IN_REVIEW: "Đang chờ duyệt",
  AWAITING_REVIEW: "Chờ rà soát",
  IN_PROGRESS: "Đang thực hiện",
  INACTIVE: "Đã vô hiệu hóa",
  SCRUM: "Scrum",
  KANBAN: "Kanban",
  INVITED: "Đã mời",
  LOCKED: "Đã khóa",
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  HIGHEST: "Rất cao",
  MUST_RUN: "Bắt buộc chạy",
  NEEDS_REVIEW: "Cần rà soát",
  NEEDS_TEST_COVERAGE: "Cần bổ sung kiểm thử",
  NEEDS_UPDATE: "Cần cập nhật",
  MORE_TESTING_REQUIRED: "Cần kiểm thử thêm",
  NEW: "Mới",
  NORMAL: "Bình thường",
  NO_GO: "Không phát hành",
  NOT_APPLICABLE: "Không áp dụng",
  NOT_REQUESTED: "Chưa dùng trong tìm kiếm AI",
  NOT_RUN: "Chưa chạy",
  OBSOLETE: "Không còn phù hợp",
  OPEN: "Đang mở",
  OPTIONAL: "Không bắt buộc",
  PASS: "Đạt",
  PASSED: "Đạt",
  PARTIAL_EXECUTION: "Thực thi một phần",
  PARSE_FAILED: "Phân tích tệp thất bại",
  PENDING: "Chờ duyệt",
  PENDING_APPROVAL: "Chờ phê duyệt",
  POTENTIALLY_AFFECTED: "Có thể bị ảnh hưởng",
  PREVIEW_READY: "Sẵn sàng xem trước",
  QUEUED: "Đang chờ xử lý",
  RECONCILIATION_REQUIRED: "Cần đối soát kết quả",
  READY: "Sẵn sàng",
  READY_FOR_RETEST: "Sẵn sàng kiểm thử lại",
  REJECTED: "Đã từ chối",
  REVIEWED: "Đã rà soát",
  REVIEW_READY: "Sẵn sàng rà soát",
  REOPENED: "Đã mở lại",
  RESOLVED: "Đã xử lý",
  RUNNING: "Đang xử lý",
  SHOULD_RUN: "Nên chạy",
  SKIPPED: "Đã bỏ qua",
  STALE: "Đã lỗi thời",
  STILL_VALID: "Vẫn hợp lệ",
  TESTABLE: "Có thể kiểm thử",
  TESTABLE_WITH_RISK: "Có thể kiểm thử kèm rủi ro",
  NOT_TESTABLE: "Không thể kiểm thử",
  NEEDS_CLARIFICATION: "Cần làm rõ",
  NOT_CONFIGURED: "Chưa cấu hình",
  INSUFFICIENT_DATA: "Chưa đủ dữ liệu",
  MANUAL_REQUIRED: "Cần đánh giá thủ công",
  SCHEDULE: "Tiến độ",
  EFFORT: "Nỗ lực",
  BLOCKED_TESTS: "Ca bị chặn",
  BLOCKER: "Lỗi chặn phát hành",
  REQUEST_RETEST: "Yêu cầu kiểm thử lại",
  OBSERVED: "Đã tiếp nhận sự kiện",
  PLAN_CREATED: "Đã lập kế hoạch xử lý",
  GRAPH_COMPLETED: "Đã hoàn tất luồng xử lý",
  UNCERTAINTY_ASSESSED: "Đã đánh giá thông tin còn thiếu",
  SUCCESS: "Thành công",
  SUGGESTED: "AI đề xuất",
  SUPERSEDED: "Đã được thay thế",
  SUSPENDED: "Tạm ngưng",
  UNCHANGED: "Không thay đổi",
  UNKNOWN: "Chưa xác định",
  INDEXED: "Đã lập chỉ mục",
  INDEXING: "Đang lập chỉ mục",
  ABORTED: "Đã hủy",
  CANCELLED: "Đã hủy",
  DECISION_PENDING: "Chờ hoàn tất",
  DELETED: "Đã xóa",
  DEVELOPMENT: "Đang phát triển",
  EXTRACTED: "Đã trích xuất",
  DONE: "Hoàn thành",
  IMPORTED: "Đã nhập",
  NEEDS_MAPPING: "Cần liên kết thủ công",
  NOT_STARTED: "Chưa bắt đầu",
  PENDING_REVIEW: "Chờ rà soát",
  REVOKE_PENDING: "Đang gỡ khỏi tìm kiếm AI",
  PLANNED: "Đã lập kế hoạch",
  PUBLISHED: "Đã phát hành",
  REVOKED: "Đã thu hồi",
  TODO: "Cần làm",
  UNBOUND: "Chưa liên kết",
  VERIFIED: "Đã xác minh",
  WAIVED: "Được chấp nhận ngoại lệ",
  WARN: "Cảnh báo",
  WARNING: "Cảnh báo",
};

const valueLabels = {
  Backlog: "Danh sách chờ",
  equivalence_partitioning: "Phân vùng tương đương",
  boundary_value: "Giá trị biên",
  decision_table: "Bảng quyết định",
  state_transition: "Chuyển trạng thái",
  error_guessing: "Dự đoán lỗi",
  recommended: "Nên dùng",
  possible: "Có thể dùng",
  insufficient_evidence: "Thiếu dữ liệu để áp dụng",
  not_applicable: "Không phù hợp",
  user_story: "Câu chuyện người dùng",
  main_flow: "Luồng chính",
  exception_flow: "Luồng ngoại lệ",
  data_rules: "Dữ liệu và quy tắc",
  integration: "Giao diện hoặc tích hợp",
  quality_measure: "Thuộc tính chất lượng và mức đo",
  api_operations: "Thao tác API liên kết",
  dependencies: "Phụ thuộc",
  actors: "Tác nhân",
  business_rules: "Quy tắc nghiệp vụ",
  acceptance_criteria: "Tiêu chí chấp nhận",
  content_doc: "Nội dung yêu cầu",
  requirement_key: "Mã yêu cầu",
  source_refs: "Nguồn dẫn",
  REQUIREMENT: "Yêu cầu",
  INITIATIVE: "Sáng kiến",
  EPIC: "Hạng mục lớn",
  STORY: "Câu chuyện người dùng",
  TASK: "Công việc",
  BUG: "Lỗi",
  SUBTASK: "Công việc con",
  SCRUM: "Scrum",
  KANBAN: "Kanban",
  TEST_STRATEGY: "Chiến lược kiểm thử",
  TEST_PLAN: "Kế hoạch kiểm thử",
  TEST_CONDITION: "Điều kiện kiểm thử",
  TEST_CASE: "Ca kiểm thử",
  TestCaseDraft: "Bản nháp ca kiểm thử",
  TestCaseVersion: "Phiên bản ca kiểm thử",
  TestEnvironment: "Môi trường kiểm thử",
  TestCompletionReport: "Báo cáo hoàn tất kiểm thử",
  TestPlan: "Kế hoạch kiểm thử",
  TestResult: "Kết quả kiểm thử",
  TestRun: "Lượt chạy kiểm thử",
  TestScenario: "Kịch bản kiểm thử",
  TestStatusReport: "Báo cáo trạng thái kiểm thử",
  TestMonitoringSnapshot: "Mốc số liệu kiểm thử",
  QualityGateEvaluation: "Đánh giá điều kiện chất lượng",
  Requirement: "Yêu cầu",
  RequirementDocument: "Tài liệu yêu cầu",
  RequirementVersion: "Phiên bản yêu cầu",
  Defect: "Lỗi",
  Build: "Bản dựng",
  Report: "Báo cáo công việc",
  ReportSettings: "Cấu hình báo cáo",
  ReportSchedule: "Lịch báo cáo",
  ReportTemplate: "Mẫu báo cáo",
  report_created: "Tạo báo cáo công việc",
  report_updated: "Cập nhật bản nháp báo cáo",
  report_submit: "Gửi báo cáo rà soát",
  report_request_changes: "Yêu cầu sửa báo cáo",
  report_approve: "Duyệt báo cáo",
  report_publish: "Phát hành báo cáo",
  report_archive: "Lưu trữ báo cáo",
  report_new_version_created: "Tạo phiên bản báo cáo",
  report_delivery_access_changed: "Cập nhật quyền người nhận báo cáo",
  report_settings_updated: "Cập nhật cấu hình báo cáo",
  report_schedule_created: "Tạo lịch báo cáo",
  report_ai_sections_applied: "Áp dụng nội dung AI đã chọn vào báo cáo",
  work_item_created: "Tạo công việc",
  project_business_role_denied: "Từ chối thao tác ngoài vai trò dự án",
  Project: "Dự án",
  RELEASE: "Bản phát hành",
  SPRINT: "Đợt lặp",
  MANUAL: "Chạy theo yêu cầu",
  IMPACT_ANALYSIS: "Phân tích ảnh hưởng",
  STATUS_REPORT: "Báo cáo trạng thái",
  COMPLETION_REPORT: "Báo cáo hoàn tất",
  COMPILE_BLUEPRINT: "Lập blueprint kiểm thử",
  CREATE_REQUIREMENT_CANDIDATES: "Đề xuất yêu cầu",
  CREATE_TEST_CASE_CANDIDATES: "Đề xuất ca kiểm thử",
  CREATE_FINDINGS: "Phát hiện điểm thiếu hoặc mâu thuẫn",
  READ_PROJECT_MCP: "Đọc dữ liệu dự án qua kết nối MCP",
  REQUEST_CLARIFICATION: "Tạo câu hỏi làm rõ",
  PROPOSE_ASSIGNMENT: "Đề xuất người thực hiện",
  PROPOSE_TRANSITION: "Đề xuất chuyển trạng thái",
  RUN_CHANGE_SIMULATION: "Phân tích ảnh hưởng khi yêu cầu thay đổi",
  REWORK_REQUIRED: "Cần chỉnh sửa lại",
  CORRECTNESS: "Tính chính xác",
  COMPLETENESS: "Tính đầy đủ",
  CONSISTENCY: "Tính nhất quán",
  TESTABILITY: "Khả năng kiểm thử",
  TRACEABILITY: "Khả năng truy vết",
  SECURITY: "Bảo mật",
  PERFORMANCE: "Hiệu năng",
  MAINTAINABILITY: "Khả năng bảo trì",
  completion_report_created: "Đã tạo báo cáo hoàn tất kiểm thử",
  completion_report_approved: "Đã duyệt báo cáo hoàn tất kiểm thử",
  completion_report_closed: "Đã đóng báo cáo hoàn tất kiểm thử",
  defect_created: "Đã ghi nhận lỗi",
  defect_retested: "Đã kiểm thử lại lỗi",
  defect_transitioned: "Đã cập nhật trạng thái lỗi",
  test_completion_signed_off: "Đã ký xác nhận báo cáo hoàn tất kiểm thử",
  test_completion_submitted: "Đã gửi báo cáo hoàn tất để rà soát",
  status_report_created: "Đã tạo báo cáo trạng thái kiểm thử",
  test_plan_created: "Đã tạo kế hoạch kiểm thử",
  test_plan_updated: "Đã cập nhật kế hoạch kiểm thử",
  test_plan_submitted: "Đã gửi kế hoạch kiểm thử để rà soát",
  test_plan_approved: "Đã duyệt kế hoạch kiểm thử",
  test_scenario_created: "Đã tạo kịch bản kiểm thử",
  test_scenario_submit: "Đã gửi kịch bản để rà soát",
  test_scenario_approve: "Đã duyệt kịch bản kiểm thử",
  test_case_draft_created: "Đã tạo bản nháp ca kiểm thử",
  test_case_review_submitted: "Đã gửi ca kiểm thử để rà soát",
  test_case_version_approved: "Đã duyệt phiên bản ca kiểm thử",
  requirement_document_uploaded: "Đã tải tài liệu yêu cầu lên",
  requirement_document_parse_succeeded: "Đã xử lý xong tài liệu yêu cầu",
  requirement_document_archived: "Đã lưu trữ tài liệu yêu cầu",
  requirement_document_restored: "Đã khôi phục tài liệu yêu cầu",
  "requirement_document.ai_read_updated": "Đã cập nhật quyền AI đọc tài liệu",
  "requirement_document.access_updated": "Đã cập nhật quyền truy cập tài liệu",
  "requirement_document.access_update_pending": "Đang cập nhật quyền truy cập tài liệu",
  "requirement_document.ai_read_revocation_pending": "Đang thu hồi quyền AI đọc tài liệu",
  "requirement_document.ai_read_event_cancellation_pending": "Đang hủy tác vụ AI đọc tài liệu",
  requirement_created: "Đã tạo yêu cầu từ tài liệu",
  requirement_clarification_created: "Đã tạo phiếu làm rõ yêu cầu",
  requirement_quality_analyzed: "Đã đánh giá chất lượng yêu cầu",
  requirement_review_submitted: "Đã gửi yêu cầu để rà soát",
  requirement_version_baselined: "Đã chốt phiên bản yêu cầu",
  impact_analysis_created: "Đã phân tích ảnh hưởng",
  impact_analysis_rerun: "Đã phân tích lại ảnh hưởng",
  release_created: "Đã tạo bản phát hành",
  build_created: "Đã tạo bản dựng",
  test_run_created: "Đã tạo lượt chạy kiểm thử",
  test_run_assigned: "Đã phân công lượt chạy kiểm thử",
  test_run_started: "Đã bắt đầu lượt chạy kiểm thử",
  quality_gate_evaluated: "Đã đánh giá điều kiện chất lượng",
  exit_criteria_evaluated: "Đã đánh giá điều kiện kết thúc kiểm thử",
  monitoring_snapshot_created: "Đã lưu mốc số liệu kiểm thử",
  test_run_completed: "Đã hoàn tất lượt chạy kiểm thử",
  test_result_recorded: "Đã ghi nhận kết quả kiểm thử",
  project_created: "Đã tạo dự án",
  MAJOR: "Lớn",
  MINOR: "Nhỏ",
  QUESTION: "Cần làm rõ",
  IMPROVEMENT: "Đề xuất cải tiến",
  POSITIVE: "Dương",
  NEGATIVE: "Âm",
  BOUNDARY: "Biên",
  authorization: "Phân quyền",
  authentication: "Xác thực",
  input_validation: "Kiểm tra đầu vào",
  session: "Phiên đăng nhập",
  data_protection: "Bảo vệ dữ liệu",
  ADMIN: "Quản trị viên",
  USER: "Người dùng",
  QA: "QA",
  TESTER: "Kiểm thử viên",
  BA: "Chuyên viên phân tích nghiệp vụ",
  DEVELOPER: "Lập trình viên",
  VIEWER: "Người xem",
  ADMIN_ONLY: "Chỉ quản trị viên",
  ALL_SERVICE_IDENTITIES: "Mọi danh tính dịch vụ",
  ALL_USERS: "Mọi tài khoản",
  APPLY_INCOMING: "Áp dụng dữ liệu nhận về",
  AUTHENTICATED: "Tài khoản đã xác thực",
  BIDIRECTIONAL: "Hai chiều",
  BREAK_GLASS: "Truy cập khẩn cấp",
  KEEP_CURRENT: "Giữ dữ liệu hiện tại",
  KEEP_LOCAL: "Giữ dữ liệu nội bộ",
  KEEP_REMOTE: "Giữ dữ liệu bên ngoài",
  PROJECT_METADATA: "Siêu dữ liệu dự án",
  PULL: "Nhận dữ liệu",
  PUSH: "Gửi dữ liệu",
  RATE_LIMITS: "Giới hạn truy cập",
  SAFE_ALL: "Mọi thao tác an toàn",
  SERVICE_IDENTITY: "Danh tính dịch vụ",
  DEFECT_CREATED: "Lỗi được tạo",
  Project: "Dự án",
  ProjectSettings: "Cài đặt dự án",
  TestSuite: "Bộ kiểm thử",
  TestRun: "Lần chạy kiểm thử",
  TestPlan: "Kế hoạch kiểm thử",
  TestStrategy: "Chiến lược kiểm thử",
  TestCaseVersion: "Phiên bản ca kiểm thử",
  RequirementVersion: "Phiên bản yêu cầu",
  RequirementTemplate: "Mẫu yêu cầu",
  RequirementDocument: "Tài liệu yêu cầu",
  RequirementClarification: "Phiếu làm rõ yêu cầu",
  AIResult: "Kết quả AI",
  Requirement: "Yêu cầu",
  APIImport: "Đặc tả API",
  JUnitResultImport: "Kết quả kiểm thử",
  project_permission_denied: "Từ chối quyền dự án",
  project_membership_required: "Từ chối truy cập do chưa tham gia dự án",
  project_settings_updated: "Cập nhật cài đặt dự án",
  test_case_version_approved: "Duyệt phiên bản ca kiểm thử",
  test_case_group_approved: "Duyệt nhóm ca kiểm thử",
  test_case_approved: "Duyệt ca kiểm thử",
  test_case_draft_created: "Tạo bản nháp ca kiểm thử",
  defect_created: "Ghi nhận lỗi",
  test_adequacy_assessment_refreshed: "Cập nhật hồ sơ đảm bảo",
  test_adequacy_review_submitted: "Gửi rà soát hồ sơ đảm bảo",
  test_adequacy_coverage_decided: "Cập nhật quyết định nghĩa vụ kiểm thử",
  test_adequacy_changes_requested: "Yêu cầu chỉnh sửa hồ sơ đảm bảo",
  project_task_created: "Tạo công việc dự án",
  project_completion_percent_updated: "Cập nhật tiến độ dự án",
  requirement_import_confirmed: "Xác nhận nhập yêu cầu",
  requirement_import_previewed: "Xem trước dữ liệu yêu cầu",
  requirement_template_created: "Tạo mẫu yêu cầu",
  test_suite_created: "Tạo bộ kiểm thử",
  test_plan_created: "Tạo kế hoạch kiểm thử",
  test_plan_approved: "Duyệt kế hoạch kiểm thử",
  test_run_created: "Tạo lần chạy kiểm thử",
  test_run_started: "Bắt đầu lần chạy kiểm thử",
  test_strategy_created: "Tạo chiến lược kiểm thử",
  test_strategy_submitted: "Gửi chiến lược kiểm thử để rà soát",
  test_strategy_reviewed: "Rà soát chiến lược kiểm thử",
  test_strategy_approved: "Duyệt chiến lược kiểm thử",
  test_case_review_submitted: "Gửi ca kiểm thử để rà soát",
  requirement_review_submitted: "Gửi yêu cầu để rà soát",
  requirement_version_baselined: "Chốt phiên bản yêu cầu làm mốc",
  TestCaseDraft: "Bản nháp ca kiểm thử",
  TestAdequacyAssessment: "Hồ sơ đảm bảo yêu cầu",
  CoverageItem: "Nghĩa vụ kiểm thử",
  ProjectTask: "Công việc dự án",
  RequirementImport: "Lần nhập yêu cầu",
  requirement_document_reindexed: "Lập chỉ mục lại tài liệu yêu cầu",
  knowledge_source_created: "Tạo tài liệu tham chiếu",
  requirement_created: "Tạo yêu cầu",
  requirement_document_created: "Tạo tài liệu yêu cầu",
  requirement_extraction_requested: "Yêu cầu trích xuất nội dung yêu cầu",
  requirement_extraction_completed: "Hoàn tất trích xuất nội dung yêu cầu",
  api_artifact_confirmed: "Đã nhập đặc tả API",
  api_artifact_reviewed: "Đã rà soát đặc tả API",
  api_artifact_preview_created: "Đã xem trước đặc tả API",
  api_artifact_impact_created: "Đã phân tích ảnh hưởng của đặc tả API",
  api_artifact_archived: "Đã lưu trữ đặc tả API",
  junit_result_imported: "Đã nhập kết quả kiểm thử",
  requirement_template_updated: "Đã cập nhật mẫu yêu cầu",
  release_created: "Đã tạo bản phát hành",
  project_created: "Tạo dự án",
  ADMIN_USER_MEMBERSHIPS_VIEWED: "Xem vai trò dự án của tài khoản",
  ADMIN_USER_SESSIONS_VIEWED: "Xem phiên đăng nhập của tài khoản",
  REGISTER_USER: "Đăng ký tài khoản",
  EMAIL_VERIFICATION_REQUESTED: "Yêu cầu xác minh email",
  review_comment_created: "Tạo nhận xét rà soát",
  regression_recommendation_created: "Tạo đề xuất hồi quy",
  maintenance_proposal_applied: "Áp dụng đề xuất bảo trì",
  maintenance_proposals_created: "Tạo đề xuất bảo trì",
  impact_analysis_reviewed: "Rà soát phân tích ảnh hưởng",
  ReviewComment: "Nhận xét rà soát",
  RegressionRecommendation: "Đề xuất hồi quy",
  MaintenanceProposal: "Đề xuất bảo trì",
  ImpactAnalysis: "Phân tích ảnh hưởng",
  authentication: "Xác thực",
  testing: "Kiểm thử",
  worker: "Xử lý nền",
  ai: "Trí tuệ nhân tạo",
  content: "Nội dung",
  mongodb: "Cơ sở dữ liệu",
  web: "Ứng dụng web",
  chat: "Trò chuyện",
  SRS: "Đặc tả yêu cầu phần mềm",
  BRD: "Tài liệu yêu cầu nghiệp vụ",
  USER_STORY: "Câu chuyện người dùng",
  ACCEPTANCE_CRITERIA: "Tiêu chí chấp nhận",
  BUSINESS_RULE: "Quy tắc nghiệp vụ",
  API_SPEC: "Đặc tả giao diện lập trình ứng dụng",
  UI_SPEC: "Đặc tả giao diện người dùng",
  ARCHITECTURE: "Kiến trúc",
  MEETING_NOTE: "Biên bản họp",
  RELEASE_NOTE: "Ghi chú phát hành",
  BUG_HISTORY: "Lịch sử lỗi",
  TEST_ARTIFACT: "Tài sản kiểm thử",
  REGULATION: "Quy định",
  REFERENCE: "Tài liệu tham chiếu",
  OTHER: "Nguồn khác",
  APPROVED_SOURCE: "Đã được phê duyệt",
  CONTROLLED_SOURCE: "Được quản lý chính thức",
  PROJECT_REFERENCE: "Tài liệu tham chiếu của dự án",
  SUPPLEMENTAL: "Tài liệu bổ sung",
  DRAFT: "Bản nháp",
  UNVERIFIED: "Chưa xác minh",
  "duplicate.scan.requested": "Yêu cầu kiểm tra trùng lặp",
  UPDATE_TEST_CASE: "Cập nhật ca kiểm thử",
  CREATE_TEST_CASE: "Tạo ca kiểm thử",
  OBSOLETE_TEST_CASE: "Đánh dấu ca kiểm thử không còn phù hợp",
  TEXT_ONLY: "Chỉ thay đổi cách diễn đạt",
  MODIFIED_INPUT: "Thay đổi dữ liệu đầu vào",
  MODIFIED_BOUNDARY: "Thay đổi giá trị biên",
  MODIFIED_PERMISSION: "Thay đổi phân quyền",
  MODIFIED_ERROR: "Thay đổi xử lý lỗi",
  ADDED_BEHAVIOR: "Thêm hành vi",
  REMOVED_BEHAVIOR: "Loại bỏ hành vi",
  requirement_document: "Tài liệu yêu cầu",
  requirement_documents: "Tài liệu yêu cầu",
  requirement_version: "Phiên bản yêu cầu",
  requirement: "Yêu cầu",
  acceptance_criterion: "Tiêu chí chấp nhận",
  test_scenario: "Kịch bản kiểm thử",
  test_case: "Ca kiểm thử",
  test_case_version: "Phiên bản ca kiểm thử",
  OBLIGATION: "Nghĩa vụ kiểm thử",
  CLARIFICATION: "Điểm cần làm rõ",
  test_case_versions: "Phiên bản ca kiểm thử",
  test_run: "Lần chạy kiểm thử",
  defect: "Lỗi",
  api: "API",
  blocker: "Chặn toàn bộ",
  boundary: "Giá trị biên",
  boolean: "Đúng hoặc sai",
  business_rule: "Quy tắc nghiệp vụ",
  choice: "Lựa chọn",
  concurrency: "Xử lý đồng thời",
  critical: "Nghiêm trọng",
  constraint: "Ràng buộc",
  custom: "Tùy chỉnh",
  data: "Dữ liệu",
  data_persistence: "Lưu trữ dữ liệu",
  date: "Ngày",
  desktop: "Ứng dụng máy tính",
  embedded: "Thiết bị nhúng",
  error_handling: "Xử lý lỗi",
  feature: "Theo tính năng",
  functional: "Chức năng",
  UNIT: "Đơn vị",
  INTEGRATION: "Tích hợp",
  SYSTEM: "Hệ thống",
  ACCEPTANCE: "Nghiệm thu",
  unassessed: "Chưa đánh giá",
  performance: "Hiệu năng",
  security: "Bảo mật",
  usability: "Khả năng sử dụng",
  compatibility: "Tương thích",
  reliability: "Độ tin cậy",
  accessibility: "Khả năng tiếp cận",
  happy_path: "Luồng thành công",
  high: "Cao",
  integration: "Tích hợp",
  low: "Thấp",
  major: "Lớn",
  medium: "Trung bình",
  minor: "Nhỏ",
  mobile: "Ứng dụng di động",
  negative: "Tình huống lỗi",
  non_functional: "Phi chức năng",
  number: "Số",
  other: "Khác",
  permission: "Phân quyền",
  regression: "Hồi quy",
  sanity: "Kiểm tra nhanh có trọng tâm",
  smoke: "Kiểm tra nhanh",
  state_transition: "Chuyển trạng thái",
  trivial: "Không đáng kể",
  ui: "Giao diện",
  validation: "Xác thực dữ liệu",
  system: "Hệ thống",
  text: "Văn bản",
  manual: "Thủ công",
  candidate: "Ứng viên tự động hóa",
  automated: "Đã tự động hóa",
  development: "Phát triển",
  staging: "Tiền triển khai",
  production: "Vận hành chính thức",
  custom: "Tùy chỉnh",
};

export function statusLabel(value) {
  return labels[String(value || "").toUpperCase()] || String(value || "Chưa xác định");
}

export function valueLabel(value) {
  const normalizedValue = String(value || "").toLowerCase();
  return valueLabels[value] || valueLabels[normalizedValue] || statusLabel(value);
}

export function formatDate(value) {
  if (!value) return "Chưa có";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Chưa có"
    : date.toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

export function formatCalendarDate(value) {
  if (!value) return "Chưa có";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function messageOf(reason) {
  const profileMessages = {
    CV_AI_EXTRACTION_UNAVAILABLE:
      "Dịch vụ trích xuất CV đang tạm thời không phản hồi. Hồ sơ chưa được cập nhật; hãy thử lại sau.",
    CV_AI_EVIDENCE_INVALID:
      "AI trả về thông tin CV chưa khớp với trích dẫn nguồn. Hồ sơ chưa được cập nhật; hãy thử lại sau.",
    CV_CONTENT_UNSAFE: "Không thể xử lý CV này vì nội dung không vượt qua kiểm tra an toàn.",
    CV_TEXT_LIMIT_EXCEEDED:
      "CV có quá nhiều nội dung để trích xuất trong một lần. Hãy dùng bản CV ngắn hơn.",
    CV_CONVERSION_FAILED:
      "Không đọc được tệp CV. Hãy kiểm tra định dạng hoặc lưu lại tệp rồi thử lại.",
    CV_TEXT_NOT_EXTRACTED:
      "Không tìm thấy nội dung văn bản trong CV. Hãy dùng bản PDF có thể chọn văn bản hoặc tệp DOCX/TXT.",
  };
  if (profileMessages[reason?.code]) return profileMessages[reason.code];
  if (reason?.code === "PROJECT_COMPLEXITY_SOURCE_SCOPE_TOO_LARGE") {
    return "Tài liệu và yêu cầu đã chọn có quá nhiều nội dung để đánh giá trong một lượt. Hãy chọn phạm vi nhỏ hơn rồi thử lại; kết quả chưa được tạo.";
  }
  const automationMessages = {
    PROJECT_INITIAL_QA_MUST_DIFFER_FROM_BA:
      "Người tạo dự án không thể đồng thời là người phụ trách kiểm thử đầu tiên. Hãy chọn thành viên khác.",
    AUTOMATION_PUBLICATION_NOT_AUTHORIZED:
      "Lượt AI chưa được cấp quyền tự động công bố kết quả này.",
    AUTOMATION_EXECUTOR_UNAVAILABLE: "Chưa có người thực hiện hợp lệ cho lượt tự động hóa này.",
    AUTOMATION_PRINCIPAL_ROLE_CHANGED:
      "Vai trò người thực hiện đã thay đổi; cần kiểm tra lại quyền dự án.",
    AUTOMATION_PRINCIPAL_UNAVAILABLE: "Không thể xác minh quyền của người thực hiện hiện tại.",
    AUTHORIZATION_EXPIRED:
      "Phiên ủy quyền của lượt chạy đã hết hạn; hãy kiểm tra quyền hiện tại rồi tiếp tục.",
    PROJECT_AUTHORIZATION_CHECK_FAILED:
      "Chưa xác minh được quyền truy cập dự án. Hãy thử lại khi dịch vụ phân quyền sẵn sàng.",
    PROJECT_BA_EXECUTOR_UNAVAILABLE: "Dự án chưa có người phụ trách nghiệp vụ đang hoạt động.",
    PROJECT_QA_EXECUTOR_UNAVAILABLE: "Dự án chưa có người phụ trách kiểm thử đang hoạt động.",
    AUTOMATION_RETRY_REQUIRES_RECONCILIATION:
      "Chưa thể tiếp tục an toàn. Hãy đối soát kết quả thao tác trước.",
    AUTOMATION_RETRY_NOT_ALLOWED: "Lượt chạy hiện không ở trạng thái có thể tiếp tục.",
    AUTOMATION_ACTION_OUTCOME_UNCERTAIN:
      "Chưa xác định được kết quả thao tác trước; cần đối soát để tránh ghi trùng.",
    AUTOMATION_QUEUE_UNAVAILABLE:
      "Hàng đợi AI tạm thời chưa sẵn sàng. Hãy thử tiếp tục lại sau khi hàng đợi hoạt động.",
    REVISION_CONFLICT:
      "Dữ liệu đã được thay đổi ở phiên khác. Hãy tải lại và đối chiếu trước khi lưu.",
    IDEMPOTENCY_KEY_REUSED:
      "Nội dung yêu cầu đã thay đổi nhưng đang dùng lại mã của lần trước. Hãy chạy lại thao tác.",
    REQUIREMENT_QUALITY_ANALYSIS_IN_PROGRESS:
      "Lần rà soát Requirement này đang chạy. Hãy đợi một chút rồi tải lại kết quả.",
    REQUIREMENT_QUALITY_ANALYSIS_SOURCE_CHANGED:
      "Requirement đã thay đổi trong lúc AI rà soát. Hãy chạy lại để phân tích đúng phiên bản mới nhất.",
    REQUIREMENT_QUALITY_ANALYSIS_CLAIM_LOST:
      "Không thể lưu kết quả rà soát vì lượt xử lý đã thay đổi. Hãy tải lại và chạy lại.",
    IMPACT_SOURCE_CHANGED:
      "Nguồn hoặc liên kết truy vết đã thay đổi sau lần phân tích. Hãy chạy lại phân tích trước khi tiếp tục.",
    SCENARIO_INCOMPLETE: "Bổ sung mục tiêu và yêu cầu nguồn trước khi duyệt kịch bản.",
    SCENARIO_DRAFT_REQUIRED: "Kịch bản mới phải được lưu nháp trước khi gửi rà soát.",
    SCENARIO_BATCH_SIZE_INVALID:
      "Nhóm kịch bản cần có từ 1 đến 100 mục. Hãy điều chỉnh lựa chọn rồi thử lại.",
    SCENARIO_KEY_EXISTS:
      "Mã kịch bản đã được dùng trong dự án. Tải lại danh sách hoặc chọn mã khác.",
    SCENARIO_PREVIEW_REQUIRED: "Hãy xem trước và chọn các kịch bản cần lưu trước khi tiếp tục.",
    SCENARIO_PREVIEW_STALE:
      "Yêu cầu hoặc tiêu chí đã thay đổi sau lần xem trước. Tải lại nguồn và tạo bản xem trước mới.",
    IMMUTABLE_SCENARIO:
      "Kịch bản đã gửi rà soát hoặc được duyệt. Hãy yêu cầu chỉnh sửa hoặc tạo bản sao để thay đổi nội dung.",
    ACCEPTANCE_CRITERIA_NOT_IN_REQUIREMENT:
      "Có tiêu chí không thuộc phiên bản yêu cầu đã chọn. Tải lại yêu cầu và chọn lại tiêu chí.",
    DUPLICATE_ACCEPTANCE_CRITERIA:
      "Một tiêu chí đang được chọn nhiều lần. Bỏ lựa chọn trùng rồi thử lại.",
    DUPLICATE_DESIGN_TECHNIQUE:
      "Một kỹ thuật kiểm thử đang được chọn nhiều lần. Bỏ lựa chọn trùng rồi thử lại.",
    GENERATION_EVIDENCE_LIMIT_EXCEEDED:
      "Yêu cầu có quá nhiều tiêu chí để tạo ca đầy đủ trong một lượt. Chưa có ca nào được tạo; hãy thu hẹp phạm vi.",
    GENERATION_INSTRUCTION_TOO_LONG:
      "Hướng dẫn bổ sung quá dài. Rút gọn nội dung rồi tạo bản xem trước lại.",
    GENERATION_LIMIT_EXCEEDED:
      "Số ca yêu cầu vượt giới hạn cho một lượt. Giảm số lượng hoặc chia thành các lượt riêng.",
    INVALID_GENERATION_CATEGORIES:
      "Có loại kiểm thử không còn hợp lệ. Tải lại danh sách lựa chọn rồi thử lại.",
    AI_GENERATION_INVALID:
      "Chưa tạo được bản nháp kiểm thử hợp lệ. Không có kết quả nào được lưu; hãy thử lại.",
    AI_PROVIDER_UNAVAILABLE:
      "Dịch vụ AI đang tạm thời không phản hồi. Dữ liệu hiện có được giữ nguyên; hãy thử lại sau.",
    AI_UNGROUNDED_OUTPUT:
      "Đề xuất có nội dung chưa được tài liệu xác nhận. Bổ sung nguồn hoặc điều chỉnh phạm vi rồi thử lại.",
    AI_RECOMMENDATION_INVALID:
      "Chưa tạo được đề xuất hợp lệ. Dữ liệu hiện có được giữ nguyên; hãy tải lại rồi thử lại.",
    TECHNIQUE_EVIDENCE_INSUFFICIENT:
      "Nguồn hiện tại chưa đủ căn cứ cho các kỹ thuật đã chọn. Bổ sung tài liệu hoặc chọn kỹ thuật phù hợp hơn.",
    TECHNIQUE_EVIDENCE_LIMIT_EXCEEDED:
      "Phạm vi bằng chứng vượt giới hạn của một lượt. Hãy thu hẹp nguồn trước khi tạo ca.",
    TECHNIQUE_GENERATION_INCOMPLETE:
      "Chưa tạo được ca cho mọi kỹ thuật đã chọn. Chưa lưu nhóm ca thiếu; hãy xem lại nguồn hoặc số lượng ca.",
    TEST_DESIGN_REQUIREMENT_CHANGED:
      "Yêu cầu đã thay đổi hoặc chưa còn được duyệt. Tải lại phiên bản yêu cầu trước khi tạo hoặc lưu ca.",
    TEST_DESIGN_PREVIEW_STALE:
      "Yêu cầu hoặc bộ ca hiện có đã thay đổi sau lần xem trước. Tạo lại bản xem trước trước khi lưu.",
    TEST_DESIGN_CHALLENGE_SOURCE_CHANGED:
      "Giả thuyết kiểm thử không còn khớp với nguồn hoặc kỹ thuật đã chọn. Nhận lại gợi ý rồi thử lại.",
    TEST_DESIGN_CHALLENGE_NOT_ADDRESSED:
      "Chưa có ca kiểm thử cho mọi giả thuyết đã chọn. Bổ sung căn cứ hoặc thu hẹp giả thuyết.",
    TEST_DESIGN_CHALLENGE_NOT_DISTINGUISHING:
      "Ca đề xuất chưa phân biệt được với ca hiện có. Nhận gợi ý mới hoặc điều chỉnh phạm vi kiểm thử.",
    TEST_CASE_PREVIEW_REQUIRED: "Hãy xem trước và chọn các ca cần lưu trước khi tiếp tục.",
    TEST_CASE_DRAFT_REVISION_REQUIRED:
      "Thiếu thông tin phiên bản bản nháp. Tải lại ca rồi thử lại.",
    TEST_CASE_DRAFT_REVISION_STALE:
      "Bản nháp đã thay đổi trong lúc xử lý. Tải lại và đối chiếu trước khi tiếp tục.",
    SYSTEM_ADMIN_REQUIRED: "Thao tác này chỉ dành cho Admin hệ thống.",
    PAYROLL_FILE_EMPTY: "Tệp không có dữ liệu. Hãy chọn một tệp khác.",
    PAYROLL_FILE_TOO_LARGE: "Tệp vượt quá dung lượng cho phép. Hãy giảm dung lượng rồi thử lại.",
    PAYROLL_FILE_FORMAT_UNSUPPORTED: "Chỉ hỗ trợ tệp CSV hoặc XLSX.",
    PAYROLL_DOCLING_CONVERSION_FAILED:
      "Không đọc được bảng lương. Kiểm tra lại tệp hoặc lưu thành CSV/XLSX rồi thử lại.",
    PAYROLL_DOCUMENT_HAS_UNPROCESSED_BLOCKS:
      "Một phần bảng lương chưa đọc được. Hãy kiểm tra tệp và thử nhập lại.",
    PAYROLL_SHEET_EMPTY: "Không tìm thấy bảng có tiêu đề và dữ liệu trong tệp.",
    PAYROLL_HEADERS_MUST_BE_NONEMPTY_AND_UNIQUE:
      "Các cột cần có tên riêng biệt. Hãy sửa hàng tiêu đề trong tệp rồi nhập lại.",
    PAYROLL_COLUMN_MAPPING_INVALID:
      "Cách ghép cột không hợp lệ. Chọn lại các cột trong bản xem trước.",
    PAYROLL_COLUMN_NOT_FOUND:
      "Một cột đã chọn không còn trong tệp. Đọc lại tiêu đề rồi chọn cột lại.",
    PAYROLL_PREVIEW_NOT_FOUND: "Không tìm thấy bản xem trước. Hãy tạo bản xem trước mới.",
    PAYROLL_PREVIEW_REVISION_CONFLICT:
      "Bản xem trước đã thay đổi. Tải lại và kiểm tra các dòng trước khi áp dụng.",
    PAYROLL_PREVIEW_EXPIRED: "Bản xem trước đã hết hạn. Hãy tạo bản xem trước mới.",
    PAYROLL_ROWS_REQUIRE_RESOLUTION:
      "Hãy đánh dấu bỏ qua các dòng lỗi hoặc xung đột trước khi áp dụng những dòng hợp lệ.",
    PAYROLL_CONFLICT_MUST_BE_REIMPORTED_WITH_NON_OVERLAPPING_DATES:
      "Các thời hạn đang bị chồng lấn. Sửa ngày hiệu lực trong tệp rồi nhập lại các dòng đó.",
    PAYROLL_RATE_CHANGED_REPREVIEW_REQUIRED:
      "Đơn giá đã thay đổi sau khi xem trước. Tạo bản xem trước mới để kiểm tra trước khi áp dụng.",
    PAYROLL_EMPLOYEE_REQUIRED: "Nhập mã nhân viên hoặc email ở dòng này.",
    PAYROLL_EMPLOYEE_NOT_FOUND: "Không tìm thấy tài khoản khớp với mã nhân viên hoặc email này.",
    HOURLY_COST_INVALID: "Đơn giá phải lớn hơn 0 và có tối đa 4 chữ số thập phân.",
    PAYROLL_CURRENCY_INVALID: "Mã tiền tệ cần có 3 chữ cái, ví dụ VND hoặc USD.",
    PAYROLL_DATE_INVALID: "Ngày hiệu lực không hợp lệ. Dùng định dạng YYYY-MM-DD.",
    PAYROLL_PERIOD_INVALID: "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.",
    CAPACITY_PERIOD_OVERLAP:
      "Khoảng thời gian này trùng với kỳ công suất đã khai báo. Chọn một kỳ không chồng lấn.",
    CAPACITY_REVISION_CONFLICT:
      "Kỳ công suất đã được cập nhật ở nơi khác. Tải lại dữ liệu rồi lưu lại thay đổi.",
    CAPACITY_USER_NOT_FOUND:
      "Có tài khoản trong danh sách công suất không còn hợp lệ. Tải lại danh sách nhân sự.",
    PROJECT_FINANCIAL_REVISION_CONFLICT:
      "Giá và điều khoản dự án đã thay đổi ở nơi khác. Tải lại dự án rồi lưu lại.",
    PROJECT_NOT_FOUND: "Không tìm thấy dự án hoặc bạn không còn quyền truy cập.",
    TEST_PLAN_NOT_FOUND: "Không tìm thấy kế hoạch kiểm thử. Tải lại danh sách rồi thử lại.",
    IMPORT_CANDIDATE_COUNT_INVALID:
      "Số yêu cầu trong bản nhập không hợp lệ. Tạo lại bản xem trước rồi thử lại.",
    IMPORT_CANDIDATE_INCOMPLETE:
      "Một yêu cầu đang thiếu nội dung hoặc nguồn dẫn. Bổ sung dữ liệu trước khi nhập.",
    IMPORT_CANDIDATE_LIMIT_EXCEEDED:
      "Tài liệu tạo ra quá nhiều yêu cầu trong một lượt. Chia nhỏ phạm vi rồi nhập lại.",
    IMPORT_CANDIDATE_NOT_FOUND: "Không tìm thấy mục nhập này. Tải lại bản xem trước.",
    IMPORT_CONFIRMATION_CONFLICT:
      "Bản nhập đã thay đổi trong lúc xác nhận. Tải lại trạng thái trước khi tiếp tục.",
    IMPORT_CONFIRMED_VERSION_MISSING:
      "Không tìm thấy phiên bản yêu cầu đã xác nhận. Tải lại bản nhập để đối chiếu.",
    IMPORT_MATCH_CHANGED:
      "Các yêu cầu hiện có đã thay đổi sau lần đối chiếu. Chạy đối chiếu lại trước khi nhập.",
    IMPORT_MATCH_REVIEW_REQUIRED:
      "Có yêu cầu gần trùng cần được xem xét. Chọn cách xử lý cho từng mục rồi tiếp tục.",
    IMPORT_REQUIREMENT_COMPARISON_LIMIT_EXCEEDED:
      "Có quá nhiều yêu cầu cần đối chiếu cùng lúc. Thu hẹp lựa chọn rồi thử lại.",
    IMPORT_REQUIREMENT_KEY_CONFLICT:
      "Mã yêu cầu trong bản nhập bị trùng. Sửa mã hoặc bỏ chọn mục trùng rồi thử lại.",
    IMPORT_REQUIREMENT_VERSION_MISSING:
      "Không tìm thấy phiên bản yêu cầu cần đối chiếu. Tải lại dữ liệu dự án.",
    IMPORT_RESOLUTION_INCOMPLETE:
      "Chưa chọn cách xử lý cho mọi yêu cầu trùng. Hoàn tất lựa chọn rồi tiếp tục.",
    IMPORT_RESOLUTION_TARGET_REQUIRED: "Chọn yêu cầu đích để liên kết mục này rồi tiếp tục.",
    IMPORT_REVISION_CONFLICT:
      "Bản nhập đã được cập nhật ở nơi khác. Tải lại bản xem trước rồi thử lại.",
    IMPORT_SELECTION_REQUIRED: "Chọn ít nhất một yêu cầu để nhập.",
    IMPORT_SEPARATE_REASON_REQUIRED: "Ghi lý do giữ riêng yêu cầu gần trùng trước khi xác nhận.",
    IMPORT_SOURCE_MISSING:
      "Không tìm thấy tài liệu nguồn của bản nhập. Tải lại tài liệu rồi tạo bản xem trước mới.",
    IMPORT_TEST_CASE_IMPACT_LIMIT_EXCEEDED:
      "Có quá nhiều ca kiểm thử bị ảnh hưởng để đối chiếu trong một lượt. Thu hẹp phạm vi rồi thử lại.",
    INVALID_IMPORT_RESOLUTION:
      "Cách xử lý yêu cầu trùng không còn hợp lệ. Tải lại bản xem trước và chọn lại.",
    REQUIREMENT_EVIDENCE_INVALID:
      "Nguồn dẫn của yêu cầu không khớp nội dung tài liệu. Hãy tạo lại bản xem trước.",
    REQUIREMENT_EXTRACTION_UNAVAILABLE:
      "Chưa trích xuất được yêu cầu từ tài liệu. Tài liệu vẫn được giữ nguyên; hãy thử lại sau.",
    REQUIREMENT_SEMANTIC_MATCH_UNAVAILABLE:
      "Chưa thể đối chiếu các yêu cầu tương tự. Dữ liệu chưa được xác nhận; hãy thử lại sau.",
    REQUIREMENT_SOURCE_TOO_LARGE:
      "Tài liệu vượt giới hạn xử lý yêu cầu. Chia nhỏ tài liệu rồi nhập lại.",
    SOURCE_LINK_REQUIRES_EXACT_MATCH:
      "Chỉ có thể liên kết nguồn khi nội dung khớp chính xác. Chọn một kết quả khớp hoàn toàn.",
    SOURCE_LINK_STATE_CHANGED:
      "Trạng thái liên kết nguồn đã thay đổi. Tải lại bản đối chiếu trước khi tiếp tục.",
    TEMPLATE_SOURCE_ACCESS_DENIED:
      "Bạn không có quyền truy cập mẫu nguồn này. Chọn mẫu khác hoặc liên hệ quản trị viên.",
    DUPLICATE_PREVIEW_INDEX:
      "Một mục xem trước đang được chọn nhiều lần. Bỏ lựa chọn trùng rồi thử lại.",
    COVERAGE_ITEM_SOURCE_INVALID:
      "Một mục truy vết không còn hợp lệ trong nguồn đã chọn. Tải lại yêu cầu và chọn lại.",
    IDEMPOTENCY_RECEIPT_INCOMPLETE:
      "Chưa xác minh được kết quả lần lưu trước. Tải lại dữ liệu trước khi thử lại để tránh ghi trùng.",
    REUSABLE_TEST_STEP_NOT_FOUND:
      "Không tìm thấy bước kiểm thử dùng lại. Tải lại thư viện bước rồi chọn lại.",
    TEST_REPOSITORY_NODE_NOT_FOUND:
      "Không tìm thấy thư mục ca kiểm thử. Tải lại cấu trúc kho rồi chọn lại.",
    INVALID_STATE_TRANSITION:
      "Trạng thái đã thay đổi nên thao tác này không còn phù hợp. Tải lại dữ liệu rồi thử lại.",
    PROJECT_RESPONSIBILITY_REQUIRED:
      "Bạn chưa được phân công thực hiện quyết định này. Liên hệ người quản lý dự án để kiểm tra phân công.",
    PROJECT_RESPONSIBILITIES_INVALID:
      "Thông tin người chịu trách nhiệm không hợp lệ. Chọn lại thành viên dự án.",
    PROJECT_RESPONSIBLE_MEMBER_INVALID:
      "Người được chọn phải đang hoạt động trong dự án và có vai trò phù hợp.",
    REVIEW_AUTHORSHIP_UNVERIFIED:
      "Lịch sử người sửa bản này chưa đầy đủ để xác minh duyệt độc lập. Cần đối chiếu lịch sử trước khi duyệt.",
    REQUIREMENT_TECHNICAL_REVIEW_REQUIRED:
      "Cần hoàn tất rà soát kỹ thuật cho phiên bản hiện tại trước khi xác nhận nghiệp vụ.",
    DESIGN_ASSIGNMENT_REQUIRED: "Bạn chỉ được soạn nội dung kiểm thử đã được giao cho mình.",
    DESIGN_REASSIGNMENT_DENIED: "Chỉ người có quyền phân công mới được thay đổi người phụ trách.",
    DEFECT_TRIAGE_AUTHORITY_REQUIRED:
      "Việc đổi mức độ, ưu tiên hoặc người phụ trách lỗi cần quyền phân loại lỗi.",
    DEFECT_ASSIGNMENT_REQUIRED: "Bạn chỉ được sửa lỗi đang được giao cho mình.",
    TEST_CASE_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa ca này không thể tự duyệt. Một người có quyền khác cần xem và quyết định.",
    TEST_PLAN_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa kế hoạch này không thể tự duyệt. Một người có quyền khác cần xem và quyết định.",
    REQUIREMENT_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa yêu cầu không thể tự xác nhận cùng phiên bản.",
    TEST_SCENARIO_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa kịch bản rà soát không thể tự duyệt kịch bản đó.",
    TEST_CONDITION_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa điều kiện rà soát không thể tự duyệt điều kiện đó.",
    TEST_ADEQUACY_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa hồ sơ bảo đảm rà soát không thể tự duyệt hồ sơ đó.",
    TEST_STATUS_REPORT_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa báo cáo trạng thái rà soát không thể tự duyệt báo cáo đó.",
    TEST_COMPLETION_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa báo cáo hoàn tất rà soát không thể tự duyệt báo cáo đó.",
    TEST_STRATEGY_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa chiến lược rà soát không thể tự duyệt chiến lược đó.",
    CAUSAL_ANALYSIS_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa phân tích nguyên nhân rà soát không thể tự duyệt phân tích đó.",
    QUALITY_EVALUATION_SELF_REVIEW_FORBIDDEN:
      "Người tạo hoặc sửa đánh giá chất lượng rà soát không thể tự duyệt đánh giá đó.",
    PROJECT_MISMATCH:
      "Mục đã chọn không thuộc dự án hiện tại. Tải lại dữ liệu và chọn mục trong đúng dự án.",
    VERIFIED_REQUIREMENT_EVENT_REQUIRED:
      "Chỉ có thể phân tích yêu cầu đã được xác minh. Mở yêu cầu và hoàn tất bước rà soát trước.",
    TEST_CONDITION_EVENT_KEY_INVALID:
      "Mã điều kiện kiểm thử không hợp lệ. Tải lại dữ liệu rồi thử lại.",
    TEST_CONDITION_EVENT_KEY_CONFLICT:
      "Điều kiện kiểm thử đã được cập nhật ở nơi khác. Tải lại danh sách rồi thử lại.",
    TEST_BASIS_SOURCE_CHANGED: "Nguồn kiểm thử đã thay đổi. Phân tích lại trước khi tiếp tục.",
    TEST_BASIS_NOT_BASELINED:
      "Chưa ghi nhận phiên bản cơ sở của nguồn kiểm thử. Tải lại yêu cầu rồi tạo bản phân tích mới.",
    REQUIREMENT_EVENT_SOURCE_CHANGED:
      "Yêu cầu hoặc phiên bản nguồn đã đổi sau khi mở lượt phân tích. Tải lại rồi chạy lại.",
    ENTITY_NOT_FOUND: "Không tìm thấy mục cần xử lý. Tải lại dữ liệu rồi thử lại.",
    TEST_RUN_NOT_FOUND: "Không tìm thấy lượt chạy kiểm thử. Tải lại danh sách rồi thử lại.",
    EXECUTION_CONFLICT:
      "Kết quả thực thi đã được cập nhật ở nơi khác. Tải lại lượt chạy trước khi ghi kết quả.",
    API_DEFINITION_INVALID:
      "Không đọc được đặc tả API. Kiểm tra lại định dạng OpenAPI hoặc Postman rồi tải lên lại.",
    API_ARTIFACT_REQUIRED: "Chọn tệp OpenAPI hoặc Postman để tiếp tục.",
    API_ARTIFACT_JSON_INVALID: "Nội dung tệp không phải JSON hợp lệ. Sửa tệp rồi thử lại.",
    API_ARTIFACT_OBJECT_REQUIRED:
      "Nội dung đặc tả cần có cấu trúc JSON dạng đối tượng ở cấp cao nhất.",
    API_ARTIFACT_HAS_NO_OPERATIONS:
      "Không tìm thấy thao tác API trong đặc tả. Kiểm tra lại đường dẫn và phương thức.",
    API_ARTIFACT_NOT_REVIEWABLE:
      "Bản nhập này không còn ở trạng thái có thể rà soát. Tải lại danh sách để xem trạng thái mới.",
    API_ARTIFACT_SELECTION_REQUIRED: "Chọn ít nhất một thao tác API sau khi rà soát.",
    API_ARTIFACT_REVIEW_REQUIRED: "Hãy rà soát và xác nhận đặc tả API trước khi tiếp tục.",
    API_ARTIFACT_NOT_CONFIRMED: "Đặc tả API chưa được xác nhận nên chưa thể tạo ca kiểm thử.",
    API_ARTIFACT_VERSION_INVALID:
      "Không tìm thấy đủ hai phiên bản đặc tả API để so sánh. Tải lại danh sách phiên bản.",
    API_OPERATION_SOURCE_INVALID:
      "Thao tác API không còn liên kết với đặc tả đã xác nhận. Tải lại dữ liệu trước khi tiếp tục.",
    API_OPERATION_EVIDENCE_TOO_LARGE:
      "Thao tác API có quá nhiều nội dung để tạo ca trong một lượt. Hãy giảm phạm vi đặc tả.",
    API_TEST_GENERATION_REQUIRES_AUTOMATION_EVENT:
      "Chưa thể chạy sinh ca cho thao tác API này. Kiểm tra trạng thái xử lý rồi thử lại.",
    API_TEST_GENERATION_UNAVAILABLE:
      "AI chưa thể tạo ca từ đặc tả API lúc này. Đặc tả vẫn được giữ nguyên; hãy thử lại sau.",
    API_TEST_GENERATION_CONTRACT_INVALID:
      "AI trả về ca không đúng cấu trúc. Chưa có ca nào được nhập; hãy thử lại.",
    API_TEST_GENERATION_EVIDENCE_INSUFFICIENT:
      "Đặc tả chưa có đủ thông tin để tạo ca kiểm thử. Bổ sung mô tả hoặc schema cho thao tác API.",
    API_TEST_GENERATION_GROUNDING_INVALID:
      "Một ca AI đề xuất không khớp với đặc tả API đã xác nhận. Ca chưa được lưu; hãy thử lại.",
    API_OPERATION_SOURCE_CHANGED:
      "Đặc tả API đã thay đổi sau lần xem trước. Tạo lại bản xem trước trước khi tiếp tục.",
    INVALID_PREVIEW_INDEX:
      "Lựa chọn thao tác API không còn hợp lệ. Tải lại bản xem trước rồi chọn lại.",
    TEST_IMPORT_IDEMPOTENCY_CONFLICT:
      "Mã xử lý bản nhập đã được dùng cho dữ liệu khác. Tạo lượt nhập mới rồi thử lại.",
    TEST_IMPORT_FORMAT_UNSUPPORTED: "Định dạng tệp chưa được hỗ trợ để nhập ca kiểm thử.",
    TEST_IMPORT_ROW_LIMIT_EXCEEDED:
      "Tệp có quá nhiều dòng để xử lý cùng lúc. Chia tệp thành các phần nhỏ hơn rồi nhập lại.",
    TEST_IMPORT_ROWS_INCOMPLETE:
      "Một số dòng thiếu tên hoặc nội dung kiểm thử bắt buộc. Sửa các dòng được báo rồi nhập lại.",
    TEST_IMPORT_EMPTY: "Tệp không có ca kiểm thử để nhập.",
    TEST_IMPORT_ENCODING_INVALID:
      "Không đọc được bảng mã của tệp. Lưu lại tệp bằng UTF-8 rồi thử nhập lại.",
    TEST_IMPORT_SOURCE_CHANGED:
      "Nguồn API đã thay đổi hoặc được lưu trữ. Tạo lại bản xem trước trước khi nhập ca.",
    TEST_IMPORT_SELECTION_REQUIRED: "Chọn ít nhất một ca trong bản xem trước để nhập.",
    TEST_IMPORT_AUTOMATION_EMPTY_SELECTION_UNSAFE:
      "Không thể tự nhập nhóm ca này vì còn nội dung cần người rà soát. Mở bản xem trước và chọn ca phù hợp.",
    TEST_IMPORT_CONFIRM_IN_PROGRESS:
      "Bản nhập đang được xử lý. Chờ hoàn tất rồi tải lại trạng thái trước khi thử lại.",
    TEST_IMPORT_RESOLUTION_INVALID:
      "Cách xử lý ca trùng hoặc phiên bản không hợp lệ. Tải lại bản xem trước và kiểm tra lựa chọn.",
    TEST_IMPORT_SEPARATE_REASON_REQUIRED:
      "Ghi lý do giữ ca riêng khi nội dung gần giống một ca đã có.",
    TEST_IMPORT_INCOMPLETE_ACK_REQUIRED:
      "Xác nhận ca thiếu bước hoặc kết quả kiểm chứng trước khi tiếp tục nhập.",
    TEST_IMPORT_REUPLOAD_REQUIRED:
      "Nguồn của bản xem trước đã cũ. Tải tệp lên lại để kiểm tra trước khi nhập.",
    TEST_IMPORT_DRAFT_INVALID:
      "Một ca trong bản xem trước không hợp lệ. Chưa có ca nào được nhập; hãy tạo lại bản xem trước.",
    TEST_IMPORT_DUPLICATE_REVIEW_REQUIRED:
      "Có ca gần trùng với ca đã có. Bỏ chọn ca trùng hoặc ghi lý do giữ riêng trước khi nhập.",
    TEST_IMPORT_TARGET_CHANGED:
      "Ca hoặc phiên bản đích đã thay đổi sau lần xem trước. Tải lại và đối chiếu trước khi nhập.",
    DOCUMENT_SUMMARY_JOB_CONTEXT_INVALID:
      "Không thể xác minh dự án của yêu cầu tóm tắt. Tải lại trang rồi thử lại.",
    DOCUMENT_SUMMARY_JOB_NOT_FOUND:
      "Không tìm thấy lượt tóm tắt này. Tải lại tài liệu để kiểm tra trạng thái mới nhất.",
    DOCUMENT_SUMMARY_JOB_NOT_CANCELLABLE: "Lượt tóm tắt đã kết thúc nên không thể hủy.",
    DOCUMENT_SUMMARY_JOB_NOT_RETRYABLE:
      "Lượt tóm tắt hiện không thể chạy lại. Tạo một lượt tóm tắt mới để tiếp tục.",
    DOCUMENT_SUMMARY_JOB_RUNNING: "Lượt tóm tắt đang chạy. Hãy chờ hoàn tất trước khi thử lại.",
    SUMMARY_SOURCE_CHANGED_OR_ACCESS_REVOKED:
      "Tài liệu đã thay đổi hoặc quyền truy cập không còn hiệu lực. Kiểm tra lại nguồn rồi tạo lượt tóm tắt mới.",
    SUMMARY_WORKER_UNAVAILABLE:
      "Dịch vụ xử lý tài liệu đang tạm thời không sẵn sàng. Dữ liệu nguồn được giữ nguyên; hãy thử lại sau.",
    SUMMARY_WORKER_FAILED:
      "Chưa thể tóm tắt tài liệu trong lượt này. Dữ liệu nguồn được giữ nguyên; hãy thử lại.",
    SUMMARY_FAILED:
      "Một phần tài liệu chưa tóm tắt được. Xem danh sách tài liệu bị bỏ qua hoặc thử lại phần còn thiếu.",
    RuntimeError: "Quá trình tóm tắt gặp lỗi. Dữ liệu nguồn được giữ nguyên; hãy thử lại sau.",
    TimeoutError: "Quá trình tóm tắt quá thời gian cho phép. Hãy thử lại sau.",
    ValueError: "Nội dung tài liệu chưa phù hợp để tóm tắt. Kiểm tra lại tệp rồi thử lại.",
    TEST_PLAN_DATA_OWNER_NOT_ACTIVE:
      "Người chuẩn bị dữ liệu phải là thành viên đang hoạt động của dự án.",
    TEST_PLAN_REVISION_REASON_REQUIRED: "Nhập lý do yêu cầu chỉnh sửa kế hoạch.",
    COMPLETION_AI_SOURCE_CHANGED:
      "Báo cáo đã thay đổi. Hãy tải lại trước khi yêu cầu AI tạo đề xuất.",
    COMPLETION_AI_UNAVAILABLE: "AI chưa tạo được đề xuất hợp lệ. Hãy thử lại sau.",
    STATUS_REPORT_AI_UNAVAILABLE: "AI chưa tạo được diễn giải hợp lệ. Hãy thử lại sau.",
    STATUS_REPORT_EVENT_SUPERSEDED:
      "Báo cáo đã thay đổi. Hãy tải lại trước khi yêu cầu AI tạo đề xuất.",
    DUPLICATE_SOURCE_NOT_READY:
      "Tài liệu trùng đang được xử lý hoặc chưa phân tích xong. Hãy chờ nguồn sẵn sàng rồi thử lại.",
    DUPLICATE_SOURCE_ARCHIVED:
      "Tài liệu trùng đang được lưu trữ. Hãy khôi phục tài liệu hiện có trước khi dùng lại.",
    DUPLICATE_SOURCE_RECOVERY_PENDING:
      "Đã tìm thấy tài liệu trùng nhưng chưa khôi phục được chỉ mục. Nguồn vẫn được giữ; hãy thử lại sau.",
    DUPLICATE_SOURCE_SETTINGS_CONFLICT:
      "Tệp này đã có trong dự án với phạm vi chia sẻ hoặc cấu hình AI khác.",
    SOURCE_EXTRACTION_INCOMPLETE:
      "Tự động hóa đã dừng an toàn vì còn phần tài liệu chưa trích xuất đầy đủ. Xem chi tiết vị trí trong kết quả lượt chạy.",
    TEST_CASE_CUSTOM_FIELD_VALUE_INVALID:
      "Một hoặc nhiều trường mở rộng chưa khớp kiểu dữ liệu hoặc lựa chọn đã cấu hình.",
    TEST_CASE_CUSTOM_FIELD_REQUIRED:
      "Cần điền các trường mở rộng bắt buộc trước khi gửi duyệt hoặc duyệt ca.",
    TEST_CASE_CUSTOM_FIELD_UNKNOWN:
      "Có trường mở rộng không còn cấu hình trong dự án. Hãy bỏ trường cũ hoặc tải lại dữ liệu.",
    TEST_CASE_OWNER_ROLE_INVALID: "Người phụ trách phải là thành viên đang hoạt động của dự án.",
    TEST_CASE_COMPARISON_STALE:
      "Bản so sánh hoặc nguồn đã thay đổi. Mở lại ca để đối chiếu trước khi duyệt.",
    TEST_CASE_STEPS_REQUIRED:
      "Ca kiểm thử cần có ít nhất một bước với kết quả mong đợi trước khi duyệt.",
    TEST_CASE_SOURCE_REVIEW_REQUIRED:
      "Ca do AI đề xuất chưa có dẫn chứng nguồn. Đối chiếu nguồn và lưu lại trước khi duyệt.",
    TEST_CASE_DUPLICATE_REVIEW_REQUIRED:
      "Ca gần trùng với ca đang hiệu lực. Hãy loại ca trùng hoặc ghi lý do giữ riêng trước khi duyệt.",
    TEST_CASE_BATCH_DUPLICATE_REVIEW_REQUIRED:
      "Các ca được chọn có nội dung gần trùng. Bỏ ca trùng hoặc ghi lý do giữ riêng trước khi duyệt.",
    TEST_CASE_BATCH_SIZE_INVALID:
      "Nhóm cần có từ 1 đến 100 ca. Hãy điều chỉnh lựa chọn rồi thử lại.",
    TEST_CASE_BATCH_SOURCE_MISMATCH:
      "Các ca trong nhóm không cùng lượt đề xuất. Tải lại danh sách và chọn lại nhóm cần xử lý.",
    TEST_CASE_BATCH_TARGET_CONFLICT:
      "Có nhiều đề xuất cùng nhắm đến một ca gốc. Chỉ chọn một đề xuất cho mỗi ca trong lượt này.",
    TEST_CASE_LINT_BLOCKED:
      "Ca kiểm thử còn lỗi nội dung bắt buộc. Mở ca, xử lý các mục được đánh dấu rồi gửi duyệt lại.",
    TEST_CASE_EVIDENCE_CHANGED:
      "Yêu cầu hoặc tiêu chí nguồn đã thay đổi. Tải lại ca, đối chiếu nguồn mới rồi lưu lại.",
    TEST_CASE_EVIDENCE_REQUIRED:
      "Ca do AI tạo cần liên kết với yêu cầu và có dẫn chứng nguồn trước khi lưu.",
    TEST_CASE_EXISTING_KEY_REQUIRES_VERSION_DRAFT:
      "Mã ca này đã tồn tại. Hãy tạo bản nháp phiên bản mới cho ca hiện có thay vì tạo ca khác cùng mã.",
    TEST_CASE_IMPACT_REASON_REQUIRED: "Hãy ghi lý do đánh giá ảnh hưởng trước khi duyệt ca.",
    TEST_CASE_MERGE_INCOMPLETE:
      "Không xác minh được bản ghép đã lưu. Tải lại ca để kiểm tra trạng thái trước khi thao tác tiếp.",
    TEST_CASE_MERGE_INVALID:
      "Bản ghép chưa hợp lệ. Kiểm tra nội dung, các bước và nguồn dẫn rồi lưu lại.",
    TEST_CASE_OWNER_NOT_ACTIVE_PROJECT_MEMBER:
      "Người phụ trách phải là thành viên đang hoạt động của dự án.",
    TEST_CASE_STEP_IDENTITY_CONFLICT:
      "Một bước đã bị thay đổi trong lúc ghép. Tải lại ca và đối chiếu các bước trước khi lưu.",
    TEST_CASE_VERSION_RESOLUTION_INVALID:
      "Thông tin tạo phiên bản chưa hợp lệ. Kiểm tra ca đích và lý do thay đổi rồi thử lại.",
    TEST_CASE_VERSION_TARGET_CHANGED:
      "Ca đích đã thay đổi sau khi tạo bản xem trước. Tạo lại bản xem trước trước khi lưu.",
    TEST_CASE_CURRENT_VERSION_MISSING:
      "Không tìm thấy phiên bản ca đang hiệu lực để đối chiếu trùng lặp. Nhóm chưa được duyệt; hãy tải lại và báo quản trị viên nếu lỗi còn tiếp diễn.",
    TEST_CASE_BASE_VERSION_CHANGED:
      "Ca gốc đã được cập nhật trong lúc rà soát. Tải lại, đối chiếu phiên bản mới rồi duyệt lại.",
    TEST_CASE_PARENT_VERSION_CHANGED:
      "Ca đã có phiên bản gốc mới. Tải lại và đối chiếu trước khi duyệt.",
    TEST_CASE_VERSION_CONFLICT:
      "Phiên bản ca vừa thay đổi. Nhóm chưa được duyệt; tải lại rồi đối chiếu lại.",
    TEST_CASE_VERSION_HISTORY_INVALID:
      "Lịch sử phiên bản của ca không nhất quán. Ca chưa được duyệt; cần kiểm tra dữ liệu trước khi tiếp tục.",
    TEST_CASE_APPROVAL_INCOMPLETE:
      "Không xác minh được kết quả duyệt nhóm. Hãy tải lại danh sách để kiểm tra trạng thái từng ca trước khi thao tác tiếp.",
    MULTIPLE_DRAFTS_FOR_SAME_TEST_CASE:
      "Nhóm có nhiều bản nháp cho cùng một mã ca. Chỉ chọn một bản cho mỗi mã rồi thử lại.",
    MAX_CONCURRENT_PROJECTS_REACHED:
      "Người được chọn đã đạt giới hạn số dự án đang thực hiện. Thay đổi chưa được lưu; hãy chọn người khác hoặc nhờ Admin cập nhật giới hạn.",
    RESOURCE_CAPACITY_CHANGED_RETRY_ASSIGNMENT:
      "Giới hạn công suất vừa thay đổi. Hãy tải lại dữ liệu rồi thử phân công lại.",
    PROJECT_COMPLEXITY_EVIDENCE_REQUIRED:
      "Chưa có tài liệu được phép dùng AI hoặc yêu cầu đã duyệt để đánh giá dự án.",
    PROJECT_COMPLEXITY_SOURCE_SCOPE_UNAVAILABLE:
      "Nguồn đã chọn không còn hợp lệ hoặc không còn trong phạm vi được phép. Hãy tải lại danh sách nguồn.",
    PROJECT_COMPLEXITY_SOURCE_SCOPE_REQUIRED:
      "Hãy chọn ít nhất một tài liệu hoặc yêu cầu đã duyệt để đánh giá.",
    PROJECT_COMPLEXITY_SOURCE_SCOPE_TOO_LARGE:
      "Phạm vi tài liệu vượt giới hạn cho một lượt đánh giá. Hãy thu hẹp nguồn hoặc chia phạm vi trước khi chạy; hệ thống chưa đánh giá một phần.",
    PROJECT_COMPLEXITY_RESPONSE_INVALID:
      "AI trả về hồ sơ đánh giá chưa đầy đủ. Không có kết quả nào được lưu.",
    PROJECT_COMPLEXITY_DIMENSIONS_INVALID:
      "AI chưa đánh giá đủ các chiều cần thiết. Không có kết quả nào được lưu.",
    PROJECT_COMPLEXITY_EVIDENCE_REFERENCE_INVALID:
      "AI dẫn đến nguồn không thuộc phạm vi dự án. Không có kết quả nào được lưu.",
    PROJECT_COMPLEXITY_GROUNDING_REQUIRED:
      "AI chưa đưa ra căn cứ cho một mức đánh giá. Không có kết quả nào được lưu.",
    PROJECT_COMPLEXITY_GROUNDING_INVALID:
      "Một trích dẫn không khớp nguyên văn với nguồn. Không có kết quả nào được lưu.",
    PROJECT_COMPLEXITY_SOURCES_CHANGED:
      "Nguồn đã thay đổi trong lúc đánh giá. Hãy chạy lại để dùng phiên bản mới nhất.",
    PROJECT_COMPLEXITY_IDEMPOTENCY_KEY_REUSED:
      "Yêu cầu đánh giá đã đổi nhưng đang dùng lại mã của lần trước. Hãy bấm đánh giá lại.",
    PROJECT_COMPLEXITY_ASSESSMENT_IN_PROGRESS:
      "Lần đánh giá này vẫn đang chạy. Hãy đợi hoàn tất rồi tải lại kết quả.",
    PROJECT_COMPLEXITY_RESERVATION_INVALID:
      "Không thể khôi phục lần đánh giá trước. Hãy tạo một lượt đánh giá mới.",
    PROJECT_COMPLEXITY_RESERVATION_EXPIRED:
      "Lượt đánh giá đã hết thời gian giữ. Hãy thử lại để tạo lượt mới.",
    EXECUTION_RESULT_NOT_RECORDED: "Cần lưu kết quả kiểm thử trước khi yêu cầu AI phân tích.",
    EXECUTION_ASSISTANCE_UNAVAILABLE:
      "Chưa thể phân tích kết quả lúc này. Kết quả kiểm thử vẫn được giữ nguyên; bạn có thể thử lại.",
    EXECUTION_ASSISTANCE_RESPONSE_INVALID:
      "AI trả về đề xuất không đầy đủ. Không có thay đổi nào được áp dụng.",
    EXECUTION_ASSISTANCE_DEFECT_STATUS_INVALID:
      "Chỉ có thể đề xuất bản nháp lỗi cho kết quả Không đạt hoặc Bị chặn.",
    EXECUTION_ASSISTANCE_REFERENCE_INVALID:
      "AI dẫn đến nguồn ngoài kết quả kiểm thử này. Không có đề xuất nào được áp dụng.",
    EXECUTION_ASSISTANCE_STEP_INVALID:
      "AI đề cập đến bước không tồn tại trong phiên bản ca kiểm thử đang chạy.",
    EXECUTION_ASSISTANCE_GROUNDING_INVALID:
      "Có trích dẫn không khớp với nội dung đã lưu. Không có đề xuất nào được áp dụng.",
    EXECUTION_ASSISTANCE_GROUNDING_REQUIRED: "Đề xuất thiếu căn cứ từ kết quả kiểm thử đã lưu.",
    EXECUTION_ASSISTANCE_EVIDENCE_REQUIRED: "Chưa có nội dung kết quả kiểm thử để phân tích.",
    EXECUTION_ASSISTANCE_SCOPE_TOO_LARGE:
      "Nội dung kết quả vượt giới hạn phân tích. Hãy bổ sung kết quả ngắn gọn hơn.",
    EXECUTION_ASSISTANCE_SOURCE_CHANGED:
      "Kết quả kiểm thử đã thay đổi trong lúc phân tích. Hãy yêu cầu phân tích lại.",
  };
  if (automationMessages[reason?.code]) return automationMessages[reason.code];
  if (
    [
      "PROJECT_PERMISSION_DENIED",
      "PROJECT_MEMBERSHIP_REQUIRED",
      "PROJECT_MEMBERSHIP_INACTIVE",
      "PROJECT_ARCHIVED_READ_DENIED",
    ].includes(reason?.code)
  )
    return "";
  const message =
    reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "";
  if (message && message !== reason?.code && !/^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$/.test(message)) {
    return message;
  }
  return "Không thể hoàn tất thao tác. Tải lại dữ liệu rồi thử lại.";
}
