import { expect, test } from "@playwright/test";

const projectId = process.env.LIVE_COMPARE_PROJECT_ID;
const apiToken = process.env.LIVE_COMPARE_TOKEN;
const saveDraftId = process.env.LIVE_COMPARE_SAVE_DRAFT_ID;
const saveTestCaseKey = process.env.LIVE_COMPARE_SAVE_TEST_CASE_KEY;
const conflictDraftId = process.env.LIVE_COMPARE_CONFLICT_DRAFT_ID;
const conflictTestCaseKey = process.env.LIVE_COMPARE_CONFLICT_TEST_CASE_KEY;
const fixtureNamespace = process.env.LIVE_COMPARE_FIXTURE_NAMESPACE?.trim();
const originalTitle = process.env.LIVE_COMPARE_ORIGINAL_TITLE || "Tên ca gốc đang dùng";
const proposalTitle = process.env.LIVE_COMPARE_PROPOSAL_TITLE || "Tên ca AI đề xuất";
const backendUrl = process.env.LIVE_COMPARE_BACKEND_URL || "http://localhost:8017";
const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const frontendApiUrl =
  process.env.E2E_FRONTEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

function parsedUrl(value) {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

const parsedBackendUrl = parsedUrl(backendUrl);
const parsedAppUrl = parsedUrl(appBaseUrl);
const parsedFrontendApiUrl = parsedUrl(frontendApiUrl);
const localApiHost = Boolean(parsedBackendUrl && loopbackHosts.has(parsedBackendUrl.hostname));
const localAppHost = Boolean(parsedAppUrl && loopbackHosts.has(parsedAppUrl.hostname));
const localFrontendApiHost = Boolean(
  parsedFrontendApiUrl && loopbackHosts.has(parsedFrontendApiUrl.hostname),
);
const isolatedFixture =
  process.env.E2E_DISPOSABLE_DATABASE === "true" &&
  process.env.LIVE_COMPARE_DISPOSABLE_FIXTURE === "true" &&
  localApiHost &&
  localAppHost &&
  localFrontendApiHost &&
  Boolean(fixtureNamespace) &&
  projectId?.startsWith("PRJ-E2E-") &&
  projectId.includes(fixtureNamespace) &&
  saveDraftId?.startsWith("DRAFT-E2E-") &&
  saveDraftId.includes(fixtureNamespace) &&
  conflictDraftId?.startsWith("DRAFT-E2E-") &&
  conflictDraftId.includes(fixtureNamespace) &&
  saveDraftId !== conflictDraftId &&
  [saveTestCaseKey, conflictTestCaseKey].every(
    (key) => key?.startsWith("TC-E2E-") && key.includes(fixtureNamespace),
  ) &&
  saveTestCaseKey !== conflictTestCaseKey;
const liveApiEnabled = process.env.E2E_LIVE_READONLY === "true" || isolatedFixture;

async function verifyFixture(request, draftId, testCaseKey) {
  const headers = { Authorization: `Bearer ${apiToken}` };
  const projectResponse = await request.get(`${backendUrl}/kiem-thu/du-an/${projectId}`, {
    headers,
  });
  expect(projectResponse.status(), "disposable project fixture must be readable").toBe(200);
  const projectBody = await projectResponse.json();
  const project = projectBody?.data ?? projectBody;
  expect(String(project?._id), "fixture project ID must match the isolated namespace").toBe(
    projectId,
  );
  expect(projectId).toContain(fixtureNamespace);
  expect(
    project?.current_membership?.project_roles || [project?.current_membership?.project_role],
  ).toContain("QA");
  expect(project?.current_permissions).toContain("testcase.update");

  const draftResponse = await request.get(
    `${backendUrl}/kiem-thu/ban-nhap-ca-kiem-thu/${draftId}`,
    { headers },
  );
  expect(draftResponse.status(), "disposable Test Case draft must be readable").toBe(200);
  const draftBody = await draftResponse.json();
  const draft = draftBody?.data ?? draftBody;
  expect(String(draft?._id), "fixture draft ID must match the isolated namespace").toBe(draftId);
  expect(draft?.project_id, "fixture draft must belong to the isolated project").toBe(projectId);
  expect(draft?.test_case_key, "fixture Test Case key must match the isolated namespace").toBe(
    testCaseKey,
  );
  expect(draft?.status, "fixture must be an editable draft").toBe("DRAFT");
  return { project, draft };
}

test("live Testing API rejects anonymous compare and merge requests", async ({ request }) => {
  test.skip(!liveApiEnabled || !localApiHost, "live API checks are opt-in and require loopback");
  const projectIdWithoutSession = "PRJ-E2E-ANONYMOUS-NO-DATA";
  const draftIdWithoutSession = "DRAFT-E2E-ANONYMOUS-NO-DATA";

  const listResponse = await request.get(
    `${backendUrl}/kiem-thu/du-an/${projectIdWithoutSession}/ban-nhap-ca-kiem-thu`,
  );
  expect(listResponse.status()).toBe(401);
  expect(await listResponse.json()).toMatchObject({ error: { code: "AUTH_REQUIRED" } });

  const mergeResponse = await request.post(
    `${backendUrl}/kiem-thu/ban-nhap-ca-kiem-thu/${draftIdWithoutSession}/luu-ban-ghep`,
    { data: {} },
  );
  expect(mergeResponse.status()).toBe(401);
  expect(await mergeResponse.json()).toMatchObject({ error: { code: "AUTH_REQUIRED" } });
});

test("QA compares and saves a merged Test Case through the live Testing API", async ({
  page,
  request,
}) => {
  test.skip(
    !isolatedFixture || !apiToken,
    "requires a disposable local database and two distinct namespaced draft fixtures; this test writes a draft",
  );
  await verifyFixture(request, saveDraftId, saveTestCaseKey);

  const livePaths = new Set([
    `/kiem-thu/du-an/${projectId}`,
    `/kiem-thu/du-an/${projectId}/ca-kiem-thu`,
    `/kiem-thu/du-an/${projectId}/ban-nhap-ca-kiem-thu`,
    `/kiem-thu/ban-nhap-ca-kiem-thu/${saveDraftId}/so-sanh`,
    `/kiem-thu/ban-nhap-ca-kiem-thu/${saveDraftId}/luu-ban-ghep`,
  ]);
  const liveResponses = [];

  await page.context().addCookies([{ name: "token", value: apiToken, url: appBaseUrl }]);
  await page.addInitScript((token) => localStorage.setItem("veriq_token", token), apiToken);
  await page.route(`${parsedFrontendApiUrl.origin}/**`, async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname.startsWith("/xac-thuc/")) {
      const response = await route.fetch();
      liveResponses.push({
        path: requestUrl.pathname,
        status: response.status(),
        request_id: response.headers()["x-request-id"] || response.headers()["x-correlation-id"],
      });
      await route.fulfill({ response });
      return;
    }
    if (livePaths.has(requestUrl.pathname)) {
      const response = await route.fetch({
        url: `${backendUrl}${requestUrl.pathname}${requestUrl.search}`,
      });
      const responseHeaders = response.headers();
      liveResponses.push({
        path: requestUrl.pathname,
        status: response.status(),
        request_id: responseHeaders["x-request-id"] || responseHeaders["x-correlation-id"],
      });
      await route.fulfill({ response });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], status: "SUCCESS" }),
    });
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("cell", { name: saveTestCaseKey }).first()).toBeVisible();
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(page.getByRole("heading", { name: "So sánh và ghép ca kiểm thử" })).toBeVisible();
  await expect(page.getByText(originalTitle, { exact: true }).first()).toBeVisible();
  await expect(page.getByText(proposalTitle, { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Dùng đề xuất AI" }).first().click();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(
    page.getByText("Đã lưu bản ghép. Ca cần được rà soát lại trước khi duyệt."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Gửi rà soát" }).first()).toBeVisible();
  await expect
    .poll(() =>
      liveResponses.some((item) => item.path.endsWith("/luu-ban-ghep") && item.status === 200),
    )
    .toBe(true);
  expect(
    liveResponses.some((item) => item.path.endsWith("/ca-kiem-thu") && item.status === 200),
  ).toBe(true);
  await page.getByRole("button", { name: "Đóng", exact: true }).last().click();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("cell", { name: originalTitle, exact: true }).first()).toBeVisible();
  await expect(page.getByRole("cell", { name: proposalTitle, exact: true }).first()).toBeVisible();
  expect(liveResponses.some((item) => item.path.endsWith("/so-sanh") && item.status === 200)).toBe(
    true,
  );
  await test.info().attach("live-api-evidence.json", {
    body: Buffer.from(
      JSON.stringify({ case: test.info().title, requests: liveResponses }, null, 2),
    ),
    contentType: "application/json",
  });
});

test("QA keeps merged edits when another writer changes the draft revision", async ({
  page,
  request,
}) => {
  test.skip(
    !isolatedFixture || !apiToken,
    "requires a disposable local database and two distinct namespaced draft fixtures; this test writes a draft",
  );
  await verifyFixture(request, conflictDraftId, conflictTestCaseKey);

  const paths = new Set([
    "/kiem-thu/du-an/" + projectId,
    "/kiem-thu/du-an/" + projectId + "/ca-kiem-thu",
    "/kiem-thu/du-an/" + projectId + "/ban-nhap-ca-kiem-thu",
    "/kiem-thu/ban-nhap-ca-kiem-thu/" + conflictDraftId + "/so-sanh",
    "/kiem-thu/ban-nhap-ca-kiem-thu/" + conflictDraftId + "/luu-ban-ghep",
  ]);
  const saveResponses = [];
  const liveResponses = [];

  await page.context().addCookies([{ name: "token", value: apiToken, url: appBaseUrl }]);
  await page.addInitScript((token) => localStorage.setItem("veriq_token", token), apiToken);
  await page.route(`${parsedFrontendApiUrl.origin}/**`, async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname.startsWith("/xac-thuc/")) {
      const response = await route.fetch();
      const responseHeaders = response.headers();
      liveResponses.push({
        path: requestUrl.pathname,
        status: response.status(),
        request_id: responseHeaders["x-request-id"] || responseHeaders["x-correlation-id"],
      });
      await route.fulfill({ response });
      return;
    }
    if (paths.has(requestUrl.pathname)) {
      const response = await route.fetch({
        url: backendUrl + requestUrl.pathname + requestUrl.search,
      });
      const responseHeaders = response.headers();
      liveResponses.push({
        path: requestUrl.pathname,
        status: response.status(),
        request_id: responseHeaders["x-request-id"] || responseHeaders["x-correlation-id"],
      });
      if (requestUrl.pathname.endsWith("/luu-ban-ghep")) {
        saveResponses.push({ status: response.status(), body: await response.json() });
      }
      await route.fulfill({ response });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], status: "SUCCESS" }),
    });
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/du-an/" + projectId + "/ca-kiem-thu", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("cell", { name: conflictTestCaseKey }).first()).toBeVisible();
  await page.getByRole("cell", { name: conflictTestCaseKey }).first().click();
  await page.getByRole("button", { name: "So sánh / ghép bản gốc và AI" }).click();
  await expect(page.getByRole("heading", { name: "So sánh và ghép ca kiểm thử" })).toBeVisible();
  await page.getByRole("button", { name: "Lấy nội dung AI" }).click();

  const headers = { Authorization: "Bearer " + apiToken };
  const comparisonResponse = await request.get(
    backendUrl + "/kiem-thu/ban-nhap-ca-kiem-thu/" + conflictDraftId + "/so-sanh",
    { headers },
  );
  liveResponses.push({
    path: `/kiem-thu/ban-nhap-ca-kiem-thu/${conflictDraftId}/so-sanh`,
    status: comparisonResponse.status(),
    request_id:
      comparisonResponse.headers()["x-request-id"] ||
      comparisonResponse.headers()["x-correlation-id"],
  });
  expect(comparisonResponse.status()).toBe(200);
  const comparison = (await comparisonResponse.json()).data;
  const competingUpdate = await request.patch(
    backendUrl + "/kiem-thu/ban-nhap-ca-kiem-thu/" + conflictDraftId,
    {
      headers,
      data: {
        expected_revision: comparison.draft.revision,
        title: comparison.draft.title + " — cập nhật đồng thời",
      },
    },
  );
  liveResponses.push({
    path: `/kiem-thu/ban-nhap-ca-kiem-thu/${conflictDraftId}`,
    status: competingUpdate.status(),
    request_id:
      competingUpdate.headers()["x-request-id"] || competingUpdate.headers()["x-correlation-id"],
  });
  expect(competingUpdate.status()).toBe(200);

  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Nguồn hoặc bản nháp đã đổi" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Tải lại dữ liệu đối chiếu" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu bản ghép" })).toBeDisabled();
  await expect(page.getByText(proposalTitle, { exact: true }).last()).toBeVisible();
  await expect.poll(() => saveResponses.length).toBe(1);
  expect(saveResponses[0].status).toBe(409);
  expect(saveResponses[0].body?.error?.code).toBe("REVISION_CONFLICT");

  const persistedResponse = await request.get(
    backendUrl + "/kiem-thu/ban-nhap-ca-kiem-thu/" + conflictDraftId + "/so-sanh",
    { headers },
  );
  liveResponses.push({
    path: `/kiem-thu/ban-nhap-ca-kiem-thu/${conflictDraftId}/so-sanh`,
    status: persistedResponse.status(),
    request_id:
      persistedResponse.headers()["x-request-id"] ||
      persistedResponse.headers()["x-correlation-id"],
  });
  expect(persistedResponse.status()).toBe(200);
  const persisted = (await persistedResponse.json()).data.draft;
  expect(persisted.title).toBe(comparison.draft.title + " — cập nhật đồng thời");
  expect(persisted.revision).toBe(comparison.draft.revision + 1);
  await test.info().attach("live-api-evidence.json", {
    body: Buffer.from(
      JSON.stringify({ case: test.info().title, requests: liveResponses }, null, 2),
    ),
    contentType: "application/json",
  });
});
