"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import WorkReportsPanel from "../../components/WorkReportsPanel";
import TestStatusReportPanel from "../../components/TestStatusReportPanel";
import CompletionPage from "./CompletionPage";
import MetricDefinitionPanel from "../../components/MetricDefinitionPanel";
import ReleaseQualityPanel from "../../components/ReleaseQualityPanel";
import ProcessImprovementPanel from "../../components/ProcessImprovementPanel";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";

function metricRate(value) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? `${Math.round(numericValue * 100)}%` : "Chưa đủ dữ liệu";
}

function metricPercentage(value) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? `${Math.round(numericValue)}%` : "Chưa đủ dữ liệu";
}

function metricCount(value) {
  if (value === null || value === undefined || value === "") return "Chưa đủ dữ liệu";
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : "Chưa đủ dữ liệu";
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
  testability_blueprint_compilation: "Lập bản đồ điều kiện kiểm thử",
  scenario_generation: "Tạo kịch bản kiểm thử",
  test_generation: "Tạo ca kiểm thử",
  test_condition_generation: "Đề xuất điều kiện kiểm thử",
  test_plan_draft_generation: "Đề xuất Test Plan",
  test_data_generation: "Tạo dữ liệu kiểm thử",
  execution_assistance: "Hỗ trợ thực thi kiểm thử",
  impact_analysis: "Phân tích ảnh hưởng",
  project_question: "Hỏi đáp dự án",
  security_test_generation: "Đề xuất kiểm thử bảo mật",
  performance_plan_generation: "Đề xuất kiểm thử hiệu năng",
  automation_script_generation: "Tạo bản nháp mã tự động hóa",
  causal_analysis: "Phân tích nguyên nhân khả dĩ",
  status_report_narrative: "Soạn diễn giải báo cáo trạng thái",
  completion_report_narrative: "Soạn diễn giải báo cáo hoàn tất",
  lessons_learned_clustering: "Nhóm bài học kinh nghiệm",
};

function aiCapabilityLabel(value) {
  return aiCapabilityLabels[value] || valueLabel(value);
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
    <Metric
      label={label}
      value={unavailable ? "—" : value}
      detail={detail || (unavailable ? unavailableDetail : undefined)}
    />
  );
}

