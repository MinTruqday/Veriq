import { expect, test } from "@playwright/test";

const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const apiBase = (
  process.env.E2E_FRONTEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

const publicRoutes = [
  ["/", "Veriq"],
  ["/dang-nhap", "Đăng nhập"],
  ["/quen-mat-khau", "Khôi phục mật khẩu"],
  ["/dat-lai-mat-khau?token=e2e-reset-token", "Đặt mật khẩu mới"],
  ["/xac-thuc", "Xác thực"],
  ["/xac-minh-thu-dien-tu?email=register%40example.test", "Xác minh địa chỉ thư điện tử"],
  ["/dieu-khoan", "Điều khoản"],
];

test("public and authentication pages render without horizontal overflow", async ({ page }) => {
  const widths = [1920, 1440, 1280, 768, 390];
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    for (const [route, heading] of publicRoutes) {
      const response = await page.goto(route, { waitUntil: "domcontentloaded" });
      expect(response?.ok(), `${route} should respond successfully`).toBeTruthy();
      await expect(page.locator("body")).toContainText(heading);
      const logo = page.locator('img[alt="Veriq"]').first();
      await expect(logo).toHaveAttribute("src", "/brand/veriq-logo.png");
      await expect
        .poll(() => logo.evaluate((image) => image.complete && image.naturalWidth > 0))
        .toBe(true);
      const dimensions = await page.evaluate(() => ({
        viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));
      expect(dimensions.document, `${route} document overflow at ${width}px`).toBe(width);
      expect(dimensions.body, `${route} body overflow at ${width}px`).toBe(width);
    }
  }

  expect(pageErrors).toEqual([]);
});

test("failed login preserves user input and shows the returned error", async ({ page }) => {
  await page.route("**/xac-thuc/dang-nhap", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: { message: "Thông tin đăng nhập kiểm thử không hợp lệ" } }),
    });
  });

  await page.goto("/dang-nhap");
  await page.getByLabel("Email").fill("ui-check@example.invalid");
  await page.locator("#login-password").fill("incorrect-test-password");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page.getByText("Thông tin đăng nhập kiểm thử không hợp lệ")).toBeVisible();
  await expect(page.getByLabel("Email")).toHaveValue("ui-check@example.invalid");
  await expect(page.locator("#login-password")).toHaveValue("incorrect-test-password");
});

test("password recovery preserves input after errors and completes each step", async ({ page }) => {
  let verificationAttempts = 0;
  let resetAttempts = 0;
  const receivedRequests = [];

  await page.route(`${apiBase}/xac-thuc/quen-mat-khau`, async (route) => {
    receivedRequests.push({ path: "/quen-mat-khau", body: route.request().postDataJSON() });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: {} }),
    });
  });
  await page.route(`${apiBase}/xac-thuc/xac-nhan-ma`, async (route) => {
    receivedRequests.push({ path: "/xac-nhan-ma", body: route.request().postDataJSON() });
    verificationAttempts += 1;
    await route.fulfill({
      status: verificationAttempts === 1 ? 400 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        verificationAttempts === 1 ? { detail: "Mã xác thực kiểm thử không hợp lệ" } : { data: {} },
      ),
    });
  });
  await page.route(`${apiBase}/xac-thuc/dat-lai-mat-khau`, async (route) => {
    receivedRequests.push({ path: "/dat-lai-mat-khau", body: route.request().postDataJSON() });
    resetAttempts += 1;
    await route.fulfill({
      status: resetAttempts === 1 ? 400 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        resetAttempts === 1 ? { detail: "Không thể đặt lại mật khẩu kiểm thử" } : { data: {} },
      ),
    });
  });

  await page.goto("/quen-mat-khau");
  await page.getByLabel("Email").fill("recovery@example.test");
  await page.getByRole("button", { name: "Gửi mã" }).click();
  await expect(page).toHaveURL(/\/xac-thuc\?email=recovery%40example.test$/);
  await page.getByLabel("Mã xác thực").fill("123456");
  await page.getByRole("button", { name: "Xác nhận" }).click();
  await expect(page.getByText("Mã xác thực kiểm thử không hợp lệ")).toBeVisible();
  await expect(page.getByLabel("Mã xác thực")).toHaveValue("123456");
  await page.getByRole("button", { name: "Xác nhận" }).click();
  await expect(page).toHaveURL(/\/dat-lai-mat-khau\?token=123456$/);
  await page.getByLabel("Mật khẩu mới").fill("correct-horse-battery-1");
  await page.getByRole("button", { name: "Cập nhật" }).click();
  await expect(page.getByText("Không thể đặt lại mật khẩu kiểm thử")).toBeVisible();
  await expect(page.getByLabel("Mật khẩu mới")).toHaveValue("correct-horse-battery-1");
  await page.getByRole("button", { name: "Cập nhật" }).click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
  expect(receivedRequests).toEqual([
    { path: "/quen-mat-khau", body: { email: "recovery@example.test" } },
    { path: "/xac-nhan-ma", body: { token: "123456" } },
    { path: "/xac-nhan-ma", body: { token: "123456" } },
    {
      path: "/dat-lai-mat-khau",
      body: { token: "123456", new_password: "correct-horse-battery-1" },
    },
    {
      path: "/dat-lai-mat-khau",
      body: { token: "123456", new_password: "correct-horse-battery-1" },
    },
  ]);
});

