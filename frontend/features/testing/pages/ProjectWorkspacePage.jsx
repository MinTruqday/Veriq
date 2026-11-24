"use client";
import dynamic from "next/dynamic";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ErrorState, LoadingState } from "../components/WorkspacePrimitives";
import { useProject } from "../hooks/useProject";
import { PROJECTS_ROUTE, PROJECT_SECTION_SLUGS, projectRoute } from "../routes";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { formatDateTime } from "@/shared/lib/dateTime.mjs";
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
const DashboardPage = dynamic(() => import("./workspace/DashboardPage"), {
  loading: workspaceLoading,
});
const DefectsPage = dynamic(() => import("./workspace/DefectsPage"), { loading: workspaceLoading });
const DocumentReaderPage = dynamic(() => import("./workspace/DocumentReaderPage"), {
  loading: workspaceLoading,
});
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
const SettingsPage = dynamic(() => import("./workspace/SettingsPage"), {
  loading: workspaceLoading,
});
const TestDesignPage = dynamic(() => import("./workspace/TestDesignPage"), {
  loading: workspaceLoading,
});
const TraceabilityPage = dynamic(() => import("./workspace/TraceabilityPage"), {
  loading: workspaceLoading,
});
const TestAnalysisPage = dynamic(() => import("./workspace/TestAnalysisPage"), {
  loading: workspaceLoading,
});
const MonitoringPage = dynamic(() => import("./workspace/MonitoringPage"), {
  loading: workspaceLoading,
});
const ReleasesPage = dynamic(() => import("./workspace/ReleasesPage"), {
  loading: workspaceLoading,
});