export default function ReportsPage({ project }) {
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
  const [activeTab, setActiveTab] = useState("summary");
  const [error, setError] = useState("");
  const loadGeneration = useRef(0);
  const optionsGeneration = useRef(0);
  const loadedProjectId = useRef(project._id);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadReports = can("report.read");
  const canReadAiAnalytics = can("analytics.ai.read");
  const canCreateSnapshot = canReadCoverage && can("coverage.snapshot.create");
  const canFilterScope = can("release.read") || can("build.read") || can("environment.read");
  const hasScopedFilter = Boolean(
    scope.release_id ||
      scope.release ||
      scope.environment_id ||
      scope.environment ||
      scope.build_id ||
      scope.build,
  );
  const reportTabs = [
    ...(can("workreport.read") ? [{ id: "work", label: "Công việc và định kỳ" }] : []),
    ...(canReadAnalytics || canReadAiAnalytics || canReadCoverage || canReadReports
      ? [{ id: "summary", label: "Tổng quan" }]
      : []),
    ...(can("teststatusreport.read") || can("testcompletion.read")
      ? [{ id: "reports", label: "Báo cáo" }]
      : []),
    ...(can("qualityevaluation.read") || can("measurement.read") || can("processimprovement.read")
      ? [{ id: "quality", label: "Chất lượng và cải tiến" }]
      : []),
  ];
  const visibleTab = reportTabs.some((tab) => tab.id === activeTab) ? activeTab : reportTabs[0]?.id;
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
    const requests = [
      ["dashboard", canReadAnalytics ? testingApi.dashboard(project._id) : Promise.resolve(null)],
      [
        "coverage",
        canReadCoverage ? testingApi.coverage(project._id, scope) : Promise.resolve(null),
      ],
      [
        "snapshots",
        canReadCoverage ? testingApi.listCoverageSnapshots(project._id) : Promise.resolve([]),
      ],
      [
        "maintenance",
        canReadAnalytics ? testingApi.maintenanceAnalytics(project._id) : Promise.resolve(null),
      ],
      ["ai", canReadAiAnalytics ? testingApi.aiAnalytics(project._id) : Promise.resolve(null)],
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
        canReadAnalytics ? testingApi.projectActivity(project._id) : Promise.resolve([]),
      ],
    ];
    const results = await Promise.allSettled(requests.map(([, request]) => request));
    if (requestGeneration !== loadGeneration.current) return;
    const data = {
      dashboard: null,
      coverage: null,
      snapshots: [],
      maintenance: null,
      ai: null,
      execution: null,
      defects: null,
      activity: [],
    };
    const errors = [];
    results.forEach((result, index) => {
      const [key] = requests[index];
      if (result.status === "fulfilled") data[key] = result.value;
      else if (result.reason?.status !== 403) errors.push(messageOf(result.reason));
    });
    setValue(data);
    setError([...new Set(errors)].join(" · "));
  }, [canReadAiAnalytics, canReadAnalytics, canReadCoverage, canReadReports, project._id, scope]);
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
  return (
    <WorkspacePage title="Báo cáo" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      {reportTabs.length > 1 && (
        <SegmentedTabs
          label="Nhóm báo cáo"
          value={visibleTab}
          onChange={setActiveTab}
          tabs={reportTabs}
        />
      )}
      {visibleTab === "work" && <WorkReportsPanel project={project} />}
      {visibleTab === "reports" && (
        <div className="space-y-6">
          {can("teststatusreport.read") && <TestStatusReportPanel project={project} />}
          {can("testcompletion.read") && <CompletionPage project={project} />}
        </div>
      )}
      {visibleTab === "quality" && (
        <div className="space-y-6">
          {can("qualityevaluation.read") && <ReleaseQualityPanel project={project} />}
          {can("measurement.read") && <MetricDefinitionPanel project={project} />}
          {can("processimprovement.read") && <ProcessImprovementPanel project={project} />}
        </div>
      )}
      {visibleTab === "summary" && (
        <div className="space-y-6">
          {(canReadReports || canReadCoverage) && (canFilterScope || canCreateSnapshot) && (
            <Panel
              title="Phạm vi dữ liệu"
              actions={
                canCreateSnapshot ? (
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
                ) : null
              }
            >
              {canFilterScope && (
                <div className="grid gap-3 p-5 sm:grid-cols-3">
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
            </Panel>
          )}
          {!value && !error ? (
            <LoadingState />
          ) : value ? (
            <>
              {value.coverage && (
                <section aria-labelledby="coverage-metrics-heading" className="space-y-3">
                  <div>
                    <h2 className="text-base font-semibold" id="coverage-metrics-heading">
                      Liên kết yêu cầu và kết quả kiểm thử
                    </h2>
                    <p className="mt-1 text-sm text-ink-muted">
                      Tỷ lệ ca đã chạy tính theo bản phát hành và bản dựng, chưa lọc theo môi
                      trường.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
                    <ReportMetric
                      label="Yêu cầu có liên kết kiểm thử"
                      value={metricPercentage(value.coverage.requirement_coverage)}
                    />
                    <ReportMetric
                      label="Tiêu chí chấp nhận có liên kết"
                      value={metricPercentage(value.coverage.acceptance_criterion_coverage)}
                    />
                    <ReportMetric
                      label="Liên kết còn hiệu lực"
                      value={metricPercentage(value.coverage.fresh_coverage)}
                    />
                    <ReportMetric
                      label="Ca kiểm thử đã chạy"
                      value={metricPercentage(value.coverage.execution_coverage)}
                    />
                    <ReportMetric
                      label="Ca kiểm thử cần cập nhật"
                      value={metricCount(value.coverage.stale_tests)}
                    />
                  </div>
                </section>
              )}
              {(value.execution || value.defects) && (
                <section aria-labelledby="execution-metrics-heading" className="space-y-3">
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
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                    {value.execution && (
                      <ReportMetric
                        label="Kết quả kiểm thử đạt"
                        value={metricRate(value.execution.pass_rate)}
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
                  </div>
                </section>
              )}
              {(value.dashboard || value.defects || value.maintenance || value.ai) && (
                <section aria-labelledby="project-metrics-heading" className="space-y-3">
                  <div>
                    <h2 className="text-base font-semibold" id="project-metrics-heading">
                      Chỉ số toàn dự án
                    </h2>
                  </div>
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
                    {value.dashboard && (
                      <ReportMetric
                        label="Lỗi đang mở"
                        value={metricCount(value.dashboard.open_defects)}
                      />
                    )}
                    {value.defects && (
                      <ReportMetric
                        label="Số lần mở lại lỗi"
                        value={metricCount(value.defects.reopened_count)}
                      />
                    )}
                    {value.maintenance && (
                      <ReportMetric
                        label="Lượt phân tích ảnh hưởng"
                        value={metricCount(value.maintenance.impact_analysis_count)}
                      />
                    )}
                    {value.ai && (
                      <>
                        {(() => {
                          const requests = value.ai.ai_request_metrics || {};
                          const requestCount = Number(requests.request_count || 0);
                          const degradedCount = Number(requests.degraded_count || 0);
                          const degradedRate = requestCount ? degradedCount / requestCount : null;
                          return (
                            <ReportMetric
                              label="Yêu cầu AI cần xem lại hoặc gặp lỗi"
                              value={requestCount ? metricCount(degradedCount) : "Chưa đủ dữ liệu"}
                              detail={
                                degradedRate === null
                                  ? "Chưa ghi nhận lượt yêu cầu AI"
                                  : `${metricRate(degradedRate)} trên ${metricCount(requestCount)} lượt yêu cầu`
                              }
                            />
                          );
                        })()}
                        <ReportMetric
                          label="Thời gian phản hồi AI trung bình"
                          value={
                            value.ai.ai_request_metrics?.average_latency_ms === null ||
                            value.ai.ai_request_metrics?.average_latency_ms === undefined ||
                            !Number.isFinite(
                              Number(value.ai.ai_request_metrics?.average_latency_ms),
                            )
                              ? "Chưa đủ dữ liệu"
                              : `${Math.round(Number(value.ai.ai_request_metrics.average_latency_ms))} ms`
                          }
                        />
                      </>
                    )}
                  </div>
                </section>
              )}
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
                          render: (item) => valueLabel(item.severity),
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
                          render: (item) => metricPercentage(item.coverage),
                        },
                      ]}
                    />
                  </Panel>
                )}
                {value.ai && (
                  <details className="self-start rounded-xl border border-border bg-surface px-5 py-4">
                    <summary className="cursor-pointer font-semibold text-ink">
                      Kết quả AI và phản hồi duyệt
                    </summary>
                    <div className="mt-4 space-y-5">
                      <section>
                        <h3 className="mb-2 text-sm font-medium">Yêu cầu AI theo chức năng</h3>
                        <DataTable
                          items={countRows(value.ai.ai_request_metrics?.by_capability, "request")}
                          empty="Chưa ghi nhận yêu cầu AI"
                          columns={[
                            { key: "label", label: "Chức năng" },
                            { key: "count", label: "Số lượt" },
                          ]}
                        />
                        <p className="mt-2 text-xs text-ink-muted">
                          Thành công:{" "}
                          {metricCount(value.ai.ai_request_metrics?.by_status?.SUCCESS || 0)} · Cần
                          xem lại: {metricCount(value.ai.ai_request_metrics?.degraded_count || 0)}
                          {value.ai.ai_request_metrics?.sample_truncated
                            ? " · Danh sách đang hiển thị tối đa 10.000 lượt gần nhất"
                            : ""}
                        </p>
                      </section>
                      <section>
                        <h3 className="mb-2 text-sm font-medium">Kết quả AI đã lưu</h3>
                        <DataTable
                          items={countRows(value.ai.ai_result_metrics?.by_capability, "result")}
                          empty="Chưa có kết quả AI được lưu"
                          columns={[
                            { key: "label", label: "Chức năng" },
                            { key: "count", label: "Số kết quả" },
                          ]}
                        />
                        <p className="mt-2 text-xs text-ink-muted">
                          Có dẫn chứng nguồn:{" "}
                          {metricCount(value.ai.ai_result_metrics?.grounded_record_count || 0)} ·
                          Chưa có tham chiếu nguồn:{" "}
                          {metricCount(value.ai.ai_result_metrics?.without_evidence_ref_count || 0)}
                          {value.ai.ai_result_metrics?.sample_truncated
                            ? " · Danh sách đang hiển thị tối đa 10.000 kết quả gần nhất"
                            : ""}
                        </p>
                      </section>
                      <section>
                        <h3 className="mb-2 text-sm font-medium">Quyết định duyệt đề xuất</h3>
                        <DataTable
                          items={
                            Array.isArray(value.ai.proposal_status)
                              ? value.ai.proposal_status.map((item) => ({
                                  _id: item._id || item.status,
                                  status: item._id || item.status,
                                  count: item.count,
                                }))
                              : Object.entries(value.ai.proposal_status || {}).map(
                                  ([status, count]) => ({ _id: status, status, count }),
                                )
                          }
                          empty="Chưa có đề xuất được duyệt hoặc từ chối"
                          columns={[
                            {
                              key: "status",
                              label: "Quyết định",
                              render: (item) => valueLabel(item.status),
                            },
                            { key: "count", label: "Số lượng" },
                          ]}
                        />
                        <p className="mt-2 text-xs text-ink-muted">
                          Tỷ lệ được chấp nhận:{" "}
                          {value.ai.proposal_acceptance_rate == null
                            ? "Chưa đủ dữ liệu"
                            : metricRate(value.ai.proposal_acceptance_rate)}{" "}
                          · Đề xuất bị từ chối có ghi lý do:{" "}
                          {metricCount(value.ai.rejection_review_note_recorded_count || 0)} · Chưa
                          ghi lý do:{" "}
                          {metricCount(value.ai.rejection_review_note_missing_count || 0)}
                        </p>
                        <p className="mt-2 text-xs text-ink-muted">
                          Báo cáo chỉ tổng hợp dữ liệu đã lưu. Những quyết định cũ chưa có mã lý do
                          hoặc danh sách trường thay đổi sẽ được giữ là chưa ghi nhận.
                        </p>
                        <div className="mt-4 grid gap-4 xl:grid-cols-2">
                          <div>
                            <h4 className="mb-2 text-sm font-medium">Lý do đã chọn</h4>
                            <DataTable
                              items={Object.entries(
                                value.ai.decision_feedback?.reason_code_counts || {},
                              ).map(([reason, count]) => ({
                                _id: reason,
                                reason,
                                count,
                                label: aiDecisionReasonLabels[reason] || valueLabel(reason),
                              }))}
                              empty="Chưa có mã lý do được ghi nhận"
                              columns={[
                                { key: "label", label: "Lý do" },
                                { key: "count", label: "Số lần" },
                              ]}
                            />
                          </div>
                          <div>
                            <h4 className="mb-2 text-sm font-medium">Nội dung thường được chỉnh</h4>
                            <DataTable
                              items={Object.entries(
                                value.ai.decision_feedback?.changed_field_counts || {},
                              ).map(([field, count]) => ({
                                _id: field,
                                field,
                                count,
                                label: aiChangedFieldLabels[field] || valueLabel(field),
                              }))}
                              empty="Chưa ghi nhận trường được chỉnh"
                              columns={[
                                { key: "label", label: "Nội dung" },
                                { key: "count", label: "Số lần" },
                              ]}
                            />
                          </div>
                        </div>
                        <p className="mt-2 text-xs text-ink-muted">
                          Đã từ chối nhưng chưa chọn lý do:{" "}
                          {metricCount(
                            value.ai.decision_feedback?.decisions_without_reason_code || 0,
                          )}
                          {value.ai.decision_feedback?.sample_truncated
                            ? " · Số liệu dựa trên tối đa 10.000 quyết định gần nhất"
                            : ""}
                        </p>
                      </section>
                      <section>
                        <h3 className="mb-2 text-sm font-medium">
                          Phản hồi với Test Case do AI đề xuất
                        </h3>
                        <p className="mb-3 text-xs text-ink-muted">
                          Chỉ tính ca có nguồn gốc AI. Bản duyệt được so với đề xuất ban đầu; nội
                          dung ghi chú và người duyệt không xuất hiện trong báo cáo này.
                        </p>
                        <div className="grid gap-4 xl:grid-cols-3">
                          <div>
                            <h4 className="mb-2 text-sm font-medium">Quyết định đã duyệt</h4>
                            <DataTable
                              items={Object.entries(
                                value.ai.ai_test_case_feedback?.approved_decision_counts || {},
                              ).map(([decision, count]) => ({
                                _id: decision,
                                decision,
                                count,
                                label: valueLabel(decision),
                              }))}
                              empty="Chưa có Test Case AI được duyệt"
                              columns={[
                                { key: "label", label: "Kết quả" },
                                { key: "count", label: "Số lượng" },
                              ]}
                            />
                          </div>
                          <div>
                            <h4 className="mb-2 text-sm font-medium">Lý do yêu cầu chỉnh sửa</h4>
                            <DataTable
                              items={Object.entries(
                                value.ai.ai_test_case_feedback?.changes_requested_reason_counts ||
                                  {},
                              ).map(([reason, count]) => ({
                                _id: reason,
                                reason,
                                count,
                                label: aiDecisionReasonLabels[reason] || valueLabel(reason),
                              }))}
                              empty="Chưa có lý do được ghi nhận"
                              columns={[
                                { key: "label", label: "Lý do" },
                                { key: "count", label: "Số lần" },
                              ]}
                            />
                          </div>
                          <div>
                            <h4 className="mb-2 text-sm font-medium">Trường thường được chỉnh</h4>
                            <DataTable
                              items={Object.entries(
                                value.ai.ai_test_case_feedback?.changed_field_counts || {},
                              ).map(([field, count]) => ({
                                _id: field,
                                field,
                                count,
                                label: aiChangedFieldLabels[field] || valueLabel(field),
                              }))}
                              empty="Chưa ghi nhận trường được chỉnh"
                              columns={[
                                { key: "label", label: "Nội dung" },
                                { key: "count", label: "Số lần" },
                              ]}
                            />
                          </div>
                        </div>
                        <p className="mt-3 text-xs text-ink-muted">
                          Đề xuất đã tạo:{" "}
                          {metricCount(value.ai.ai_test_case_feedback?.generated_draft_count || 0)}{" "}
                          · Yêu cầu chỉnh sửa:{" "}
                          {metricCount(
                            value.ai.ai_test_case_feedback?.changes_requested_count || 0,
                          )}{" "}
                          · Phiên bản AI đã duyệt trong báo cáo:{" "}
                          {metricCount(
                            Object.values(
                              value.ai.ai_test_case_feedback?.approved_decision_counts || {},
                            ).reduce((total, count) => total + Number(count || 0), 0),
                          )}
                          {value.ai.ai_test_case_feedback?.generated_draft_sample_truncated ||
                          value.ai.ai_test_case_feedback?.changes_requested_sample_truncated ||
                          value.ai.ai_test_case_feedback?.approved_version_sample_truncated
                            ? " · Một hoặc nhiều danh sách được giới hạn ở 10.000 bản ghi gần nhất"
                            : ""}
                        </p>
                      </section>
                    </div>
                  </details>
                )}
              </div>
              {value.coverage && (
                <Panel title="Mốc độ phủ">
                  <DataTable
                    items={value.snapshots}
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
                        render: (item) => metricPercentage(item.metrics?.requirement_coverage),
                      },
                      {
                        key: "fresh_coverage",
                        label: "Liên kết còn hiệu lực",
                        render: (item) => metricPercentage(item.metrics?.fresh_coverage),
                      },
                      {
                        key: "execution_coverage",
                        label: "Ca kiểm thử đã chạy",
                        render: (item) => metricPercentage(item.metrics?.execution_coverage),
                      },
                    ]}
                  />
                </Panel>
              )}
              {value.activity && (
                <Panel title="Hoạt động toàn dự án">
                  <div
                    className="max-h-[34rem] overflow-auto overscroll-contain"
                    role="region"
                    aria-label="Danh sách hoạt động chất lượng"
                    tabIndex={0}
                  >
                    <DataTable
                      items={value.activity.filter(
                        (item) => item.action !== "project_membership_required",
                      )}
                      empty="Chưa có hoạt động"
                      columns={[
                        {
                          key: "action",
                          label: "Hành động",
                          render: (item) => valueLabel(item.action),
                        },
                        {
                          key: "entity_type",
                          label: "Loại dữ liệu",
                          render: (item) => valueLabel(item.entity_type),
                        },
                        {
                          key: "entity_id",
                          label: "Đối tượng",
                          render: (item) =>
                            item.entity_key ||
                            item.entity_name ||
                            item.entity_title ||
                            valueLabel(item.entity_type) ||
                            "—",
                        },
                        {
                          key: "created_at",
                          label: "Thời điểm",
                          render: (item) => formatDate(item.created_at),
                        },
                      ]}
                    />
                  </div>
                </Panel>
              )}
            </>
          ) : null}
        </div>
      )}
      {dialog}
    </WorkspacePage>
  );
}
