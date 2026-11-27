"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import SearchField from "@/shared/components/ui/SearchField";

const groups = {
  project: "Dự án và thành viên",
  requirement: "Yêu cầu",
  requirement_document: "Tài liệu yêu cầu",
  requirement_dependency: "Phụ thuộc yêu cầu",
  acceptance_criteria: "Tiêu chí chấp nhận",
  business_rule: "Quy tắc nghiệp vụ",
  testplan: "Kế hoạch kiểm thử",
  testanalysis: "Phân tích kiểm thử",
  testcondition: "Điều kiện kiểm thử",
  testcase: "Ca kiểm thử",
  testsuite: "Bộ ca kiểm thử",
  testrun: "Lần chạy kiểm thử",
  testresult: "Kết quả kiểm thử",
  teststatusreport: "Báo cáo tiến độ",
  testcompletion: "Báo cáo hoàn tất",
  defect: "Lỗi",
  release: "Bản phát hành",
  build: "Bản dựng",
  environment: "Môi trường kiểm thử",
  coverage: "Độ bao phủ",
  trace: "Truy vết",
  risk: "Rủi ro",
  impact: "Ảnh hưởng thay đổi",
  changeset: "Đề xuất thay đổi",
  regression: "Kiểm thử hồi quy",
  report: "Xuất báo cáo",
  proposal: "Đề xuất",
  ai: "AI",
  apiartifact: "Đặc tả API",
  automation: "Script kiểm thử",
  knowledge: "Tài liệu tham chiếu",
  attachment: "Tệp đính kèm",
  comment: "Nhận xét",
  collaboration: "Cộng tác",
  notification: "Thông báo",
  analytics: "Phân tích số liệu",
};

const actions = {
  read: "Xem",
  create: "Tạo mới",
  update: "Chỉnh sửa",
  write: "Soạn nội dung",
  manage: "Quản lý",
  approve: "Phê duyệt",
  review: "Rà soát",
  submit_review: "Gửi rà soát",
  request_changes: "Yêu cầu chỉnh sửa",
  reject: "Từ chối",
  assign: "Phân công",
  execute: "Thực hiện",
  start: "Bắt đầu",
  complete: "Hoàn tất",
  abort: "Hủy",
  close: "Đóng",
  confirm: "Xác nhận",
  decide: "Ghi quyết định",
  accept_risk: "Chấp nhận rủi ro",
  override: "Điều chỉnh có giải trình",
  publish: "Phát hành",
  export: "Xuất tệp",
  download: "Tải tệp",
  upload: "Tải lên",
  import: "Nhập dữ liệu",
  extract: "Trích xuất",
  review_extraction: "Rà soát nội dung trích xuất",
  confirm_extraction: "Xác nhận nội dung trích xuất",
  archive: "Lưu trữ",
  restore: "Khôi phục",
  clone: "Sao chép",
  merge: "Gộp",
  split: "Tách",
  correct: "Hiệu chỉnh",
  retest: "Kiểm tra lại",
  triage: "Phân loại và xử lý",
  revoke: "Thu hồi",
  retry: "Thử lại",
  recover: "Phục hồi",
  lint: "Kiểm tra nội dung",
  evaluate: "Đánh giá",
  measure: "Đo lường",
  annotate: "Ghi chú",
  moderate: "Quản lý nội dung chia sẻ",
  generate: "Đề xuất nội dung",
  ai: "Dùng AI hỗ trợ",
  run_ai: "Chạy AI hỗ trợ",
  ask_project: "Hỏi về dự án",
  duplicate_check: "Kiểm tra trùng lặp",
  run_duplicate_check: "Kiểm tra trùng lặp",
  run_lint: "Kiểm tra chất lượng nội dung",
  run_impact: "Phân tích ảnh hưởng",
  generate_testcase: "Đề xuất ca kiểm thử",
  generate_api_testcase: "Đề xuất ca kiểm thử API",
  generate_automation_script: "Đề xuất script kiểm thử",
  generate_performance_plan: "Đề xuất kiểm thử hiệu năng",
  generate_security_tests: "Đề xuất kiểm thử bảo mật",
  generate_regression: "Đề xuất kiểm thử hồi quy",
  create_proposal: "Tạo đề xuất",
  suggest_bug_trace: "Gợi ý liên kết lỗi",
  "members.read": "Xem thành viên",
  "members.manage": "Quản lý thành viên",
  "settings.manage": "Cấu hình dự án",
  "audit.read": "Xem lịch sử kiểm toán",
  "version.read": "Xem phiên bản",
  "version.create": "Tạo phiên bản",
  "template.read": "Xem mẫu",
  "template.manage": "Quản lý mẫu",
  "template.archive": "Lưu trữ mẫu",
  "bulk.update": "Chỉnh sửa nhiều mục",
  "bulk.approve": "Duyệt nhiều mục",
  "bulk.archive": "Lưu trữ nhiều mục",
  "bulk.generate": "Đề xuất nhiều mục",
  "transition.resolve": "Cập nhật tiến độ xử lý lỗi",
  "trace.manage": "Quản lý liên kết truy vết",
  "handover.manage": "Quản lý bàn giao",
  "risk.manage": "Quản lý rủi ro tồn đọng",
  "secret_ref.manage": "Quản lý tham chiếu thông tin bảo mật",
  "exit_criteria.override": "Ghi nhận sai lệch điều kiện kết thúc",
  "preferences.manage": "Cài đặt thông báo",
  "watch.manage": "Theo dõi thông báo",
  "project_rule.manage": "Cài đặt thông báo dự án",
  mark_read: "Đánh dấu đã đọc",
  update_own: "Sửa nội dung của mình",
  delete_own: "Xóa nội dung của mình",
  delete_own_unreferenced: "Xóa tệp của mình chưa được sử dụng",
  "conflict.resolve": "Giải quyết xung đột",
};

