"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import AgentRunPanel from "../../components/AgentRunPanel";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  WorkspacePage,
  StatusPill,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import { formatProjectDate } from "../../lib/projectSchedule.logic.mjs";
import { taskProgressPresentation } from "../../lib/projectProgress.logic.mjs";

function projectOverviewDescription(project) {
  const start = project.planned_start_at ? formatProjectDate(project.planned_start_at) : null;
  const end = project.planned_end_at ? formatProjectDate(project.planned_end_at) : null;
  if (start && end) return `${start} – ${end}`;
  if (start) return `Từ ${start}`;
  if (end) return `Đến ${end}`;
  return "";
}

export default function DashboardPage({ project }) {
  const [value, setValue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [taskSummary, setTaskSummary] = useState(project.task_summary);
  const permissions = project.current_permissions || [];
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadAutomationRuns = can("proposal.read") || can("automation.read");
  const canReadKnowledge = can("knowledge.read");
  useEffect(() => {
    let active = true;
    const requests = [];
    setLoading(true);
    setError("");
    if (canReadAnalytics) {
      requests.push(["dashboard", testingApi.dashboard(project._id)]);
    }
    if (canReadCoverage) {
      requests.push(["coverage", testingApi.coverage(project._id)]);
    }
    requests.push(["project", testingApi.getProject(project._id)]);
    Promise.allSettled(requests.map(([, request]) => request))
      .then((results) => {
        if (!active) return;
        const data = {};
        results.forEach((result, index) => {
          const [key] = requests[index];
          if (result.status === "fulfilled") data[key] = result.value;
          else if (result.reason?.status !== 403) setError(messageOf(result.reason));
        });
        const currentProject = data.project;
        setValue({ dashboard: data.dashboard || null, coverage: data.coverage || null });
        if (!currentProject) return;
        setTaskSummary(currentProject.task_summary);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [canReadAnalytics, canReadCoverage, project._id, reloadVersion]);
  const base = `/du-an/${project._id}`;
  const navigationCards = [
    ["lap-ke-hoach/backlog", "Lập kế hoạch", "project.read"],
    ["yeu-cau", "Yêu cầu", "requirement.read"],
    ["ho-so-dam-bao", "Hồ sơ đảm bảo", "requirement.read", "testcase.read"],
    ["ca-kiem-thu", "Thiết kế kiểm thử", "testcase.read"],
    ["ke-hoach-kiem-thu", "Lập kế hoạch kiểm thử", "testplan.read"],
    ["lan-chay-kiem-thu", "Thực thi kiểm thử", "testrun.read"],
    ["loi", "Xử lý lỗi", "defect.read"],
    ["ban-phat-hanh", "Quyết định phát hành", "release.read"],
  ].filter(
    ([, , permission, secondPermission]) =>
      can(permission) && (!secondPermission || can(secondPermission)),
  );
  const dashboard = value?.dashboard;
  const coverage = value?.coverage;
  const taskProgress = taskProgressPresentation(taskSummary);
  const hasOverviewMetrics =
    Boolean(dashboard && (can("requirement.read") || can("testcase.read") || can("defect.read"))) ||
    Boolean(can("coverage.read") && coverage?.requirement_coverage != null);
  const hasDetailedCoverage =
    can("coverage.read") &&
    [
      coverage?.acceptance_criterion_coverage,
      coverage?.fresh_coverage,
      coverage?.execution_coverage,
    ].some((metric) => metric != null);
  const hasQualityMetrics =
    Boolean(dashboard && (can("testcase.read") || can("testrun.read") || can("impact.read"))) ||
    hasDetailedCoverage;
  return (
    <WorkspacePage title={project.name} description={projectOverviewDescription(project)}>
      {error && (
        <div className="space-y-3">
          <ErrorState message={error} />
          <button
            className="secondary-button"
            disabled={loading}
            onClick={() => setReloadVersion((current) => current + 1)}
            type="button"
          >
            {loading ? "Đang tải lại" : "Tải lại dữ liệu"}
          </button>
        </div>
      )}
      {loading ? (
        <LoadingState />
      ) : (
        <>
          <Panel title="Tiến độ công việc">
            <div className="grid gap-5 p-5">
              <div>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span>
                    {taskProgress.completionPercent == null
                      ? taskProgress.label
                      : `Hoàn thành ${taskProgress.completionPercent}%`}
                  </span>
                  {taskProgress.applicableTotal > 0 && taskProgress.completed != null && (
                    <span className="shrink-0 text-ink-muted">
                      {taskProgress.completed}/{taskProgress.applicableTotal} công việc
                    </span>
                  )}
                </div>
                {taskProgress.completionPercent != null && (
                  <div
                    aria-label="Tiến độ công việc được tính từ công việc chưa hủy"
                    aria-valuemax={100}
                    aria-valuemin={0}
                    aria-valuenow={taskProgress.completionPercent}
                    className="mt-3 h-2 overflow-hidden rounded-full bg-surface-quiet"
                    role="progressbar"
                  >
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${taskProgress.completionPercent}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </Panel>
          {canReadAutomationRuns && <AgentRunPanel project={project} showDefinitions={false} />}
          {(dashboard || coverage) && hasOverviewMetrics && (
            <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,220px),1fr))] gap-3">
              {can("requirement.read") && dashboard && (
                <Metric label="Yêu cầu" value={dashboard.requirements} />
              )}
              {can("testcase.read") && dashboard && (
                <Metric label="Ca kiểm thử đang hoạt động" value={dashboard.active_tests} />
              )}
              {can("defect.read") && dashboard && (
                <Metric label="Lỗi đang mở" value={dashboard.open_defects} />
              )}
              {can("coverage.read") && coverage?.requirement_coverage != null && (
                <Metric
                  label="Yêu cầu có liên kết kiểm thử"
                  value={`${coverage.requirement_coverage}%`}
                />
              )}
            </div>
          )}
          {(dashboard || coverage) && hasQualityMetrics && (
            <details className="rounded-panel border border-border bg-surface p-4 shadow-sm">
              <summary className="cursor-pointer text-sm font-medium">
                Số liệu kiểm thử chi tiết
              </summary>
              <div className="mt-4 grid grid-cols-[repeat(auto-fill,minmax(min(100%,220px),1fr))] gap-3">
                {can("testcase.read") && dashboard && (
                  <Metric label="Ca kiểm thử cần rà soát" value={dashboard.tests_needing_update} />
                )}
                {can("coverage.read") && coverage && (
                  <>
                    {coverage.acceptance_criterion_coverage != null && (
                      <Metric
                        label="Tiêu chí chấp nhận có liên kết kiểm thử"
                        value={`${coverage.acceptance_criterion_coverage}%`}
                      />
                    )}
                    {coverage.fresh_coverage != null && (
                      <Metric
                        label="Yêu cầu có liên kết kiểm thử còn hiệu lực"
                        value={`${coverage.fresh_coverage}%`}
                      />
                    )}
                    {coverage.execution_coverage != null && (
                      <Metric
                        label="Phạm vi đã có kết quả thực thi"
                        value={`${coverage.execution_coverage}%`}
                      />
                    )}
                  </>
                )}
                {can("testrun.read") && dashboard && (
                  <Metric label="Tác vụ AI đang xử lý" value={dashboard.current_runs} />
                )}
                {can("impact.read") && dashboard && (
                  <Metric label="Thay đổi chờ rà soát" value={dashboard.changes_waiting_impact} />
                )}
              </div>
            </details>
          )}
          {(navigationCards.length > 0 || canReadKnowledge) && (
            <div
              className={`grid gap-4 ${navigationCards.length > 0 && canReadKnowledge ? "lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]" : ""}`}
            >
              {navigationCards.length > 0 && (
                <Panel title="Đi tới công việc">
                  <div className="grid gap-3 p-5 sm:grid-cols-2">
                    {navigationCards.map(([href, label]) => (
                      <Link
                        className="group rounded-control border border-border p-4 transition hover:border-brand hover:bg-brand-soft"
                        href={`${base}/${href}`}
                        key={href}
                      >
                        <p className="text-[13px] font-semibold group-hover:text-brand">{label}</p>
                      </Link>
                    ))}
                  </div>
                </Panel>
              )}
              {canReadKnowledge && (
                <Panel title="Tài liệu và nguồn">
                  <div className="p-5">
                    <Link className="apple-button w-full" href={`${base}/tri-thuc`}>
                      Mở tài liệu và nguồn
                    </Link>
                  </div>
                </Panel>
              )}
            </div>
          )}
          {dashboard && can("defect.read") && can("testrun.read") && (
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Lỗi đang mở theo mức độ">
                {Object.keys(dashboard.open_defects_by_severity || {}).length > 0 ? (
                  <div className="grid grid-cols-2 gap-3 p-5 xl:grid-cols-3">
                    {Object.entries(dashboard.open_defects_by_severity).map(([severity, count]) => (
                      <div
                        className="min-w-0 rounded-xl border border-border p-3 xl:p-4"
                        key={severity}
                      >
                        <p className="break-words text-[11px] leading-4 text-ink-muted">
                          {valueLabel(severity)}
                        </p>
                        <p className="mt-1 text-xl font-semibold">{count}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="p-5 text-[13px] text-ink-muted">Chưa có dữ liệu mức độ lỗi</p>
                )}
              </Panel>
              <Panel title="Lần chạy mới nhất">
                {dashboard.latest_run ? (
                  <div className="space-y-3 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <Link
                        className="font-semibold text-brand"
                        href={`${base}/thuc-thi/${dashboard.latest_run._id}`}
                      >
                        {dashboard.latest_run.name}
                      </Link>
                      <StatusPill value={dashboard.latest_run.status} />
                    </div>
                    <p className="text-[12px] text-ink-muted">
                      Bản dựng {dashboard.latest_run.build || "Chưa đặt"} tại{" "}
                      {dashboard.latest_run.environment || "Chưa đặt"}
                    </p>
                    <div className="flex flex-wrap gap-3 text-[12px]">
                      {Object.entries(dashboard.latest_run.result_counts || {}).map(
                        ([status, count]) => (
                          <span
                            className="rounded-full border border-border px-3 py-1"
                            key={status}
                          >
                            {valueLabel(status)} {count}
                          </span>
                        ),
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="p-5 text-[13px] text-ink-muted">Chưa có lần chạy</p>
                )}
              </Panel>
            </div>
          )}
          {dashboard && can("requirement.read") && can("impact.read") && (
            <Panel title="Thay đổi gần đây">
              <DataTable
                items={dashboard.recent_changes}
                empty="Chưa có thay đổi yêu cầu gần đây"
                columns={[
                  { key: "requirement_label", label: "Yêu cầu" },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                  {
                    key: "created_at",
                    label: "Tạo lúc",
                    render: (item) => formatDate(item.created_at),
                  },
                ]}
              />
            </Panel>
          )}
        </>
      )}
    </WorkspacePage>
  );
}
