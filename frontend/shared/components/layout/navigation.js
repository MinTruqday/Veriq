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

export const PROJECT_SETTINGS_PERMISSIONS = [
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
  "project.connector.read",
  "cicd.read",
  "webhook.project.read",
];

export function hasNavigationPermission(item, permissions) {
  const granted = Array.isArray(permissions) ? permissions : [];
  return (
    (!item.permission || granted.includes(item.permission)) &&
    (item.permissions || []).every((permission) => granted.includes(permission)) &&
    (!item.anyPermission || item.anyPermission.some((permission) => granted.includes(permission)))
  );
}

export function testCaseSubsectionItems(projectId) {
  const root = projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases);
  return [
    { id: "cases", label: "Ca kiểm thử", href: root, permission: "testcase.read" },
    {
      id: "adequacy",
      label: "Hồ sơ đảm bảo",
      href: `${root}/do-day-du`,
      permissions: ["requirement.read", "testcase.read"],
    },
    {
      id: "ai",
      label: "Tạo ca bằng AI",
      href: `${root}/ai`,
      anyPermission: ["ai.generate_testcase", "ai.generate_scenario", "testcase.duplicate_check"],
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
      anyPermission: ["ai.generate_automation_script", "automation.script.export"],
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
      group.items.some((item) => item.id === "test-repository"),
    )?.items || [];
  return designItems.filter((item) =>
    ["test-repository", "test-cases", "reusable-steps", "test-data", "test-sets"].includes(item.id),
  );
}

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
            permissions: ["testcase.read"],
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
            label: "Phân tích thay đổi",
            href: `${root}/${PROJECT_SECTION_SLUGS.changes}`,
            icon: GitCompareArrows,
            anyPermission: ["changeset.read", "proposal.read"],
          },
        ],
        design: [
          {
            id: "test-strategy",
            label: "Chiến lược kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.governance}`,
            icon: ClipboardCheck,
            permission: "teststrategy.read",
          },
          {
            id: "test-analysis",
            label: "Phân tích kiểm thử",
            href: `${root}/${PROJECT_SECTION_SLUGS.testAnalysis}`,
            icon: TestTube2,
            permission: "testcondition.read",
          },
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
            label: "Tự động hóa",
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
              "coverage.read",
              "teststatusreport.read",
              "testcompletion.read",
              "qualityevaluation.read",
              "measurement.read",
              "processimprovement.read",
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
            label: "Tự động hóa AI",
            href: `${root}/${PROJECT_SECTION_SLUGS.aiReview}`,
            icon: BrainCircuit,
            permission: "proposal.read",
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
    {
      label: "Lập kế hoạch",
      href: projectId ? `${root}/${PROJECT_SECTION_SLUGS.planning}` : "",
      defaultActiveItemId: "backlog",
      items: projectItems.planning,
    },
    { label: "Bảo đảm yêu cầu", items: projectItems.requirements },
    { label: "Thiết kế kiểm thử", items: projectItems.design },
    { label: "Kế hoạch và thực thi", items: projectItems.execution },
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
      items: group.items.filter(
        (item) =>
          (!item.requireAuth || user) &&
          (!item.requireAdmin || user?.system_role === "ADMIN") &&
          hasNavigationPermission(item, permissions),
      ),
    }))
    .filter((group) => group.items.length > 0);
}
