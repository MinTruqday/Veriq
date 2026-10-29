import { expect, test } from "@playwright/test";

const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const apiBase = (
  process.env.E2E_FRONTEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

async function authenticate(page, user) {
  const token = `e2e-session-${user._id}`;
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
}

function jsonResponse(route, data, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({ data, status: status < 400 ? "SUCCESS" : "ERROR" }),
  });
}

test("account profile, session controls and notification preferences use their APIs", async ({
  page,
}) => {
  const user = {
    _id: "account-settings-user",
    email: "account-settings@example.test",
    full_name: "Người dùng kiểm thử",
    system_role: "USER",
  };
  const requests = [];
  let profileName = user.full_name;
  let sessionRevoked = false;
  let savedSettings;

  await authenticate(page, user);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === "/xac-thuc/ca-nhan" && method === "GET") {
      await jsonResponse(route, { ...user, full_name: profileName });
      return;
    }
    if (pathname === "/xac-thuc/ca-nhan" && method === "PATCH") {
      const body = request.postDataJSON();
      requests.push({ pathname, method, body });
      profileName = body.full_name;
      await jsonResponse(route, { ...user, ...body });
      return;
    }
    if (pathname === "/xac-thuc/phien" && method === "GET") {
      await jsonResponse(route, [
        { _id: "session-current", is_current: true, created_at: "2026-10-27T10:00:00Z" },
        ...(!sessionRevoked
          ? [{ _id: "session-old", is_current: false, created_at: "2026-10-26T10:00:00Z" }]
          : []),
      ]);
      return;
    }
    if (pathname === "/xac-thuc/phien/session-old" && method === "DELETE") {
      requests.push({ pathname, method });
      sessionRevoked = true;
      await jsonResponse(route, { revoked: true });
      return;
    }
    if (pathname === "/thong-bao/cai-dat" && method === "GET") {
      await jsonResponse(route, {
        enable_comment_notifications: true,
        enable_mention_notifications: false,
        enable_system_notifications: true,
      });
      return;
    }
    if (pathname === "/thong-bao/cai-dat" && method === "POST") {
      savedSettings = request.postDataJSON();
      requests.push({ pathname, method, body: savedSettings });
      await jsonResponse(route, savedSettings);
      return;
    }
    if (pathname === "/thong-bao" && method === "GET") {
      await jsonResponse(route, []);
      return;
    }
    await jsonResponse(route, []);
  });

  await page.goto(`${appBaseUrl}/cai-dat`);
  await expect(page.getByRole("heading", { name: "Tài khoản và bảo mật" })).toBeVisible();
  await page.getByLabel("Tên hiển thị").fill("Tên đã cập nhật");
  await page.getByRole("button", { name: "Lưu thông tin" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã cập nhật thông tin cá nhân" }),
  ).toBeVisible();
  await expect(page.getByText("Phiên đăng nhập khác")).toBeVisible();
  await page.getByRole("button", { name: "Thu hồi" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã thu hồi phiên đăng nhập" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cài đặt thông báo" })).toBeVisible();
  await page.getByLabel("Thông báo khi được nhắc tên").check();
  await page.getByRole("button", { name: "Lưu cài đặt" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu cài đặt thông báo" }),
  ).toBeVisible();

  expect(requests).toContainEqual({
    pathname: "/xac-thuc/ca-nhan",
    method: "PATCH",
    body: { full_name: "Tên đã cập nhật", locale: "vi-VN", timezone: "Asia/Ho_Chi_Minh" },
  });
  expect(requests).toContainEqual({ pathname: "/xac-thuc/phien/session-old", method: "DELETE" });
  expect(savedSettings).toEqual({
    enable_comment_notifications: true,
    enable_mention_notifications: true,
    enable_system_notifications: true,
  });
});