test("public account registration route is removed", async ({ page }) => {
  const response = await page.goto("/dang-ky");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Tạo tài khoản" })).toHaveCount(0);
});

test("email verification keeps the token after errors and confirms the account", async ({
  page,
}) => {
  let attempts = 0;
  const token = "email-verification-token-with-enough-length";
  await page.route(`${apiBase}/xac-thuc/xac-minh-thu-dien-tu`, async (route) => {
    attempts += 1;
    await route.fulfill({
      status: attempts === 1 ? 400 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        attempts === 1
          ? { detail: "Mã xác minh kiểm thử đã hết hạn" }
          : { data: { verified: true, email: "register@example.test" } },
      ),
    });
  });

  await page.goto("/xac-minh-thu-dien-tu?email=register%40example.test");
  await page.getByLabel("Mã xác minh").fill(token);
  await page.getByRole("button", { name: "Xác minh email" }).click();
  await expect(page.getByText("Mã xác minh kiểm thử đã hết hạn")).toBeVisible();
  await expect(page.getByLabel("Mã xác minh")).toHaveValue(token);
  await page.getByRole("button", { name: "Xác minh email" }).click();
  await expect(page.getByRole("heading", { name: "Email đã được xác minh" })).toBeVisible();
  await expect(page.getByText("Địa chỉ register@example.test đã được xác minh.")).toBeVisible();
});

test("successful password login verifies the session before opening the project list", async ({
  page,
}) => {
  const token = "e2e-login-success-token";
  let identityAuthorization;
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/xac-thuc/dang-nhap") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { access_token: token } }),
      });
      return;
    }
    if (pathname === "/xac-thuc/ca-nhan") {
      identityAuthorization = request.headers().authorization;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: "user-e2e-login", email: "login@example.test", full_name: "Người dùng" },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto("/dang-nhap");
  await page.getByLabel("Email").fill("login@example.test");
  await page.locator("#login-password").fill("correct-horse-battery-1");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page).toHaveURL(/\/du-an$/);
  expect(identityAuthorization).toBe(`Bearer ${token}`);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("veriq_token"))).toBe(token);
});

