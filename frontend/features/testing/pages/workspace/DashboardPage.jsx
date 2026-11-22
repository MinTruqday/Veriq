"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import AIRunPanel from "../../components/AIRunPanel";
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
import { formatDate as formatDateValue, messageOf, valueLabel } from "../../lib/testing";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

function latestRunLabel(run) {
  const name = String(run?.name || "").trim();
  const containsInternalCode = /\b[A-Z][A-Z0-9]*(?:_+[A-Z0-9]+)+\b/.test(name);
  return name && !containsInternalCode ? name : "Lần chạy kiểm thử";
}

function latestRunContext(run, dateTimeOptions) {
  const details = [];
  if (run?.build) details.push(`Bản dựng ${run.build}`);
  if (run?.environment) details.push(`Môi trường ${valueLabel(run.environment)}`);
  if (run?.created_at) details.push(formatDateValue(run.created_at, dateTimeOptions));
  return details.join(" · ");
}

function formatCoveragePercent(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? `${Math.round(numericValue)}%` : "—";
}

function OverviewMetric({ label, value, detail, percent = null }) {
  const radius = 27;
  const circumference = 2 * Math.PI * radius;
  const hasPercent = percent != null && Number.isFinite(Number(percent));
  const normalizedPercent = hasPercent
    ? Math.max(0, Math.min(100, Number(percent)))
    : Number(value) > 0
      ? 100
      : 0;
  const dash = (circumference * normalizedPercent) / 100;

  return (
    <div className="flex min-w-0 flex-col items-center gap-2 text-center">
      <dt className="min-h-10 text-[13px] font-medium leading-5 text-ink">{label}</dt>
      <dd className="m-0">
        <div className="relative size-[76px]">
          <svg
            aria-label={`${label}: ${value}`}
            className="size-full -rotate-90"
            role="img"
            viewBox="0 0 64 64"
          >
            <circle
              cx="32"
              cy="32"
              r={radius}
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="5"
            />
            {normalizedPercent > 0 && (
              <circle
                cx="32"
                cy="32"
                r={radius}
                fill="none"
                stroke="hsl(var(--brand))"
                strokeDasharray={`${dash} ${circumference}`}
                strokeLinecap="round"
                strokeWidth="5"
              />
            )}
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[14px] font-semibold tabular-nums text-ink">
            {value}
          </span>
        </div>
      </dd>
      <p className="text-xs leading-4 text-ink-muted">{detail}</p>
    </div>
  );
}