test("password change preserves entered values after a rejection and updates sessions on success", async ({
  page,
}) => {
  const user = {
    _id: "password-change-user",
    email: "password-change@example.test",
    full_name: "Người dùng đổi mật khẩu",
    system_role: "USER",
  };
  let changeAttempts = 0;
  let submittedPassword;

  await authenticate(page, user);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === "/xac-thuc/ca-nhan" && method === "GET") {
      await jsonResponse(route, user);
      return;
    }
    if (pathname === "/xac-thuc/phien" && method === "GET") {
      await jsonResponse(route, [{ _id: "current-password-session", is_current: true }]);
      return;
    }
    if (pathname === "/xac-thuc/doi-mat-khau" && method === "POST") {
      changeAttempts += 1;
      submittedPassword = request.postDataJSON();
      if (changeAttempts === 1) {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Mật khẩu hiện tại không đúng" }),
        });
        return;
      }
      await jsonResponse(route, { other_sessions_revoked: true });
      return;
    }
    if (pathname === "/thong-bao" && method === "GET") {
      await jsonResponse(route, []);
      return;
    }
    await jsonResponse(route, []);
  });

  await page.goto(`${appBaseUrl}/cai-dat`);
  await page.getByLabel("Mật khẩu hiện tại").fill("incorrect-current-password");
  await page.getByLabel("Mật khẩu mới").fill("new-test-password-123");
  await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Mật khẩu hiện tại không đúng" }),
  ).toBeVisible();
  await expect(page.getByLabel("Mật khẩu hiện tại")).toHaveValue("incorrect-current-password");
  await expect(page.getByLabel("Mật khẩu mới")).toHaveValue("new-test-password-123");
  await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã đổi mật khẩu và đóng các phiên khác" }),
  ).toBeVisible();
  await expect(page.getByLabel("Mật khẩu hiện tại")).toHaveValue("");
  await expect(page.getByLabel("Mật khẩu mới")).toHaveValue("");
  expect(changeAttempts).toBe(2);
  expect(submittedPassword).toEqual({
    current_password: "incorrect-current-password",
    new_password: "new-test-password-123",
  });
});

test("notification list reads, marks, deletes and reports API failures without losing items", async ({
  page,
}) => {
  const user = {
    _id: "notification-user",
    email: "notification@example.test",
    full_name: "Người nhận thông báo",
    system_role: "USER",
  };
  let notifications = [
    { _id: "notice-1", title: "Cần rà soát", body: "Yêu cầu có thay đổi", is_read: false },
    { _id: "notice-2", title: "Đã phân công", body: "Bạn được giao kiểm thử", is_read: false },
  ];
  let failDelete = true;
  const mutations = [];

  await authenticate(page, user);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === "/xac-thuc/ca-nhan" && method === "GET") {
      await jsonResponse(route, user);
      return;
    }
    if (pathname === "/thong-bao" && method === "GET") {
      await jsonResponse(route, notifications);
      return;
    }
    if (pathname === "/thong-bao/notice-1/doc-hieu" && method === "PATCH") {
      mutations.push({ pathname, method });
      notifications = notifications.map((item) =>
        item._id === "notice-1" ? { ...item, is_read: true } : item,
      );
      await jsonResponse(route, { updated: true });
      return;
    }
    if (pathname === "/thong-bao/doc-tat-ca" && method === "PATCH") {
      mutations.push({ pathname, method });
      notifications = notifications.map((item) => ({ ...item, is_read: true }));
      await jsonResponse(route, { updated: notifications.length });
      return;
    }
    if (pathname === "/thong-bao/notice-2" && method === "DELETE") {
      mutations.push({ pathname, method });
      if (failDelete) {
        failDelete = false;
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ message: "Tạm thời không thể xóa thông báo" }),
        });
        return;
      }
      notifications = notifications.filter((item) => item._id !== "notice-2");
      await jsonResponse(route, { deleted: true });
      return;
    }
    await jsonResponse(route, []);
  });

  await page.goto(`${appBaseUrl}/thong-bao`);
  await expect(page.getByText("Cần rà soát")).toBeVisible();
  await page
    .locator("article")
    .filter({ hasText: "Cần rà soát" })
    .getByRole("button", { name: "Đánh dấu đã đọc" })
    .click();
  await expect(page.getByText("Cần rà soát")).toBeVisible();
  await page.locator("main header").getByRole("button", { name: "Đánh dấu đã đọc" }).click();
  await expect(page.getByText("0 chưa đọc")).toBeVisible();
  await page.getByRole("button", { name: "Xóa" }).last().click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Tạm thời không thể xóa thông báo" }),
  ).toBeVisible();
  await expect(page.getByText("Đã phân công")).toBeVisible();
  await page
    .locator("article")
    .filter({ hasText: "Đã phân công" })
    .getByRole("button", { name: "Xóa" })
    .click();
  await expect(page.getByText("Đã phân công")).toHaveCount(0);
  expect(mutations).toEqual([
    { pathname: "/thong-bao/notice-1/doc-hieu", method: "PATCH" },
    { pathname: "/thong-bao/doc-tat-ca", method: "PATCH" },
    { pathname: "/thong-bao/notice-2", method: "DELETE" },
    { pathname: "/thong-bao/notice-2", method: "DELETE" },
  ]);
});