test("Google callback completes once and returns only to its saved internal destination", async ({
  page,
}) => {
  const token = "e2e-google-login-token";
  let callbackRequests = 0;
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/google/chuyen-huong") {
      callbackRequests += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            access_token: token,
            user: { email: "google@example.test", has_passkey: true },
          },
        }),
      });
      return;
    }
    if (pathname === "/xac-thuc/ca-nhan") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { _id: "user-e2e-google", email: "google@example.test" } }),
      });
      return;
    }
    if (pathname === "/kiem-thu/du-an/PRJ-E2E") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            _id: "PRJ-E2E",
            name: "Dự án kiểm thử callback",
            planning_method: "SCRUM",
            current_permissions: ["project.read"],
          },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto("/dang-nhap");
  await page.evaluate(() => sessionStorage.setItem("veriq_return_path", "/du-an/PRJ-E2E"));
  await page.goto("/dang-nhap/google/chuyen-huong?code=e2e-code&state=e2e-state");

  await expect(page).toHaveURL(/\/du-an\/PRJ-E2E$/);
  expect(callbackRequests).toBe(1);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("veriq_token"))).toBe(token);
  await expect
    .poll(() => page.evaluate(() => sessionStorage.getItem("veriq_return_path")))
    .toBeNull();
});

test("Google callback failure gives a recoverable path back to login", async ({ page }) => {
  await page.route(`${apiBase}/**`, async (route) => {
    if (new URL(route.request().url()).pathname === "/xac-thuc/google/chuyen-huong") {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Không thể xác thực Google trong kiểm thử" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto("/dang-nhap/google/chuyen-huong?code=e2e-code&state=e2e-state");

  await expect(page.getByText("Không thể xác thực Google trong kiểm thử")).toBeVisible();
  await page.getByRole("button", { name: "Quay lại đăng nhập" }).click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
});

test("an expired session clears local credentials and preserves the protected destination", async ({
  page,
}) => {
  const projectId = "PRJ-E2E-EXPIRED-SESSION";
  const token = "e2e-expired-session";
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan" || pathname === "/xac-thuc/lam-moi-phien") {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Phiên đăng nhập đã hết hạn" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto(`/du-an/${projectId}/yeu-cau/REQ-E2E-EXPIRED`);

  await expect(page).toHaveURL(
    new RegExp(
      `/dang-nhap\\?next=${encodeURIComponent(`/du-an/${projectId}/yeu-cau/REQ-E2E-EXPIRED`)}`,
    ),
  );
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("veriq_token"))).toBeNull();
  await expect(page.context().cookies(appBaseUrl)).resolves.toEqual(
    expect.not.arrayContaining([expect.objectContaining({ name: "token", value: token })]),
  );
});

test("a temporary refresh failure keeps the session and offers retry", async ({ page }) => {
  const token = "e2e-temporary-refresh-failure";
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await route.fulfill({ status: 401, body: "{}" });
      return;
    }
    if (pathname === "/xac-thuc/lam-moi-phien") {
      await route.fulfill({ status: 503, body: "{}" });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"data":[]}' });
  });

  await page.goto("/du-an/PRJ-E2E-TEMPORARY-REFRESH-FAILURE");

  await expect(page.getByRole("heading", { name: "Chưa xác minh được phiên" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Thử xác minh lại" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("veriq_token"))).toBe(token);
  await expect(page.context().cookies(appBaseUrl)).resolves.toEqual(
    expect.arrayContaining([expect.objectContaining({ name: "token", value: token })]),
  );
});

test("a delayed identity response from an old session cannot replace a new login", async ({
  page,
}) => {
  const oldToken = "e2e-old-session";
  const newToken = "e2e-new-session";
  let releaseOldIdentity;
  let oldIdentityStarted;
  const oldIdentityStartedPromise = new Promise((resolve) => {
    oldIdentityStarted = resolve;
  });
  const oldIdentityResponse = new Promise((resolve) => {
    releaseOldIdentity = resolve;
  });

  await page.context().addCookies([{ name: "token", value: oldToken, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), oldToken);
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      if (request.headers().authorization === `Bearer ${oldToken}`) {
        oldIdentityStarted();
        await oldIdentityResponse;
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Phiên cũ đã hết hạn" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: "new-session-user", email: "new@example.test", full_name: "Tài khoản mới" },
        }),
      });
      return;
    }
    if (pathname === "/xac-thuc/dang-nhap") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { access_token: newToken } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  try {
    await page.goto("/dang-nhap");
    await oldIdentityStartedPromise;
    await page.getByLabel("Email").fill("new@example.test");
    await page.locator("#login-password").fill("valid-test-password");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/du-an$/);

    releaseOldIdentity();
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem("veriq_token")))
      .toBe(newToken);
  } finally {
    releaseOldIdentity();
  }
});

