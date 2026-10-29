"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ProjectNotificationsPanel from "../../components/ProjectNotificationsPanel";
import WebhookPanel from "../../components/WebhookPanel";
import ProjectConnectorsPanel from "../../components/ProjectConnectorsPanel";
import MemberSkillProfilePanel from "../../components/MemberSkillProfilePanel";
import CicdPanel from "../../components/CicdPanel";
import {
  ErrorState,
  LoadingState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import {
  invalidProjectDateRange,
  minimumProjectEndDate,
} from "../../lib/projectSchedule.logic.mjs";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";

const toggleSettings = [
  ["requirement_lint_blocking", "Chặn duyệt yêu cầu khi còn lỗi kiểm tra"],
  ["trace_before_baseline", "Bắt buộc truy vết trước khi đặt phiên bản chuẩn cho yêu cầu"],
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
  ["rca_reopen_threshold", "Số lần mở lại lỗi để đề xuất phân tích nguyên nhân gốc", 1, 100, 1],
  ["rca_duplicate_threshold", "Số lỗi cùng cụm để đề xuất phân tích nguyên nhân gốc", 2, 100, 1],
];

const selectSettings = [
  ["default_invite_role", "Vai trò mời mặc định", ["TESTER", "BA", "DEVELOPER", "VIEWER"]],
  ["read_after_archive_policy", "Quyền đọc sau khi lưu trữ", ["ALLOW_READ", "DENY_READ"]],
  ["default_environment", "Môi trường mặc định", ["development", "staging", "production"]],
];

function memberDisplayName(member) {
  return (
    [member.user_label, member.user?.full_name, member.user?.email].find(
      (value) =>
        value &&
        value !== member.user_id &&
        !/^[0-9a-f]{24}$/i.test(value) &&
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value),
    ) || "Tài khoản không xác định"
  );
}

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
  const [dataLoading, setDataLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState({});
  const [activeSettingsSection, setActiveSettingsSection] = useState("project");
  const loadedProjectId = useRef(project._id);
  const settingsLoadRevision = useRef(0);
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || "");
  const [projectType, setProjectType] = useState(project.project_type || "web");
  const [locale, setLocale] = useState(project.locale || "vi-VN");
  const [timezone, setTimezone] = useState(project.timezone || "Asia/Ho_Chi_Minh");
  const [automationFramework, setAutomationFramework] = useState(
    project.automation_framework || "",
  );
  const [automationLanguage, setAutomationLanguage] = useState(project.automation_language || "");
  const [plannedStartAt, setPlannedStartAt] = useState(
    project.planned_start_at ? String(project.planned_start_at).slice(0, 10) : "",
  );
  const [plannedEndAt, setPlannedEndAt] = useState(
    project.planned_end_at ? String(project.planned_end_at).slice(0, 10) : "",
  );
  const plannedDateRangeInvalid = invalidProjectDateRange(plannedStartAt, plannedEndAt);
  const minimumPlannedEndAt = minimumProjectEndDate(plannedStartAt);
  useEffect(() => {
    setPlannedStartAt(
      project.planned_start_at ? String(project.planned_start_at).slice(0, 10) : "",
    );
    setPlannedEndAt(project.planned_end_at ? String(project.planned_end_at).slice(0, 10) : "");
    setAutomationFramework(project.automation_framework || "");
    setAutomationLanguage(project.automation_language || "");
  }, [
    project._id,
    project.revision,
    project.planned_end_at,
    project.planned_start_at,
    project.automation_framework,
    project.automation_language,
  ]);
  const [settings, setSettings] = useState({
    impact_confidence_threshold: project.settings?.impact_confidence_threshold ?? 0.75,
    ...Object.fromEntries(
      toggleSettings.map(([key]) => [
        key,
        project.settings?.[key] ??
          ["ba_can_create_defect", "developer_can_create_defect"].includes(key),
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
  const can = (permission) => project.current_permissions?.includes(permission);
  const settingsSections = [
    {
      id: "project",
      label: "Dự án",
      permissions: ["project.update", "project.settings.manage", "project.archive"],
    },
    {
      id: "members",
      label: "Thành viên",
      permissions: ["project.members.read", "project.members.manage"],
    },
    {
      id: "my-profile",
      label: "Năng lực của tôi",
      permissions: ["project.read"],
    },
    {
      id: "notifications",
      label: "Thông báo",
      permissions: [
        "notification.watch.manage",
        "notification.preferences.manage",
        "notification.project_rule.manage",
      ],
    },
    {
      id: "integrations",
      label: "Tích hợp",
      permissions: ["project.connector.read", "cicd.read", "webhook.project.read"],
    },
    {
      id: "analytics",
      label: "Phân tích",
      permissions: ["analytics.read", "analytics.ai.read"],
    },
  ].filter((section) => section.permissions.some(can));
  const visibleSettingsSection = settingsSections.some(
    (section) => section.id === activeSettingsSection,
  )
    ? activeSettingsSection
    : settingsSections[0]?.id;
  const activeQaCount = members.filter(
    (item) => item.project_role === "QA" && item.status === "ACTIVE",
  ).length;
  const isOnlyActiveQa = (item) =>
    item.project_role === "QA" && item.status === "ACTIVE" && activeQaCount === 1;
  const loadSettingsData = useCallback(async () => {
    const requestRevision = ++settingsLoadRevision.current;
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      setAudit([]);
      setMembers([]);
      setAnalytics(null);
      setLoadErrors({});
    }
    setDataLoading(true);
    const permissions = new Set(project.current_permissions || []);
    setLoadErrors({});
    const results = await Promise.allSettled([
      workspaceView === "audit" && permissions.has("project.audit.read")
        ? testingApi.audit(project._id)
        : Promise.resolve([]),
      visibleSettingsSection === "analytics" && permissions.has("analytics.read")
        ? testingApi.maintenanceAnalytics(project._id)
        : Promise.resolve({}),
      visibleSettingsSection === "analytics" && permissions.has("analytics.ai.read")
        ? testingApi.aiAnalytics(project._id)
        : Promise.resolve({}),
      visibleSettingsSection === "members" && permissions.has("project.members.read")
        ? testingApi.listMembers(project._id)
        : Promise.resolve([]),
    ]);
    if (requestRevision !== settingsLoadRevision.current) return;
    const nextErrors = {};
    const valueAt = (index, key, fallback) => {
      const result = results[index];
      if (result.status === "fulfilled") return result.value;
      nextErrors[key] = [nextErrors[key], messageOf(result.reason)].filter(Boolean).join(" · ");
      return fallback;
    };
    setAudit(valueAt(0, "audit", []));
    setAnalytics({ ...valueAt(1, "analytics", {}), ...valueAt(2, "analytics", {}) });
    setMembers(valueAt(3, "members", []));
    setLoadErrors(nextErrors);
    setDataLoading(false);
  }, [project._id, project.current_permissions, visibleSettingsSection, workspaceView]);
  useEffect(() => {
    void loadSettingsData();
  }, [loadSettingsData]);
  if (workspaceView === "audit") {
    return (
      <WorkspacePage title="Nhật ký kiểm toán" actions={<ProjectCrumb projectId={project._id} />}>
        {error && <ErrorState message={error} />}
        <Panel title="Nhật ký kiểm toán">
          {dataLoading ? (
            <div className="p-5">
              <LoadingState />
            </div>
          ) : loadErrors.audit ? (
            <div className="space-y-3 p-5">
              <ErrorState message={loadErrors.audit} />
              <button
                className="secondary-button"
                type="button"
                onClick={() => void loadSettingsData()}
              >
                Tải lại
              </button>
            </div>
          ) : (
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
                {
                  key: "artifact_id",
                  label: "Đối tượng",
                  render: (item) => (
                    <details>
                      <summary className="cursor-pointer text-sm">Xem chi tiết</summary>
                      <span className="mt-1 block break-all text-xs text-ink-muted">
                        Mã đối tượng: {item.artifact_id || "Không có"}
                      </span>
                    </details>
                  ),
                },
                {
                  key: "actor_id",
                  label: "Người thực hiện",
                  render: (item) => item.actor_label || "Thành viên dự án",
                },
                {
                  key: "created_at",
                  label: "Thời điểm",
                  render: (item) => formatDate(item.created_at),
                },
              ]}
            />
          )}
        </Panel>
      </WorkspacePage>
    );
  }
  return (
    <WorkspacePage title="Cài đặt dự án" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      <SegmentedTabs
        tabs={settingsSections}
        value={visibleSettingsSection}
        onChange={setActiveSettingsSection}
        label="Nhóm cài đặt dự án"
      />
      <div className="min-w-0" role="tabpanel" aria-label="Cài đặt dự án">
        {visibleSettingsSection === "my-profile" && (
          <MemberSkillProfilePanel projectId={project._id} />
        )}
        {visibleSettingsSection === "project" && (
          <Panel title="Thông tin dự án">
            <form
              className="space-y-4 p-5"
              onSubmit={async (event) => {
                event.preventDefault();
                try {
                  const payload = can("project.settings.manage")
                    ? {
                        expected_revision: project.revision,
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
                            "testcase.template.archive":
                              settings.tester_can_archive_testcase_templates
                                ? ["QA", "TESTER"]
                                : ["QA"],
                          },
                        },
                        automation_framework: automationFramework || null,
                        automation_language: automationLanguage || null,
                      }
                    : {
                        expected_revision: project.revision,
                        name,
                        description,
                        project_type: projectType,
                        locale,
                        timezone,
                        automation_framework: automationFramework || null,
                        automation_language: automationLanguage || null,
                      };
                  if (can("project.settings.manage")) {
                    await testingApi.updateProjectSettings(project._id, payload);
                  } else {
                    await testingApi.updateProject(project._id, payload);
                  }
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
                  readOnly={!can("project.update")}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <div className="grid gap-3 rounded-xl border border-border p-4 sm:grid-cols-2">
                <label className="field-label">
                  Loại dự án
                  <select
                    className="apple-input mt-2"
                    disabled={!can("project.update")}
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
                    readOnly={!can("project.update")}
                    value={locale}
                    onChange={(event) => setLocale(event.target.value)}
                  />
                </label>
                <label className="field-label sm:col-span-2">
                  Múi giờ
                  <input
                    className="apple-input mt-2"
                    readOnly={!can("project.update")}
                    value={timezone}
                    onChange={(event) => setTimezone(event.target.value)}
                  />
                </label>
              </div>
              <section className="space-y-3 rounded-xl border border-border p-4">
                <div>
                  <h3 className="text-sm font-semibold text-ink">Tự động hóa kiểm thử</h3>
                  <p className="mt-1 text-sm text-ink-muted">
                    Chọn công cụ và ngôn ngữ dùng cho các ca kiểm thử tự động của dự án.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="field-label">
                    Công cụ
                    <select
                      className="apple-input mt-2"
                      disabled={!can("project.update") && !can("project.settings.manage")}
                      value={automationFramework}
                      onChange={(event) => {
                        const value = event.target.value;
                        setAutomationFramework(value);
                        if (!value) setAutomationLanguage("");
                        else if (value === "selenium") setAutomationLanguage("python");
                        else if (automationLanguage === "python") setAutomationLanguage("");
                      }}
                    >
                      <option value="">Chưa cấu hình</option>
                      <option value="playwright">Playwright</option>
                      <option value="cypress">Cypress</option>
                      <option value="selenium">Selenium</option>
                    </select>
                  </label>
                  <label className="field-label">
                    Ngôn ngữ
                    <select
                      className="apple-input mt-2"
                      disabled={
                        (!can("project.update") && !can("project.settings.manage")) ||
                        !automationFramework ||
                        automationFramework === "selenium"
                      }
                      value={automationLanguage}
                      onChange={(event) => setAutomationLanguage(event.target.value)}
                    >
                      <option value="">Chưa cấu hình</option>
                      {automationFramework === "selenium" ? (
                        <option value="python">Python</option>
                      ) : (
                        <>
                          <option value="typescript">TypeScript</option>
                          <option value="javascript">JavaScript</option>
                        </>
                      )}
                    </select>
                  </label>
                </div>
              </section>
              {can("project.update") && (
                <Panel title="Thời gian dự án">
                  <div className="grid gap-3 p-4 sm:grid-cols-2">
                    <label className="field-label">
                      Bắt đầu dự kiến
                      <input
                        className="apple-input mt-2 w-full"
                        type="date"
                        disabled={!can("project.update")}
                        value={plannedStartAt}
                        onChange={(event) => setPlannedStartAt(event.target.value)}
                      />
                    </label>
                    <label className="field-label">
                      Kết thúc dự kiến
                      <input
                        className="apple-input mt-2 w-full"
                        type="date"
                        min={minimumPlannedEndAt}
                        disabled={!can("project.update")}
                        value={plannedEndAt}
                        onChange={(event) => setPlannedEndAt(event.target.value)}
                      />
                    </label>
                    {plannedDateRangeInvalid && (
                      <p className="sm:col-span-2 text-sm text-danger" role="alert">
                        Ngày kết thúc phải sau ngày bắt đầu.
                      </p>
                    )}
                    <div className="sm:col-span-2">
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={!can("project.update") || plannedDateRangeInvalid}
                        onClick={async () => {
                          setError("");
                          try {
                            await testingApi.updateProject(project._id, {
                              expected_revision: project.revision,
                              planned_start_at: plannedStartAt
                                ? new Date(`${plannedStartAt}T00:00:00.000Z`).toISOString()
                                : null,
                              planned_end_at: plannedEndAt
                                ? new Date(`${plannedEndAt}T00:00:00.000Z`).toISOString()
                                : null,
                            });
                            await onProjectChange();
                          } catch (reason) {
                            setError(messageOf(reason));
                          }
                        }}
                      >
                        Lưu thời gian dự án
                      </button>
                    </div>
                  </div>
                </Panel>
              )}
              {can("project.settings.manage") && (
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
              )}
              <label className="field-label">
                Mô tả
                <textarea
                  className="apple-input mt-2 min-h-28"
                  readOnly={!can("project.update")}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-3">
                {(can("project.update") || can("project.settings.manage")) && (
                  <button className="apple-button" type="submit">
                    Lưu thay đổi
                  </button>
                )}
                {can("project.archive") && (
                  <button
                    className="danger-button"
                    type="button"
                    onClick={async () => {
                      await ask({
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
                        onConfirm: async (answer) => {
                          try {
                            await testingApi.archiveProject(project._id, {
                              expected_revision: project.revision,
                              reason: answer.reason,
                            });
                            window.location.assign("/du-an");
                          } catch (reason) {
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
                    }}
                  >
                    Lưu trữ dự án
                  </button>
                )}
              </div>
            </form>
          </Panel>
        )}
        {visibleSettingsSection === "members" && (
          <Panel title={can("project.members.read") ? "Thành viên dự án" : "Lời mời thành viên"}>
            <div className="space-y-3 p-5">
              {dataLoading ? (
                <LoadingState />
              ) : loadErrors.members ? (
                <div className="space-y-3">
                  <ErrorState message={loadErrors.members} />
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void loadSettingsData()}
                  >
                    Tải lại
                  </button>
                </div>
              ) : (
                <>
                  {can("project.members.manage") && (
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
                          if (can("project.members.read")) {
                            setMembers(await testingApi.listMembers(project._id));
                          }
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
                      <select
                        className="apple-input"
                        name="project_role"
                        aria-label="Vai trò dự án"
                      >
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
                  )}
                  {can("project.members.read") ? (
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
                                {memberDisplayName(item)}
                              </span>
                              {item.user?.email && item.user.email !== memberDisplayName(item) && (
                                <span className="text-[12px] text-ink-muted">
                                  {item.user.email}
                                </span>
                              )}
                            </span>
                          ),
                        },
                        {
                          key: "project_role",
                          label: "Vai trò",
                          render: (item) =>
                            can("project.members.manage") ? (
                              <select
                                aria-label={`Vai trò ${memberDisplayName(item)}`}
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
                            ) : (
                              <span>
                                {settingValueLabels[item.project_role] || item.project_role}
                              </span>
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
                          hideWhenEmpty: true,
                          render: (item) =>
                            !can("project.members.manage") ? null : isOnlyActiveQa(item) ? (
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
                                          await testingApi.resendMemberInvite(
                                            project._id,
                                            item.user_id,
                                          );
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
                                          await testingApi.cancelMemberInvite(
                                            project._id,
                                            item.user_id,
                                          );
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
                                      description: `${memberDisplayName(item)} sẽ mất toàn bộ quyền truy cập dự án này`,
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
                  ) : null}
                </>
              )}
            </div>
          </Panel>
        )}
        {visibleSettingsSection === "analytics" && (
          <Panel title="Phân tích bảo trì">
            {dataLoading ? (
              <div className="p-5">
                <LoadingState />
              </div>
            ) : loadErrors.analytics ? (
              <div className="space-y-3 p-5">
                <ErrorState message={loadErrors.analytics} />
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void loadSettingsData()}
                >
                  Tải lại
                </button>
              </div>
            ) : (
              <div className="grid gap-5 p-5 sm:grid-cols-2">
                {can("analytics.read") && (
                  <>
                    <div>
                      <p className="text-3xl font-semibold">
                        {analytics?.impact_analysis_count || 0}
                      </p>
                      <p className="field-label mt-2">Phân tích ảnh hưởng</p>
                    </div>
                    <div>
                      <p className="text-3xl font-semibold">{analytics?.tests_stale || 0}</p>
                      <p className="field-label mt-2">Ca kiểm thử cũ</p>
                    </div>
                  </>
                )}
                {can("analytics.ai.read") && (
                  <>
                    <div>
                      <p className="text-3xl font-semibold">{analytics?.degraded_count || 0}</p>
                      <p className="field-label mt-2">
                        Lượt phân tích ảnh hưởng bị suy giảm hoặc không thành công
                      </p>
                    </div>
                    <div>
                      <p className="text-3xl font-semibold">
                        {Math.round(analytics?.average_latency_ms || 0)} ms
                      </p>
                      <p className="field-label mt-2">
                        Thời gian phản hồi trung bình của phân tích ảnh hưởng
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}
          </Panel>
        )}
      </div>
      {visibleSettingsSection === "notifications" && (
        <ProjectNotificationsPanel project={project} />
      )}
      {visibleSettingsSection === "integrations" && (
        <div className="grid min-w-0 gap-5 2xl:grid-cols-2">
          <ProjectConnectorsPanel project={project} />
          <CicdPanel project={project} />
          <WebhookPanel project={project} />
        </div>
      )}
      {dialog}
    </WorkspacePage>
  );
}