export default function ProjectWorkspacePage({ projectId, section, initialQuery = "" }) {
  const router = useRouter();
  const state = useProject(projectId);
  const dateTimeOptions = useDateTimeOptions(state.project);
  const areaBySlug = {
    [PROJECT_SECTION_SLUGS.testAnalysis]: "test-analysis",
    [PROJECT_SECTION_SLUGS.monitoring]: "monitoring",
    [PROJECT_SECTION_SLUGS.releases]: "releases",
    [PROJECT_SECTION_SLUGS.requirements]: "requirements",
    [PROJECT_SECTION_SLUGS.testCases]: "test-design",
    [PROJECT_SECTION_SLUGS.testData]: "test-design",
    [PROJECT_SECTION_SLUGS.testSets]: "test-design",
    [PROJECT_SECTION_SLUGS.traceability]: "traceability",
    [PROJECT_SECTION_SLUGS.execution]: "execution",
    [PROJECT_SECTION_SLUGS.testPlans]: "execution",
    [PROJECT_SECTION_SLUGS.testRuns]: "execution",
    [PROJECT_SECTION_SLUGS.automation]: "execution",
    [PROJECT_SECTION_SLUGS.defects]: "defects",
    [PROJECT_SECTION_SLUGS.reports]: "reports",
    [PROJECT_SECTION_SLUGS.audit]: "settings",
    [PROJECT_SECTION_SLUGS.knowledge]: "knowledge",
    "tim-kiem": "knowledge",
    [PROJECT_SECTION_SLUGS.settings]: "settings",
    [PROJECT_SECTION_SLUGS.documentReader]: section[1] ? "document-reader" : "documents",
  };
  const legacyRedirectTarget =
    section[0] === PROJECT_SECTION_SLUGS.changes
      ? projectRoute(projectId, PROJECT_SECTION_SLUGS.requirements)
      : section[0] === PROJECT_SECTION_SLUGS.testDesign
        ? projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases)
        : "";
  const area = section[0] ? areaBySlug[section[0]] : "dashboard";
  const caseSubsectionItem =
    section[0] === PROJECT_SECTION_SLUGS.testCases &&
    section[1] &&
    testCaseSubsectionItems(projectId, true).find(
      (item) => item.href.split("/").at(-1) === section[1],
    );
  const invalidCaseSubsection = Boolean(
    section[0] === PROJECT_SECTION_SLUGS.testCases &&
      section[1] &&
      section[1] !== "tao-moi" &&
      !caseSubsectionItem,
  );
  const invalidSection = Boolean(
    (section[0] && !area && !legacyRedirectTarget) || invalidCaseSubsection,
  );
  const requiredPermissions = {
    "test-analysis": "testcondition.read",
    monitoring: "testmonitor.read",
    releases: "release.read",
    dashboard: "project.read",
    requirements: "requirement.read",
    "test-design": "testcase.read",
    traceability: "trace.read",
    execution: "testrun.read",
    defects: "defect.read",
    knowledge: "knowledge.read",
    reports: null,
    settings: section[0] === PROJECT_SECTION_SLUGS.audit ? "project.audit.read" : null,
    "document-reader": "requirement_document.read",
    documents: "requirement_document.read",
  };
  const sectionPermission = {
    [PROJECT_SECTION_SLUGS.testData]: ["testdata.read", "testcase.read"],
    [PROJECT_SECTION_SLUGS.testSets]: ["testsuite.read", "testcase.read"],
    [PROJECT_SECTION_SLUGS.testPlans]: "testplan.read",
    [PROJECT_SECTION_SLUGS.testRuns]: "testrun.read",
    [PROJECT_SECTION_SLUGS.automation]: "automation.read",
  }[section[0]];
  const sectionAnyPermissions = {
    [PROJECT_SECTION_SLUGS.testAnalysis]: ["testcondition.read", "testanalysis.read"],
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
          "analytics.ai.read",
          "coverage.read",
          "teststatusreport.read",
          "testcompletion.read",
        ]
      : area === "changes"
        ? ["changeset.read"]
          : area === "settings" && section[0] !== PROJECT_SECTION_SLUGS.audit
            ? PROJECT_SETTINGS_PERMISSIONS
            : null;
  const hasRequiredPermission = sectionAnyPermissions
    ? sectionAnyPermissions.some((permission) => permissions.includes(permission))
    : Array.isArray(requiredPermission)
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
  if (state.loading || state.project?._id !== projectId)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (state.forbidden)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (mustLeaveWorkspace) return null;
  if (!state.project)
    return (
      <div className="p-8">
        <ErrorState message={state.error || "Không tìm thấy dự án"} />
      </div>
    );
  const workspaceViewBySlug = {
    [PROJECT_SECTION_SLUGS.testCases]: "cases",
    [PROJECT_SECTION_SLUGS.testData]: "test-data",
    [PROJECT_SECTION_SLUGS.testSets]: "test-sets",
    [PROJECT_SECTION_SLUGS.testPlans]: "test-plans",
    [PROJECT_SECTION_SLUGS.testRuns]: "test-runs",
    [PROJECT_SECTION_SLUGS.execution]: "test-runs",
    [PROJECT_SECTION_SLUGS.automation]: "automation",
    [PROJECT_SECTION_SLUGS.audit]: "audit",
  };
  const props = {
    project: state.project,
    section: section.slice(1),
    workspaceView:
      section[0] === PROJECT_SECTION_SLUGS.testCases && section[1] === "bo-kiem-thu"
        ? "test-sets"
        : workspaceViewBySlug[section[0]] || "",
    setGlobalError: state.setError,
  };
  const pages = {
    "test-analysis": <TestAnalysisPage {...props} />,
    monitoring: <MonitoringPage {...props} />,
    releases: <ReleasesPage {...props} />,
    requirements: <RequirementsPage {...props} />,
    documents: <RequirementsPage {...props} workspaceView="documents" />,
    "test-design": <TestDesignPage {...props} />,
    traceability: <TraceabilityPage {...props} />,
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
    "document-reader": <DocumentReaderPage {...props} />,
  };
  return (
    <div className="workspace-page min-w-0">
      {state.error && (
        <div className="mx-auto w-full max-w-screen-2xl px-4 pt-4 sm:px-6">
          <ErrorState message={`Chưa làm mới được thông tin dự án: ${state.error}`} />
        </div>
      )}
      {state.project.access_context?.mode === "BREAK_GLASS" && (
        <div className="border-b border-warning/40 bg-warning-soft px-5 py-3 text-[13px] font-semibold text-warning">
          Quyền truy cập khẩn cấp đang hoạt động đến{" "}
          {formatDateTime(state.project.access_context.expires_at, dateTimeOptions)}
        </div>
      )}
      {pages[area] || <DashboardPage {...props} />}
    </div>
  );
}
