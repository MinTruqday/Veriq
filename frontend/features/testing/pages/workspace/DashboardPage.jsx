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
  const [taskSummary, setTaskSummary] = useState(project.task_summary);
  const permissions = project.current_permissions || [];
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadAutomationRuns = can("proposal.read") || can("automation.read");
  useEffect(() => {
    let active = true;
    const requests = [];
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
  }, [canReadAnalytics, canReadCoverage, project._id]);
  const base = `/du-an/${project._id}`;
  const navigationCards = [
    ["lap-ke-hoach/backlog", "Lập kế hoạch", "project.read"],
    ["yeu-cau", "Làm rõ yêu cầu", "requirement.read"],
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
    can("requirement.read") ||
    can("testcase.read") ||
    can("defect.read") ||
    (can("coverage.read") && Boolean(coverage));
  const hasQualityMetrics =
    can("testcase.read") ||
    (can("coverage.read") && Boolean(coverage)) ||
    can("testrun.read") ||
    can("impact.read");
  return (
    <WorkspacePage title={project.name} description={projectOverviewDescription(project)}>
      {error && <ErrorState message={error} />}
      {loading ? (
        <LoadingState />
      ) : (
        <>
          <Panel title="Tiến độ dự án">
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
                      {taskProgress.completed} hoàn thành
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
          {dashboard && hasOverviewMetrics && (
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              {can("requirement.read") && <Metric label="Yêu cầu" value={dashboard.requirements} />}
              {can("testcase.read") && (
                <Metric label="Kiểm thử đang hoạt động" value={dashboard.active_tests} />
              )}
              {can("defect.read") && <Metric label="Lỗi đang mở" value={dashboard.open_defects} />}
              {can("coverage.read") && coverage && (
                <Metric label="Độ phủ yêu cầu" value={`${coverage.requirement_coverage}%`} />
              )}
            </div>
          )}
          {dashboard && hasQualityMetrics && (
            <details className="rounded-panel border border-border bg-surface p-4 shadow-sm">
              <summary className="cursor-pointer text-sm font-medium">
                Chỉ số chất lượng chi tiết
              </summary>
              <div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
                {can("testcase.read") && (
                  <Metric label="Kiểm thử cần cập nhật" value={dashboard.tests_needing_update} />
                )}
                {can("coverage.read") && coverage && (
                  <>
                    <Metric
                      label="Độ phủ tiêu chí chấp nhận"
                      value={`${coverage.acceptance_criterion_coverage}%`}
                    />
                    <Metric label="Độ phủ còn hiệu lực" value={`${coverage.fresh_coverage}%`} />
                    <Metric label="Độ phủ thực thi" value={`${coverage.execution_coverage}%`} />
                  </>
                )}
                {can("testrun.read") && (
                  <Metric label="Lần chạy hiện tại" value={dashboard.current_runs} />
                )}
                {can("impact.read") && (
                  <Metric label="Thay đổi chờ rà soát" value={dashboard.changes_waiting_impact} />
                )}
              </div>
            </details>
          )}
          {(navigationCards.length > 0 || can("knowledge.read")) && (
            <div className="grid gap-4 lg:grid-cols-3">
              {navigationCards.length > 0 && (
                <Panel title="Đi tới công việc" className="lg:col-span-2">
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
              {can("knowledge.read") && (
                <Panel title="Tài liệu và nguồn">
                  <div className="space-y-3 p-5">
                    <p className="text-sm leading-6 text-ink-muted">
                      Chỉ tài liệu được cấp quyền mới được dùng làm nguồn dẫn hoặc cho phép AI đọc
                    </p>
                    <Link className="apple-button w-full" href={`${base}/tri-thuc`}>
                      Mở tài liệu tham chiếu
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
                  <div className="grid grid-cols-2 gap-3 p-5 md:grid-cols-3 xl:grid-cols-5">
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
                empty="Chưa có bộ thay đổi"
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
