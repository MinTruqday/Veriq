"use client";
import { useEffect, useState } from "react";
import DataTable from "../../components/DataTable";
import ProjectNotificationsPanel from "../../components/ProjectNotificationsPanel";
import WebhookPanel from "../../components/WebhookPanel";
import ProjectConnectorsPanel from "../../components/ProjectConnectorsPanel";
import CicdPanel from "../../components/CicdPanel";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";

const toggleSettings = [
  ["requirement_lint_blocking", "Chặn duyệt yêu cầu khi còn lỗi kiểm tra"],
  ["trace_before_baseline", "Bắt buộc truy vết trước khi đặt phiên bản chuẩn cho yêu cầu"],
  ["ba_can_approve_requirements", "Cho phép chuyên viên phân tích duyệt yêu cầu"],
  ["testcase_lint_blocking", "Chặn duyệt ca kiểm thử khi còn lỗi kiểm tra"],
  ["trace_before_testcase_approve", "Bắt buộc truy vết trước khi duyệt ca kiểm thử"],
  ["tester_can_create_run", "Cho phép kiểm thử viên tạo lần chạy kiểm thử"],
  ["tester_can_manage_runs", "Cho phép kiểm thử viên quản lý lần chạy kiểm thử"],
  ["tester_can_assign_runs", "Cho phép kiểm thử viên phân công lần chạy và ca kiểm thử"],
  ["tester_can_start_runs", "Cho phép kiểm thử viên bắt đầu lần chạy kiểm thử"],
  ["tester_can_complete_runs", "Cho phép kiểm thử viên hoàn tất lần chạy kiểm thử"],
  ["tester_can_abort_runs", "Cho phép kiểm thử viên hủy lần chạy kiểm thử"],
  ["tester_can_correct_results", "Cho phép kiểm thử viên hiệu chỉnh kết quả"],
  ["tester_can_assign_testplans", "Cho phép kiểm thử viên phân công kế hoạch kiểm thử"],
  ["strict_test_plan_approval", "Chỉ phê duyệt kế hoạch kiểm thử khi đã đủ thông tin quản trị"],
  ["require_release_for_test_plan", "Yêu cầu chọn bản phát hành trước khi phê duyệt kế hoạch"],
  ["require_environment_for_test_plan", "Yêu cầu chọn môi trường trước khi phê duyệt kế hoạch"],
  ["partial_complete_allowed", "Cho phép hoàn tất một phần lần chạy kiểm thử"],
  ["allow_not_applicable_results", "Cho phép kết quả Không áp dụng khi có lý do"],
  ["tester_can_close_defect", "Cho phép kiểm thử viên đóng lỗi"],
  ["tester_can_reject_defect", "Cho phép kiểm thử viên từ chối lỗi"],
  ["tester_can_mark_duplicate_defect", "Cho phép kiểm thử viên đánh dấu lỗi trùng"],
  ["ba_can_create_defect", "Cho phép chuyên viên phân tích tạo lỗi"],
  ["developer_can_create_defect", "Cho phép lập trình viên tạo lỗi"],
  ["ba_can_update_defect", "Cho phép chuyên viên phân tích cập nhật lỗi"],
  ["tester_can_confirm_trace", "Cho phép kiểm thử viên xác nhận liên kết truy vết"],
  ["tester_can_revoke_trace", "Cho phép kiểm thử viên thu hồi liên kết truy vết"],
  ["ba_can_confirm_trace", "Cho phép chuyên viên phân tích xác nhận liên kết truy vết"],
  ["ba_can_revoke_trace", "Cho phép chuyên viên phân tích thu hồi liên kết truy vết"],
  ["tester_can_override_impact", "Cho phép kiểm thử viên điều chỉnh phân tích ảnh hưởng"],
  ["tester_can_close_impact", "Cho phép kiểm thử viên đóng phân tích ảnh hưởng"],
  ["tester_can_manage_knowledge", "Cho phép kiểm thử viên quản lý tài liệu tham chiếu"],
  ["tester_can_archive_testcase_templates", "Cho phép kiểm thử viên lưu trữ mẫu ca kiểm thử"],
  ["viewer_can_export", "Cho phép người xem xuất báo cáo"],
  ["developer_can_export", "Cho phép lập trình viên xuất báo cáo"],
  ["ai_auto_draft", "Cho phép AI tạo bản nháp"],
  [
    "require_completion_report_before_release_close",
    "Yêu cầu báo cáo hoàn tất đã phê duyệt trước khi đóng bản phát hành",
  ],
];