test("a protected direct URL redirects an anonymous visitor to login", async ({ page }) => {
  const projectId = "PRJ-E2E-UNAUTH";
  const protectedRoutes = [
    "",
    "lap-ke-hoach/backlog",
    "lap-ke-hoach/board",
    "lap-ke-hoach/sprint",
    "lap-ke-hoach/roadmap",
    "cong-viec",
    "ban-phat-hanh",
    "yeu-cau",
    "yeu-cau/REQ-E2E-UNAUTH",
    "ho-so-dam-bao",
    "phieu-lam-ro",
    "thay-doi",
    "quan-tri-kiem-thu",
    "phan-tich-kiem-thu",
    "kho-kiem-thu",
    "ca-kiem-thu",
    "buoc-dung-lai",
    "du-lieu-kiem-thu",
    "bo-kiem-thu",
    "ke-hoach-kiem-thu",
    "lan-chay-kiem-thu",
    "tu-dong-hoa",
    "truy-vet",
    "thuc-thi",
    "loi",
    "bao-cao",
    "nhat-ky-kiem-toan",
    "tri-thuc",
    "cai-dat",
  ];

  for (const route of protectedRoutes) {
    const pathname = `/du-an/${projectId}${route ? `/${route}` : ""}`;
    await page.goto(pathname, { waitUntil: "domcontentloaded" });
    await expect(page, `${pathname} must require a session`).toHaveURL(/\/dang-nhap/);
    await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
  }
});

test("an authenticated member is redirected away from a project route they cannot read", async ({
  page,
}) => {
  const projectId = "PRJ-E2E-ROUTE-PERMISSION";
  const token = "e2e-route-permission-session";
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const data =
      pathname === "/xac-thuc/ca-nhan"
        ? { _id: "member-e2e", email: "member@example.test", full_name: "Thành viên" }
        : pathname === `/kiem-thu/du-an/${projectId}`
          ? {
              _id: projectId,
              name: "Dự án giới hạn quyền",
              planning_method: "SCRUM",
              current_permissions: ["project.read"],
            }
          : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data, status: "SUCCESS" }),
    });
  });

  await page.goto(`/du-an/${projectId}/yeu-cau/REQ-E2E-PRIVATE`);

  await expect(page).toHaveURL(new RegExp(`/du-an/${projectId}$`));
  await expect(page.getByText("Yêu cầu không có quyền truy cập", { exact: true })).toHaveCount(0);
});

