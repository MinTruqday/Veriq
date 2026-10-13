import {
  Activity,
  BrainCircuit,
  Bug,
  BarChart3,
  FileCheck2,
  FolderKanban,
  GitCompareArrows,
  Gauge,
  LayoutDashboard,
  Network,
  PlayCircle,
  Search,
  ShieldCheck,
  ScanSearch,
  Settings,
  TestTube2,
  ListTodo,
} from "lucide-react";
import {
  OPERATIONS_ROUTE,
  PROJECTS_ROUTE,
  PROJECT_SECTION_SLUGS,
  projectRoute,
} from "@/features/testing/routes";

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
          {
            id: "requirements",
            label: "Yêu cầu",
            href: `${root}/${PROJECT_SECTION_SLUGS.requirements}`,
            icon: FileCheck2,
            permission: "requirement.read",
          },
          {
            id: "test-analysis",
            label: "Phân tích kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testAnalysis}`,
            icon: ScanSearch,
            permission: "testcondition.read",
          },
          {
            id: "test-design",
            label: "Thiết kế kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testDesign}`,
            icon: TestTube2,
            permission: "testcase.read",
          },
          {
            id: "project-tasks",
            label: "Công việc dự án",
            href: `${root}/${PROJECT_SECTION_SLUGS.projectTasks}`,
            icon: ListTodo,
            permission: "project.read",
          },
        ],
        planning: [
          {
            id: "governance",
            label: "Chiến lược kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.governance}`,
            icon: ShieldCheck,
            permission: "teststrategy.read",
          },
          {
            id: "execution",
            label: "Kế hoạch và thực thi",
            href: `${root}/${PROJECT_SECTION_SLUGS.execution}`,
            icon: PlayCircle,
            permission: "testrun.read",
          },
          {
            id: "monitoring",
            label: "Giám sát và kiểm soát",
            href: `${root}/${PROJECT_SECTION_SLUGS.monitoring}`,
            icon: Gauge,
            permission: "testmonitor.read",
          },
          {
            id: "traceability",
            label: "Truy vết",
            href: `${root}/${PROJECT_SECTION_SLUGS.traceability}`,
            icon: Network,
            permission: "trace.read",
          },
        ],
        quality: [
          {
            id: "changes",
            label: "Phân tích thay đổi",
            href: `${root}/${PROJECT_SECTION_SLUGS.changes}`,
            icon: GitCompareArrows,
            permission: "impact.read",
          },
          {
            id: "ai-review",
            label: "Rà soát đề xuất AI",
            href: `${root}/${PROJECT_SECTION_SLUGS.aiReview}`,
            icon: BrainCircuit,
            permission: "proposal.read",
          },
          {
            id: "defects",
            label: "Lỗi",
            href: `${root}/${PROJECT_SECTION_SLUGS.defects}`,
            icon: Bug,
            permission: "defect.read",
          },
          {
            id: "reports",
            label: "Báo cáo",
            href: `${root}/${PROJECT_SECTION_SLUGS.reports}`,
            icon: BarChart3,
            permission: "report.read",
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
            label: "Cài đặt và nhật ký",
            href: `${root}/${PROJECT_SECTION_SLUGS.settings}`,
            icon: Activity,
            permission: "project.settings.manage",
          },
        ],
      }
    : { project: [], planning: [], quality: [], resources: [] };
  return [
    {
      label: "Không gian làm việc",
      items: [
        { id: "projects", label: "Dự án", href: PROJECTS_ROUTE, icon: FolderKanban },
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
    { label: "Lập kế hoạch và thực thi", items: projectItems.planning },
    { label: "Chất lượng và thay đổi", items: projectItems.quality },
    { label: "Tri thức và cấu hình", items: projectItems.resources },
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
      items: group.items.filter(
        (item) =>
          (!item.requireAuth || user) &&
          (!item.requireAdmin || user?.system_role === "ADMIN") &&
          (!item.permission || permissions?.includes(item.permission)),
      ),
    }))
    .filter((group) => group.items.length > 0);
}
