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
import ProjectTasksPage from "./workspace/ProjectTasksPage";
import { PROJECT_SECTION_SLUGS } from "../routes";

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
    [PROJECT_SECTION_SLUGS.requirements]: "requirements",
    [PROJECT_SECTION_SLUGS.testDesign]: "test-design",
    [PROJECT_SECTION_SLUGS.traceability]: "traceability",
    [PROJECT_SECTION_SLUGS.changes]: "changes",
    [PROJECT_SECTION_SLUGS.execution]: "execution",
    [PROJECT_SECTION_SLUGS.aiReview]: "ai-review",
    [PROJECT_SECTION_SLUGS.defects]: "defects",
    [PROJECT_SECTION_SLUGS.reports]: "reports",
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
  const props = {
    project: state.project,
    section: section.slice(1),
    setGlobalError: state.setError,
  };
  const pages = {
    governance: <TestGovernancePage {...props} />,
    "test-analysis": <TestAnalysisPage {...props} />,
    monitoring: <MonitoringPage {...props} />,
    "project-tasks": <ProjectTasksPage {...props} />,
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
      {pages[area] || <DashboardPage {...props} />}
    </>
  );
}
