import { expect, test } from "@playwright/test";
import {
  navigationGroupsFor,
  testCaseSubsectionItems,
} from "../shared/components/layout/navigation.js";
import { PROJECT_SECTION_SLUGS } from "../features/testing/routes.js";
import {
  hasNavigationPermission,
  legacyProjectRouteItems,
  projectSearchRouteItem,
} from "../shared/components/layout/navigationAccess.mjs";

const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const apiBaseUrl = process.env.E2E_API_URL || process.env.NEXT_PUBLIC_API_URL || "";
const projectId = process.env.E2E_LIVE_PROJECT_ID || "";
const enabled = process.env.E2E_LIVE_READONLY === "true";
const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
function isLoopbackUrl(value) {
  if (!value) return false;
  try {
    return loopbackHosts.has(new URL(value).hostname);
  } catch {
    return false;
  }
}

const localApp = isLoopbackUrl(appBaseUrl);
const localApi = isLoopbackUrl(apiBaseUrl);
const viewportMatrix = [
  { name: "desktop-1920", width: 1920, height: 1080 },
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "desktop-1280", width: 1280, height: 800 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-390", width: 390, height: 844 },
];
const projectRoles = ["BA", "QA", "TESTER", "DEVELOPER", "VIEWER"].map((role) => ({
  role,
  token: process.env[`E2E_ROLE_${role}_TOKEN`],
}));
const adminToken = process.env.E2E_ROLE_ADMIN_TOKEN;

function unwrap(body) {
  return body?.data ?? body;
}

function localPath(url) {
  return new URL(url).pathname;
}

function projectWorkspaceRoutes(project) {
  const projectPath = `/du-an/${encodeURIComponent(projectId)}`;
  const groups = navigationGroupsFor(projectPath, project.planning_method || "SCRUM");
  const groupedRoutes = groups.flatMap((group) => {
    const routes = group.items;
    if (!group.href) return routes;
    const defaultRoute = routes.find((route) => route.id === group.defaultActiveItemId);
    return defaultRoute ? [...routes, { ...defaultRoute, href: group.href }] : routes;
  });
  const extras = [
    ...testCaseSubsectionItems(projectId),
    projectSearchRouteItem(projectId),
    ...legacyProjectRouteItems(projectId, {
      projectTasksSlug: PROJECT_SECTION_SLUGS.projectTasks,
      testDesignSlug: PROJECT_SECTION_SLUGS.testDesign,
    }).map((route) => ({
      ...route,
      redirectTo:
        route.id === "legacy-project-tasks"
          ? `${projectPath}/${PROJECT_SECTION_SLUGS.planning}/backlog`
          : `${projectPath}/${PROJECT_SECTION_SLUGS.testCases}`,
    })),
  ].filter(Boolean);
  const routesByHref = new Map();
  for (const route of [...groupedRoutes, ...extras]) {
    if (route.href?.startsWith(`${projectPath}/`) || route.href === projectPath) {
      if (!routesByHref.has(route.href)) routesByHref.set(route.href, route);
    }
  }
  return [...routesByHref.values()].sort((left, right) => left.href.localeCompare(right.href));
}

async function readIdentityAndProject(request, role, token) {
  const headers = { Authorization: `Bearer ${token}` };
  const identityResponse = await request.get(`${apiBaseUrl}/xac-thuc/ca-nhan`, { headers });
  expect(identityResponse.status(), `${role} session must be accepted`).toBe(200);
  const identity = unwrap(await identityResponse.json());

  if (role === "ADMIN") {
    expect(identity.system_role).toBe("ADMIN");
    return { identity, project: null };
  }

  const projectResponse = await request.get(`${apiBaseUrl}/kiem-thu/du-an/${projectId}`, {
    headers,
  });
  expect(projectResponse.status(), `${role} must be able to read the selected project`).toBe(200);
  const project = unwrap(await projectResponse.json());
  expect(String(project?._id)).toBe(projectId);
  const membershipRoles = project?.current_membership?.project_roles || [
    project?.current_membership?.project_role,
  ];
  expect(membershipRoles, `${role} token must have the expected project role`).toContain(role);
  expect(project.current_permissions).toContain("project.read");
  return { identity, project };
}

async function prepareAuthenticatedPage(page, token) {
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
}