const reasons = {
  ROLE_NOT_ALLOWED: "Không thuộc trách nhiệm của vai trò này",
  RESPONSIBILITY_NOT_ASSIGNED: "Bạn chưa được chỉ định thực hiện trách nhiệm này",
  PERMISSION_NOT_GRANTED: "Dự án chưa cấp quyền này cho bạn",
  PROJECT_ARCHIVED: "Dự án đã lưu trữ",
  PROJECT_ARCHIVED_READ_DENIED: "Dự án đã lưu trữ và hạn chế quyền xem",
};

function responsibilityLabel(value) {
  return `Trách nhiệm · ${String(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase())}`;
}

export default function ProjectAccessPanel({ project }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [permissionQuery, setPermissionQuery] = useState("");
  const [permissionFilter, setPermissionFilter] = useState("ALL");
  const requestSequence = useRef(0);
  const projectId = project?._id;
  const load = useCallback(async () => {
    if (!projectId) return;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const value = await testingApi.listEffectiveAccess(projectId);
      if (sequence === requestSequence.current) setData(value);
    } catch (reason) {
      if (sequence === requestSequence.current) {
        setData(null);
        setError(messageOf(reason));
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    setData(null);
    load();
    return () => {
      requestSequence.current += 1;
    };
  }, [load, project?.revision]);

  const grouped = new Map();
  for (const capability of data?.capabilities || []) {
    const [domain, ...parts] = capability.permission.split(".");
    const label = groups[domain] || "Chức năng khác";
    const items = grouped.get(label) || [];
    items.push({ ...capability, label: actions[parts.join(".")] || "Thao tác bổ sung" });
    grouped.set(label, items);
  }
  const normalizedPermissionQuery = permissionQuery.trim().toLocaleLowerCase("vi");
  const visibleGroups = [...grouped]
    .sort(([left], [right]) => left.localeCompare(right, "vi"))
    .map(([label, items]) => [
      label,
      items.filter((item) => {
        const matchesAccess =
          permissionFilter === "ALL" ||
          (permissionFilter === "ALLOWED" ? item.allowed : !item.allowed);
        const searchable = [label, item.label, item.permission, reasons[item.reason_code]]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase("vi");
        return (
          matchesAccess &&
          (!normalizedPermissionQuery || searchable.includes(normalizedPermissionQuery))
        );
      }),
    ])
    .filter(([, items]) => items.length > 0);
  const allCapabilities = data?.capabilities || [];
  const allowedCount = allCapabilities.filter((item) => item.allowed).length;
  const visibleCapabilityCount = visibleGroups.reduce(
    (count, [, items]) => count + items.length,
    0,
  );

  return (
    <Panel
      title="Quyền của tôi trong dự án"
      actions={
        <button
          type="button"
          className="icon-button h-9 w-9"
          aria-label="Cập nhật quyền truy cập"
          title="Cập nhật quyền truy cập"
          disabled={loading}
          onClick={load}
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
        </button>
      }
    >
      <div className="space-y-4 p-5">
        {loading && <LoadingState label="Đang kiểm tra quyền truy cập" />}
        {error && <ErrorState message={error} />}
        {!loading && data && (
          <>
            <section aria-label="Tóm tắt quyền truy cập" className="grid gap-3 sm:grid-cols-2">
              <article className="rounded-panel border border-border bg-surface p-4">
                <p className="text-xs font-medium text-ink-muted">Vai trò trong dự án</p>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {(data.roles || []).length ? (
                    data.roles.map((role) => (
                      <li
                        className="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand"
                        key={role}
                      >
                        {valueLabel(role)}
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-ink-muted">Chưa có vai trò được trả về.</li>
                  )}
                </ul>
              </article>
              <article className="rounded-panel border border-border bg-surface p-4">
                <p className="text-xs font-medium text-ink-muted">Quyền được phép</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-ink">
                  {allowedCount}
                  <span className="text-base font-normal text-ink-muted">
                    {" "}
                    / {allCapabilities.length}
                  </span>
                </p>
                <p className="mt-1 text-xs text-ink-muted">Thao tác trên tài nguyên của dự án</p>
              </article>
            </section>

            {(data.responsibilities || []).length > 0 && (
              <section aria-labelledby="project-responsibilities-heading" className="space-y-3">
                <div>
                  <h3 id="project-responsibilities-heading" className="text-sm font-semibold">
                    Trách nhiệm được phân công
                  </h3>
                  <p className="mt-1 text-xs text-ink-muted">
                    Một số thao tác còn phụ thuộc người phụ trách được giao.
                  </p>
                </div>
                <ul className="grid gap-2 sm:grid-cols-2">
                  {data.responsibilities.map((item) => {
                    const assignedToYou = Boolean(item.assigned_to_you);
                    const assignmentLabel = assignedToYou
                      ? "Được giao cho bạn"
                      : item.configured
                        ? "Đã giao người khác"
                        : "Chưa phân công";
                    return (
                      <li
                        className="flex min-w-0 items-start justify-between gap-3 rounded-control border border-border p-3"
                        key={item.name}
                      >
                        <span className="min-w-0 break-words text-[13px] font-medium text-ink">
                          {responsibilityLabel(item.name)}
                        </span>
                        <span
                          className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium ${assignedToYou ? "bg-brand-soft text-brand" : "bg-surface-quiet text-ink-muted"}`}
                        >
                          {assignmentLabel}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}

            <section
              aria-labelledby="project-capabilities-heading"
              className="space-y-3 border-t border-border pt-4"
            >
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h3 id="project-capabilities-heading" className="text-sm font-semibold">
                    Chức năng và quyền truy cập
                  </h3>
                  <p className="mt-1 text-xs leading-5 text-ink-muted">
                    Thao tác trên từng mục còn phụ thuộc phân công, trạng thái và phiên bản đang xử
                    lý.
                  </p>
                </div>
                <span className="text-xs text-ink-muted" aria-live="polite">
                  {visibleCapabilityCount} / {allCapabilities.length} quyền
                </span>
              </div>
              <SearchField
                ariaLabel="Tìm chức năng hoặc quyền"
                onChange={(event) => setPermissionQuery(event.target.value)}
                placeholder="Tìm chức năng, quyền hoặc lý do bị giới hạn"
                value={permissionQuery}
              />
              <div aria-label="Lọc quyền truy cập" className="flex flex-wrap gap-2" role="group">
                {[
                  ["ALL", `Tất cả (${allCapabilities.length})`],
                  ["ALLOWED", `Được phép (${allowedCount})`],
                  ["DENIED", `Chưa được phép (${allCapabilities.length - allowedCount})`],
                ].map(([filter, label]) => (
                  <button
                    aria-pressed={permissionFilter === filter}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium ${permissionFilter === filter ? "border-brand bg-brand/5 text-ink" : "border-border text-ink-muted hover:bg-surface-quiet"}`}
                    key={filter}
                    onClick={() => setPermissionFilter(filter)}
                    type="button"
                  >
                    {label}
                  </button>
                ))}
              </div>
              {visibleGroups.length ? (
                <div className="max-h-[34rem] space-y-2 overflow-y-auto overscroll-contain pr-1">
                  {visibleGroups.map(([label, items]) => {
                    const groupAllowedCount = items.filter((item) => item.allowed).length;
                    return (
                      <details className="rounded-control border border-border" key={label}>
                        <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 px-4 py-3 text-[13px] font-medium hover:bg-surface-quiet">
                          <span>{label}</span>
                          <span className="text-xs text-ink-muted">
                            {groupAllowedCount} / {items.length} được phép
                          </span>
                        </summary>
                        <ul className="divide-y divide-border border-t border-border px-4 text-[12px]">
                          {items.map((item) => (
                            <li
                              className="grid gap-1 py-2 sm:grid-cols-[minmax(8rem,0.8fr)_minmax(0,1.2fr)] sm:gap-4"
                              key={item.permission}
                            >
                              <span className="font-medium text-ink">{item.label}</span>
                              <span className={item.allowed ? "text-brand" : "text-ink-muted"}>
                                {item.allowed
                                  ? "Được phép"
                                  : reasons[item.reason_code] || "Chưa được phép"}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    );
                  })}
                </div>
              ) : (
                <p
                  className="rounded-control bg-surface-quiet p-4 text-sm text-ink-muted"
                  role="status"
                >
                  Không có quyền nào khớp với bộ lọc.
                </p>
              )}
            </section>
          </>
        )}
      </div>
    </Panel>
  );
}
