import assert from "node:assert/strict";
import test from "node:test";
import {
  canSeeNavigationItem,
  canOpenNavigationPath,
  canOpenRoleRestrictedPath,
  canRenderProtectedRoute,
  hasNavigationRole,
  legacyProjectRouteItems,
  projectSearchRouteItem,
} from "./navigationAccess.mjs";

const groups = [
  {
    items: [
      { id: "project", href: "/du-an/p1", permission: "project.read" },
      { id: "requirements", href: "/du-an/p1/yeu-cau", permission: "requirement.read" },
      {
        id: "assurance",
        href: "/du-an/p1/ho-so-dam-bao",
        permissions: ["requirement.read", "testcase.read"],
      },
      {
        id: "reports",
        href: "/du-an/p1/bao-cao",
        anyPermission: ["report.read", "analytics.read"],
      },
    ],
  },
];

test("direct nested route resolves to its most specific permission", () => {
  const access = canOpenNavigationPath(groups, "/du-an/p1/yeu-cau/REQ-1", ["project.read"]);
  assert.equal(access.item.id, "requirements");
  assert.equal(access.allowed, false);
});

test("project search route requires knowledge access and is reachable for authorized members", () => {
  const searchItem = projectSearchRouteItem("p1");
  assert.equal(searchItem.href, "/du-an/p1/tim-kiem");
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/tim-kiem", [], [searchItem]).allowed,
    false,
  );
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/tim-kiem", ["knowledge.read"], [searchItem]).allowed,
    true,
  );
});

test("planning group entry route uses the same permission as its default destination", () => {
  const planningGroups = [
    {
      href: "/du-an/p1/lap-ke-hoach",
      defaultActiveItemId: "backlog",
      items: [
        { id: "backlog", href: "/du-an/p1/lap-ke-hoach/backlog", permission: "project.read" },
      ],
    },
  ];
  const denied = canOpenNavigationPath(planningGroups, "/du-an/p1/lap-ke-hoach", []);
  assert.equal(denied.item.id, "backlog");
  assert.equal(denied.allowed, false);
  assert.equal(
    canOpenNavigationPath(planningGroups, "/du-an/p1/lap-ke-hoach", ["project.read"]).allowed,
    true,
  );
});

test("legacy project URLs reach their permission-checked canonical redirect", () => {
  const legacyRoutes = legacyProjectRouteItems("p1", {
    projectTasksSlug: "cong-viec",
    testDesignSlug: "thiet-ke-kiem-thu",
  });
  const tasks = canOpenNavigationPath(
    groups,
    "/du-an/p1/cong-viec",
    ["project.read"],
    legacyRoutes,
  );
  const design = canOpenNavigationPath(
    groups,
    "/du-an/p1/thiet-ke-kiem-thu",
    ["testcase.read"],
    legacyRoutes,
  );
  assert.equal(tasks.item.id, "legacy-project-tasks");
  assert.equal(tasks.allowed, true);
  assert.equal(design.item.id, "legacy-test-design");
  assert.equal(design.allowed, true);
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/cong-viec", ["testcase.read"], legacyRoutes).allowed,
    false,
  );
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/thiet-ke-kiem-thu", ["project.read"], legacyRoutes)
      .allowed,
    false,
  );
});

test("direct test design subroute uses its own permission before workspace renders", () => {
  const access = canOpenNavigationPath(
    groups,
    "/du-an/p1/ca-kiem-thu/ai",
    ["project.read", "testcase.read"],
    [
      {
        id: "test-case-ai",
        href: "/du-an/p1/ca-kiem-thu/ai",
        permissions: ["testcase.read"],
        anyPermission: ["ai.generate_testcase", "ai.generate_scenario"],
      },
    ],
  );
  assert.equal(access.item.id, "test-case-ai");
  assert.equal(access.allowed, false);
  assert.equal(
    canOpenNavigationPath(
      groups,
      "/du-an/p1/ca-kiem-thu/ai",
      ["testcase.read", "ai.generate_testcase"],
      [
        {
          id: "test-case-ai",
          href: "/du-an/p1/ca-kiem-thu/ai",
          permissions: ["testcase.read"],
          anyPermission: ["ai.generate_testcase", "ai.generate_scenario"],
        },
      ],
    ).allowed,
    true,
  );
});

test("route requiring multiple permissions stays hidden until all are granted", () => {
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/ho-so-dam-bao", ["requirement.read"]).allowed,
    false,
  );
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/ho-so-dam-bao", ["requirement.read", "testcase.read"])
      .allowed,
    true,
  );
});

test("route with alternative permissions opens for any one granted permission", () => {
  assert.equal(
    canOpenNavigationPath(groups, "/du-an/p1/bao-cao", ["analytics.read"]).allowed,
    true,
  );
  assert.equal(canOpenNavigationPath(groups, "/du-an/p1/bao-cao", []).allowed, false);
});

test("unlisted workspace routes fail closed instead of inheriting project read access", () => {
  const access = canOpenNavigationPath(groups, "/du-an/p1/not-a-known-page", []);
  assert.equal(access.item, null);
  assert.equal(access.allowed, false);
  assert.equal(canOpenNavigationPath(groups, "/du-an/p1", ["project.read"]).allowed, true);
});

test("project content stays hidden until permission lookup is complete", () => {
  assert.equal(
    canRenderProtectedRoute({
      requireAuth: true,
      isLoading: false,
      user: { id: "user-1" },
      projectId: "project-1",
      projectAccessReady: false,
      routeDenied: false,
    }),
    false,
  );
});

test("a denied project route does not render while redirecting", () => {
  assert.equal(
    canRenderProtectedRoute({
      requireAuth: true,
      isLoading: false,
      user: { id: "user-1" },
      projectId: "project-1",
      projectAccessReady: true,
      routeDenied: true,
    }),
    false,
  );
});

test("a permitted project route renders after permission lookup", () => {
  assert.equal(
    canRenderProtectedRoute({
      requireAuth: true,
      isLoading: false,
      user: { id: "user-1" },
      projectId: "project-1",
      projectAccessReady: true,
      routeDenied: false,
    }),
    true,
  );
});

test("a role-restricted global route does not render for a non-admin", () => {
  const item = { requireAdmin: true };
  assert.equal(hasNavigationRole(item, { id: "user-1", system_role: "USER" }), false);
  assert.equal(hasNavigationRole(item, { id: "admin-1", system_role: "ADMIN" }), true);
  assert.equal(
    canRenderProtectedRoute({
      requireAuth: true,
      isLoading: false,
      user: { id: "user-1", system_role: "USER" },
      projectId: "",
      projectAccessReady: true,
      routeDenied: true,
    }),
    false,
  );
});

test("authenticated navigation items stay hidden on public pages", () => {
  const projects = { id: "projects", requireAuth: true };
  assert.equal(canSeeNavigationItem(projects, null, null), false);
  assert.equal(canSeeNavigationItem(projects, { id: "user-1" }, null), true);
});

test("platform operations direct route is restricted to authenticated platform admins", () => {
  const globalGroups = [
    {
      items: [{ id: "operations", href: "/van-hanh", requireAdmin: true }],
    },
  ];
  assert.equal(canOpenRoleRestrictedPath(globalGroups, "/van-hanh", null).allowed, false);
  assert.equal(
    canOpenRoleRestrictedPath(globalGroups, "/van-hanh", { id: "user-1", system_role: "USER" })
      .allowed,
    false,
  );
  assert.equal(
    canOpenRoleRestrictedPath(globalGroups, "/van-hanh", { id: "admin-1", system_role: "ADMIN" })
      .allowed,
    true,
  );
});