for (const { role, token } of projectRoles) {
  test(`live read-only workspace smoke: ${role} routes and responsive layout`, async ({
    browser,
    request,
  }, testInfo) => {
    test.skip(!enabled, "live read-only suite is opt-in");
    expect(localApp, "E2E_BASE_URL must point to a loopback host").toBe(true);
    expect(localApi, "E2E_API_URL must point to a loopback host").toBe(true);
    expect(projectId, "E2E_LIVE_PROJECT_ID is required").not.toBe("");
    expect(token, `E2E_ROLE_${role}_TOKEN is required`).toBeTruthy();

    const { project } = await readIdentityAndProject(request, role, token);
    const browserContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await browserContext.newPage();
    const pageErrors = [];
    const writeRequests = [];
    const viewportEvidence = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("request", (browserRequest) => {
      if (!["GET", "HEAD", "OPTIONS"].includes(browserRequest.method())) {
        writeRequests.push({ method: browserRequest.method(), url: browserRequest.url() });
      }
    });

    try {
      await prepareAuthenticatedPage(page, token);
      await page.goto(`${appBaseUrl}/du-an/${encodeURIComponent(projectId)}`, {
        waitUntil: "domcontentloaded",
      });
      await expect(page.locator("#main-content")).toBeVisible();
      await expect(page.getByText(project.name, { exact: true }).first()).toBeVisible();

      const permissions = project.current_permissions;
      const routes = projectWorkspaceRoutes(project);
      expect(
        routes.length,
        "workspace route capability metadata must be discoverable",
      ).toBeGreaterThan(0);
      for (const route of routes) {
        const target = route.href;
        await page.goto(`${appBaseUrl}${target}`, { waitUntil: "domcontentloaded" });
        const allowed = hasNavigationPermission(route, permissions);
        const expectedPath = allowed
          ? route.redirectTo || target
          : `/du-an/${encodeURIComponent(projectId)}`;
        await expect
          .poll(() => localPath(page.url()), {
            message: `${role}: ${route.label || route.id} permission gate`,
          })
          .toBe(expectedPath);
        if (allowed) {
          await expect(page.locator("#main-content h1").first()).toBeVisible();
        }
      }

      await page.goto(`${appBaseUrl}/du-an/${encodeURIComponent(projectId)}`, {
        waitUntil: "domcontentloaded",
      });
      await expect(page.locator("#main-content")).toBeVisible();

      for (const viewport of viewportMatrix) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await expect(page.locator("#main-content")).toBeVisible();
        const layout = await page.evaluate(() => ({
          viewportWidth: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          mainWidth: Math.round(
            document.querySelector("#main-content")?.getBoundingClientRect().width || 0,
          ),
        }));
        viewportEvidence.push({ ...viewport, ...layout });
        expect(
          layout.documentWidth,
          `${role} ${viewport.name} document overflow`,
        ).toBeLessThanOrEqual(layout.viewportWidth + 1);
        expect(layout.bodyWidth, `${role} ${viewport.name} body overflow`).toBeLessThanOrEqual(
          layout.viewportWidth + 1,
        );

        if (viewport.width <= 768) {
          const trigger = page.getByRole("button", { name: "Mở điều hướng" });
          await expect(trigger).toBeVisible();
          await trigger.click();
          const drawer = page.getByRole("dialog", { name: "Điều hướng chính" });
          await expect(drawer).toBeVisible();
          await page.keyboard.press("Escape");
          await expect(drawer).toHaveCount(0);
          await expect(trigger).toBeFocused();
        }

        if ([1920, 390].includes(viewport.width)) {
          await testInfo.attach(`${role}-${viewport.name}.png`, {
            body: await page.screenshot({ fullPage: true }),
            contentType: "image/png",
          });
        }
      }

      expect(writeRequests, `${role} smoke must remain read-only`).toEqual([]);
      expect(pageErrors, `${role} browser runtime errors`).toEqual([]);
      await testInfo.attach(`${role}-route-viewport-evidence.json`, {
        body: Buffer.from(
          JSON.stringify(
            {
              role,
              project_id: projectId,
              permissions,
              routes: routes.map((route) => ({
                id: route.id,
                name: route.label || route.id,
                path: route.href,
                required_permission: route.permission || null,
                required_permissions: route.permissions || [],
                any_permission: route.anyPermission || [],
                allowed: hasNavigationPermission(route, permissions),
              })),
              viewports: viewportEvidence,
              page_errors: pageErrors,
              write_requests: writeRequests,
            },
            null,
            2,
          ),
        ),
        contentType: "application/json",
      });
    } finally {
      await browserContext.close();
    }
  });
}

test("live read-only platform admin route gate", async ({ browser, request }, testInfo) => {
  test.skip(!enabled, "live read-only suite is opt-in");
  expect(localApp, "E2E_BASE_URL must point to a loopback host").toBe(true);
  expect(localApi, "E2E_API_URL must point to a loopback host").toBe(true);
  expect(adminToken, "E2E_ROLE_ADMIN_TOKEN is required").toBeTruthy();
  const { identity } = await readIdentityAndProject(request, "ADMIN", adminToken);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const writes = [];
  page.on("request", (browserRequest) => {
    if (!["GET", "HEAD", "OPTIONS"].includes(browserRequest.method())) {
      writes.push({ method: browserRequest.method(), url: browserRequest.url() });
    }
  });
  try {
    await prepareAuthenticatedPage(page, adminToken);
    await page.goto(`${appBaseUrl}/van-hanh`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#main-content")).toBeVisible();
    await expect.poll(() => localPath(page.url())).toBe("/van-hanh");
    expect(writes).toEqual([]);
    await testInfo.attach("admin-route-evidence.json", {
      body: Buffer.from(
        JSON.stringify(
          { system_role: identity.system_role, route: localPath(page.url()), writes },
          null,
          2,
        ),
      ),
      contentType: "application/json",
    });
  } finally {
    await context.close();
  }
});

test("live read-only suite requires loopback app and API targets", async () => {
  test.skip(!enabled, "live read-only suite is opt-in");
  expect(localApp, "E2E_BASE_URL must point to a loopback host").toBe(true);
  expect(localApi, "E2E_API_URL must point to a loopback host").toBe(true);
});
