"use client";
import { ErrorState, LoadingState } from "../components/WorkspacePrimitives";
import { useProject } from "../hooks/useProject";
import ChangesPage from "./workspace/ChangesPage";
import DashboardPage from "./workspace/DashboardPage";
import DefectsPage from "./workspace/DefectsPage";
import ExecutionPage from "./workspace/ExecutionPage";
import KnowledgePage from "./workspace/KnowledgePage";
import RequirementsPage from "./workspace/RequirementsPage";
import ReportsPage from "./workspace/ReportsPage";
import ReviewQueuePage from "./workspace/ReviewQueuePage";
import SettingsPage from "./workspace/SettingsPage";
import TestDesignPage from "./workspace/TestDesignPage";
import TraceabilityPage from "./workspace/TraceabilityPage";
import TestGovernancePage from "./workspace/TestGovernancePage";
import TestAnalysisPage from "./workspace/TestAnalysisPage";
import MonitoringPage from "./workspace/MonitoringPage";
import PlanningPage from "./workspace/PlanningPage";
import ReleasesPage from "./workspace/ReleasesPage";
import { PROJECT_SECTION_SLUGS } from "../routes";
import { valueLabel } from "../lib/testing";

export default function ProjectWorkspacePage({ projectId, section, initialQuery = "" }) {
  const state = useProject(projectId);
  if (state.loading)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (state.error || !state.project)
    return (
      <div className="p-8">
        <ErrorState message={state.error || "Không tìm thấy dự án"} />
      </div>
    );
  const areaBySlug = {
    [PROJECT_SECTION_SLUGS.governance]: "governance",
    [PROJECT_SECTION_SLUGS.testAnalysis]: "test-analysis",
    [PROJECT_SECTION_SLUGS.monitoring]: "monitoring",
    [PROJECT_SECTION_SLUGS.projectTasks]: "project-tasks",
    [PROJECT_SECTION_SLUGS.planning]: "planning",
    [PROJECT_SECTION_SLUGS.releases]: "releases",
    [PROJECT_SECTION_SLUGS.requirements]: "requirements",
    [PROJECT_SECTION_SLUGS.assurance]: "requirements",
    [PROJECT_SECTION_SLUGS.clarifications]: "requirements",
    [PROJECT_SECTION_SLUGS.testDesign]: "test-design",
    [PROJECT_SECTION_SLUGS.testRepository]: "test-design",
    [PROJECT_SECTION_SLUGS.testCases]: "test-design",
    [PROJECT_SECTION_SLUGS.reusableSteps]: "test-design",
    [PROJECT_SECTION_SLUGS.testData]: "test-design",
    [PROJECT_SECTION_SLUGS.testSets]: "test-design",
    [PROJECT_SECTION_SLUGS.traceability]: "traceability",
    [PROJECT_SECTION_SLUGS.changes]: "changes",
    [PROJECT_SECTION_SLUGS.execution]: "execution",
    [PROJECT_SECTION_SLUGS.testPlans]: "execution",
    [PROJECT_SECTION_SLUGS.testRuns]: "execution",
    [PROJECT_SECTION_SLUGS.automation]: "execution",
    [PROJECT_SECTION_SLUGS.aiReview]: "ai-review",
    [PROJECT_SECTION_SLUGS.defects]: "defects",
    [PROJECT_SECTION_SLUGS.reports]: "reports",
    [PROJECT_SECTION_SLUGS.audit]: "settings",
    [PROJECT_SECTION_SLUGS.knowledge]: "knowledge",
    "tim-kiem": "knowledge",
    [PROJECT_SECTION_SLUGS.settings]: "settings",
  };
  const area = section[0] ? areaBySlug[section[0]] : "dashboard";
  const requiredPermissions = {
    governance: "teststrategy.read",
    "test-analysis": "testcondition.read",
    monitoring: "testmonitor.read",
    "project-tasks": "project.read",
    planning: "project.read",
    releases: "release.read",
    dashboard: "project.read",
    requirements: "requirement.read",
    "test-design": "testcase.read",
    traceability: "trace.read",
    changes: "impact.read",
    "ai-review": "proposal.read",
    execution: "testrun.read",
    defects: "defect.read",
    knowledge: "knowledge.read",
    reports: "report.read",
    settings: "project.settings.manage",
  };
  const requiredPermission = requiredPermissions[area];
  if (requiredPermission && !state.project.current_permissions?.includes(requiredPermission)) {
    return (
      <div className="p-8">
        <ErrorState message="Bạn không có quyền mở khu vực này trong dự án" />
      </div>
    );
  }
  const workspaceViewBySlug = {
    [PROJECT_SECTION_SLUGS.assurance]: "assurance",
    [PROJECT_SECTION_SLUGS.clarifications]: "clarifications",
    [PROJECT_SECTION_SLUGS.testRepository]: "repository",
    [PROJECT_SECTION_SLUGS.testCases]: "cases",
    [PROJECT_SECTION_SLUGS.reusableSteps]: "reusable-steps",
    [PROJECT_SECTION_SLUGS.testData]: "test-data",
    [PROJECT_SECTION_SLUGS.testSets]: "test-sets",
    [PROJECT_SECTION_SLUGS.testPlans]: "test-plans",
    [PROJECT_SECTION_SLUGS.testRuns]: "test-runs",
    [PROJECT_SECTION_SLUGS.automation]: "automation",
    [PROJECT_SECTION_SLUGS.audit]: "audit",
  };
  const props = {
    project: state.project,
    section: section.slice(1),
    workspaceView: workspaceViewBySlug[section[0]] || "",
    setGlobalError: state.setError,
  };
  const pages = {
    governance: <TestGovernancePage {...props} />,
    "test-analysis": <TestAnalysisPage {...props} />,
    monitoring: <MonitoringPage {...props} />,
    "project-tasks": <PlanningPage {...props} />,
    planning: <PlanningPage {...props} />,
    releases: <ReleasesPage {...props} />,
    requirements: <RequirementsPage {...props} />,
    "test-design": <TestDesignPage {...props} />,
    traceability: <TraceabilityPage {...props} />,
    changes: <ChangesPage {...props} />,
    "ai-review": <ReviewQueuePage {...props} />,
    execution: <ExecutionPage {...props} />,
    defects: <DefectsPage {...props} />,
    knowledge: (
      <KnowledgePage
        {...props}
        initialQuery={initialQuery}
        useGlobalSearch={section[0] === "tim-kiem"}
      />
    ),
    reports: <ReportsPage {...props} />,
    settings: <SettingsPage {...props} onProjectChange={state.reload} />,
  };
  return (
    <>
      {state.project.access_context?.mode === "BREAK_GLASS" && (
        <div className="border-b border-warning/40 bg-warning-soft px-5 py-3 text-[13px] font-semibold text-warning">
          Quyền truy cập khẩn cấp đang hoạt động đến{" "}
          {new Date(state.project.access_context.expires_at).toLocaleString("vi-VN")}
        </div>
      )}
      <div className="border-b border-border bg-surface-raised">
        <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-[12px] text-ink-muted sm:px-6 md:px-9">
          <span className="font-semibold text-ink">{state.project.key}</span>
          <span aria-hidden="true">/</span>
          <span className="truncate">{state.project.name}</span>
          <span className="hidden text-border-strong sm:inline" aria-hidden="true">
            •
          </span>
          <span>{state.project.planning_method === "KANBAN" ? "Kanban" : "Scrum"}</span>
          {state.project.current_membership?.project_role && (
            <>
              <span className="hidden text-border-strong sm:inline" aria-hidden="true">
                •
              </span>
              <span>{valueLabel(state.project.current_membership.project_role)}</span>
            </>
          )}
        </div>
      </div>
      {pages[area] || <DashboardPage {...props} />}
    </>
  );
}
