import {
  Activity,
  Archive,
  BrainCircuit,
  Bug,
  BarChart3,
  FileCheck2,
  FolderKanban,
  GitCompareArrows,
  LayoutDashboard,
  Network,
  PlayCircle,
  Search,
  Settings,
  TestTube2,
  Database,
  History,
} from "lucide-react";
import {
  OPERATIONS_ROUTE,
  PROJECTS_ROUTE,
  PROJECT_SECTION_SLUGS,
  projectRoute,
} from "../../../features/testing/routes";
import {
  canSeeNavigationItem,
  hasNavigationPermission,
  navigationItemForPath,
} from "./navigationAccess.mjs";

export { hasNavigationPermission, navigationItemForPath };

export const PROJECT_SETTINGS_PERMISSIONS = [
  "project.read",
  "project.settings.manage",
  "project.update",
  "project.archive",
  "project.members.read",
  "project.members.manage",
  "analytics.read",
  "analytics.ai.read",
  "notification.watch.manage",
  "notification.preferences.manage",
  "notification.project_rule.manage",
];

export function testCaseSubsectionItems(projectId) {
  const root = projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases);
  return [
    { id: "cases", label: "Ca kiểm thử", href: root, permission: "testcase.read" },
    {
      id: "ai",
      label: "Hoạt động AI",
      href: `${root}/ai`,
      anyPermission: ["proposal.read", "requirement.read"],
      permissions: ["testcase.read"],
    },
    {
      id: "scenarios",
      label: "Kịch bản",
      href: `${root}/kich-ban`,
      permission: "testscenario.read",
      permissions: ["testcase.read"],
    },
    {
      id: "templates",
      label: "Mẫu",
      href: `${root}/mau`,
      permission: "testcase.template.read",
      permissions: ["testcase.read"],
    },
    {
      id: "automation",
      label: "Mã kiểm thử tự động",
      href: `${root}/tu-dong-hoa`,
      permission: "automation.read",
      permissions: ["testcase.read"],
    },
    {
      id: "api",
      label: "API",
      href: `${root}/api`,
      permission: "apiartifact.read",
      permissions: ["testcase.read"],
    },
    {
      id: "import",
      label: "Nhập và xuất",
      href: `${root}/nhap-xuat`,
      anyPermission: ["testcase.import", "testcase.export"],
      permissions: ["testcase.read"],
    },
  ];
}

export function testDesignSectionItems(projectId) {
  const designItems =
    navigationGroupsFor(projectRoute(projectId)).find((group) =>
      group.items.some((item) => item.id === "test-cases"),
    )?.items || [];
  return designItems.filter((item) =>
    ["test-scenarios", "test-cases", "test-data", "test-sets"].includes(item.id),
  );
}

export function projectIdFromPath(pathname) {
  const match = pathname.match(/^\/du-an\/([^/]+)/);
  return match?.[1] || "";
}

