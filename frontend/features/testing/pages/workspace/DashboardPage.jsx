"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import AgentRunPanel from "../../components/AgentRunPanel";
import ProjectComplexityAssessmentPanel from "../../components/ProjectComplexityAssessmentPanel";
import ProjectCompletenessReviewPanel from "../../components/ProjectCompletenessReviewPanel";
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

function latestRunLabel(run) {
  const name = String(run?.name || "").trim();
  const containsInternalCode = /\b[A-Z][A-Z0-9]*(?:_+[A-Z0-9]+)+\b/.test(name);
  return name && !containsInternalCode ? name : "Lần chạy kiểm thử";
}

function latestRunContext(run) {
  const details = [];
  if (run?.build) details.push(`Bản dựng ${run.build}`);
  if (run?.environment) details.push(`Môi trường ${valueLabel(run.environment)}`);
  if (run?.created_at) details.push(formatDate(run.created_at));
  return details.join(" · ");
}

function formatCoveragePercent(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? `${Math.round(numericValue)}%` : "—";
}

export default function DashboardPage({ project }) {
  const { user } = useAuth();
  const [value, setValue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [taskSummary, setTaskSummary] = useState(project.task_summary);
  const [showAiReview, setShowAiReview] = useState(false);
  const permissions = project.current_permissions || [];
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadAgentRuns = can("proposal.read") || can("automation.read");
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
  const openDefectSeverities = Object.entries(dashboard?.open_defects_by_severity || {}).filter(
    ([, count]) => Number(count) > 0,
  );
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
        <LoadingState label="Đang tải tổng quan dự án" variant="dashboard" />
      ) : (
        <>
          <Panel title="Tiến độ và số liệu chính">
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
              {(dashboard || coverage) && hasOverviewMetrics && (
                <dl className="grid gap-x-5 gap-y-4 border-t border-border pt-4 sm:grid-cols-2 xl:grid-cols-4">
                  {can("requirement.read") && dashboard && (
                    <div className="min-w-0">
                      <dt className="text-[12px] leading-5 text-ink-muted">Yêu cầu đã duyệt</dt>
                      <dd className="mt-1 text-[24px] font-semibold leading-7 tabular-nums text-ink">
                        {dashboard.requirements}
                      </dd>
                    </div>
                  )}
                  {can("testcase.read") && dashboard && (
                    <div className="min-w-0">
                      <dt className="text-[12px] leading-5 text-ink-muted">
                        Ca kiểm thử đang hoạt động
                      </dt>
                      <dd className="mt-1 text-[24px] font-semibold leading-7 tabular-nums text-ink">
                        {dashboard.active_tests}
                      </dd>
                    </div>
                  )}
                  {can("defect.read") && dashboard && (
                    <div className="min-w-0">
                      <dt className="text-[12px] leading-5 text-ink-muted">Lỗi đang mở</dt>
                      <dd className="mt-1 text-[24px] font-semibold leading-7 tabular-nums text-ink">
                        {dashboard.open_defects}
                      </dd>
                    </div>
                  )}
                  {can("coverage.read") && coverage?.requirement_coverage != null && (
                    <div className="min-w-0">
                      <dt className="text-[12px] leading-5 text-ink-muted">
                        Yêu cầu có liên kết kiểm thử
                      </dt>
                      <dd className="mt-1 text-[24px] font-semibold leading-7 tabular-nums text-ink">
                        {formatCoveragePercent(coverage.requirement_coverage)}
                      </dd>
                    </div>
                  )}
                </dl>
              )}
            </div>
          </Panel>
          {project.current_permissions?.includes("ai.ask_project") && (
            <details onToggle={(event) => setShowAiReview(event.currentTarget.open)}>
              <summary className="cursor-pointer border-y border-border py-3 text-sm font-medium">
                Đánh giá và rà soát bằng AI
              </summary>
              {showAiReview && (
                <div className="mt-3 grid gap-3">
                  <ProjectComplexityAssessmentPanel project={project} />
                  <ProjectCompletenessReviewPanel project={project} user={user} />
                </div>
              )}
            </details>
          )}
          {(dashboard || coverage) && hasQualityMetrics && (
            <details className="border-y border-border">
              <summary className="cursor-pointer py-3 text-sm font-medium">
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
                  <Metric label="Lượt chạy kiểm thử chưa kết thúc" value={dashboard.current_runs} />
                )}
                {can("impact.read") && dashboard && (
                  <Metric label="Thay đổi chờ rà soát" value={dashboard.changes_waiting_impact} />
                )}
              </div>
            </details>
          )}
          <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(19rem,1fr)]">
            <div className="grid min-w-0 content-start gap-5">
              {canReadAgentRuns && <AgentRunPanel project={project} compact />}
              {dashboard && can("requirement.read") && can("impact.read") && (
                <Panel title="Thay đổi gần đây">
                  {dashboard.recent_changes?.length > 0 ? (
                    <DataTable
                      items={dashboard.recent_changes}
                      columns={[
                        { key: "requirement_label", label: "Yêu cầu" },
                        {
                          key: "status",
                          label: "Trạng thái",
                          render: (item) => <StatusPill value={item.status} />,
                        },
                        {
                          key: "created_at",
                          label: "Cập nhật lúc",
                          render: (item) => formatDate(item.created_at),
                        },
                      ]}
                    />
                  ) : (
                    <p className="px-5 py-4 text-[13px] text-ink-muted">
                      Chưa có thay đổi yêu cầu gần đây
                    </p>
                  )}
                </Panel>
              )}
            </div>
            <div className="grid min-w-0 content-start gap-5">
              {dashboard && can("defect.read") && (
                <Panel title="Lỗi đang mở theo mức độ">
                  {openDefectSeverities.length > 0 ? (
                    <div className="divide-y divide-border px-5">
                      {openDefectSeverities.map(([severity, count]) => (
                        <div
                          className="flex min-w-0 items-center justify-between gap-4 py-3"
                          key={severity}
                        >
                          <p className="min-w-0 break-words text-[13px] text-ink-muted">
                            {valueLabel(severity)}
                          </p>
                          <p className="shrink-0 text-lg font-semibold tabular-nums">{count}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="p-5 text-[13px] text-ink-muted">Không có lỗi đang mở</p>
                  )}
                </Panel>
              )}
              {dashboard && can("testrun.read") && (
                <Panel title="Lần chạy mới nhất">
                  {dashboard.latest_run ? (
                    <div className="space-y-3 p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <Link
                          className="font-semibold text-brand"
                          href={`${base}/thuc-thi/${dashboard.latest_run._id}`}
                        >
                          {latestRunLabel(dashboard.latest_run)}
                        </Link>
                        <StatusPill value={dashboard.latest_run.status} />
                      </div>
                      {latestRunContext(dashboard.latest_run) && (
                        <p className="text-[12px] text-ink-muted">
                          {latestRunContext(dashboard.latest_run)}
                        </p>
                      )}
                      <div className="flex flex-wrap gap-2 text-[12px]">
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
              )}
            </div>
          </div>
          {(navigationCards.length > 0 || canReadKnowledge) && (
            <section aria-labelledby="project-areas-heading" className="min-w-0">
              <h2 className="mb-2 text-sm font-semibold text-ink" id="project-areas-heading">
                Khu vực dự án
              </h2>
              <nav
                aria-label="Khu vực dự án"
                className="grid grid-cols-1 gap-x-8 sm:grid-cols-2 xl:grid-cols-4"
              >
                {navigationCards.map(([href, label]) => (
                  <Link
                    className="flex min-h-10 min-w-0 items-center justify-between gap-3 border-b border-border/70 py-2 text-[13px] font-medium text-ink transition-colors hover:text-brand"
                    href={`${base}/${href}`}
                    key={href}
                  >
                    <span className="min-w-0 break-words">{label}</span>
                    <span aria-hidden="true" className="shrink-0 text-ink-muted">
                      ›
                    </span>
                  </Link>
                ))}
                {canReadKnowledge && (
                  <Link
                    className="flex min-h-10 min-w-0 items-center justify-between gap-3 border-b border-border/70 py-2 text-[13px] font-medium text-ink transition-colors hover:text-brand"
                    href={`${base}/tri-thuc`}
                    key="tri-thuc"
                  >
                    <span className="min-w-0 break-words">Tài liệu và nguồn</span>
                    <span aria-hidden="true" className="shrink-0 text-ink-muted">
                      ›
                    </span>
                  </Link>
                )}
              </nav>
            </section>
          )}
        </>
      )}
    </WorkspacePage>
  );
}
