"use client";

import { Fragment, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import PlatformUsersPanel from "../components/PlatformUsersPanel";
import { ErrorState, Panel, WorkspacePage } from "../components/WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import SearchField from "@/shared/components/ui/SearchField";

const ROLE_ORDER = ["BA", "TESTER", "SYSTEM_ADMIN"];
const ROLE_LABELS = {
  BA: "Chuyên viên nghiệp vụ",
  TESTER: "Kiểm thử viên",
  SYSTEM_ADMIN: "Quản trị hệ thống",
};

const PERMISSION_RESOURCES = {
  acceptance_criteria: "Tiêu chí chấp nhận",
  "ai.result_metadata": "Thông tin kết quả AI",
  ai: "AI",
  analytics: "Báo cáo phân tích",
  apiartifact: "Tài liệu API",
  "automation.script": "Kịch bản tự động hóa",
  automation: "Tự động hóa",
  attachment: "Tệp đính kèm",
  build: "Bản dựng",
  business_rule: "Quy tắc nghiệp vụ",
  causalanalysis: "Phân tích nguyên nhân",
  changeset: "Tập thay đổi",
  cicd: "Tích hợp và triển khai",
  collaboration: "Cộng tác",
  comment: "Bình luận",
  coverage: "Độ bao phủ kiểm thử",
  defect: "Lỗi",
  device_matrix: "Ma trận thiết bị",
  environmentincident: "Sự cố môi trường",
  environment: "Môi trường kiểm thử",
  impact: "Phân tích tác động",
  knowledge: "Kho kiến thức",
  measurement: "Chỉ số đo lường",
  nfrtest: "Kiểm thử phi chức năng",
  notification: "Thông báo",
  preventionaction: "Biện pháp phòng ngừa",
  processimprovement: "Cải tiến quy trình",
  "project.connector": "Kết nối dự án",
  "project.members": "Thành viên dự án",
  "project.settings": "Cài đặt dự án",
  project: "Dự án",
  proposal: "Đề xuất",
  qualityevaluation: "Đánh giá chất lượng",
  regression: "Kiểm thử hồi quy",
  release: "Bản phát hành",
  report: "Báo cáo",
  requirement_dependency: "Liên kết yêu cầu",
  requirement_document: "Tài liệu yêu cầu",
  requirement: "Yêu cầu",
  reviewsession: "Phiên rà soát",
  risk: "Rủi ro",
  statisticalquality: "Thống kê chất lượng",
  testadequacy: "Mức độ đầy đủ của kiểm thử",
  testmonitor: "Giám sát kiểm thử",
  "testanalysis.finding": "Phát hiện phân tích kiểm thử",
  testanalysis: "Phân tích kiểm thử",
  "testcase.template": "Mẫu ca kiểm thử",
  testcase: "Ca kiểm thử",
  testcompletion: "Báo cáo hoàn tất",
  testcondition: "Điều kiện kiểm thử",
  testdata: "Dữ liệu kiểm thử",
  testplan: "Kế hoạch kiểm thử",
  testresult: "Kết quả kiểm thử",
  testrun: "Lượt chạy kiểm thử",
  testscenario: "Kịch bản kiểm thử",
  teststatusreport: "Báo cáo tiến độ",
  teststrategy: "Chiến lược kiểm thử",
  testsuite: "Bộ kiểm thử",
  trace: "Truy vết",
  "webhook.project": "Webhook dự án",
  workreport: "Báo cáo công việc",
};

const PERMISSION_ACTIONS = {
  accept_risk: "Chấp nhận rủi ro",
  annotate: "Ghi chú kết quả",
  approve: "Phê duyệt",
  "audit.read": "Xem nhật ký dự án",
  "ai.read": "Xem kết quả AI",
  "bulk.approve": "Phê duyệt hàng loạt",
  "bulk.archive": "Lưu trữ hàng loạt",
  "bulk.generate": "Tạo hàng loạt",
  "bulk.update": "Cập nhật hàng loạt",
  close: "Đóng",
  clone: "Sao chép",
  complete: "Hoàn tất",
  confirm: "Xác nhận",
  confirm_extraction: "Xác nhận nội dung trích xuất",
  create: "Tạo",
  create_proposal: "Tạo đề xuất bằng AI",
  "version.create": "Tạo phiên bản",
  "lesson.create": "Ghi nhận bài học",
  "control.create": "Tạo mục điều phối",
  "finding.create": "Ghi nhận phát hiện",
  "snapshot.create": "Tạo bản chụp dữ liệu",
  delete_own: "Xóa bình luận của mình",
  delete_own_unreferenced: "Xóa tệp chưa được liên kết do mình tải lên",
  decide: "Ra quyết định",
  "diff.read": "Xem nội dung thay đổi",
  duplicate_check: "Kiểm tra trùng lặp",
  execute: "Thực hiện",
  export: "Xuất dữ liệu",
  "script.export": "Xuất kịch bản",
  "finding.assign": "Phân công xử lý phát hiện",
  "control.assign": "Phân công điều phối",
  generate: "Tạo",
  generate_api_testcase: "Tạo ca kiểm thử API bằng AI",
  generate_automation_script: "Tạo kịch bản tự động hóa bằng AI",
  generate_performance_plan: "Tạo kế hoạch kiểm thử hiệu năng bằng AI",
  generate_regression: "Tạo kiểm thử hồi quy bằng AI",
  generate_scenario: "Tạo kịch bản kiểm thử bằng AI",
  generate_security_tests: "Tạo kiểm thử bảo mật bằng AI",
  generate_testcase: "Tạo ca kiểm thử bằng AI",
  import: "Nhập dữ liệu",
  "evidence.import": "Nhập minh chứng",
  ingest: "Nhận kết quả từ công cụ",
  "result.ingest": "Nhận kết quả kiểm thử",
  manage: "Quản lý",
  "finding.manage": "Quản lý phát hiện",
  "handover.manage": "Quản lý bàn giao",
  "priority.manage": "Quản lý mức ưu tiên",
  "risk.manage": "Quản lý rủi ro",
  "secret_ref.manage": "Quản lý tham chiếu bí mật",
  "severity.manage": "Quản lý mức độ nghiêm trọng",
  "project_rule.manage": "Quản lý quy tắc thông báo dự án",
  "preferences.manage": "Quản lý tùy chọn thông báo",
  "watch.manage": "Quản lý theo dõi thông báo",
  "script.approve": "Phê duyệt kịch bản",
  "script.update": "Cập nhật kịch bản",
  "control.update": "Cập nhật điều phối",
  "finding.verify": "Xác minh phát hiện",
  moderate: "Kiểm duyệt",
  merge: "Gộp",
  ask_project: "Trao đổi với AI về dự án",
  "result_metadata.read": "Xem thông tin kết quả AI",
  run_duplicate_check: "Kiểm tra trùng lặp bằng AI",
  run_impact: "Phân tích tác động bằng AI",
  run_lint: "Rà soát nội dung bằng AI",
  suggest_bug_trace: "Đề xuất liên kết lỗi bằng AI",
  override: "Ghi đè quyết định",
  publish: "Phát hành",
  read: "Xem",
  "presence.read": "Xem trạng thái cộng tác",
  recover: "Khôi phục liên kết",
  reject: "Từ chối",
  replay: "Chạy lại sự kiện",
  resolve: "Xử lý",
  "conflict.resolve": "Giải quyết xung đột nội dung",
  resolve_finding: "Xử lý phát hiện",
  restore: "Khôi phục",
  retest: "Kiểm thử lại",
  review: "Rà soát",
  "version.read": "Xem phiên bản",
  "exit_criteria.override": "Cho phép vượt tiêu chí kết thúc",
  run_ai: "Chạy phân tích bằng AI",
  "waiver.approve": "Phê duyệt ngoại lệ",
  review_extraction: "Rà soát nội dung trích xuất",
  "result.correct": "Điều chỉnh kết quả kiểm thử",
  "transition.resolve": "Chuyển lỗi sang trạng thái đã xử lý",
  submit_review: "Gửi rà soát",
  split: "Tách",
  start: "Bắt đầu",
  triage: "Phân loại lỗi",
  update: "Cập nhật",
  upload: "Tải lên",
  bind: "Liên kết dữ liệu",
  archive: "Lưu trữ",
  correct: "Điều chỉnh kết quả",
  preview: "Xem trước",
  retry: "Thử lại",
  sync: "Đồng bộ",
  trigger: "Khởi chạy",
  abort: "Hủy",
  evaluate: "Đánh giá",
  measure: "Đo lường",
  revoke: "Thu hồi",
  write: "Ghi nội dung",
  ai: "Tạo nội dung bằng AI",
  assign: "Phân công",
  verify: "Xác minh",
  "private.read": "Xem lỗi riêng tư",
  "trace.manage": "Quản lý liên kết truy vết",
  "report.create": "Tạo báo cáo",
  update_own: "Cập nhật bình luận của mình",
};

const PERMISSION_RESOURCE_KEYS = Object.keys(PERMISSION_RESOURCES).sort(
  (left, right) => right.length - left.length,
);
const PERMISSION_LABEL_OVERRIDES = {
  "comment.create": "Viết bình luận",
  "project.create": "Tạo dự án",
  "project.delete": "Xóa dự án",
  "project.read": "Xem dự án",
  "project.update": "Cập nhật dự án",
  "project.members.manage": "Thêm, cập nhật hoặc gỡ thành viên dự án",
  "project.members.read": "Xem thành viên dự án",
  "project.settings.manage": "Cập nhật cài đặt dự án",
  "requirement_document.upload": "Tải tài liệu yêu cầu lên",
  "requirement_document.download": "Tải tài liệu yêu cầu xuống",
  "requirement_document.delete": "Xóa tài liệu yêu cầu",
  "requirement_document.read": "Xem tài liệu yêu cầu",
  "report.export": "Tải báo cáo xuống",
  "project.audit.read": "Xem nhật ký dự án",
  "testresult.correct": "Điều chỉnh kết quả kiểm thử",
  "ai.read": "Xem kết quả AI",
  "ai.result_metadata.read": "Xem thông tin kết quả AI",
  "analytics.ai.read": "Xem kết quả AI của báo cáo phân tích",
  "apiartifact.archive": "Lưu trữ tài liệu API",
  "apiartifact.confirm": "Xác nhận tài liệu API",
  "apiartifact.diff.read": "Xem nội dung thay đổi tài liệu API",
  "apiartifact.import": "Nhập dữ liệu tài liệu API",
  "apiartifact.read": "Xem tài liệu API",
  "apiartifact.review": "Rà soát tài liệu API",
  "testanalysis.run_ai": "Chạy phân tích kiểm thử bằng AI",
  "testanalysis.verify_finding": "Xác minh phát hiện phân tích kiểm thử",
  "testcase.lint": "Rà soát chất lượng ca kiểm thử",
  "testmonitor.control.assign": "Phân công điều phối giám sát kiểm thử",
  "testmonitor.control.create": "Tạo mục điều phối giám sát kiểm thử",
  "testmonitor.control.update": "Cập nhật điều phối giám sát kiểm thử",
  "testmonitor.exit_criteria.override": "Cho phép vượt tiêu chí kết thúc giám sát kiểm thử",
  "testmonitor.read": "Xem giám sát kiểm thử",
  "testmonitor.report.create": "Tạo báo cáo giám sát kiểm thử",
  "testmonitor.snapshot.create": "Tạo bản chụp dữ liệu giám sát kiểm thử",
  "workreport.ai": "Tạo nội dung báo cáo bằng AI",
};

const permissionResource = (permission) =>
  PERMISSION_RESOURCE_KEYS.find((resource) => permission.startsWith(`${resource}`)) ||
  permission.split("")[0];

const permissionLabel = (permission) => {
  if (PERMISSION_LABEL_OVERRIDES[permission]) return PERMISSION_LABEL_OVERRIDES[permission];
  const resource = permissionResource(permission);
  const action = permission.slice(resource.length + 1);
  const resourceLabel = (PERMISSION_RESOURCES[resource] || "nội dung khác").toLocaleLowerCase(
    "vi-VN",
  );
  if (action === "upload") return `Tải ${resourceLabel} lên`;
  if (action === "download") return `Tải ${resourceLabel} xuống`;
  const actionLabel = PERMISSION_ACTIONS[action] || "Thao tác với";
  if (actionLabel.toLocaleLowerCase("vi-VN").includes(resourceLabel)) return actionLabel;
  return `${actionLabel} ${resourceLabel}`;
};

export default function OperationsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [roles, setRoles] = useState(null);
  const [error, setError] = useState("");
  const [permissions, setPermissions] = useState([]);
  const [permissionQuery, setPermissionQuery] = useState("");
  const [revision, setRevision] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const isAdmin = user?.system_role === "ADMIN";
  const normalizedPermissionQuery = permissionQuery.trim().toLocaleLowerCase();
  const permissionRows = permissions
    .map((permission) => ({
      permission,
      resource: permissionResource(permission),
      label: permissionLabel(permission),
    }))
    .sort(
      (left, right) =>
        left.resource.localeCompare(right.resource) || left.label.localeCompare(right.label),
    )
    .filter((row) =>
      [row.resource, row.label, row.permission].some((value) =>
        value.toLocaleLowerCase().includes(normalizedPermissionQuery),
      ),
    );

  useEffect(() => {
    if (isLoading) return;
    if (!user) router.replace("/dang-nhap");
    else if (!isAdmin) router.replace("/du-an");
  }, [isLoading, isAdmin, router, user]);

  useEffect(() => {
    if (!isAdmin) return undefined;
    let active = true;
    testingApi.getProjectRolePermissions().then(
      (data) => {
        if (active) {
          const current = data.role_permissions || {};
          setRoles(Object.fromEntries(ROLE_ORDER.map((role) => [role, current[role] || []])));
          setPermissions(data.permissions || []);
          setRevision(data.revision);
        }
      },
      (reason) => {
        if (active) setError(messageOf(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [isAdmin]);

  if (isLoading || !isAdmin) return null;
  return (
    <WorkspacePage title="Quản lý tài khoản">
      <PlatformUsersPanel />
      <Panel title="Quyền theo vai trò dự án">
        <div className="space-y-3 p-5">
          {error && <ErrorState message={error} />}
          {!roles && !error && <p>Đang tải quyền vai trò…</p>}
          {roles && (
            <>
              <p className="max-w-[1050px] text-sm text-ink-muted">
                Tên quyền được diễn đạt bằng tiếng Việt. Đánh dấu nghĩa là vai trò được cấp quyền;
                quản trị hệ thống luôn có toàn quyền
              </p>
              <div className="grid max-w-[1050px] gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <SearchField
                  ariaLabel="Tìm quyền theo tên hoặc nhóm"
                  onChange={(event) => setPermissionQuery(event.target.value)}
                  placeholder="Tìm quyền, nhóm hoặc mã permission"
                  value={permissionQuery}
                />
                <p aria-live="polite" className="text-xs text-ink-muted">
                  {permissionRows.length} / {permissions.length} quyền
                </p>
              </div>
              {permissionRows.length ? (
                <div className="max-h-[68dvh] max-w-[1050px] overflow-auto overscroll-contain rounded-control border border-border">
                  <table className="w-full min-w-[720px] table-fixed text-left text-sm">
                    <colgroup>
                      <col className="w-[58%]" />
                      <col className="w-[14%]" />
                      <col className="w-[14%]" />
                      <col className="w-[14%]" />
                    </colgroup>
                    <thead className="sticky top-0 z-20 bg-surface">
                      <tr>
                        <th className="sticky left-0 z-30 bg-surface p-2">Quyền</th>
                        {ROLE_ORDER.map((role) => (
                          <th key={role} className="p-2 text-center">
                            {ROLE_LABELS[role]}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {permissionRows.map((row, index) => (
                        <Fragment key={row.permission}>
                          {(index === 0 || row.resource !== permissionRows[index - 1].resource) && (
                            <tr className="border-t border-border bg-surface-quiet">
                              <th
                                className="px-3 py-2 text-left text-xs font-semibold text-ink-muted"
                                colSpan={4}
                              >
                                {PERMISSION_RESOURCES[row.resource] || "Quyền khác"}
                              </th>
                            </tr>
                          )}
                          <tr className="border-t border-border">
                            <th
                              className="sticky left-0 z-10 bg-surface p-2 font-normal"
                              title={row.permission}
                            >
                              {row.label}
                            </th>
                            {ROLE_ORDER.map((role) => (
                              <td key={role} className="p-2 text-center">
                                <input
                                  type="checkbox"
                                  aria-label={`${ROLE_LABELS[role]}: ${row.label}`}
                                  title={row.permission}
                                  checked={roles[role].includes(row.permission)}
                                  disabled={role === "SYSTEM_ADMIN"}
                                  onChange={(event) => {
                                    const checked = event.target.checked;
                                    setSaved(false);
                                    setRoles((current) => ({
                                      ...current,
                                      [role]: checked
                                        ? [...current[role], row.permission]
                                        : current[role].filter((item) => item !== row.permission),
                                    }));
                                  }}
                                />
                              </td>
                            ))}
                          </tr>
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="max-w-[1050px] rounded-control border border-border p-4 text-sm text-ink-muted">
                  Không có quyền nào khớp với nội dung tìm kiếm
                </p>
              )}
              <button
                className="apple-button"
                type="button"
                disabled={saving}
                onClick={async () => {
                  setSaving(true);
                  setError("");
                  try {
                    const data = await testingApi.updateProjectRolePermissions({
                      revision,
                      role_permissions: roles,
                    });
                    setRoles(
                      Object.fromEntries(
                        ROLE_ORDER.map((role) => [role, data.role_permissions[role] || []]),
                      ),
                    );
                    setRevision(data.revision);
                    setSaved(true);
                  } catch (reason) {
                    setError(messageOf(reason));
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                {saving ? "Đang lưu…" : "Lưu phân quyền"}
              </button>
              {saved && <p role="status">Đã lưu phân quyền</p>}
            </>
          )}
        </div>
      </Panel>
    </WorkspacePage>
  );
}
