"use client";
import dynamic from "next/dynamic";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ErrorState, LoadingState } from "../components/WorkspacePrimitives";
import { useProject } from "../hooks/useProject";
import { PROJECTS_ROUTE, PROJECT_SECTION_SLUGS, projectRoute } from "../routes";
import {
  hasNavigationPermission,
  PROJECT_SETTINGS_PERMISSIONS,
  testCaseSubsectionItems,
} from "@/shared/components/layout/navigation";

const workspaceLoading = () => (
  <div className="p-8">
    <LoadingState />
  </div>
);
const ChangesPage = dynamic(() => import("./workspace/ChangesPage"), { loading: workspaceLoading });
const DashboardPage = dynamic(() => import("./workspace/DashboardPage"), {
  loading: workspaceLoading,
});
const DefectsPage = dynamic(() => import("./workspace/DefectsPage"), { loading: workspaceLoading });
const ExecutionPage = dynamic(() => import("./workspace/ExecutionPage"), {
  loading: workspaceLoading,
});
const KnowledgePage = dynamic(() => import("./workspace/KnowledgePage"), {
  loading: workspaceLoading,
});
const RequirementsPage = dynamic(() => import("./workspace/RequirementsPage"), {
  loading: workspaceLoading,
});
const ReportsPage = dynamic(() => import("./workspace/ReportsPage"), { loading: workspaceLoading });
const ReviewQueuePage = dynamic(() => import("./workspace/ReviewQueuePage"), {
  loading: workspaceLoading,
});
const SettingsPage = dynamic(() => import("./workspace/SettingsPage"), {
  loading: workspaceLoading,
});
const TestDesignPage = dynamic(() => import("./workspace/TestDesignPage"), {
  loading: workspaceLoading,
});
const TraceabilityPage = dynamic(() => import("./workspace/TraceabilityPage"), {
  loading: workspaceLoading,
});
const TestGovernancePage = dynamic(() => import("./workspace/TestGovernancePage"), {
  loading: workspaceLoading,
});
const TestAnalysisPage = dynamic(() => import("./workspace/TestAnalysisPage"), {
  loading: workspaceLoading,
});
const MonitoringPage = dynamic(() => import("./workspace/MonitoringPage"), {
  loading: workspaceLoading,
});
const PlanningPage = dynamic(() => import("./workspace/PlanningPage"), {
  loading: workspaceLoading,
});
const ReleasesPage = dynamic(() => import("./workspace/ReleasesPage"), {
  loading: workspaceLoading,
});

