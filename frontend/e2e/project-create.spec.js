import { expect, test } from "@playwright/test";

const apiBase = (
  process.env.E2E_FRONTEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");
const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const token = "project-create-e2e-session";

async function installProjectList(page, { createStatus = 409, projects = [] } = {}) {
  const state = { createdPayload: null, projects };
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: "ba-project-e2e", email: "ba@example.test", full_name: "BA kiểm thử" },
        }),
      });
      return;
    }
    if (pathname === "/kiem-thu/du-an/kha-nang") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { can_create_project: true } }),
      });
      return;
    }
    if (pathname === "/kiem-thu/du-an" && request.method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: state.projects }),
      });
      return;
    }
    if (pathname === "/kiem-thu/loi-moi-du-an") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [] }),
      });
      return;
    }
    if (pathname === "/kiem-thu/du-an" && request.method() === "POST") {
      if (createStatus < 400) {
        state.createdPayload = request.postDataJSON();
        state.projects = [
          {
            _id: "project-created-e2e",
            ...state.createdPayload,
            status: "ACTIVE",
            project_completion_percent: null,
            task_summary: null,
          },
        ];
      }
      await route.fulfill({
        status: createStatus,
        contentType: "application/json",
        body: JSON.stringify(
          createStatus < 400
            ? { data: { _id: "project-created-e2e" } }
            : {
                error: {
                  code: "INITIAL_QA_NOT_ELIGIBLE",
                  message: "Tài khoản được chọn không có vai trò QA",
                },
              },
        ),
      });
      return;
    }
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "E2E route was not mocked" } }),
    });
  });
  return state;
}

async function installProjectOverview(page, role) {
  const state = {
    project: {
      _id: "project-overview-e2e",
      key: "OVERVIEW",
      name: "Dự án tổng quan",
      description: "Kiểm tra hai chỉ số tiến độ",
      planning_method: "SCRUM",
      status: "ACTIVE",
      revision: 7,
      planned_start_at: "2026-10-27T00:00:00.000Z",
      planned_end_at: "2026-11-03T00:00:00.000Z",
      project_completion_percent: 40,
      task_summary: { completed: 2, total: 4, blocked: 1, completion_percent: 49 },
      current_membership: { project_role: role, project_roles: [role] },
      current_permissions: role === "QA" ? ["project.read", "project.update"] : ["project.read"],
    },
    updates: [],
  };
  const sessionToken = `project-overview-${role.toLowerCase()}-session`;
  await page.context().addCookies([{ name: "token", value: sessionToken, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), sessionToken);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: `${role.toLowerCase()}-overview-e2e`, email: "member@example.test" },
        }),
      });
      return;
    }
    if (pathname === `/kiem-thu/du-an/${state.project._id}` && request.method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: state.project }),
      });
      return;
    }
    if (
      pathname === `/kiem-thu/du-an/${state.project._id}/tien-do` &&
      request.method() === "PATCH"
    ) {
      const payload = request.postDataJSON();
      state.updates.push(payload);
      state.project = {
        ...state.project,
        project_completion_percent: payload.project_completion_percent,
        revision: state.project.revision + 1,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: state.project }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });
  return state;
}

test("project creation explains combined BA and QA roles and retains input after API denial", async ({
  page,
}) => {
  const requestErrors = [];
  page.on("requestfailed", (request) => requestErrors.push(request.url()));
  await installProjectList(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/du-an", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Tạo dự án" }).click();

  await expect(page.getByText(/cả vai trò BA và QA/i)).toBeVisible();
  await page.getByLabel("Mã dự án").fill("CHECKOUT");
  await page.getByLabel("Tài khoản QA đầu tiên").fill("qa@example.test");
  await page.getByLabel("Tên dự án").fill("Kiểm tra quyền tạo dự án");
  await page.getByLabel("Phương thức làm việc").selectOption("KANBAN");
  await page.getByLabel("Ngày bắt đầu dự kiến").fill("2026-10-27");
  await page.getByLabel("Ngày kết thúc dự kiến").fill("2026-11-03");
  await page.getByRole("button", { name: "Lưu dự án" }).click();

  await expect(page.getByText("Tài khoản được chọn không có vai trò QA")).toBeVisible();
  await expect(page.getByLabel("Mã dự án")).toHaveValue("CHECKOUT");
  await expect(page.getByLabel("Tài khoản QA đầu tiên")).toHaveValue("qa@example.test");
  await expect(page.getByLabel("Tên dự án")).toHaveValue("Kiểm tra quyền tạo dự án");
  await expect(page.getByLabel("Phương thức làm việc")).toHaveValue("KANBAN");
  await expect(page.getByLabel("Ngày bắt đầu dự kiến")).toHaveValue("2026-10-27");
  await expect(page.getByLabel("Ngày kết thúc dự kiến")).toHaveValue("2026-11-03");
  expect(requestErrors).toEqual([]);
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBe(dimensions.viewport);
});

