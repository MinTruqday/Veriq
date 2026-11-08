"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";

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
  testscenario: "Tình huống kiểm thử",
  testcase: "Ca kiểm thử",
  testsuite: "Bộ ca kiểm thử",
  testdata: "Dữ liệu kiểm thử",
  teststrategy: "Chiến lược kiểm thử",
  testadequacy: "Độ đầy đủ kiểm thử",
  testrun: "Lần chạy kiểm thử",
  testresult: "Kết quả kiểm thử",
  testmonitor: "Giám sát kiểm thử",
  teststatusreport: "Báo cáo trạng thái kiểm thử",
  testcompletion: "Hoàn tất kiểm thử",
  defect: "Lỗi",
  release: "Bản phát hành",
  build: "Bản dựng",
  environment: "Môi trường kiểm thử",
  environmentincident: "Sự cố môi trường",
  device_matrix: "Thiết bị kiểm thử",
  nfrtest: "Kiểm thử phi chức năng",
  coverage: "Độ bao phủ",
  trace: "Truy vết",
  risk: "Rủi ro",
  impact: "Ảnh hưởng thay đổi",
  changeset: "Đề xuất thay đổi",
  reviewsession: "Phiên rà soát",
  qualitygate: "Điều kiện chất lượng",
  qualityevaluation: "Đánh giá chất lượng",
  measurement: "Chỉ số chất lượng",
  statisticalquality: "Thống kê chất lượng",
  causalanalysis: "Phân tích nguyên nhân",
  preventionaction: "Hành động phòng ngừa",
  processimprovement: "Cải tiến quy trình",
  regression: "Kiểm thử hồi quy",
  workreport: "Báo cáo công việc",
  report: "Xuất báo cáo",
  proposal: "Đề xuất",
  ai: "AI Agent",
  apiartifact: "Đặc tả API",
  automation: "Script kiểm thử",
  cicd: "Tích hợp kiểm thử",
  webhook: "Kết nối sự kiện",
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
  generate_scenario: "Đề xuất tình huống kiểm thử",
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
  "connector.read": "Xem kết nối",
  "connector.manage": "Quản lý kết nối",
  "connector.review": "Rà soát kết nối",
  "connector.sync": "Đồng bộ kết nối",
  "bulk.update": "Chỉnh sửa nhiều mục",
  "bulk.approve": "Duyệt nhiều mục",
  "bulk.archive": "Lưu trữ nhiều mục",
  "bulk.generate": "Đề xuất nhiều mục",
  "script.update": "Chỉnh sửa script",
  "script.approve": "Duyệt script",
  "script.export": "Xuất script",
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
            <dl className="space-y-3 text-[13px]">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <dt className="text-ink-muted">Vai trò</dt>
                <dd className="font-medium">{data.roles.map(valueLabel).join(", ")}</dd>
              </div>
              {(data.responsibilities || []).map((item) => (
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1" key={item.name}>
                  <dt className="text-ink-muted">{responsibilityLabel(item.name)}</dt>
                  <dd className={item.assigned_to_you ? "font-medium" : ""}>
                    {item.assigned_to_you
                      ? "Được giao cho bạn"
                      : item.configured
                        ? "Đã giao cho người phụ trách khác"
                        : "Chưa phân công"}
                  </dd>
                </div>
              ))}
            </dl>
            <details className="border-t border-border pt-4">
              <summary className="cursor-pointer text-[13px] font-medium">
                Chức năng và quyền truy cập
              </summary>
              <p className="mt-3 text-[12px] leading-5 text-ink-muted">
                Thao tác trên từng mục còn phụ thuộc phân công, trạng thái và phiên bản đang xử lý.
              </p>
              <div className="mt-3 max-h-[28rem] space-y-1 overflow-y-auto overscroll-contain pr-2">
                {[...grouped]
                  .sort(([left], [right]) => left.localeCompare(right))
                  .map(([label, items]) => (
                    <details className="border-b border-border py-2" key={label}>
                      <summary className="cursor-pointer text-[13px]">
                        {label}
                        <span className="ml-2 text-[12px] text-ink-muted">
                          Được phép {items.filter((item) => item.allowed).length}/{items.length}
                        </span>
                      </summary>
                      <ul className="mt-2 divide-y divide-border text-[12px]">
                        {items.map((item) => (
                          <li
                            className="flex flex-wrap justify-between gap-x-5 gap-y-1 py-2 pl-4"
                            key={item.permission}
                          >
                            <span className="font-medium">{item.label}</span>
                            <span className={item.allowed ? "text-ink" : "text-ink-muted"}>
                              {item.allowed
                                ? "Được phép"
                                : reasons[item.reason_code] || "Chưa được phép"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ))}
              </div>
            </details>
          </>
        )}
      </div>
    </Panel>
  );
}