const numberSettings = [
  ["impact_confidence_threshold", "Ngưỡng tin cậy phân tích ảnh hưởng", 0, 1, 0.01],
  ["testcase_duplicate_threshold", "Ngưỡng phát hiện ca kiểm thử trùng", 0, 1, 0.01],
  ["impact_candidate_limit", "Số ứng viên ảnh hưởng tối đa", 1, 5000, 1],
  [
    "completion_open_blocker_threshold",
    "Số lỗi chặn toàn bộ đang mở tối đa khi phê duyệt hoàn tất",
    0,
    1000,
    1,
  ],
  ["rca_reopen_threshold", "Số lần mở lại lỗi để đề xuất RCA", 1, 100, 1],
  ["rca_duplicate_threshold", "Số lỗi cùng cụm để đề xuất RCA", 2, 100, 1],
];

const selectSettings = [
  ["default_invite_role", "Vai trò mời mặc định", ["TESTER", "BA", "DEVELOPER", "VIEWER"]],
  ["read_after_archive_policy", "Quyền đọc sau khi lưu trữ", ["ALLOW_READ", "DENY_READ"]],
  ["default_environment", "Môi trường mặc định", ["development", "staging", "production"]],
];

const projectTypeLabels = {
  web: "Ứng dụng web",
  mobile: "Ứng dụng di động",
  api: "API",
  desktop: "Ứng dụng máy tính",
  embedded: "Hệ thống nhúng",
  other: "Loại khác",
};

const settingValueLabels = {
  TESTER: "Kiểm thử viên",
  BA: "Chuyên viên phân tích nghiệp vụ",
  DEVELOPER: "Lập trình viên",
  VIEWER: "Người xem",
  ALLOW_READ: "Cho phép đọc",
  DENY_READ: "Không cho phép đọc",
  development: "Phát triển",
  staging: "Tiền sản xuất",
  production: "Sản xuất",
};

