import {
  Activity,
  Bug,
  BarChart3,
  ClipboardCheck,
  FileCheck2,
  FolderKanban,
  LayoutDashboard,
  PlayCircle,
  Search,
  Settings,
  TestTube2,
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
  "environment.read",
  "environment.create",
  "environment.update",
  "environment.archive",
];

export function testCaseSubsectionItems(projectId, includeLegacy = false) {
  const root = projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases);
  const items = [{ id: "cases", label: "Ca kiểm thử", href: root, permission: "testcase.read" }];
  if (!includeLegacy) return items;
  return [
    ...items,
    {
      id: "sets",
      label: "Bộ kiểm thử",
      href: `${root}/bo-kiem-thu`,
      permission: "testsuite.read",
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
  return designItems.filter((item) => item.id === "test-cases");
}

export function projectIdFromPath(pathname) {
  if (pathname === `${PROJECTS_ROUTE}/tao-moi`) return "";
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
            id: "defects",
            label: "Lỗi",
            href: `${root}/${PROJECT_SECTION_SLUGS.defects}`,
            icon: Bug,
            permission: "defect.read",
          },
        ],
        quality: [
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
        ],
        resources: [
          {
            id: "project-documents",
            label: "Tài liệu dự án",
            href: `${root}/${PROJECT_SECTION_SLUGS.documentReader}`,
            icon: FileCheck2,
            permission: "requirement_document.read",
          },
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
          label: "Quản lý tài khoản",
          href: OPERATIONS_ROUTE,
          icon: Activity,
          requireAdmin: true,
        },
      ],
    },
    { label: "Tổng quan", items: projectItems.project },
    {
      label: "Bảo đảm yêu cầu",
      items: projectItems.requirements,
    },
    {
      label: "Kế hoạch kiểm thử",
      items: projectItems.execution.filter((item) => item.id === "test-plans"),
    },
    {
      label: "Thiết kế kiểm thử",
      items: projectItems.design.filter((item) => item.id === "test-cases"),
    },
    {
      label: "Thực thi kiểm thử",
      items: [
        ...projectItems.execution.filter(
          (item) =>
            item.id !== "test-plans" &&
            item.id !== "automation" &&
            item.id !== "execution-overview",
        ),
      ],
    },
    {
      label: "Báo cáo",
      items: projectItems.quality.filter((item) => item.id === "reports"),
    },
    { label: "Tài liệu", items: projectItems.resources },
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
