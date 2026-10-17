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
  ListTodo,
  Columns3,
  Map,
  Flag,
  ClipboardCheck,
  Database,
  FolderTree,
  History,
  MessageSquareMore,
  Puzzle,
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

export function navigationGroupsFor(pathname, planningMethod = null) {
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
        planning: [
          {
            id: "backlog",
            label: "Danh sách chờ",
            href: `${root}/${PROJECT_SECTION_SLUGS.planning}/backlog`,
            icon: ListTodo,
            permission: "project.read",
          },
          {
            id: "work-board",
            label: "Bảng công việc",
            href: `${root}/${PROJECT_SECTION_SLUGS.planning}/board`,
            icon: Columns3,
            permission: "project.read",
          },
          ...(planningMethod === "SCRUM"
            ? [
                {
                  id: "sprint",
                  label: "Đợt lặp",
                  href: `${root}/${PROJECT_SECTION_SLUGS.planning}/sprint`,
                  icon: ListTodo,
                  permission: "project.read",
                },
              ]
            : []),
          {
            id: "roadmap",
            label: "Lộ trình",
            href: `${root}/${PROJECT_SECTION_SLUGS.planning}/roadmap`,
            icon: Map,
            permission: "project.read",
          },
          {
            id: "releases",
            label: "Bản phát hành",
            href: `${root}/${PROJECT_SECTION_SLUGS.releases}`,
            icon: Flag,
            permission: "release.read",
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
            id: "assurance",
            label: "Hồ sơ đảm bảo",
            href: `${root}/${PROJECT_SECTION_SLUGS.assurance}`,
            icon: ClipboardCheck,
            permission: "requirement.read",
          },
          {
            id: "clarifications",
            label: "Phiếu làm rõ",
            href: `${root}/${PROJECT_SECTION_SLUGS.clarifications}`,
            icon: MessageSquareMore,
            permission: "requirement.read",
          },
          {
            id: "changes",
            label: "Tác động thay đổi",
            href: `${root}/${PROJECT_SECTION_SLUGS.changes}`,
            icon: GitCompareArrows,
            permission: "impact.read",
          },
        ],
        design: [
          {
            id: "test-repository",
            label: "Kho kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testRepository}`,
            icon: FolderTree,
            permission: "testcase.read",
          },
          {
            id: "test-cases",
            label: "Ca kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testCases}`,
            icon: TestTube2,
            permission: "testcase.read",
          },
          {
            id: "reusable-steps",
            label: "Bước dùng lại",
            href: `${root}/${PROJECT_SECTION_SLUGS.reusableSteps}`,
            icon: Puzzle,
            permission: "testcase.read",
          },
          {
            id: "test-data",
            label: "Dữ liệu kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testData}`,
            icon: Database,
            permission: "testcase.read",
          },
          {
            id: "test-sets",
            label: "Bộ kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testSets}`,
            icon: Archive,
            permission: "testcase.read",
          },
        ],
        execution: [
          {
            id: "test-plans",
            label: "Kế hoạch kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testPlans}`,
            icon: ClipboardCheck,
            permission: "testrun.read",
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
            label: "Tự động hóa",
            href: `${root}/${PROJECT_SECTION_SLUGS.automation}`,
            icon: BrainCircuit,
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
            permission: "report.read",
          },
          {
            id: "audit",
            label: "Nhật ký audit",
            href: `${root}/${PROJECT_SECTION_SLUGS.audit}`,
            icon: History,
            permission: "project.settings.manage",
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
            permission: "project.settings.manage",
          },
        ],
      }
    : {
        project: [],
        planning: [],
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
    { label: "Lập kế hoạch", items: projectItems.planning },
    { label: "Bảo đảm yêu cầu", items: projectItems.requirements },
    { label: "Thiết kế kiểm thử", items: projectItems.design },
    { label: "Kế hoạch và thực thi", items: projectItems.execution },
    { label: "Theo dõi", items: projectItems.quality },
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