export function navigationGroupsFor(pathname) {
  const projectId = projectIdFromPath(pathname);
  const root = projectId ? projectRoute(projectId) : "";
  const projectItems = projectId
    ? {
        project: [
          {
            id: "dashboard",
            label: "Tổng quan",
            href: root,
            icon: LayoutDashboard,
            permission: "project.read",
          },
        ],
        requirements: [
          {
            id: "requirements",
            label: "Yêu cầu",
            href: `${root}/${PROJECT_SECTION_SLUGS.requirements}`,
            icon: FileCheck2,
            permission: "requirement.read",
          },
          {
            id: "changes",
            label: "Phân tích thay đổi",
            href: `${root}/${PROJECT_SECTION_SLUGS.changes}`,
            icon: GitCompareArrows,
            permission: "changeset.read",
          },
        ],
        design: [
          {
            id: "test-analysis",
            label: "Phân tích kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testAnalysis}`,
            icon: TestTube2,
            anyPermission: ["testcondition.read", "testanalysis.read"],
          },
          {
            id: "test-cases",
            label: "Ca kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testCases}`,
            icon: TestTube2,
            permission: "testcase.read",
          },
          {
            id: "test-data",
            label: "Dữ liệu kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testData}`,
            icon: Database,
            permission: "testdata.read",
            permissions: ["testcase.read"],
          },
          {
            id: "test-sets",
            label: "Bộ kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testSets}`,
            icon: Archive,
            permission: "testsuite.read",
            permissions: ["testcase.read"],
          },
        ],
        execution: [
          {
            id: "execution-overview",
            label: "Tổng quan",
            href: `${root}/${PROJECT_SECTION_SLUGS.execution}`,
            icon: LayoutDashboard,
            permission: "testrun.read",
          },
          {
            id: "test-plans",
            label: "Kế hoạch kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testPlans}`,
            icon: ClipboardCheck,
            permission: "testplan.read",
          },
          {
            id: "test-runs",
            label: "Lần chạy kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testRuns}`,
            icon: PlayCircle,
            permission: "testrun.read",
          },
          {
            id: "automation",
            label: "Mã kiểm thử tự động",
            href: `${root}/${PROJECT_SECTION_SLUGS.automation}`,
            icon: BrainCircuit,
            permission: "automation.read",
          },
          {
            id: "defects",
            label: "Lỗi",
            href: `${root}/${PROJECT_SECTION_SLUGS.defects}`,
            icon: Bug,
            permission: "defect.read",
          },
        ],
        quality: [
          {
            id: "monitoring",
            label: "Giám sát kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.monitoring}`,
            icon: Activity,
            permission: "testmonitor.read",
          },
          {
            id: "traceability",
            label: "Truy vết",
            href: `${root}/${PROJECT_SECTION_SLUGS.traceability}`,
            icon: Network,
            permission: "trace.read",
          },
          {
            id: "reports",
            label: "Báo cáo",
            href: `${root}/${PROJECT_SECTION_SLUGS.reports}`,
            icon: BarChart3,
            anyPermission: [
              "report.read",
              "analytics.read",
              "analytics.ai.read",
              "coverage.read",
              "teststatusreport.read",
              "testcompletion.read",
            ],
          },
          {
            id: "audit",
            label: "Nhật ký kiểm toán",
            href: `${root}/${PROJECT_SECTION_SLUGS.audit}`,
            icon: History,
            permission: "project.audit.read",
          },
          {
            id: "ai-review",
            label: "Hoạt động AI",
            href: `${root}/${PROJECT_SECTION_SLUGS.aiReview}`,
            icon: BrainCircuit,
            anyPermission: ["requirement.read", "proposal.read"],
          },
        ],
        resources: [
          {
            id: "knowledge",
            label: "Tài liệu tham chiếu",
            href: `${root}/${PROJECT_SECTION_SLUGS.knowledge}`,
            icon: Search,
            permission: "knowledge.read",
          },
          {
            id: "project-settings",
            label: "Cài đặt dự án",
            href: `${root}/${PROJECT_SECTION_SLUGS.settings}`,
            icon: Activity,
            anyPermission: PROJECT_SETTINGS_PERMISSIONS,
          },
        ],
      }
    : {
        project: [],
        requirements: [],
        design: [],
        execution: [],
        quality: [],
        resources: [],
      };
  return [
    {
      label: "Không gian làm việc",
      items: [
        {
          id: "projects",
          label: "Dự án",
          href: PROJECTS_ROUTE,
          icon: FolderKanban,
          requireAuth: true,
        },
        {
          id: "operations",
          label: "Vận hành nền tảng",
          href: OPERATIONS_ROUTE,
          icon: Activity,
          requireAdmin: true,
        },
      ],
    },
    { label: "Dự án", items: projectItems.project },
    { label: "Bảo đảm yêu cầu", items: projectItems.requirements },
    {
      label: "Kế hoạch kiểm thử",
      items: projectItems.execution.filter((item) => item.id === "test-plans"),
    },
    {
      label: "Thiết kế kiểm thử",
      items: [
        ...projectItems.design.filter((item) => item.id === "test-analysis"),
        ...(projectId
          ? [
              {
                id: "test-scenarios",
                label: "Kịch bản kiểm thử",
                href: `${root}/${PROJECT_SECTION_SLUGS.testCases}/kich-ban`,
                icon: TestTube2,
                permission: "testscenario.read",
                permissions: ["testcase.read"],
              },
            ]
          : []),
        ...projectItems.design.filter((item) => item.id !== "test-analysis"),
      ],
    },
    {
      label: "Thực thi kiểm thử",
      items: projectItems.execution.filter((item) => item.id !== "test-plans"),
    },
    { label: "Theo dõi", items: projectItems.quality },
    { label: "Tài liệu và cài đặt", items: projectItems.resources },
    {
      label: "Tài khoản",
      items: [
        {
          id: "account-settings",
          label: "Tài khoản",
          href: "/cai-dat",
          icon: Settings,
          requireAuth: true,
        },
      ],
    },
  ];
}

export function availableNavigation(groups, user, permissions = null) {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canSeeNavigationItem(item, user, permissions)),
    }))
    .filter((group) => group.items.length > 0);
}