export default function ProjectWorkspacePage({ projectId, section, initialQuery = "" }) {
  const router = useRouter();
  const state = useProject(projectId);
  const areaBySlug = {
    [PROJECT_SECTION_SLUGS.governance]: "governance",
    [PROJECT_SECTION_SLUGS.testAnalysis]: "test-analysis",
    [PROJECT_SECTION_SLUGS.monitoring]: "monitoring",
    [PROJECT_SECTION_SLUGS.planning]: "planning",
    [PROJECT_SECTION_SLUGS.releases]: "releases",
    [PROJECT_SECTION_SLUGS.requirements]: "requirements",
    [PROJECT_SECTION_SLUGS.assurance]: "requirements",
    [PROJECT_SECTION_SLUGS.clarifications]: "requirements",
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
  const legacyRedirectTarget =
    section[0] === PROJECT_SECTION_SLUGS.projectTasks
      ? projectRoute(projectId, PROJECT_SECTION_SLUGS.planning, "backlog")
      : section[0] === PROJECT_SECTION_SLUGS.testDesign
        ? projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases)
        : "";
  const area = section[0] ? areaBySlug[section[0]] : "dashboard";
  const caseSubsectionItem =
    section[0] === PROJECT_SECTION_SLUGS.testCases &&
    section[1] &&
    testCaseSubsectionItems(projectId).find((item) => item.href.split("/").at(-1) === section[1]);
  const invalidCaseSubsection = Boolean(
    section[0] === PROJECT_SECTION_SLUGS.testCases && section[1] && !caseSubsectionItem,
  );
  const planningSubsections = ["list", "backlog", "board", "sprint", "roadmap"];
  const invalidPlanningSubsection = Boolean(
    section[0] === PROJECT_SECTION_SLUGS.planning &&
      section[1] &&
      !planningSubsections.includes(section[1]),
  );
  const unavailableSprint = Boolean(
    !state.loading &&
      state.project &&
      section[0] === PROJECT_SECTION_SLUGS.planning &&
      section[1] === "sprint" &&
      (state.project.planning_method || "SCRUM") !== "SCRUM",
  );
  const invalidSection = Boolean(
    (section[0] && !area && !legacyRedirectTarget) ||
      invalidCaseSubsection ||
      invalidPlanningSubsection ||
      unavailableSprint,
  );
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
    changes: null,
    "ai-review": null,
    execution: "testrun.read",
    defects: "defect.read",
    knowledge: "knowledge.read",
    reports: null,
    settings: section[0] === PROJECT_SECTION_SLUGS.audit ? "project.audit.read" : null,
  };
  const sectionPermission = {
    [PROJECT_SECTION_SLUGS.assurance]: ["requirement.read", "testcase.read"],
    [PROJECT_SECTION_SLUGS.testData]: ["testdata.read", "testcase.read"],
    [PROJECT_SECTION_SLUGS.testSets]: ["testsuite.read", "testcase.read"],
    [PROJECT_SECTION_SLUGS.testPlans]: "testplan.read",
    [PROJECT_SECTION_SLUGS.testRuns]: "testrun.read",
    [PROJECT_SECTION_SLUGS.automation]: "automation.read",
  }[section[0]];
  const permissions = state.project?.current_permissions || [];
  const hasCaseSubsectionPermission =
    !caseSubsectionItem || hasNavigationPermission(caseSubsectionItem, permissions);
  const requiredPermission = sectionPermission || requiredPermissions[area];
  const areaAnyPermissions =
    area === "reports"
      ? [
          "report.read",
          "analytics.read",
          "coverage.read",
          "teststatusreport.read",
          "testcompletion.read",
          "qualityevaluation.read",
          "measurement.read",
          "processimprovement.read",
        ]
      : area === "changes"
        ? ["changeset.read"]
        : area === "ai-review"
          ? ["automation.read", "proposal.read"]
          : area === "settings" && section[0] !== PROJECT_SECTION_SLUGS.audit
            ? PROJECT_SETTINGS_PERMISSIONS
            : null;
  const hasRequiredPermission = Array.isArray(requiredPermission)
    ? requiredPermission.every((permission) => permissions.includes(permission))
    : requiredPermission
      ? permissions.includes(requiredPermission)
      : !areaAnyPermissions ||
        areaAnyPermissions.some((permission) => permissions.includes(permission));
  const lacksSectionPermission = Boolean(
    !state.loading &&
      !state.error &&
      state.project &&
      (!hasRequiredPermission || !hasCaseSubsectionPermission),
  );
  const mustLeaveWorkspace =
    state.forbidden || invalidSection || lacksSectionPermission || Boolean(legacyRedirectTarget);
  const accessFallback =
    section.length && permissions.includes("project.read")
      ? projectRoute(projectId)
      : PROJECTS_ROUTE;
  useEffect(() => {
    if (legacyRedirectTarget) {
      router.replace(legacyRedirectTarget);
      return;
    }
    if (state.forbidden) {
      router.replace(PROJECTS_ROUTE);
      return;
    }
    if (invalidSection || lacksSectionPermission) {
      router.replace(accessFallback);
    }
  }, [
    accessFallback,
    invalidSection,
    lacksSectionPermission,
    legacyRedirectTarget,
    router,
    state.forbidden,
  ]);
  if (state.loading)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (mustLeaveWorkspace) return null;
  if (state.error || !state.project)
    return (
      <div className="p-8">
        <ErrorState message={state.error || "Không tìm thấy dự án"} />
      </div>
    );
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
    <div className="workspace-page min-w-0">
      {state.project.access_context?.mode === "BREAK_GLASS" && (
        <div className="border-b border-warning/40 bg-warning-soft px-5 py-3 text-[13px] font-semibold text-warning">
          Quyền truy cập khẩn cấp đang hoạt động đến{" "}
          {new Date(state.project.access_context.expires_at).toLocaleString("vi-VN")}
        </div>
      )}
      {pages[area] || <DashboardPage {...props} />}
    </div>
  );
}