export default function DashboardPage({ project }) {
  const { user } = useAuth();
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const [value, setValue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [projectDetails, setProjectDetails] = useState(project);
  const [projectMembers, setProjectMembers] = useState([]);
  const [showAiReview, setShowAiReview] = useState(false);
  const permissions = project.current_permissions || [];
  const can = (permission) => permissions.includes(permission);
  const canReadAnalytics = can("analytics.read");
  const canReadCoverage = can("coverage.read");
  const canReadAIRuns = can("proposal.read") || can("requirement.read");
  const canReadProjectMembers = can("project.members.read");
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
    if (canReadProjectMembers) {
      requests.push(["members", testingApi.listMembers(project._id)]);
    }
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
        if (currentProject) setProjectDetails(currentProject);
        setProjectMembers(data.members || []);
        setValue({ dashboard: data.dashboard || null, coverage: data.coverage || null });
        if (!currentProject) return;
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [canReadAnalytics, canReadCoverage, canReadProjectMembers, project._id, reloadVersion]);
  const base = `/du-an/${project._id}`;
  const dashboard = value?.dashboard;
  const coverage = value?.coverage;
  const openDefectSeverities = Object.entries(dashboard?.open_defects_by_severity || {}).filter(
    ([, count]) => Number(count) > 0,
  );
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
  const hasRecentChanges = Boolean(dashboard && can("requirement.read") && can("impact.read"));
  return (
    <WorkspacePage title={project.name}>
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
          <Panel title="Tiến trình kiểm thử">
            <div className="p-5">
              <ol className="grid gap-4 sm:grid-cols-5" aria-label="Các giai đoạn kiểm thử">
                {[
                  {
                    label: "Yêu cầu",
                    count: can("requirement.read") ? dashboard?.requirements_total : null,
                    href: projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements),
                    permission: "requirement.read",
                  },
                  {
                    label: "Kế hoạch",
                    count: can("testplan.read") ? dashboard?.test_plans : null,
                    href: projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans),
                    permission: "testplan.read",
                  },
                  {
                    label: "Thiết kế",
                    count: can("testcase.read") ? dashboard?.active_tests : null,
                    href: projectRoute(project._id, PROJECT_SECTION_SLUGS.testCases),
                    permission: "testcase.read",
                  },
                  {
                    label: "Thực thi",
                    count: can("testrun.read") ? dashboard?.current_runs : null,
                    href: projectRoute(project._id, PROJECT_SECTION_SLUGS.testRuns),
                    permission: "testrun.read",
                  },
                  {
                    label: "Báo cáo và phát hành",
                    count:
                      can("testcompletion.read") || can("release.read")
                        ? (can("testcompletion.read")
                            ? Number(dashboard?.completion_reports || 0)
                            : 0) + (can("release.read") ? Number(dashboard?.releases || 0) : 0)
                        : null,
                    detail: [
                      can("testcompletion.read")
                        ? `${dashboard?.completion_reports ?? 0} báo cáo`
                        : null,
                      can("release.read") ? `${dashboard?.releases ?? 0} bản phát hành` : null,
                    ]
                      .filter(Boolean)
                      .join(" · "),
                    href: projectRoute(project._id, PROJECT_SECTION_SLUGS.reports),
                    permissions: ["testcompletion.read", "release.read"],
                  },
                ]
                  .filter((stage) =>
                    (stage.permissions || [stage.permission]).some((permission) => can(permission)),
                  )
                  .map((stage, index, stages) => (
                    <li className="relative min-w-0" key={stage.label}>
                      {index < stages.length - 1 && (
                        <span
                          aria-hidden="true"
                          className="absolute left-5 right-[-1rem] top-5 hidden h-px bg-border sm:block"
                        />
                      )}
                      <Link
                        className="relative flex min-w-0 flex-col items-start gap-1 rounded-control p-1 text-left hover:text-brand"
                        href={stage.href}
                      >
                        <span className="flex size-10 items-center justify-center rounded-full border border-brand/40 bg-surface-raised text-xs font-semibold text-brand">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="text-[13px] font-medium">{stage.label}</span>
                        <span className="text-xs text-ink-muted">
                          {stage.detail ||
                            (stage.count == null ? "Chưa có số liệu" : `${stage.count} mục`)}
                        </span>
                      </Link>
                    </li>
                  ))}
              </ol>
            </div>
          </Panel>
          {(dashboard || coverage) && hasOverviewMetrics && (
            <Panel title="Tổng quan kiểm thử">
              <dl className="grid grid-cols-1 gap-x-5 gap-y-6 p-5 sm:grid-cols-2 xl:grid-cols-4">
                {can("requirement.read") && dashboard && (
                  <OverviewMetric
                    label="Yêu cầu đã duyệt"
                    value={`${dashboard.requirements}/${dashboard.requirements_total}`}
                    percent={
                      dashboard.requirements_total > 0
                        ? (dashboard.requirements / dashboard.requirements_total) * 100
                        : 0
                    }
                    detail={`${dashboard.requirements} đã duyệt · ${Math.max(dashboard.requirements_total - dashboard.requirements, 0)} cần xử lý`}
                  />
                )}
                {can("testcase.read") && dashboard && (
                  <OverviewMetric
                    label="Ca kiểm thử đang hoạt động"
                    value={dashboard.active_tests}
                    detail="Ca kiểm thử có trạng thái hoạt động"
                  />
                )}
                {can("defect.read") && dashboard && (
                  <OverviewMetric
                    label="Lỗi đang mở"
                    value={dashboard.open_defects}
                    detail="Lỗi chưa đóng"
                  />
                )}
                {can("coverage.read") && coverage?.requirement_coverage != null && (
                  <OverviewMetric
                    label="Yêu cầu có liên kết kiểm thử"
                    value={formatCoveragePercent(coverage.requirement_coverage)}
                    percent={coverage.requirement_coverage}
                    detail="Độ phủ liên kết đã xác nhận"
                  />
                )}
              </dl>
            </Panel>
          )}
          <div className="grid min-w-0 items-stretch gap-5 xl:grid-cols-2">
            <Panel title="Thông tin dự án" className="h-full">
              <dl className="divide-y divide-border px-5">
                <div className="grid min-w-0 gap-2 py-3 sm:grid-cols-[7rem_minmax(0,1fr)]">
                  <dt className="text-[13px] text-ink-muted">Mô tả</dt>
                  <dd className="min-w-0 break-words text-[13px]">
                    {projectDetails.description || "Chưa có mô tả"}
                  </dd>
                </div>
                <div className="grid min-w-0 gap-2 py-3 sm:grid-cols-[7rem_minmax(0,1fr)]">
                  <dt className="text-[13px] text-ink-muted">Trưởng dự án</dt>
                  <dd className="min-w-0 break-words text-[13px]">
                    {projectMembers.find((member) => member.is_project_owner)?.user_label ||
                      (can("project.members.read") ? "Chưa phân công" : "Không có quyền xem")}
                  </dd>
                </div>
                <div className="grid min-w-0 gap-2 py-3 sm:grid-cols-[7rem_minmax(0,1fr)]">
                  <dt className="text-[13px] text-ink-muted">Thời gian dự án</dt>
                  <dd className="min-w-0 break-words text-[13px]">
                    {[projectDetails.planned_start_at, projectDetails.planned_end_at]
                      .filter(Boolean)
                      .map((date) => formatDate(date))
                      .join(" – ") || "Chưa thiết lập thời gian"}
                  </dd>
                </div>
                <div className="grid min-w-0 gap-2 py-3 sm:grid-cols-[7rem_minmax(0,1fr)]">
                  <dt className="text-[13px] text-ink-muted">Thành viên</dt>
                  <dd className="min-w-0 break-words text-[13px]">
                    {can("project.members.read")
                      ? projectMembers
                          .filter((member) => member.status === "ACTIVE")
                          .map((member) => member.user_label)
                          .filter(Boolean)
                          .join(" · ") || "Chưa có thành viên"
                      : "Không có quyền xem"}
                  </dd>
                </div>
              </dl>
            </Panel>
            <Panel title="Tình hình kiểm thử" className="h-full">
              <dl className="divide-y divide-border px-5">
                {can("requirement.read") && dashboard && (
                  <div className="flex items-center justify-between gap-3 py-3 text-[13px]">
                    <dt>Yêu cầu đã thiết lập phiên bản chuẩn</dt>
                    <dd className="font-semibold tabular-nums">{dashboard.requirements}</dd>
                  </div>
                )}
                {can("testcase.read") && dashboard && (
                  <div className="flex items-center justify-between gap-3 py-3 text-[13px]">
                    <dt>Ca kiểm thử đang hoạt động</dt>
                    <dd className="font-semibold tabular-nums">{dashboard.active_tests}</dd>
                  </div>
                )}
                {can("testrun.read") && dashboard && (
                  <div className="flex items-center justify-between gap-3 py-3 text-[13px]">
                    <dt>Lượt chạy đang thực hiện</dt>
                    <dd className="font-semibold tabular-nums">{dashboard.current_runs}</dd>
                  </div>
                )}
                {can("release.read") && dashboard && (
                  <div className="flex items-center justify-between gap-3 py-3 text-[13px]">
                    <dt>Bản phát hành</dt>
                    <dd className="font-semibold tabular-nums">{dashboard.releases}</dd>
                  </div>
                )}
              </dl>
            </Panel>
          </div>
          {canReadAnalytics && (
            <Panel title="Cần xử lý">
              <ul className="divide-y divide-border px-5">
                {can("impact.read") && dashboard?.changes_waiting_impact > 0 && (
                  <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-[13px]">
                    <span>
                      {dashboard.changes_waiting_impact} thay đổi yêu cầu cần rà soát ảnh hưởng
                    </span>
                    <Link className="font-medium text-brand" href={`${base}/thay-doi`}>
                      Xem thay đổi
                    </Link>
                  </li>
                )}
                {can("testcase.read") && dashboard?.tests_needing_update > 0 && (
                  <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-[13px]">
                    <span>{dashboard.tests_needing_update} ca kiểm thử cần cập nhật</span>
                    <Link
                      className="font-medium text-brand"
                      href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testCases)}
                    >
                      Xem ca kiểm thử
                    </Link>
                  </li>
                )}
                {can("defect.read") && dashboard?.open_defects > 0 && (
                  <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-[13px]">
                    <span>{dashboard.open_defects} lỗi đang mở</span>
                    <Link
                      className="font-medium text-brand"
                      href={projectRoute(project._id, PROJECT_SECTION_SLUGS.defects)}
                    >
                      Xem lỗi
                    </Link>
                  </li>
                )}
                {(!can("impact.read") || !dashboard?.changes_waiting_impact) &&
                  (!can("testcase.read") || !dashboard?.tests_needing_update) &&
                  (!can("defect.read") || !dashboard?.open_defects) && (
                    <li className="py-4 text-[13px] text-ink-muted">Không có mục cần xử lý</li>
                  )}
              </ul>
            </Panel>
          )}
          {(canReadAIRuns ||
            (dashboard && (can("defect.read") || can("testrun.read"))) ||
            hasRecentChanges) && (
            <div className="grid min-w-0 items-stretch gap-5 xl:grid-cols-2">
              {dashboard && can("testrun.read") && (
                <Panel className="h-full" title="Lần chạy mới nhất">
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
                      {latestRunContext(dashboard.latest_run, dateTimeOptions) && (
                        <p className="text-[12px] text-ink-muted">
                          {latestRunContext(dashboard.latest_run, dateTimeOptions)}
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
              {dashboard && can("defect.read") && (
                <Panel className="h-full" title="Lỗi cần chú ý">
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
              {canReadAIRuns && (
                <div className="min-w-0 [&>section]:h-full">
                  <AIRunPanel project={project} compact />
                </div>
              )}
              {hasRecentChanges && (
                <Panel className="h-full" title="Thay đổi gần đây">
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
                          render: (item) => formatDate(item.created_at, dateTimeOptions),
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
          )}
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
        </>
      )}
    </WorkspacePage>
  );
}
