import { expect, test } from "@playwright/test";

const apiBase = (
  process.env.E2E_FRONTEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");
const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const token = "project-create-e2e-session";

async function installProjectList(page, { createStatus = 409 } = {}) {
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
        body: JSON.stringify({ data: [] }),
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
      await route.fulfill({
        status: createStatus,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "INITIAL_QA_NOT_ELIGIBLE",
            message: "Tài khoản được chọn không có vai trò QA",
          },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "E2E route was not mocked" } }),
    });
  });
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