test("an unverified JWT role cannot open the platform administration UI", async ({ page }) => {
  const payload = Buffer.from(
    JSON.stringify({
      sub: "forged-admin@example.test",
      uid: "forged-admin",
      system_role: "ADMIN",
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
  ).toString("base64url");
  const token = `e30.${payload}.unverified-signature`;
  let identityLookups = 0;
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      identityLookups += 1;
      if (identityLookups === 1) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "identity service unavailable" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: "verified-user", email: "user@example.test", system_role: "USER" },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto("/van-hanh");

  await expect(page.getByRole("heading", { name: "Chưa xác minh được phiên" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Vận hành nền tảng" })).toHaveCount(0);
  await page.getByRole("button", { name: "Thử xác minh lại" }).click();
  await expect(page).toHaveURL(/\/du-an$/);
  await expect(page.getByRole("heading", { name: "Vận hành nền tảng" })).toHaveCount(0);
});

test("a verified platform admin can open the platform administration route directly", async ({
  page,
}) => {
  const token = "e2e-verified-admin-session";
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const data =
      pathname === "/xac-thuc/ca-nhan"
        ? {
            _id: "admin-e2e",
            email: "admin@example.test",
            full_name: "Quản trị nền tảng",
            system_role: "ADMIN",
          }
        : pathname === "/kiem-thu/van-hanh"
          ? {
              knowledge_indexing_backlog: 0,
              failed_ingestion_jobs: [],
              failed_impact_jobs: [],
              worker_failures: [],
              ai_models: {},
              ai_request_metrics: {},
              storage_usage: [],
              audit_events: [],
            }
          : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data, status: "SUCCESS" }),
    });
  });

  await page.goto("/van-hanh", { waitUntil: "domcontentloaded" });

  await expect(page).toHaveURL(/\/van-hanh$/);
  await expect(page.getByRole("heading", { name: "Vận hành nền tảng" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Vận hành nền tảng" })).toBeVisible();
  await page.getByRole("button", { name: "Đánh giá AI" }).click();
  await expect(page.getByRole("heading", { name: "Đánh giá đối chuẩn kỹ thuật AI" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Chạy đánh giá tổng hợp" })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(
    /pipeline|blueprint|\bmetric\b|\bcohort\b|benchmark|production/i,
  );
});

test("platform operations load errors can be retried", async ({ page }) => {
  const token = "e2e-platform-operations-retry-session";
  let projectRequests = 0;
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/xac-thuc/ca-nhan") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: { _id: "admin-e2e", email: "admin@example.test", system_role: "ADMIN" },
        }),
      });
      return;
    }
    if (pathname === "/kiem-thu/van-hanh") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            knowledge_indexing_backlog: 0,
            failed_ingestion_jobs: [],
            failed_impact_jobs: [],
            worker_failures: [],
            ai_models: {},
            ai_request_metrics: {},
            storage_usage: [],
            audit_events: [],
          },
        }),
      });
      return;
    }
    if (pathname === "/thong-bao") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [] }),
      });
      return;
    }
    if (pathname === "/quan-tri/du-an" && projectRequests++ === 0) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Tạm thời không tải được dự án" }),
      });
      return;
    }
    if (!pathname.startsWith("/quan-tri/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto("/van-hanh", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Vận hành nền tảng" })).toBeVisible();
  await page.getByRole("button", { name: "Cấu hình nền tảng" }).click();

  await expect(page.getByText("Tạm thời không tải được dự án")).toBeVisible();
  await page.getByRole("button", { name: "Thử tải lại" }).click();
  await expect(page.getByRole("heading", { name: "Trạng thái dịch vụ nền tảng" })).toBeVisible();
  expect(projectRequests).toBeGreaterThanOrEqual(2);
});

test("a regular user cannot open the platform administration route directly", async ({ page }) => {
  const token = "e2e-regular-user-session";
  let operationsRequests = 0;
  let platformAdministrationRequests = 0;
  await page.context().addCookies([{ name: "token", value: token, url: appBaseUrl }]);
  await page.addInitScript((value) => localStorage.setItem("veriq_token", value), token);
  await page.route(`${apiBase}/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/kiem-thu/van-hanh") operationsRequests += 1;
    if (pathname.startsWith("/quan-tri/")) platformAdministrationRequests += 1;
    const data =
      pathname === "/xac-thuc/ca-nhan"
        ? {
            _id: "user-e2e",
            email: "user@example.test",
            full_name: "Người dùng",
            system_role: "USER",
          }
        : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data, status: "SUCCESS" }),
    });
  });

  await page.goto("/van-hanh");

  await expect(page).toHaveURL(/\/du-an$/);
  await expect(page.getByRole("heading", { name: "Vận hành nền tảng" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Vận hành nền tảng" })).toHaveCount(0);
  expect(operationsRequests).toBe(0);
  expect(platformAdministrationRequests).toBe(0);
});