test("notification settings retry after load failure and retain edits after save failure", async ({
  page,
}) => {
  const user = {
    _id: "notification-settings-user",
    email: "notification-settings@example.test",
    full_name: "Người dùng",
    system_role: "USER",
  };
  let settingsLoads = 0;
  let failSave = true;

  await authenticate(page, user);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === "/xac-thuc/ca-nhan" && method === "GET") {
      await jsonResponse(route, user);
      return;
    }
    if (pathname === "/xac-thuc/phien" && method === "GET") {
      await jsonResponse(route, []);
      return;
    }
    if (pathname === "/thong-bao/cai-dat" && method === "GET") {
      settingsLoads += 1;
      if (settingsLoads <= 2) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ message: "Không tải được cài đặt" }),
        });
        return;
      }
      await jsonResponse(route, {
        enable_comment_notifications: true,
        enable_mention_notifications: true,
        enable_system_notifications: true,
      });
      return;
    }
    if (pathname === "/thong-bao/cai-dat" && method === "POST") {
      if (failSave) {
        failSave = false;
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ message: "Không lưu được cài đặt" }),
        });
        return;
      }
      await jsonResponse(route, request.postDataJSON());
      return;
    }
    await jsonResponse(route, []);
  });

  await page.goto(`${appBaseUrl}/cai-dat`);
  await expect(
    page.getByRole("alert").filter({ hasText: "Không thể tải cài đặt thông báo" }),
  ).toBeVisible();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const responsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/thong-bao/cai-dat" &&
        response.request().method() === "GET",
    );
    await page.getByRole("button", { name: "Tải lại" }).click();
    const response = await responsePromise;
    if (response.ok()) break;
  }
  await expect(page.getByLabel("Thông báo hệ thống")).toBeEnabled();
  await page.getByLabel("Thông báo hệ thống").uncheck();
  await page.getByRole("button", { name: "Lưu cài đặt" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Không lưu được cài đặt" })).toBeVisible();
  await expect(page.getByLabel("Thông báo hệ thống")).not.toBeChecked();
  await page.getByRole("button", { name: "Lưu cài đặt" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu cài đặt thông báo" }),
  ).toBeVisible();
  expect(settingsLoads).toBeGreaterThanOrEqual(2);
});

test("a platform admin can create an account through the account administration API", async ({
  page,
}) => {
  const admin = {
    _id: "platform-admin-create-user",
    email: "platform-admin@example.test",
    full_name: "Quản trị viên",
    system_role: "ADMIN",
  };
  const users = [];
  let createdPayload;

  await authenticate(page, admin);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();
    if (pathname === "/xac-thuc/ca-nhan" && method === "GET") {
      await jsonResponse(route, admin);
      return;
    }
    if (pathname === "/kiem-thu/van-hanh" && method === "GET") {
      await jsonResponse(route, {
        knowledge_indexing_backlog: 0,
        failed_ingestion_jobs: [],
        failed_impact_jobs: [],
        worker_failures: [],
        ai_models: {},
        ai_request_metrics: {},
        storage_usage: [],
        audit_events: [],
      });
      return;
    }
    if (pathname === "/quan-tri/tai-khoan" && method === "GET") {
      await jsonResponse(route, users);
      return;
    }
    if (pathname === "/quan-tri/tai-khoan" && method === "POST") {
      createdPayload = request.postDataJSON();
      users.push({
        _id: "created-account",
        email: createdPayload.email,
        full_name: createdPayload.full_name,
        system_role: "USER",
        is_active: true,
      });
      await jsonResponse(route, users.at(-1), 201);
      return;
    }
    if (pathname === "/thong-bao" && method === "GET") {
      await jsonResponse(route, []);
      return;
    }
    await jsonResponse(route, []);
  });

  await page.goto(`${appBaseUrl}/van-hanh`);
  await page.locator("main").getByRole("button", { name: "Tài khoản", exact: true }).click();
  await page.getByRole("button", { name: "Tạo tài khoản" }).click();
  const dialog = page.getByRole("dialog", { name: "Tạo tài khoản hệ thống" });
  await dialog.getByLabel("Email").fill("new-user@example.test");
  await dialog.getByLabel("Họ tên").fill("Người dùng mới");
  await dialog.getByLabel("Tên đăng nhập").fill("new_user");
  await dialog.getByLabel("Lý do").fill("Tạo tài khoản để kiểm thử quản trị");
  await dialog.getByRole("button", { name: "Tạo và gửi lời mời" }).click();
  await expect(page.getByRole("cell", { name: "new-user@example.test" })).toBeVisible();

  expect(createdPayload).toEqual({
    email: "new-user@example.test",
    full_name: "Người dùng mới",
    slug: "new_user",
    reason: "Tạo tài khoản để kiểm thử quản trị",
  });
});