test("project creation validates its date range and shows the saved schedule", async ({ page }) => {
  const state = await installProjectList(page, { createStatus: 201 });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/du-an", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Tạo dự án" }).click();

  await page.getByLabel("Mã dự án").fill("checkout");
  await page.getByLabel("Tài khoản QA đầu tiên").fill("qa@example.test");
  await page.getByLabel("Tên dự án").fill("Kiểm tra lịch dự án");
  await page.getByLabel("Ngày bắt đầu dự kiến").fill("2026-10-27");
  await page.getByLabel("Ngày kết thúc dự kiến").fill("2026-10-27");
  await expect(page.getByText("Ngày kết thúc phải sau ngày bắt đầu.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu dự án" })).toBeDisabled();

  await page.getByLabel("Ngày kết thúc dự kiến").fill("2026-11-03");
  await page.getByRole("button", { name: "Lưu dự án" }).click();
  await expect(page.getByRole("heading", { name: "Tạo dự án" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Kiểm tra lịch dự án" })).toBeVisible();
  await expect(page.getByText(/Bắt đầu dự kiến: 27\/10\/2026/)).toBeVisible();
  await expect(page.getByText(/Kết thúc dự kiến: 03\/11\/2026/)).toBeVisible();
  await expect(page.getByText("Thời lượng dự kiến: 8 ngày lịch")).toBeVisible();
  expect(state.createdPayload).toMatchObject({
    key: "CHECKOUT",
    initial_qa_user_id: "qa@example.test",
    planned_start_at: "2026-10-27T00:00:00.000Z",
    planned_end_at: "2026-11-03T00:00:00.000Z",
  });
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBe(dimensions.viewport);
});

test("project cards separate QA progress from weighted task progress without fake zero", async ({
  page,
}) => {
  await installProjectList(page, {
    projects: [
      {
        _id: "project-progress-e2e",
        key: "PAYMENT",
        name: "Dự án thanh toán",
        planning_method: "SCRUM",
        status: "ACTIVE",
        updated_at: "2026-10-27T00:00:00.000Z",
        project_completion_percent: 80,
        task_summary: { completed: 2, total: 4, blocked: 1, completion_percent: 49 },
      },
      {
        _id: "project-empty-e2e",
        key: "EMPTY",
        name: "Dự án chưa có công việc",
        planning_method: "KANBAN",
        status: "ACTIVE",
        updated_at: "2026-10-27T00:00:00.000Z",
        project_completion_percent: null,
        task_summary: { completed: 0, total: 0, blocked: 0, applicable_total: 0, cancelled: 0 },
      },
    ],
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/du-an", { waitUntil: "domcontentloaded" });

  const projectCard = page.locator("article").filter({ hasText: "Dự án thanh toán" });
  await expect(projectCard.getByRole("progressbar", { name: "Project 80%" })).toHaveAttribute(
    "aria-valuenow",
    "80",
  );
  await expect(projectCard.getByRole("progressbar", { name: "Tasks 49%" })).toHaveAttribute(
    "aria-valuenow",
    "49",
  );
  await expect(projectCard.getByText("Project · QA đánh giá")).toBeVisible();
  await expect(projectCard.getByText("Tasks · Tự tính")).toBeVisible();
  await expect(projectCard.getByText("4 công việc · 1 bị chặn")).toBeVisible();

  const emptyCard = page.locator("article").filter({ hasText: "Dự án chưa có công việc" });
  await expect(emptyCard.getByText("Project · Chưa có đánh giá của QA")).toBeVisible();
  await expect(emptyCard.getByText("Tasks · Chưa có công việc")).toBeVisible();
  await expect(emptyCard.getByRole("progressbar")).toHaveCount(0);
});

test("QA updates Project progress while Tester sees both values read-only", async ({ page }) => {
  const qaState = await installProjectOverview(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/du-an/project-overview-e2e", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("progressbar", { name: "Tiến độ tổng thể do QA đánh giá" }),
  ).toHaveAttribute("aria-valuenow", "40");
  await expect(
    page.getByRole("progressbar", {
      name: "Tiến độ công việc được tính từ các công việc chưa hủy",
    }),
  ).toHaveAttribute("aria-valuenow", "49");
  await page.getByRole("button", { name: "Cập nhật tiến độ" }).click();
  await page.getByRole("spinbutton", { name: "Tiến độ dự án" }).fill("75");
  await page.getByLabel("Ghi chú").fill("QA cập nhật theo tình hình dự án.");
  await page.getByRole("button", { name: "Lưu tiến độ" }).click();
  await expect(page.getByText("Project 75%")).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Tiến độ tổng thể do QA đánh giá" }),
  ).toHaveAttribute("aria-valuenow", "75");
  await expect(
    page.getByRole("progressbar", {
      name: "Tiến độ công việc được tính từ các công việc chưa hủy",
    }),
  ).toHaveAttribute("aria-valuenow", "49");
  expect(qaState.updates).toEqual([
    {
      expected_revision: 7,
      project_completion_percent: 75,
      note: "QA cập nhật theo tình hình dự án.",
    },
  ]);

  const testerState = await installProjectOverview(page, "TESTER");
  await page.goto("/du-an/project-overview-e2e", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("Project 40%")).toBeVisible();
  await expect(page.getByText("Tasks 49%")).toBeVisible();
  await expect(page.getByRole("button", { name: "Cập nhật tiến độ" })).toHaveCount(0);
  expect(testerState.updates).toEqual([]);
});
