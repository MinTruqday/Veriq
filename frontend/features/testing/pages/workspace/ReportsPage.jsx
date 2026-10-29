"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
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
    ...(canReadAnalytics || canReadCoverage || canReadReports
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
                      Độ phủ truy vết và thực thi
                    </h2>
                    <p className="mt-1 text-sm text-ink-muted">
                      Các chỉ số thể hiện phạm vi yêu cầu, tiêu chí, hiệu lực và kỹ thuật kiểm thử.
                      Độ phủ thực thi được lọc theo bản phát hành và bản dựng; bộ lọc môi trường
                      chưa áp dụng cho chỉ số này.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                    <Metric
                      label="Yêu cầu được bao phủ"
                      value={metricPercentage(value.coverage.requirement_coverage)}
                    />
                    <Metric
                      label="Tiêu chí chấp nhận được bao phủ"
                      value={metricPercentage(value.coverage.acceptance_criterion_coverage)}
                    />
                    <Metric
                      label="Độ phủ còn hiệu lực"
                      value={metricPercentage(value.coverage.fresh_coverage)}
                    />
                    <Metric
                      label="Độ phủ thực thi"
                      value={metricPercentage(value.coverage.execution_coverage)}
                    />
                    <Metric
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
                      <Metric
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
                        <Metric
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
                    <p className="mt-1 text-sm text-ink-muted">
                      Những số liệu dưới đây không bị giới hạn bởi bộ lọc phạm vi ở trên.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                    {value.dashboard && (
                      <Metric
                        label="Lỗi đang mở"
                        value={metricCount(value.dashboard.open_defects)}
                      />
                    )}
                    {value.defects && (
                      <Metric
                        label="Số lần mở lại lỗi"
                        value={metricCount(value.defects.reopened_count)}
                      />
                    )}
                    {value.maintenance && (
                      <Metric
                        label="Lượt phân tích ảnh hưởng"
                        value={metricCount(value.maintenance.impact_analysis_count)}
                      />
                    )}
                    {value.ai && (
                      <>
                        <Metric
                          label="Lượt AI không hoàn tất bình thường"
                          value={metricCount(value.ai.degraded_count)}
                          detail={
                            value.ai.degraded_rate === null || value.ai.degraded_rate === undefined
                              ? "Chưa đủ dữ liệu để tính tỷ lệ"
                              : `${metricRate(value.ai.degraded_rate)} số lượt có dữ liệu AI`
                          }
                        />
                        <Metric
                          label="Thời gian phản hồi AI trung bình"
                          value={
                            value.ai.average_latency_ms === null ||
                            value.ai.average_latency_ms === undefined ||
                            !Number.isFinite(Number(value.ai.average_latency_ms))
                              ? "Chưa đủ dữ liệu"
                              : `${Math.round(Number(value.ai.average_latency_ms))} ms`
                          }
                        />
                      </>
                    )}
                  </div>
                </section>
              )}
              <div className="grid gap-5 xl:grid-cols-2">
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
              <div className="grid gap-5 xl:grid-cols-2">
                {value.coverage && (
                  <Panel title="Độ phủ theo kỹ thuật">
                    <DataTable
                      items={Object.entries(value.coverage.category_coverage || {}).map(
                        ([category, coverage]) => ({ _id: category, category, coverage }),
                      )}
                      empty="Chưa có dữ liệu kỹ thuật"
                      columns={[
                        {
                          key: "category",
                          label: "Kỹ thuật",
                          render: (item) => valueLabel(item.category),
                        },
                        {
                          key: "coverage",
                          label: "Độ phủ",
                          render: (item) => metricPercentage(item.coverage),
                        },
                      ]}
                    />
                  </Panel>
                )}
                {value.ai && (
                  <Panel title="Hoạt động AI">
                    <DataTable
                      items={Object.entries(value.ai.model_versions || {}).map(
                        ([model, count]) => ({
                          _id: model,
                          model,
                          count,
                        }),
                      )}
                      empty="Chưa có lần chạy AI"
                      columns={[
                        { key: "model", label: "Phiên bản mô hình" },
                        { key: "count", label: "Lượt sử dụng" },
                      ]}
                    />
                  </Panel>
                )}
              </div>
              {value.coverage && (
                <Panel title="Mốc độ phủ">
                  <p className="px-5 pt-4 text-sm text-ink-muted">
                    Mỗi mốc lưu riêng các chỉ số và phạm vi tại thời điểm ghi nhận.
                  </p>
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
                        label: "Độ phủ yêu cầu",
                        render: (item) => metricPercentage(item.metrics?.requirement_coverage),
                      },
                      {
                        key: "fresh_coverage",
                        label: "Độ phủ còn hiệu lực",
                        render: (item) => metricPercentage(item.metrics?.fresh_coverage),
                      },
                      {
                        key: "execution_coverage",
                        label: "Độ phủ thực thi",
                        render: (item) => metricPercentage(item.metrics?.execution_coverage),
                      },
                    ]}
                  />
                </Panel>
              )}
              {value.activity && (
                <Panel title="Hoạt động chất lượng gần đây">
                  <p className="px-5 pt-4 text-sm text-ink-muted">
                    Nhật ký hoạt động của toàn dự án, không chịu ảnh hưởng của bộ lọc báo cáo.
                  </p>
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
                            "Không có tên hiển thị",
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