test("account and notification pages fit desktop, tablet and mobile viewports", async ({
  page,
}) => {
  const user = {
    _id: "responsive-account-user",
    email: "responsive@example.test",
    full_name: "Người dùng responsive",
    system_role: "USER",
  };
  await authenticate(page, user);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await jsonResponse(route, user);
      return;
    }
    if (pathname === "/xac-thuc/phien") {
      await jsonResponse(route, [{ _id: "current", is_current: true }]);
      return;
    }
    if (pathname === "/thong-bao/cai-dat") {
      await jsonResponse(route, {
        enable_comment_notifications: true,
        enable_mention_notifications: true,
        enable_system_notifications: true,
      });
      return;
    }
    if (pathname === "/thong-bao") {
      await jsonResponse(route, []);
      return;
    }
    await jsonResponse(route, []);
  });

  for (const width of [1920, 1440, 1280, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [path, heading] of [
      ["/cai-dat", "Tài khoản và bảo mật"],
      ["/thong-bao", "Thông báo"],
    ]) {
      await page.goto(`${appBaseUrl}${path}`);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      const dimensions = await page.evaluate(() => ({
        viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));
      expect(dimensions.document, `${path} overflows at ${width}px`).toBe(width);
      expect(dimensions.body, `${path} body overflows at ${width}px`).toBe(width);
    }
  }
});

test("payroll import uses a localized file control and stays aligned on a narrow admin workspace", async ({
  page,
}) => {
  const admin = {
    _id: "payroll-import-admin",
    email: "payroll-admin@example.test",
    full_name: "Quản trị viên",
    system_role: "ADMIN",
  };
  let headerReadCount = 0;

  await authenticate(page, admin);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await jsonResponse(route, admin);
      return;
    }
    if (pathname === "/kiem-thu/van-hanh") {
      await jsonResponse(route, {
        knowledge_indexing_backlog: 0,
        failed_ingestion_jobs: [],
        failed_impact_jobs: [],
        worker_failures: [],
        ai_models: {},
        ai_request_metrics: {},
        storage_usage: [],
        audit_events: [],
      });
      return;
    }
    if (pathname === "/kiem-thu/quan-tri/tai-chinh/bang-luong/cot") {
      headerReadCount += 1;
      await jsonResponse(route, {
        headers: ["employee", "hourly_cost", "currency", "valid_from", "valid_until"],
      });
      return;
    }
    await jsonResponse(route, []);
  });

  await page.setViewportSize({ width: 680, height: 900 });
  await page.goto(`${appBaseUrl}/van-hanh`);
  await page.getByRole("button", { name: "Bảng lương" }).click();
  const fileInput = page.getByLabel("Chọn bảng CSV hoặc XLSX");
  await expect(page.getByText("Chưa chọn tệp", { exact: true })).toBeVisible();
  await expect(page.getByText("Dùng mẫu CSV hoặc tệp CSV/XLSX", { exact: false })).toBeVisible();
  await expect(page.getByText("Chỉ Admin được xem", { exact: false })).toHaveCount(0);
  await fileInput.setInputFiles({
    name: "bang-luong.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("employee,hourly_cost,currency,valid_from,valid_until\n"),
  });
  await expect(page.getByText("bang-luong.csv", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Mã nhân viên hoặc email")).toHaveValue("employee");
  expect(headerReadCount).toBe(1);

  const narrowLayout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(narrowLayout.document).toBeLessThanOrEqual(narrowLayout.viewport);

  await page.setViewportSize({ width: 1440, height: 900 });
  const desktopLayout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(desktopLayout.document).toBeLessThanOrEqual(desktopLayout.viewport);
});
