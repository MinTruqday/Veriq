"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
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
        setReleases(releaseValues);
        setBuilds(buildValues);
        setEnvironments(environmentValues);
      })
      .catch((reason) => setError(messageOf(reason)));
  }, [permissions, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
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
      <div className="space-y-6" hidden={visibleTab !== "reports"}>
        {can("teststatusreport.read") && <TestStatusReportPanel project={project} />}
        {can("testcompletion.read") && <CompletionPage project={project} />}
      </div>
      <div className="space-y-6" hidden={visibleTab !== "quality"}>
        {can("qualityevaluation.read") && <ReleaseQualityPanel project={project} />}
        {can("measurement.read") && <MetricDefinitionPanel project={project} />}
        {can("processimprovement.read") && <ProcessImprovementPanel project={project} />}
      </div>
      <div className="space-y-6" hidden={visibleTab !== "summary"}>
        {(canReadReports || canReadCoverage) && (canFilterScope || canCreateSnapshot) && (
          <Panel
            title="Phạm vi dữ liệu"
            actions={
              canCreateSnapshot ? (
                <button
                  className="apple-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Lưu ảnh chụp độ phủ",
                      description: `Phạm vi lưu: ${scope.release || "mọi bản phát hành"} · ${scope.build || "mọi bản dựng"}`,
                      confirmLabel: "Lưu ảnh chụp",
                      fields: [
                        { name: "label", label: "Tên ảnh chụp", required: true, autoFocus: true },
                      ],
                    });
                    if (!answer) return;
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
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Lưu ảnh chụp
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
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              {value.coverage && (
                <>
                  <Metric
                    label="Độ phủ yêu cầu"
                    value={`${value.coverage.requirement_coverage}%`}
                  />
                  <Metric
                    label="Độ phủ tiêu chí chấp nhận"
                    value={`${value.coverage.acceptance_criterion_coverage}%`}
                  />
                  <Metric label="Độ phủ còn hiệu lực" value={`${value.coverage.fresh_coverage}%`} />
                  <Metric label="Độ phủ thực thi" value={`${value.coverage.execution_coverage}%`} />
                  <Metric label="Ca kiểm thử cần cập nhật" value={value.coverage.stale_tests} />
                </>
              )}
              {value.dashboard && (
                <Metric label="Lỗi đang mở" value={value.dashboard.open_defects} />
              )}
              {value.execution && (
                <Metric
                  label="Tỷ lệ kết quả kiểm thử đạt"
                  value={
                    value.execution.pass_rate === null
                      ? "Chưa đủ dữ liệu"
                      : `${Math.round(value.execution.pass_rate * 100)}%`
                  }
                  detail={
                    value.execution.terminal_result_count
                      ? `${value.execution.result_counts?.PASS || 0} trên ${value.execution.terminal_result_count} kết quả đã kết thúc`
                      : "Chưa có kết quả đã kết thúc"
                  }
                />
              )}
              {value.defects && (
                <>
                  <Metric label="Số lần mở lại lỗi" value={value.defects.reopened_count} />
                  <Metric
                    label="Tuổi trung bình lỗi mở"
                    value={`${value.defects.average_open_age_days} ngày`}
                  />
                </>
              )}
              {value.maintenance && (
                <Metric
                  label="Phân tích ảnh hưởng"
                  value={value.maintenance.impact_analysis_count}
                />
              )}
              {value.ai && (
                <Metric
                  label="Tỷ lệ đề xuất được chấp nhận"
                  value={
                    value.ai.proposal_acceptance_rate === null
                      ? "Chưa đủ dữ liệu"
                      : `${Math.round(value.ai.proposal_acceptance_rate * 100)}%`
                  }
                />
              )}
              {value.ai && (
                <Metric label="Số lần điều chỉnh kết quả AI" value={value.ai.override_count} />
              )}
              {value.ai && (
                <Metric
                  label="Tỷ lệ AI chạy suy giảm"
                  value={`${Math.round(value.ai.degraded_rate * 100)}%`}
                />
              )}
              {value.ai && (
                <Metric
                  label="Độ trễ AI trung bình"
                  value={`${Math.round(value.ai.average_latency_ms)} mili giây`}
                />
              )}
            </div>
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
                      { key: "coverage", label: "Độ phủ", render: (item) => `${item.coverage}%` },
                    ]}
                  />
                </Panel>
              )}
              {value.ai && (
                <Panel title="Trạng thái đề xuất AI">
                  <DataTable
                    items={(value.ai.proposal_status || []).map((item) => ({
                      ...item,
                      status: item._id,
                    }))}
                    empty="Chưa có đề xuất"
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
              {value.ai && (
                <Panel title="Phiên bản mô hình AI">
                  <DataTable
                    items={Object.entries(value.ai.model_versions || {}).map(([model, count]) => ({
                      _id: model,
                      model,
                      count,
                    }))}
                    empty="Chưa có lần chạy AI"
                    columns={[
                      { key: "model", label: "Mô hình" },
                      { key: "count", label: "Số lần chạy" },
                    ]}
                  />
                </Panel>
              )}
            </div>
            {value.coverage && (
              <Panel title="Ảnh chụp độ phủ">
                <DataTable
                  items={value.snapshots}
                  empty="Chưa lưu ảnh chụp"
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
                      render: (item) => `${item.metrics?.requirement_coverage ?? 0}%`,
                    },
                    {
                      key: "fresh_coverage",
                      label: "Độ phủ còn hiệu lực",
                      render: (item) => `${item.metrics?.fresh_coverage ?? 0}%`,
                    },
                    {
                      key: "execution_coverage",
                      label: "Độ phủ thực thi",
                      render: (item) => `${item.metrics?.execution_coverage ?? 0}%`,
                    },
                  ]}
                />
              </Panel>
            )}
            {value.activity && (
              <Panel title="Hoạt động chất lượng gần đây">
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
                      { key: "entity_id", label: "Mã" },
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
      {dialog}
    </WorkspacePage>
  );
}
