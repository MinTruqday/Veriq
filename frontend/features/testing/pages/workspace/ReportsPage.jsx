"use client";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import DataTable from "../../components/DataTable";
import TestStatusReportPanel from "../../components/TestStatusReportPanel";
import SimpleTestReports from "../../components/SimpleTestReports";
import CompletionPage from "./CompletionPage";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import {
  ErrorState,
  LoadingState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { formatDate as formatDateValue, messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";
import { formatNumber } from "@/shared/lib/locale.mjs";

function metricRate(value, locale) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? `${formatNumber(Math.round(numericValue * 100), locale)}%`
    : "Chưa đủ dữ liệu";
}

function metricPercentage(value, locale) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? `${formatNumber(Math.round(numericValue), locale)}%`
    : "Chưa đủ dữ liệu";
}

function metricCount(value, locale) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? formatNumber(numericValue, locale, { maximumFractionDigits: 0 })
    : "Chưa đủ dữ liệu";
}

function metricDuration(milliseconds, locale) {
  if (milliseconds === null || milliseconds === undefined || milliseconds === "") {
    return "Chưa đủ dữ liệu";
  }
  const value = Number(milliseconds);
  if (!Number.isFinite(value) || value < 0) return "Chưa đủ dữ liệu";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${formatNumber(value / 1000, locale, { maximumFractionDigits: 1 })} giây`;
}

function metricDays(value, openCount) {
  if (
    openCount !== null &&
    openCount !== undefined &&
    openCount !== "" &&
    Number.isFinite(Number(openCount)) &&
    Number(openCount) === 0
  ) {
    return "Chưa có lỗi đang mở";
  }
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? `${numericValue} ngày` : "Chưa đủ dữ liệu";
}

const aiCapabilityLabels = {
  requirement_quality_analysis: "Rà soát yêu cầu",
  requirement_template_synthesis: "Tạo mẫu yêu cầu",
  requirement_template_review: "Rà soát mẫu yêu cầu",
  scenario_generation: "Tạo kịch bản kiểm thử",
  test_generation: "Tạo ca kiểm thử",
  test_condition_generation: "Đề xuất điều kiện kiểm thử",
  test_plan_draft_generation: "Đề xuất kế hoạch kiểm thử",
  test_data_generation: "Tạo dữ liệu kiểm thử",
  execution_assistance: "Hỗ trợ thực thi kiểm thử",
  impact_analysis: "Phân tích ảnh hưởng",
  project_question: "Hỏi đáp dự án",
  security_test_generation: "Đề xuất kiểm thử bảo mật",
  performance_plan_generation: "Đề xuất kiểm thử hiệu năng",
  automation_script_generation: "Tạo bản nháp mã kiểm thử tự động",
  status_report_narrative: "Soạn diễn giải báo cáo trạng thái",
  completion_report_narrative: "Soạn diễn giải báo cáo hoàn tất",
  lessons_learned_clustering: "Nhóm bài học kinh nghiệm",
};

function reportActivityActionLabel(value) {
  const rawValue = String(value || "");
  const label = valueLabel(value);
  return label === rawValue && /^[a-z0-9]+(?:[._][a-z0-9]+)+$/i.test(rawValue) ? "Cập nhật" : label;
}

function reportActivityEntityLabel(value) {
  const rawValue = String(value || "");
  const label = valueLabel(value);
  return label === rawValue ? "Nội dung dự án" : label;
}

function countRows(values, key) {
  const rows = [];
  let otherCount = 0;
  for (const [name, count] of Object.entries(values || {})) {
    const label = aiCapabilityLabels[name];
    if (!label) {
      otherCount += Number(count || 0);
      continue;
    }
    rows.push({ _id: name, name, count, label, key });
  }
  if (otherCount)
    rows.push({ _id: "other", name: "other", count: otherCount, label: "Chức năng khác", key });
  return rows;
}

const aiDecisionReasonLabels = {
  OUT_OF_SCOPE: "Ngoài phạm vi",
  INCORRECT: "Thông tin chưa đúng",
  INCOMPLETE: "Thiếu nội dung",
  DUPLICATE: "Trùng lặp",
  UNSUPPORTED_BY_SOURCE: "Nguồn chưa đủ căn cứ",
  RISK_ACCEPTED: "Đã chấp nhận rủi ro",
  OTHER: "Lý do khác",
};

const aiChangedFieldLabels = {
  title: "Tên ca kiểm thử",
  objective_doc: "Mục tiêu",
  preconditions_doc: "Điều kiện trước",
  steps: "Các bước",
  test_data: "Dữ liệu kiểm thử",
  expected_result_doc: "Kết quả mong đợi",
  postconditions_doc: "Điều kiện sau",
  tags: "Nhãn",
  techniques: "Kỹ thuật kiểm thử",
  requirement_version_ids: "Liên kết yêu cầu",
  acceptance_criterion_ids: "Tiêu chí chấp nhận",
};

function ReportMetric({ label, value, detail }) {
  const unavailable = value === "Chưa đủ dữ liệu" || value === "Chưa có lỗi đang mở";
  const unavailableDetail =
    value === "Chưa có lỗi đang mở" ? "Không có lỗi đang mở" : "Chưa có dữ liệu";
  return (
    <div className="min-w-0 rounded-xl border border-border-strong bg-surface-raised p-4 shadow-sm">
      <dt className="min-h-10 text-[12px] font-medium leading-5 text-ink-muted">{label}</dt>
      <dd className="mt-1 text-[27px] font-semibold tracking-[-0.04em] text-ink">
        {unavailable ? "—" : value}
      </dd>
      {(detail || unavailable) && (
        <dd className="mt-1 text-[11px] leading-4 text-ink-faint">{detail || unavailableDetail}</dd>
      )}
    </div>
  );
}

export default function ReportsPage({ project }) {
  const searchParams = useSearchParams();
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const formatMetricRate = (value) => metricRate(value, dateTimeOptions.locale);
  const formatMetricPercentage = (value) => metricPercentage(value, dateTimeOptions.locale);
  const formatMetricCount = (value) => metricCount(value, dateTimeOptions.locale);
  const formatMetricDuration = (value) => metricDuration(value, dateTimeOptions.locale);
  const { ask, dialog } = useActionDialog();
  const [value, setValue] = useState(null);
  const [releases, setReleases] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [scope, setScope] = useState({
    release: "",
    release_id: "",
    environment: "",
    environment_id: "",
    build: "",
    build_id: "",
  });
  const [snapshotGeneration, setSnapshotGeneration] = useState(0);
  const [showLegacy, setShowLegacy] = useState(false);
  const [activeTab, setActiveTab] = useState("summary");
  const [activeTestReportTab, setActiveTestReportTab] = useState("status");
  const [showAllActivity, setShowAllActivity] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const loadGeneration = useRef(0);
  const optionsGeneration = useRef(0);
  const loadedProjectId = useRef(project._id);
  useEffect(() => {
    if (searchParams.get("tab") === "reports") setActiveTab("reports");
    if (searchParams.get("testReport") === "completion") {
      setActiveTab("reports");
      setActiveTestReportTab("completion");
    }
  }, [searchParams]);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadReports = can("report.read");
  const canCreateSnapshot = canReadCoverage && can("coverage.snapshot.create");
  const canFilterScope = can("release.read") || can("build.read") || can("environment.read");
  const scopeFilterCount = ["environment.read", "release.read", "build.read"].filter(can).length;
  const hasScopedFilter = Boolean(
    scope.release_id ||
      scope.release ||
      scope.environment_id ||
      scope.environment ||
      scope.build_id ||
      scope.build,
  );
  const reportTabs = [
    ...(canReadAnalytics || canReadCoverage || canReadReports
      ? [{ id: "summary", label: "Tổng quan" }]
      : []),
    ...(can("teststatusreport.read") || can("testcompletion.read")
      ? [{ id: "reports", label: "Báo cáo" }]
      : []),
  ];
  const visibleTab = reportTabs.some((tab) => tab.id === activeTab) ? activeTab : reportTabs[0]?.id;
  const testReportTabs = [
    ...(can("teststatusreport.read") ? [{ id: "status", label: "Trạng thái kiểm thử" }] : []),
    ...(can("testcompletion.read") ? [{ id: "completion", label: "Hoàn tất kiểm thử" }] : []),
  ];
  const visibleTestReportTab = testReportTabs.some((tab) => tab.id === activeTestReportTab)
    ? activeTestReportTab
    : testReportTabs[0]?.id;
  const recentActivity = useMemo(
    () =>
      (Array.isArray(value?.activity) ? value.activity : []).filter(
        (item) => item.action !== "project_membership_required",
      ),
    [value?.activity],
  );
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      setValue(null);
      setScope({
        release: "",
        release_id: "",
        environment: "",
        environment_id: "",
        build: "",
        build_id: "",
      });
    }
    setError("");
    setLoading(true);
    const requests = [
      ["dashboard", canReadAnalytics ? testingApi.dashboard(project._id) : Promise.resolve(null)],
      [
        "coverage",
        canReadCoverage ? testingApi.coverage(project._id, scope) : Promise.resolve(null),
      ],
      [
        "snapshots",
        canReadCoverage ? testingApi.listCoverageSnapshots(project._id) : Promise.resolve(null),
      ],
      [
        "maintenance",
        canReadAnalytics ? testingApi.maintenanceAnalytics(project._id) : Promise.resolve(null),
      ],
      [
        "execution",
        canReadReports ? testingApi.executionReport(project._id, scope) : Promise.resolve(null),
      ],
      [
        "defects",
        canReadReports ? testingApi.defectReport(project._id, scope) : Promise.resolve(null),
      ],
      [
        "activity",
        canReadAnalytics ? testingApi.projectActivity(project._id) : Promise.resolve(null),
      ],
    ];
    const results = await Promise.allSettled(requests.map(([, request]) => request));
    if (requestGeneration !== loadGeneration.current) return;
    const data = {};
    const errors = [];
    results.forEach((result, index) => {
      const [key] = requests[index];
      if (result.status === "fulfilled") data[key] = result.value;
      else {
        data[key] = null;
        if (result.reason?.status !== 403) errors.push(messageOf(result.reason));
      }
    });
    setValue((current) => ({
      dashboard: null,
      coverage: null,
      snapshots: null,
      maintenance: null,
      execution: null,
      defects: null,
      activity: null,
      ...(current || {}),
      ...data,
    }));
    setError([...new Set(errors)].join(" · "));
    setLoading(false);
  }, [canReadAnalytics, canReadCoverage, canReadReports, project._id, scope]);
  useEffect(() => {
    const requestGeneration = ++optionsGeneration.current;
    setReleases([]);
    setBuilds([]);
    setEnvironments([]);
    Promise.all([
      permissions.includes("release.read")
        ? testingApi.listReleases(project._id)
        : Promise.resolve([]),
      permissions.includes("build.read") ? testingApi.listBuilds(project._id) : Promise.resolve([]),
      permissions.includes("environment.read")
        ? testingApi.listEnvironments(project._id)
        : Promise.resolve([]),
    ])
      .then(([releaseValues, buildValues, environmentValues]) => {
        if (requestGeneration !== optionsGeneration.current) return;
        setReleases(releaseValues);
        setBuilds(buildValues);
        setEnvironments(environmentValues);
      })
      .catch((reason) => {
        if (requestGeneration === optionsGeneration.current) setError(messageOf(reason));
      });
    return () => {
      if (optionsGeneration.current === requestGeneration) optionsGeneration.current += 1;
    };
  }, [permissions, project._id]);
  useEffect(() => {
    if (visibleTab === "summary") void load();
  }, [load, visibleTab]);
  const createReportSnapshot = async () => {
    try {
      const [plans, availableReleases] = await Promise.all([
        testingApi.listPlans(project._id, { status: "APPROVED" }),
        can("release.read") ? testingApi.listReleases(project._id) : Promise.resolve([]),
      ]);
      if (!plans.length) {
        setError("Cần có kế hoạch kiểm thử đã duyệt để lưu mốc báo cáo.");
        return;
      }
      setError("");
      await ask({
        title: "Lưu mốc báo cáo",
        confirmLabel: "Lưu mốc",
        fields: [
          {
            name: "test_plan_id",
            label: "Kế hoạch kiểm thử",
            required: true,
            options: plans.map((plan) => ({ value: plan._id, label: plan.name })),
          },
          ...(availableReleases.length
            ? [
                {
                  name: "release_id",
                  label: "Bản phát hành",
                  options: [
                    { value: "", label: "-" },
                    ...availableReleases.map((release) => ({
                      value: release._id,
                      label: release.name,
                    })),
                  ],
                },
              ]
            : []),
          { name: "actual_effort", label: "Nỗ lực thực tế theo giờ", type: "number" },
          {
            name: "expected_completion",
            label: "Thời điểm dự kiến hoàn thành",
            type: "datetime-local",
          },
        ],
        onConfirm: async (answer) => {
          try {
            await testingApi.createMonitoringSnapshot(project._id, {
              test_plan_id: answer.test_plan_id,
              release_id: answer.release_id || null,
              actual_effort: answer.actual_effort === "" ? null : Number(answer.actual_effort),
              expected_completion: answer.expected_completion || null,
              risks: [],
              blockers: [],
            });
            setSnapshotGeneration((current) => current + 1);
          } catch (reason) {
            throw new Error(messageOf(reason));
          }
        },
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!showLegacy && (can("teststatusreport.read") || can("testcompletion.read")))
    return (
      <WorkspacePage
        title="Báo cáo"
        actions={
          <>
            <button className="secondary-button" type="button" onClick={() => setShowLegacy(true)}>
              Báo cáo trước đây
            </button>
            <ProjectCrumb projectId={project._id} />
          </>
        }
      >
        <SimpleTestReports project={project} />
      </WorkspacePage>
    );
  return (
    <WorkspacePage
      title="Báo cáo"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          <button className="secondary-button" type="button" onClick={() => setShowLegacy(false)}>
            Báo cáo kiểm thử
          </button>
          {visibleTab === "reports" &&
            can("testmonitor.snapshot.create") &&
            can("testplan.read") && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => void createReportSnapshot()}
              >
                Lưu mốc báo cáo
              </button>
            )}
          {visibleTab === "summary" && (
            <button
              className="apple-button"
              disabled={loading}
              onClick={() => void load()}
              type="button"
            >
              {loading ? "Đang tải…" : "Tải lại dữ liệu"}
            </button>
          )}
        </div>
      }
    >
      {error && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <ErrorState message={error} />
          </div>
        </div>
      )}
      {reportTabs.length > 1 && (
        <SegmentedTabs
          label="Nhóm báo cáo"
          value={visibleTab}
          onChange={setActiveTab}
          tabs={reportTabs}
        />
      )}
      {visibleTab === "reports" && (
        <div className="space-y-6">
          {testReportTabs.length > 1 && (
            <SegmentedTabs
              label="Loại báo cáo kiểm thử"
              value={visibleTestReportTab}
              onChange={setActiveTestReportTab}
              tabs={testReportTabs}
            />
          )}
          {visibleTestReportTab === "status" && (
            <TestStatusReportPanel key={snapshotGeneration} project={project} />
          )}
          {visibleTestReportTab === "completion" && (
            <CompletionPage key={snapshotGeneration} project={project} />
          )}
        </div>
      )}
      {visibleTab === "summary" && (
        <div className="space-y-6">
          {(canReadReports || canReadCoverage) && (canFilterScope || canCreateSnapshot) && (
            <section aria-labelledby="report-scope-heading" className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-base font-semibold" id="report-scope-heading">
                  Phạm vi dữ liệu
                </h2>
                {canCreateSnapshot && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={async () => {
                      await ask({
                        title: "Lưu mốc độ phủ",
                        description: `Phạm vi lưu: ${scope.release || "mọi bản phát hành"} · ${scope.build || "mọi bản dựng"}`,
                        confirmLabel: "Lưu mốc độ phủ",
                        fields: [
                          {
                            name: "label",
                            label: "Tên mốc độ phủ",
                            required: true,
                            autoFocus: true,
                          },
                        ],
                        onConfirm: async (answer) => {
                          try {
                            await testingApi.createCoverageSnapshot(project._id, {
                              label: answer.label,
                              release: scope.release,
                              release_id: scope.release_id,
                              build: scope.build,
                              build_id: scope.build_id,
                              idempotency_key: crypto.randomUUID(),
                            });
                            await load();
                          } catch (reason) {
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
                    }}
                  >
                    Lưu mốc độ phủ
                  </button>
                )}
              </div>
              {canFilterScope && (
                <div
                  className={`grid gap-3 border-y border-border py-4 ${scopeFilterCount === 1 ? "sm:grid-cols-1" : scopeFilterCount === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}
                >
                  {can("environment.read") && (
                    <select
                      aria-label="Lọc theo môi trường"
                      className="apple-input"
                      value={scope.environment_id}
                      onChange={(event) => {
                        const environmentId = event.target.value;
                        const environment = environments.find((item) => item._id === environmentId);
                        setScope({
                          ...scope,
                          environment_id: environmentId,
                          environment: environment?.name || "",
                        });
                      }}
                    >
                      <option value="">Tất cả môi trường</option>
                      {environments.map((item) => (
                        <option key={item._id} value={item._id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  )}
                  {can("release.read") && (
                    <select
                      aria-label="Lọc theo bản phát hành"
                      className="apple-input"
                      value={scope.release_id}
                      onChange={(event) => {
                        const releaseId = event.target.value;
                        const release = releases.find((item) => item._id === releaseId);
                        setScope({
                          ...scope,
                          release_id: releaseId,
                          release: release?.key || "",
                          build_id: "",
                          build: "",
                        });
                      }}
                    >
                      <option value="">Tất cả bản phát hành</option>
                      {releases.map((item) => (
                        <option key={item._id} value={item._id}>
                          {item.key} · {item.name}
                        </option>
                      ))}
                    </select>
                  )}
                  {can("build.read") && (
                    <select
                      aria-label="Lọc theo bản dựng"
                      className="apple-input"
                      value={scope.build_id}
                      onChange={(event) => {
                        const buildId = event.target.value;
                        const build = builds.find((item) => item._id === buildId);
                        const release = releases.find((item) => item._id === build?.release_id);
                        setScope({
                          ...scope,
                          build_id: buildId,
                          build: build?.identifier || "",
                          release_id: build?.release_id || scope.release_id,
                          release: release?.key || scope.release,
                        });
                      }}
                    >
                      <option value="">Tất cả bản dựng</option>
                      {builds
                        .filter((item) => !scope.release_id || item.release_id === scope.release_id)
                        .map((item) => (
                          <option key={item._id} value={item._id}>
                            {item.identifier} · {item.version}
                          </option>
                        ))}
                    </select>
                  )}
                </div>
              )}
            </section>
          )}
          {!value && loading ? (
            <LoadingState />
          ) : !value && !error ? (
            <LoadingState />
          ) : value ? (
            <>
              {value.coverage && (
                <section
                  aria-labelledby="coverage-metrics-heading"
                  className="space-y-3 rounded-xl border border-border-strong bg-white p-4 shadow-sm sm:p-5"
                >
                  <div>
                    <h2 className="text-base font-semibold" id="coverage-metrics-heading">
                      Liên kết yêu cầu và kết quả kiểm thử
                    </h2>
                    <p className="mt-1 text-sm text-ink-muted">
                      Tỷ lệ ca đã chạy tính theo bản phát hành và bản dựng, chưa lọc theo môi
                      trường.
                    </p>
                  </div>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-5 xl:grid-cols-5">
                    <ReportMetric
                      label="Yêu cầu có liên kết kiểm thử"
                      value={formatMetricPercentage(value.coverage.requirement_coverage)}
                    />
                    <ReportMetric
                      label="Tiêu chí chấp nhận có liên kết"
                      value={formatMetricPercentage(value.coverage.acceptance_criterion_coverage)}
                    />
                    <ReportMetric
                      label="Liên kết còn hiệu lực"
                      value={formatMetricPercentage(value.coverage.fresh_coverage)}
                    />
                    <ReportMetric
                      label="Ca kiểm thử đã chạy"
                      value={formatMetricPercentage(value.coverage.execution_coverage)}
                    />
                    <ReportMetric
                      label="Ca kiểm thử cần cập nhật"
                      value={formatMetricCount(value.coverage.stale_tests)}
                    />
                  </dl>
                </section>
              )}
              {(value.execution || value.defects) && (
                <section
                  aria-labelledby="execution-metrics-heading"
                  className="space-y-3 rounded-xl border border-border-strong bg-white p-4 shadow-sm sm:p-5"
                >
                  <div>
                    <h2 className="text-base font-semibold" id="execution-metrics-heading">
                      Kết quả thực thi và lỗi trong phạm vi đã chọn
                    </h2>
                    {hasScopedFilter && (
                      <p className="mt-1 text-sm text-ink-muted">
                        Các số liệu này chỉ áp dụng cho bộ lọc bản phát hành, bản dựng hoặc môi
                        trường hiện tại.
                      </p>
                    )}
                  </div>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-5 xl:grid-cols-2">
                    {value.execution && (
                      <ReportMetric
                        label="Kết quả kiểm thử đạt"
                        value={formatMetricRate(value.execution.pass_rate)}
                        detail={
                          value.execution.terminal_result_count
                            ? `${value.execution.result_counts?.PASS || 0} trên ${value.execution.terminal_result_count} kết quả đã kết thúc`
                            : "Chưa có kết quả đã kết thúc"
                        }
                      />
                    )}
                    {value.defects && (
                      <>
                        <ReportMetric
                          label="Tuổi trung bình lỗi đang mở"
                          value={metricDays(
                            value.defects.average_open_age_days,
                            value.defects.open_count,
                          )}
                        />
                      </>
                    )}
                  </dl>
                </section>
              )}
              {(value.dashboard || value.defects || value.maintenance) && (
                <section
                  aria-labelledby="project-metrics-heading"
                  className="space-y-3 rounded-xl border border-border-strong bg-white p-4 shadow-sm sm:p-5"
                >
                  <div>
                    <h2 className="text-base font-semibold" id="project-metrics-heading">
                      Chỉ số toàn dự án
                    </h2>
                  </div>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-5 xl:grid-cols-5">
                    {value.dashboard && (
                      <ReportMetric
                        label="Lỗi đang mở"
                        value={formatMetricCount(value.dashboard.open_defects)}
                      />
                    )}
                    {value.defects && (
                      <ReportMetric
                        label="Số lần mở lại lỗi"
                        value={formatMetricCount(value.defects.reopened_count)}
                      />
                    )}
                    {value.maintenance && (
                      <ReportMetric
                        label="Lượt phân tích ảnh hưởng"
                        value={formatMetricCount(value.maintenance.impact_analysis_count)}
                      />
                    )}
                  </dl>
                </section>
              )}
              <details className="space-y-4">
                <summary className="cursor-pointer border-y border-border py-4 font-semibold text-ink">
                  Số liệu chi tiết
                </summary>
                <div className="space-y-5">
                  <div
                    className={`grid gap-5 ${value.execution && value.defects ? "xl:grid-cols-2" : "grid-cols-1"}`}
                  >
                    {value.execution && (
                      <Panel title="Kết quả thực thi">
                        <DataTable
                          items={Object.entries(value.execution.result_counts || {}).map(
                            ([status, count]) => ({ _id: status, status, count }),
                          )}
                          empty="Chưa có kết quả thực thi"
                          columns={[
                            {
                              key: "status",
                              label: "Trạng thái",
                              render: (item) => valueLabel(item.status),
                            },
                            { key: "count", label: "Số lượng" },
                          ]}
                        />
                      </Panel>
                    )}
                    {value.defects && (
                      <Panel title="Lỗi theo mức độ">
                        <DataTable
                          items={Object.entries(value.defects.severity_counts || {}).map(
                            ([severity, count]) => ({ _id: severity, severity, count }),
                          )}
                          empty="Chưa có lỗi"
                          columns={[
                            {
                              key: "severity",
                              label: "Mức độ",
                              render: (item) => item.severity,
                            },
                            { key: "count", label: "Số lượng" },
                          ]}
                        />
                      </Panel>
                    )}
                  </div>
                  <div className="grid grid-cols-1 gap-5">
                    {value.coverage && (
                      <Panel title="Yêu cầu theo nhóm tình huống kiểm thử">
                        <DataTable
                          items={Object.entries(value.coverage.category_coverage || {}).map(
                            ([category, coverage]) => ({ _id: category, category, coverage }),
                          )}
                          empty="Chưa có dữ liệu theo nhóm tình huống"
                          columns={[
                            {
                              key: "category",
                              label: "Nhóm tình huống",
                              render: (item) => valueLabel(item.category),
                            },
                            {
                              key: "coverage",
                              label: "Yêu cầu có liên kết",
                              render: (item) => formatMetricPercentage(item.coverage),
                            },
                          ]}
                        />
                      </Panel>
                    )}
                  </div>
                  {value.coverage && Array.isArray(value.snapshots) && (
                    <Panel title="Mốc độ phủ">
                      <DataTable
                        items={value.snapshots || []}
                        empty="Chưa có mốc độ phủ"
                        columns={[
                          { key: "label", label: "Tên" },
                          {
                            key: "created_at",
                            label: "Thời điểm",
                            render: (item) => formatDate(item.created_at),
                          },
                          {
                            key: "requirement_coverage",
                            label: "Yêu cầu có liên kết",
                            render: (item) =>
                              formatMetricPercentage(item.metrics?.requirement_coverage),
                          },
                          {
                            key: "fresh_coverage",
                            label: "Liên kết còn hiệu lực",
                            render: (item) => formatMetricPercentage(item.metrics?.fresh_coverage),
                          },
                          {
                            key: "execution_coverage",
                            label: "Ca kiểm thử đã chạy",
                            render: (item) =>
                              formatMetricPercentage(item.metrics?.execution_coverage),
                          },
                        ]}
                      />
                    </Panel>
                  )}
                  {Array.isArray(value.activity) && (
                    <section aria-labelledby="recent-report-activity-heading" className="space-y-3">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="text-base font-semibold" id="recent-report-activity-heading">
                          Hoạt động gần đây
                        </h3>
                        {recentActivity.length > 12 && (
                          <button
                            className="text-sm font-medium text-brand"
                            type="button"
                            onClick={() => setShowAllActivity((current) => !current)}
                          >
                            {showAllActivity
                              ? "Thu gọn"
                              : `Xem tất cả ${recentActivity.length} hoạt động`}
                          </button>
                        )}
                      </div>
                      <ol
                        aria-label="Hoạt động gần đây"
                        className="divide-y divide-border border-y border-border"
                      >
                        {(showAllActivity ? recentActivity : recentActivity.slice(0, 12)).map(
                          (item, index) => (
                            <li
                              className="flex min-w-0 items-center justify-between gap-4 py-3"
                              key={item._id || `${item.action}-${item.created_at}-${index}`}
                            >
                              <div className="min-w-0">
                                <p className="truncate text-sm font-medium text-ink">
                                  {reportActivityActionLabel(item.action)}
                                </p>
                                <p className="mt-1 text-xs text-ink-muted">
                                  {reportActivityEntityLabel(item.entity_type)}
                                </p>
                              </div>
                              <time
                                className="shrink-0 text-xs text-ink-muted"
                                dateTime={item.created_at || undefined}
                              >
                                {formatDate(item.created_at)}
                              </time>
                            </li>
                          ),
                        )}
                        {!recentActivity.length && (
                          <li className="py-5 text-center text-sm text-ink-muted">
                            Chưa có hoạt động
                          </li>
                        )}
                      </ol>
                    </section>
                  )}
                </div>
              </details>
            </>
          ) : null}
        </div>
      )}
      {dialog}
    </WorkspacePage>
  );
}