export default function SettingsPage({ project, onProjectChange, workspaceView }) {
  const { ask, dialog } = useActionDialog();
  const [audit, setAudit] = useState([]);
  const [members, setMembers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || "");
  const [projectType, setProjectType] = useState(project.project_type || "web");
  const [locale, setLocale] = useState(project.locale || "vi-VN");
  const [timezone, setTimezone] = useState(project.timezone || "Asia/Ho_Chi_Minh");
  const [settings, setSettings] = useState({
    requirement_approval_required: project.settings?.requirement_approval_required ?? true,
    testcase_approval_required: project.settings?.testcase_approval_required ?? true,
    ai_auto_draft: project.settings?.ai_auto_draft ?? true,
    impact_confidence_threshold: project.settings?.impact_confidence_threshold ?? 0.75,
    ...Object.fromEntries(
      toggleSettings.map(([key]) => [
        key,
        project.settings?.[key] ??
          ["ai_auto_draft", "ba_can_create_defect", "developer_can_create_defect"].includes(key),
      ]),
    ),
    ...Object.fromEntries(
      numberSettings.map(([key, , , , step]) => [
        key,
        project.settings?.[key] ?? (step === 1 ? 100 : 0.75),
      ]),
    ),
    ...Object.fromEntries(
      selectSettings.map(([key, , values]) => [key, project.settings?.[key] ?? values[0]]),
    ),
  });
  const [error, setError] = useState("");
  const activeQaCount = members.filter(
    (item) => item.project_role === "QA" && item.status === "ACTIVE",
  ).length;
  const isOnlyActiveQa = (item) =>
    item.project_role === "QA" && item.status === "ACTIVE" && activeQaCount === 1;
  useEffect(() => {
    Promise.all([
      testingApi.audit(project._id),
      testingApi.maintenanceAnalytics(project._id),
      testingApi.aiAnalytics(project._id),
      testingApi.listMembers(project._id),
    ])
      .then(([events, value, aiValue, memberValues]) => {
        setAudit(events);
        setAnalytics({ ...value, ...aiValue });
        setMembers(memberValues);
      })
      .catch((reason) => setError(messageOf(reason)));
  }, [project._id]);
  if (workspaceView === "audit") {
    return (
      <WorkspacePage title="Nhật ký audit" actions={<ProjectCrumb projectId={project._id} />}>
        {error && <ErrorState message={error} />}
        <Panel title="Nhật ký kiểm toán">
          <DataTable
            items={audit}
            empty="Chưa có sự kiện"
            columns={[
              { key: "action", label: "Hành động", render: (item) => valueLabel(item.action) },
              {
                key: "artifact_type",
                label: "Loại dữ liệu",
                render: (item) => valueLabel(item.artifact_type),
              },
              { key: "artifact_id", label: "Mã" },
              {
                key: "actor_id",
                label: "Người thực hiện",
                render: (item) => item.actor_label || item.actor_id,
              },
              {
                key: "created_at",
                label: "Thời điểm",
                render: (item) => formatDate(item.created_at),
              },
            ]}
          />
        </Panel>
      </WorkspacePage>
    );
  }
  return (
    <WorkspacePage title="Cài đặt dự án" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Thông tin dự án">
          <form
            className="space-y-4 p-5"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await testingApi.updateProjectSettings(project._id, {
                  expected_revision: project.revision,
                  name,
                  description,
                  project_type: projectType,
                  locale,
                  timezone,
                  settings: {
                    ...(project.settings || {}),
                    ...settings,
                    action_policies: {
                      ...(project.settings?.action_policies || {}),
                      "defect.rejected": settings.tester_can_reject_defect
                        ? ["QA", "TESTER"]
                        : ["QA"],
                      "defect.duplicate": settings.tester_can_mark_duplicate_defect
                        ? ["QA", "TESTER"]
                        : ["QA"],
                      "testplan.assignments": settings.tester_can_assign_testplans
                        ? ["QA", "TESTER"]
                        : ["QA"],
                      "testcase.template.archive": settings.tester_can_archive_testcase_templates
                        ? ["QA", "TESTER"]
                        : ["QA"],
                    },
                  },
                });
                await onProjectChange();
              } catch (reason) {
                setError(messageOf(reason));
              }
            }}
          >
            <label className="field-label">
              Tên
              <input
                className="apple-input mt-2"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <div className="grid gap-3 rounded-xl border border-border p-4 sm:grid-cols-2">
              <label className="field-label">
                Loại dự án
                <select
                  className="apple-input mt-2"
                  value={projectType}
                  onChange={(event) => setProjectType(event.target.value)}
                >
                  {["web", "mobile", "api", "desktop", "embedded", "other"].map((value) => (
                    <option value={value} key={value}>
                      {projectTypeLabels[value]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Ngôn ngữ và vùng
                <input
                  className="apple-input mt-2"
                  value={locale}
                  onChange={(event) => setLocale(event.target.value)}
                />
              </label>
              <label className="field-label sm:col-span-2">
                Múi giờ
                <input
                  className="apple-input mt-2"
                  value={timezone}
                  onChange={(event) => setTimezone(event.target.value)}
                />
              </label>
            </div>
            <details className="rounded-xl border border-border p-4">
              <summary className="cursor-pointer text-[13px] font-semibold">
                Chính sách dự án
              </summary>
              <div className="mt-4 space-y-3">
                {toggleSettings.map(([key, label]) => (
                  <label className="flex items-center gap-3 text-[13px]" key={key}>
                    <input
                      type="checkbox"
                      checked={Boolean(settings[key])}
                      onChange={(event) =>
                        setSettings((current) => ({ ...current, [key]: event.target.checked }))
                      }
                    />
                    {label}
                  </label>
                ))}
                {numberSettings.map(([key, label, min, max, step]) => (
                  <label className="field-label" key={key}>
                    {label}
                    <input
                      className="apple-input mt-2"
                      type="number"
                      min={min}
                      max={max}
                      step={step}
                      value={settings[key]}
                      onChange={(event) =>
                        setSettings((current) => ({
                          ...current,
                          [key]: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                ))}
                {selectSettings.map(([key, label, values]) => (
                  <label className="field-label" key={key}>
                    {label}
                    <select
                      className="apple-input mt-2"
                      value={settings[key]}
                      onChange={(event) =>
                        setSettings((current) => ({ ...current, [key]: event.target.value }))
                      }
                    >
                      {values.map((value) => (
                        <option value={value} key={value}>
                          {settingValueLabels[value] || valueLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            </details>
            <label className="field-label">
              Mô tả
              <textarea
                className="apple-input mt-2 min-h-28"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
            <button className="apple-button" type="submit">
              Lưu với phiên bản {project.revision}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Lưu trữ dự án",
                  description: `${project.key} sẽ ngừng nhận thay đổi mới nhưng vẫn giữ lịch sử và bằng chứng`,
                  confirmLabel: "Lưu trữ",
                  danger: true,
                  fields: [
                    {
                      name: "reason",
                      label: "Lý do lưu trữ",
                      initialValue: "Dự án đã kết thúc vòng đời hoạt động",
                      required: true,
                      multiline: true,
                      autoFocus: true,
                    },
                  ],
                });
                if (!answer) return;
                try {
                  await testingApi.archiveProject(project._id, {
                    expected_revision: project.revision,
                    reason: answer.reason,
                  });
                  window.location.assign("/du-an");
                } catch (value) {
                  setError(messageOf(value));
                }
              }}
            >
              Lưu trữ dự án
            </button>
          </form>
        </Panel>
        <Panel title="Thành viên dự án">
          <div className="space-y-3 p-5">
            <form
              className="grid gap-2 sm:grid-cols-[1fr_150px_auto]"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const value = new FormData(form);
                try {
                  await testingApi.inviteMember(project._id, {
                    user_id: value.get("user_id"),
                    project_role: value.get("project_role"),
                  });
                  form.reset();
                  setMembers(await testingApi.listMembers(project._id));
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              <input
                className="apple-input"
                name="user_id"
                required
                placeholder="Email hoặc mã người dùng"
                aria-label="Email hoặc mã người dùng"
              />
              <select className="apple-input" name="project_role" aria-label="Vai trò dự án">
                <option value="TESTER">Kiểm thử viên</option>
                <option value="BA">Phân tích nghiệp vụ</option>
                <option value="DEVELOPER">Lập trình viên</option>
                <option value="VIEWER">Người xem</option>
                <option value="QA">QA</option>
              </select>
              <button className="secondary-button" type="submit">
                Gửi lời mời
              </button>
            </form>
            <DataTable
              items={members}
              empty="Chưa có thành viên"
              columns={[
                {
                  key: "user_id",
                  label: "Người dùng",
                  render: (item) => (
                    <span className="flex flex-col">
                      <span className="font-semibold text-ink">
                        {item.user_label || item.user_id}
                      </span>
                      {item.user?.email && item.user.email !== item.user_label && (
                        <span className="text-[12px] text-ink-muted">{item.user.email}</span>
                      )}
                    </span>
                  ),
                },
                {
                  key: "project_role",
                  label: "Vai trò",
                  render: (item) => (
                    <select
                      aria-label={`Vai trò ${item.user_label || item.user_id}`}
                      className="apple-input"
                      value={item.project_role}
                      disabled={item.status !== "ACTIVE" || isOnlyActiveQa(item)}
                      onChange={async (event) => {
                        try {
                          await testingApi.updateMember(project._id, item.user_id, {
                            expected_revision: item.membership_revision,
                            project_role: event.target.value,
                          });
                          setMembers(await testingApi.listMembers(project._id));
                        } catch (reason) {
                          setError(messageOf(reason));
                        }
                      }}
                    >
                      {["QA", "TESTER", "BA", "DEVELOPER", "VIEWER"].map((role) => (
                        <option key={role} value={role}>
                          {
                            {
                              QA: "QA",
                              TESTER: "Kiểm thử viên",
                              BA: "Phân tích nghiệp vụ",
                              DEVELOPER: "Lập trình viên",
                              VIEWER: "Người xem",
                            }[role]
                          }
                        </option>
                      ))}
                    </select>
                  ),
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => valueLabel(item.status),
                },
                { key: "membership_revision", label: "Lần sửa đổi" },
                {
                  key: "actions",
                  label: "Thao tác",
                  render: (item) =>
                    isOnlyActiveQa(item) ? (
                      <span className="text-[12px] text-ink-muted">
                        Bổ nhiệm thêm trưởng nhóm trước khi thay đổi hoặc xóa
                      </span>
                    ) : (
                      <span className="flex flex-wrap gap-2">
                        {item.status === "INVITED" ? (
                          <>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={async () => {
                                try {
                                  await testingApi.resendMemberInvite(project._id, item.user_id);
                                  setMembers(await testingApi.listMembers(project._id));
                                } catch (reason) {
                                  setError(messageOf(reason));
                                }
                              }}
                            >
                              Gửi lại lời mời
                            </button>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={async () => {
                                try {
                                  await testingApi.cancelMemberInvite(project._id, item.user_id);
                                  setMembers(await testingApi.listMembers(project._id));
                                } catch (reason) {
                                  setError(messageOf(reason));
                                }
                              }}
                            >
                              Hủy lời mời
                            </button>
                          </>
                        ) : item.status !== "CANCELLED" ? (
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={async () => {
                              try {
                                await testingApi.updateMember(project._id, item.user_id, {
                                  expected_revision: item.membership_revision,
                                  status: item.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
                                });
                                setMembers(await testingApi.listMembers(project._id));
                              } catch (reason) {
                                setError(messageOf(reason));
                              }
                            }}
                          >
                            {item.status === "ACTIVE" ? "Vô hiệu hóa" : "Kích hoạt"}
                          </button>
                        ) : null}
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={async () => {
                            const answer = await ask({
                              title: "Xóa thành viên khỏi dự án",
                              description: `${item.user_label || item.user_id} sẽ mất toàn bộ quyền truy cập dự án này`,
                              confirmLabel: "Xóa thành viên",
                              danger: true,
                            });
                            if (!answer) return;
                            try {
                              await testingApi.removeMember(project._id, item.user_id);
                              setMembers(await testingApi.listMembers(project._id));
                            } catch (reason) {
                              setError(messageOf(reason));
                            }
                          }}
                        >
                          Xóa
                        </button>
                      </span>
                    ),
                },
              ]}
            />
          </div>
        </Panel>
        <Panel title="Phân tích bảo trì">
          <div className="grid grid-cols-2 gap-4 p-5">
            <div>
              <p className="text-3xl font-semibold">{analytics?.impact_analysis_count || 0}</p>
              <p className="field-label mt-2">Phân tích ảnh hưởng</p>
            </div>
            <div>
              <p className="text-3xl font-semibold">{analytics?.tests_stale || 0}</p>
              <p className="field-label mt-2">Ca kiểm thử cũ</p>
            </div>
            <div>
              <p className="text-3xl font-semibold">
                {analytics?.proposal_acceptance_rate == null
                  ? "Chưa có dữ liệu"
                  : `${Math.round(analytics.proposal_acceptance_rate * 100)}%`}
              </p>
              <p className="field-label mt-2">Tỷ lệ chấp nhận đề xuất</p>
            </div>
          </div>
        </Panel>
      </div>
      <ProjectNotificationsPanel project={project} />
      <ProjectConnectorsPanel project={project} />
      <CicdPanel project={project} />
      <WebhookPanel project={project} />
      {dialog}
    </WorkspacePage>
  );
}
