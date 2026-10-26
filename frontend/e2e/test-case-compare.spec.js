import { expect, test } from "@playwright/test";

const apiBase = (
  process.env.E2E_FRONTEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");
const appBaseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
const projectId = "PRJ-E2E-CASE-COMPARE";
const draftId = "DRAFT-E2E-CASE-COMPARE";

const document = (text) => ({
  type: "doc",
  content: [{ type: "paragraph", content: [{ type: "text", text }] }],
});

function draft(revision = 2, title = "Ca kiểm thử đăng nhập") {
  return {
    _id: draftId,
    project_id: projectId,
    test_case_key: "TC-E2E-COMPARE",
    title,
    status: "IN_REVIEW",
    revision,
    origin: "ai_generated",
    steps: [
      {
        id: "step-stable-1",
        order: 1,
        action_doc: document("Nhập email hợp lệ"),
        test_data: { email: "qa@example.test" },
        expected_doc: document("Đăng nhập thành công"),
      },
    ],
    evidence_refs: ["SOURCE-E2E-1"],
    evidence_quotes: [
      { evidence_ref: "SOURCE-E2E-1", quote: "Người dùng đăng nhập bằng email hợp lệ" },
    ],
    requirement_version_ids: ["REQ-V-E2E-1"],
    priority: "HIGH",
    risk: "MEDIUM",
    expected_impact: "HIGH",
    type: "FUNCTIONAL",
  };
}

function project(role, canManageAttachments = true, canReadMembers = true, canManageNfr = false) {
  const permissions = ["project.read", "testcase.read", "testcase.duplicate_check"];
  if (role === "QA")
    permissions.push(
      "project.update",
      "requirement.read",
      "requirement.duplicate_check",
      "testcase.create",
      "testcase.update",
      "testcase.submit_review",
      "testcase.review",
      "testcase.approve",
      "testcase.bulk.update",
      "testdata.read",
      "testsuite.read",
      "teststrategy.read",
      "testcondition.read",
      "testscenario.read",
      "apiartifact.read",
      "testrun.read",
      "testplan.read",
      "automation.read",
      "requirement.create",
      "requirement_document.read",
      "requirement_document.upload",
      "requirement_document.extract",
      "trace.read",
      "release.read",
      "report.read",
    );
  if (role === "QA" && canReadMembers) permissions.push("project.members.read");
  if (role === "QA" && canManageAttachments) permissions.push("attachment.manage");
  if (role === "QA" && canManageNfr) permissions.push("nfrtest.read", "nfrtest.manage");
  return {
    _id: projectId,
    name: "Dự án kiểm thử đối chiếu",
    planning_method: "SCRUM",
    revision: 1,
    status: "ACTIVE",
    current_membership: {
      user_id: `${role.toLowerCase()}-e2e`,
      project_role: role,
      project_roles: [role],
    },
    current_permissions: permissions,
  };
}

async function installWorkspace(
  page,
  role,
  {
    conflictOnMerge = false,
    mergeFailures = 0,
    comparisonReadFailureAfterSave = false,
    draftListFailureAfterApproval = false,
    duplicates = [],
    omitProposalTestKind = false,
    bddComparison = false,
    nestedTestData = false,
    automationRun = null,
    automationRunSnapshots = [],
    automationWorkflow = null,
    automationWorkflowSnapshots = [],
    automationEvidenceFailure = false,
    automationEvidence = null,
    initialRunListFailures = 0,
    sourceDocumentStatus = "READY",
    sourceDocumentIndexStatus = "INDEXED",
    sourceUnprocessedBlocks = [],
    sourceDocumentCanRetryParse = false,
    sourceDocumentRetryFailure = null,
    customFields = [],
    initialCustomValues = null,
    initialOwnerId = null,
    initialAttachments = [],
    canManageAttachments = true,
    canReadMembers = true,
    canManageNfr = false,
    nonFunctionalPlans = [],
  } = {},
) {
  let mergedDraft = draft();
  if (initialCustomValues) mergedDraft.custom_values = initialCustomValues;
  mergedDraft.owner_id = initialOwnerId;
  mergedDraft.attachments = initialAttachments;
  if (nestedTestData) {
    mergedDraft.steps[0].test_data = {
      credentials: { email: "qa@example.test", retry_count: 1, remember: false },
      devices: ["desktop"],
    };
  }
  if (omitProposalTestKind) mergedDraft.test_kind = "security";
  if (bddComparison) {
    mergedDraft.bdd = {
      feature: "Đăng nhập",
      scenario: "Thông tin hợp lệ",
      steps: [{ id: "bdd-stable-1", keyword: "Given", text: "Có tài khoản hợp lệ" }],
    };
  }
  let savedPayload;
  let createdTestCasePayload;
  const mergeRequests = [];
  let mergeAttempts = 0;
  let comparisonReadFailureReturned = false;
  let approvalPayload;
  let approvalAttempts = 0;
  let approved = false;
  let conflictReturned = false;
  let runListCalls = 0;
  let comparisonToken = "c".repeat(64);
  let retryAccepted = false;
  let retryPayload;
  let sourceParseRetryPayload = null;
  let sourceParseRetryCount = 0;
  let currentSourceDocumentStatus = sourceDocumentStatus;
  let currentSourceDocumentCanRetryParse = sourceDocumentCanRetryParse;

  const currentAutomationWorkflow = () => {
    if (automationWorkflowSnapshots.length) {
      return automationWorkflowSnapshots[
        Math.min(Math.max(runListCalls - 1, 0), automationWorkflowSnapshots.length - 1)
      ];
    }
    return automationWorkflow;
  };
  const currentAutomationRun = () => {
    if (automationRunSnapshots.length) {
      return automationRunSnapshots[
        Math.min(Math.max(runListCalls - 1, 0), automationRunSnapshots.length - 1)
      ];
    }
    return automationRun;
  };

  await page
    .context()
    .addCookies([{ name: "token", value: `ui-${role.toLowerCase()}-session`, url: appBaseUrl }]);
  await page.addInitScript(
    (token) => localStorage.setItem("veriq_token", token),
    `ui-${role.toLowerCase()}-session`,
  );

  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let data = [];

    if (path === "/xac-thuc/ca-nhan") {
      data = {
        _id: `${role.toLowerCase()}-e2e`,
        email: `${role.toLowerCase()}@example.test`,
        full_name: role,
      };
    } else if (path === `/kiem-thu/du-an/${projectId}`) {
      data = project(role, canManageAttachments, canReadMembers, canManageNfr);
    } else if (path === `/kiem-thu/du-an/${projectId}/thanh-vien`) {
      data = [
        {
          user_id: "tester-cu",
          user_label: "Tester cũ",
          project_role: "TESTER",
          status: "ACTIVE",
        },
        {
          user_id: "tester-moi",
          user_label: "Tester mới",
          project_role: "TESTER",
          status: "ACTIVE",
        },
        {
          user_id: "tester-ngung",
          user_label: "Tester đã ngừng",
          project_role: "TESTER",
          status: "INACTIVE",
        },
      ];
    } else if (path === `/kiem-thu/du-an/${projectId}/ban-nhap-ca-kiem-thu`) {
      if (request.method() === "POST") {
        createdTestCasePayload = request.postDataJSON();
        data = { _id: "DRAFT-E2E-CREATED", ...createdTestCasePayload };
      } else if (approved && draftListFailureAfterApproval) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "TEMPORARY_READ_FAILURE",
              message: "Không tải lại được danh sách ca kiểm thử.",
            },
          }),
        });
        return;
      }
      data = approved ? [] : [mergedDraft];
    } else if (path === `/kiem-thu/du-an/${projectId}/tai-lieu-yeu-cau`) {
      data = [
        {
          _id: "RDOC-E2E-SOURCE-V1",
          project_id: projectId,
          filename: "requirements.md",
          format: "md",
          source_version: "1",
          source_version_sequence: 1,
          source_series_id: "RDOC-E2E-SOURCE-V1",
          status: currentSourceDocumentStatus,
          index_status: sourceDocumentIndexStatus,
          parse_report: { unprocessed_blocks: sourceUnprocessedBlocks },
          can_retry_parse: currentSourceDocumentCanRetryParse,
          visibility: "private",
          shared_with: [],
          ai_enabled: false,
          source_type: "SRS",
          created_by: "qa-e2e",
          revision: 1,
        },
      ];
    } else if (
      path === "/kiem-thu/tai-lieu-yeu-cau/RDOC-E2E-SOURCE-V1/thu-lai-phan-tich" &&
      request.method() === "POST"
    ) {
      sourceParseRetryPayload = request.postDataJSON();
      sourceParseRetryCount += 1;
      currentSourceDocumentStatus = sourceDocumentRetryFailure ? "PARSE_FAILED" : "READY";
      currentSourceDocumentCanRetryParse = Boolean(sourceDocumentRetryFailure);
      data = {
        _id: "RDOC-E2E-SOURCE-V1",
        project_id: projectId,
        filename: "requirements.md",
        format: "md",
        status: currentSourceDocumentStatus,
        parse_error_type: sourceDocumentRetryFailure?.parse_error_type || null,
        index_status: sourceDocumentRetryFailure ? "NOT_REQUESTED" : "INDEXED",
        ai_enabled: true,
        revision: 2,
      };
    } else if (path === `/kiem-thu/du-an/${projectId}/ca-kiem-thu`) {
      data = { items: [], total: 0, page: 1, page_size: 50 };
    } else if (path === `/kiem-thu/du-an/${projectId}/ke-hoach-phi-chuc-nang`) {
      data = {
        items: nonFunctionalPlans,
        total: nonFunctionalPlans.length,
        page: 1,
        page_size: 50,
      };
    } else if (path === `/kiem-thu/du-an/${projectId}/dieu-kien-kiem-thu`) {
      data = { items: [], total: 0, page: 1, page_size: 50 };
    } else if (path === "/kiem-thu/ke-hoach-phi-chuc-nang/NFR-E2E-1") {
      data = nonFunctionalPlans.find((item) => item._id === "NFR-E2E-1") || {};
    } else if (path === `/tu-dong-hoa-ai/du-an/${projectId}/luot-chay`) {
      runListCalls += 1;
      if (runListCalls <= initialRunListFailures) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "TEMPORARY_READ_FAILURE", message: "Không tải được trạng thái AI." },
          }),
        });
        return;
      }
      const runSnapshot = currentAutomationRun();
      const runs =
        !runSnapshot && runListCalls < 2
          ? []
          : [
              {
                automation_run_id: "AUT-E2E-EVENT-1",
                project_id: projectId,
                requester_user_id: `${role.toLowerCase()}-e2e`,
                objective: "Rà soát tài liệu sau khi tải lên",
                status: "COMPLETED",
                revision: 1,
                ...(runSnapshot || {}),
                ...(currentAutomationWorkflow() ? { workflow: currentAutomationWorkflow() } : {}),
              },
            ];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(runs),
      });
      return;
    } else if (path === "/tu-dong-hoa-ai/luot-chay/AUT-E2E-EVENT-1") {
      const runSnapshot = currentAutomationRun();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run: {
            automation_run_id: "AUT-E2E-EVENT-1",
            requester_user_id: "qa-e2e",
            requester_role: "QA",
            ...(runSnapshot || {}),
            status: retryAccepted ? "QUEUED" : runSnapshot?.status || "AWAITING_INPUT",
            error_code: retryAccepted
              ? null
              : runSnapshot?.error_code || "AUTOMATION_WAITING_FOR_INPUT",
            result: runSnapshot?.result || null,
          },
          workflow: currentAutomationWorkflow() || {
            root_automation_run_id: "AUT-E2E-EVENT-1",
            status: runSnapshot?.status || "AWAITING_INPUT",
            terminal: ["COMPLETED", "DEGRADED", "FAILED", "CANCELLED"].includes(
              runSnapshot?.status || "AWAITING_INPUT",
            ),
            succeeded: runSnapshot?.status === "COMPLETED",
            truncated: false,
            run_count: 1,
            active_count: ["QUEUED", "RUNNING"].includes(runSnapshot?.status),
            blocked_count: ["AWAITING_INPUT", "AWAITING_AUTHORIZATION"].includes(
              runSnapshot?.status || "AWAITING_INPUT",
            ),
            failed_count: ["FAILED", "DEGRADED"].includes(runSnapshot?.status),
            runs: [
              {
                automation_run_id: "AUT-E2E-EVENT-1",
                status: runSnapshot?.status || "AWAITING_INPUT",
              },
            ],
          },
          checkpoints: runSnapshot?.checkpoints || [
            {
              phase: "UNCERTAINTY_ASSESSED",
              state_snapshot: {
                uncertainties: [
                  {
                    code: "MISSING_ACCEPTANCE_RULE",
                    question: "Hệ thống xử lý thế nào khi email chưa được đăng ký?",
                    reason: "Tài liệu không mô tả hành vi cho trường hợp này.",
                    evidence_refs: ["DOC-E2E-1#page-4"],
                    blocking: true,
                  },
                ],
              },
            },
          ],
          receipt: null,
        }),
      });
      return;
    } else if (
      path === "/tu-dong-hoa-ai/luot-chay/AUT-E2E-EVENT-1/uy-quyen-lai" &&
      request.method() === "POST"
    ) {
      retryAccepted = true;
      retryPayload = request.postDataJSON();
      data = {
        ...(automationRun || {}),
        automation_run_id: "AUT-E2E-EVENT-1",
        requester_user_id: `${role.toLowerCase()}-e2e`,
        status: "QUEUED",
        revision: (automationRun?.revision || 1) + 1,
      };
    } else if (path === "/tu-dong-hoa-ai/luot-chay/AUT-E2E-EVENT-1/bang-chung") {
      if (automationEvidenceFailure) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "evidence service unavailable" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          source_facts: [
            {
              source_fact_id: "FACT-E2E-1",
              project_id: projectId,
              artifact_type: "requirement_document",
              artifact_id: "DOC-E2E-1",
              artifact_version_id: "DOC-E2E-V1",
              source: "DOC-E2E-1#page-4",
              source_start: 42,
              source_end: 78,
              quote: "Người dùng đăng nhập bằng email đã đăng ký.",
            },
          ],
          receipt: automationEvidence?.receipt || null,
        }),
      });
      return;
    } else if (path === `/kiem-thu/ban-nhap-ca-kiem-thu/${draftId}/so-sanh`) {
      if (savedPayload && comparisonReadFailureAfterSave && !comparisonReadFailureReturned) {
        comparisonReadFailureReturned = true;
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "TEMPORARY_READ_FAILURE",
              message: "Không đọc được bản mới nhất.",
            },
          }),
        });
        return;
      }
      const proposal = { ...mergedDraft, title: "Ca AI đề xuất" };
      if (bddComparison) {
        proposal.bdd = {
          ...mergedDraft.bdd,
          steps: [{ ...mergedDraft.bdd.steps[0], keyword: "When", text: "Người dùng đăng nhập" }],
        };
      }
      if (omitProposalTestKind) delete proposal.test_kind;
      data = {
        draft: mergedDraft,
        original: { ...mergedDraft, title: "Ca gốc đã có" },
        proposal,
        proposal_available: true,
        is_new: false,
        source_evidence: [],
        custom_fields: customFields,
        duplicates,
        findings: [],
        stale_reasons: [],
        comparison_token: comparisonToken,
      };
    } else if (
      path === `/kiem-thu/ban-nhap-ca-kiem-thu/${draftId}/luu-ban-ghep` &&
      request.method() === "POST"
    ) {
      savedPayload = request.postDataJSON();
      mergeRequests.push(savedPayload);
      mergeAttempts += 1;
      if (mergeAttempts <= mergeFailures) {
        await route.fulfill({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "TEMPORARY_UPSTREAM_FAILURE",
              message: "Dịch vụ tạm thời chưa phản hồi.",
            },
          }),
        });
        return;
      }
      if (conflictOnMerge && !conflictReturned) {
        conflictReturned = true;
        mergedDraft = {
          ...mergedDraft,
          revision: mergedDraft.revision + 1,
          title: "Tên ca từ nguồn mới",
        };
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "REVISION_CONFLICT", message: "Phiên bản đã đổi" },
          }),
        });
        return;
      }
      mergedDraft = { ...mergedDraft, ...savedPayload.result, revision: mergedDraft.revision + 1 };
      data = { draft: mergedDraft };
    } else if (
      path === `/kiem-thu/du-an/${projectId}/ban-nhap-ca-kiem-thu/chap-nhan-nhom` &&
      request.method() === "POST"
    ) {
      approvalPayload = request.postDataJSON();
      approvalAttempts += 1;
      approved = true;
      data = { count: 1, version_ids: ["TCV-E2E-COMPARE"], derived_pending_version_ids: [] };
    } else if (
      path === `/kiem-thu/du-an/${projectId}/truong-ca-kiem-thu` &&
      request.method() === "POST"
    ) {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "PROJECT_PERMISSION_DENIED", message: "Không có quyền" },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data, status: "SUCCESS" }),
    });
  });

  return {
    get savedPayload() {
      return savedPayload;
    },
    get createdTestCasePayload() {
      return createdTestCasePayload;
    },
    get mergeRequests() {
      return mergeRequests;
    },
    get approvalPayload() {
      return approvalPayload;
    },
    get approvalAttempts() {
      return approvalAttempts;
    },
    get approved() {
      return approved;
    },
    get retryAccepted() {
      return retryAccepted;
    },
    get runListCalls() {
      return runListCalls;
    },
    get retryPayload() {
      return retryPayload;
    },
    get sourceParseRetryPayload() {
      return sourceParseRetryPayload;
    },
    get sourceParseRetryCount() {
      return sourceParseRetryCount;
    },
    setComparisonToken(value) {
      comparisonToken = value;
    },
  };
}

test("AI run chỉ cho chủ lượt chạy nối tiếp từ checkpoint an toàn", async ({ page }) => {
  const api = await installWorkspace(page, "QA", {
    automationRun: {
      automation_run_id: "AUT-E2E-EVENT-1",
      project_id: projectId,
      requester_user_id: "qa-e2e",
      requester_role: "QA",
      objective: "Tiếp tục xử lý tài liệu đã nhập",
      status: "FAILED",
      error_code: "AUTOMATION_EXECUTION_FAILED",
      revision: 4,
      checkpoints: [
        {
          checkpoint_id: "ACP-E2E-SAFE",
          phase: "FINALIZED",
          state_snapshot: { tasks: [], uncertainties: [] },
          detail: { resumable: true },
        },
      ],
    },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /Tiếp tục xử lý tài liệu đã nhập/ }).click();
  await expect(page.getByRole("button", { name: "Tiếp tục từ điểm an toàn" })).toBeVisible();
  await page.getByRole("button", { name: "Tiếp tục từ điểm an toàn" }).click();
  await expect.poll(() => api.retryAccepted).toBe(true);
  expect(api.retryPayload).toEqual({ expected_revision: 4 });
});

test("AI status screen offers a real reload after initial event-status API failure", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", { initialRunListFailures: 2 });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();

  await expect.poll(() => api.runListCalls).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "Tải lại dữ liệu AI" })).toBeVisible();
  await page.getByRole("button", { name: "Tải lại dữ liệu AI" }).click();
  await expect(page.getByRole("heading", { name: "Lượt chạy gần đây" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Rà soát tài liệu sau khi tải lên/ }),
  ).toBeVisible();
});

test("AI run khóa retry khi checkpoint cuối có thao tác ghi chưa rõ kết quả", async ({ page }) => {
  await installWorkspace(page, "QA", {
    automationRun: {
      automation_run_id: "AUT-E2E-EVENT-1",
      project_id: projectId,
      requester_user_id: "qa-e2e",
      requester_role: "QA",
      objective: "Đối soát thao tác đã bắt đầu",
      status: "FAILED",
      error_code: "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
      revision: 5,
      checkpoints: [
        {
          checkpoint_id: "ACP-E2E-UNCERTAIN",
          phase: "ACTION_STARTED",
          state_snapshot: { tasks: [], uncertainties: [] },
          detail: { action: "WRITE", task_has_mutation: true },
        },
      ],
    },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /Đối soát thao tác đã bắt đầu/ }).click();
  await expect(page.getByRole("button", { name: "Tiếp tục từ điểm an toàn" })).toHaveCount(0);
  await expect(page.getByText(/Cần đối soát kết quả để tránh chạy lặp/)).toBeVisible();
});

test("QA compares, saves a merged draft, then approves the reviewed group", async ({ page }) => {
  const api = await installWorkspace(page, "QA");
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("cell", { name: "TC-E2E-COMPARE" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(page.getByRole("heading", { name: "So sánh và ghép ca kiểm thử" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bản gốc hiện có" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Đề xuất AI ban đầu" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bản kết quả sau chọn/ghép" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nguồn dẫn và trích dẫn" })).toBeVisible();
  await expect(page.getByText("Người dùng đăng nhập bằng email hợp lệ").first()).toBeVisible();
  await expect(page.getByText("Phiên bản Requirement liên kết").first()).toBeVisible();
  for (const width of [1920, 1440, 1280, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      page: document.documentElement.scrollWidth,
      dialog: document.querySelector('[role="dialog"]')?.getBoundingClientRect().width ?? 0,
    }));
    expect(dimensions.page, `compare dialog page overflow at ${width}px`).toBe(dimensions.viewport);
    expect(dimensions.dialog, `compare dialog missing at ${width}px`).toBeGreaterThan(0);
    const comparisonColumns = await page
      .getByRole("heading", { name: "Bản gốc hiện có" })
      .evaluate(
        (heading) =>
          getComputedStyle(heading.parentElement.parentElement)
            .gridTemplateColumns.trim()
            .split(/\s+/).length,
      );
    expect(comparisonColumns, `comparison layout at ${width}px`).toBe(width >= 1280 ? 3 : 1);
  }
  await page.getByRole("button", { name: "Dùng đề xuất AI" }).first().click();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.expected_revision).toBe(2);
  expect(api.savedPayload.comparison_token).toBe("c".repeat(64));
  await page.getByRole("button", { name: "Đóng", exact: true }).last().click();

  await page.getByRole("checkbox", { name: `Chọn ca chờ duyệt ${draftId}` }).check();
  const selectAllOnPage = page
    .getByRole("checkbox", { name: "Chọn tất cả mục trên trang" })
    .first();
  await expect.poll(() => selectAllOnPage.evaluate((element) => element.indeterminate)).toBe(true);
  await page.getByRole("button", { name: "Duyệt nhóm (1)" }).click();
  await page.getByLabel("Ghi chú duyệt").fill("Đã đối chiếu nguồn, bản AI và bản ghép.");
  await page.getByRole("button", { name: "Đối chiếu và duyệt nhóm" }).click();
  await expect.poll(() => api.approved).toBe(true);
  expect(api.approved).toBe(true);
  expect(api.approvalPayload.items).toHaveLength(1);
  expect(api.approvalPayload.items[0].comparison_token).toBe("c".repeat(64));
  expect(errors).toEqual([]);
});

test("planning load failure provides a retry that reloads the board data", async ({ page }) => {
  await installWorkspace(page, "QA");
  let boardRequests = 0;
  await page.route(`${apiBase}/kiem-thu/du-an/${projectId}/bang-cong-viec`, async (route) => {
    boardRequests += 1;
    if (boardRequests === 1) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "Không tải được bảng công việc." } }),
      });
      return;
    }
    await route.fallback();
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/lap-ke-hoach/board`, { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("alert")).toContainText("Không tải được bảng công việc");
  await page.getByRole("button", { name: "Tải lại dữ liệu lập kế hoạch" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Bảng công việc" }).first()).toBeVisible();
  expect(boardRequests).toBe(2);
});

test("QA must compare an AI draft before approving it individually", async ({ page }) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });

  await page.getByRole("button", { name: "Đối chiếu trước khi duyệt" }).click();

  await expect(page.getByRole("heading", { name: "So sánh và ghép ca kiểm thử" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bản gốc hiện có" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Đề xuất AI ban đầu" })).toBeVisible();
});

test("batch approval reports committed success when refreshing the draft list fails", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", { draftListFailureAfterApproval: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });

  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await page.getByRole("button", { name: "Dùng đề xuất AI" }).first().click();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  await page.getByRole("button", { name: "Đóng", exact: true }).last().click();

  await page.getByRole("checkbox", { name: `Chọn ca chờ duyệt ${draftId}` }).check();
  await page.getByRole("button", { name: "Duyệt nhóm (1)" }).click();
  await page.getByLabel("Ghi chú duyệt").fill("Đã rà soát trước khi duyệt.");
  await page.getByRole("button", { name: "Đối chiếu và duyệt nhóm" }).click();

  await expect.poll(() => api.approved).toBe(true);
  await expect(
    page.getByRole("alert").filter({
      hasText: "Nhóm 1 ca đã được duyệt và lưu nguyên tử, nhưng chưa tải lại được danh sách",
    }),
  ).toBeVisible();
  expect(api.approvalAttempts).toBe(1);
  expect(api.approvalPayload.operation_id).toBeTruthy();
  await expect(page.getByRole("checkbox", { name: `Chọn ca chờ duyệt ${draftId}` })).toHaveCount(0);
});

test("QA can edit a BDD step keyword without changing its stable step identity", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", { bddComparison: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  const keyword = page.getByLabel("Bản kết quả: loại bước BDD 1");
  await expect(keyword).toHaveValue("Given");
  await keyword.selectOption("Then");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();

  expect(api.savedPayload.result.bdd.steps).toEqual([
    { id: "bdd-stable-1", keyword: "Then", text: "Có tài khoản hợp lệ" },
  ]);
});

test("QA can edit nested structured test data while preserving primitive types", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", { nestedTestData: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  await page.getByText("Bước 1 · step-stable-1").click();
  await page.locator('input[aria-label="Bước 1: credentials: retry_count"]').fill("3");
  await page.locator('input[aria-label="Bước 1: credentials: remember"]').check();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();

  expect(api.savedPayload.result.steps[0].test_data).toEqual({
    credentials: { email: "qa@example.test", retry_count: 3, remember: true },
    devices: ["desktop"],
  });
});

test("QA can compare and edit owner and attachments without losing the merged draft", async ({
  page,
}) => {
  const existingAttachment = {
    filename: "huong-dan-cu.txt",
    url: "/tai-len/noi-dung/tc/huong-dan-cu.txt",
  };
  const api = await installWorkspace(page, "QA", {
    initialOwnerId: "tester-cu",
    initialAttachments: [existingAttachment],
  });

  await page.route(`${apiBase}/tai-len/duong-dan-ky-truoc`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: { upload_url: `${apiBase}/mock-storage/test-case-file`, file_path: "tc/new-file" },
      }),
    });
  });
  await page.route(`${apiBase}/mock-storage/test-case-file`, async (route) => {
    expect(route.request().method()).toBe("PUT");
    await route.fulfill({ status: 200, body: "" });
  });
  await page.route(`${apiBase}/tai-len/xac-nhan`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          filename: "huong-dan-moi.txt",
          url: "/tai-len/noi-dung/tc/huong-dan-moi.txt",
          content_type: "text/plain",
          size: 12,
        },
      }),
    });
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(page.getByText("Tester cũ").first()).toBeVisible();
  await expect(
    page
      .getByLabel("Bản kết quả: Người phụ trách")
      .locator("option", { hasText: "Tester đã ngừng" }),
  ).toHaveCount(0);
  await page.getByLabel("Bản kết quả: Người phụ trách").selectOption("tester-moi");
  await page.getByRole("button", { name: "Bỏ tệp huong-dan-cu.txt" }).click();
  await page.getByLabel("Bản kết quả: chọn tệp đính kèm").setInputFiles({
    name: "huong-dan-moi.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("noi dung"),
  });
  await expect(page.getByText("huong-dan-moi.txt").last()).toBeVisible();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();

  expect(api.savedPayload.result.owner_id).toBe("tester-moi");
  expect(api.savedPayload.result.attachments).toEqual([
    {
      filename: "huong-dan-moi.txt",
      url: "/tai-len/noi-dung/tc/huong-dan-moi.txt",
      content_type: "text/plain",
      size: 12,
    },
  ]);
});

test("QA selects an active project member when creating a Test Case", async ({ page }) => {
  const api = await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Tạo ca kiểm thử" }).click();
  await page.getByLabel("Tên", { exact: true }).fill("Kiểm thử có người phụ trách");
  const ownerSelect = page.getByLabel("Người phụ trách ca kiểm thử");
  await expect(ownerSelect.locator("option", { hasText: "Tester đã ngừng" })).toHaveCount(0);
  await ownerSelect.selectOption("tester-moi");
  await page.getByRole("button", { name: "Lưu bản nháp" }).click();
  await expect.poll(() => api.createdTestCasePayload?.owner_id).toBe("tester-moi");
});

test("Test Case step data exposes one add-row action for the whole group", async ({ page }) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Tạo ca kiểm thử" }).click();

  const stepData = page.getByRole("group", { name: "Dữ liệu bước 1" });
  await expect(stepData.getByRole("button", { name: "Thêm dòng dữ liệu" })).toHaveCount(1);
  await stepData.getByRole("button", { name: "Thêm dòng dữ liệu" }).click();
  await expect(stepData.getByRole("button", { name: "Thêm dòng dữ liệu" })).toHaveCount(1);
  await expect(stepData.getByRole("textbox", { name: /tên trường/ })).toHaveCount(2);
});

test("compare hides attachment editing when the project permission is absent", async ({ page }) => {
  const existingAttachment = {
    filename: "huong-dan-cu.txt",
    url: "/tai-len/noi-dung/tc/huong-dan-cu.txt",
  };
  const api = await installWorkspace(page, "QA", {
    initialAttachments: [existingAttachment],
    canManageAttachments: false,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  await expect(page.getByLabel("Bản kết quả: chọn tệp đính kèm")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Bỏ tệp huong-dan-cu.txt" })).toHaveCount(0);
  await page.getByLabel("Bản kết quả: Người phụ trách").selectOption("tester-moi");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();

  expect(api.savedPayload.result.owner_id).toBe("tester-moi");
  expect(api.savedPayload.result.attachments).toEqual([existingAttachment]);
});

test("compare keeps owner unchanged when member visibility permission is absent", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", {
    initialOwnerId: "tester-cu",
    canReadMembers: false,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  await expect(page.getByLabel("Bản kết quả: Người phụ trách")).toHaveCount(0);
  await expect(page.getByText("Người phụ trách đã được thiết lập")).toBeVisible();
  await expect(page.getByText(/không có quyền/i)).toHaveCount(0);
  await page.getByRole("button", { name: "Lấy nội dung AI" }).click();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.result.owner_id).toBe("tester-cu");
});

test("choosing all AI fields removes values omitted by the proposal", async ({ page }) => {
  const api = await installWorkspace(page, "QA", { omitProposalTestKind: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await page.getByRole("button", { name: "Lấy nội dung AI" }).click();
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.result).not.toHaveProperty("test_kind");
  expect(
    api.savedPayload.choices.some(
      (choice) => choice.field === "test_kind" && choice.source === "AI",
    ),
  ).toBe(true);
});

test("Requirement list heading never collapses beside a crowded toolbar", async ({ page }) => {
  await installWorkspace(page, "QA");
  const widths = [1920, 1440, 1280, 768, 390];
  const routes = [
    { path: "yeu-cau", title: "Danh sách yêu cầu", hasDuplicateAction: true },
    { path: "phieu-lam-ro", title: "Chọn yêu cầu", hasDuplicateAction: false },
  ];

  for (const route of routes) {
    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/du-an/${projectId}/${route.path}`, { waitUntil: "domcontentloaded" });
      const panel = page.locator(".requirements-list-panel");
      const heading = panel.locator(".workspace-panel-heading");
      const actions = panel.locator(".workspace-panel-actions");
      await expect(heading.getByRole("heading", { name: route.title })).toBeVisible();
      await expect(actions.getByRole("textbox", { name: "Tìm yêu cầu" })).toBeVisible();
      if (route.hasDuplicateAction) {
        await expect(actions.getByRole("button", { name: "Kiểm tra trùng lặp" })).toBeVisible();
      } else {
        await expect(actions.getByRole("button", { name: "Kiểm tra trùng lặp" })).toHaveCount(0);
      }

      const geometry = await page.evaluate(() => {
        const title = document
          .querySelector(".requirements-list-panel .workspace-panel-heading")
          ?.getBoundingClientRect();
        const toolbarElement = document.querySelector(
          ".requirements-list-panel .workspace-panel-actions",
        );
        const toolbar = toolbarElement?.getBoundingClientRect();
        const controls = [...(toolbarElement?.querySelectorAll("input, button, select") || [])];
        return {
          titleWidth: title?.width ?? 0,
          titleHeight: title?.height ?? 0,
          titleRight: title?.right ?? 0,
          toolbarTop: toolbar?.top ?? 0,
          toolbarLeft: toolbar?.left ?? 0,
          toolbarRight: toolbar?.right ?? 0,
          controlsRight: Math.max(
            ...controls.map((control) => control.getBoundingClientRect().right),
          ),
          toolbarScrollWidth: toolbarElement?.scrollWidth ?? 0,
          toolbarClientWidth: toolbarElement?.clientWidth ?? 0,
          titleBottom: title?.bottom ?? 0,
          pageWidth: document.documentElement.scrollWidth,
          viewportWidth: document.documentElement.clientWidth,
        };
      });

      expect(
        geometry.titleWidth,
        `${route.path} heading width at ${width}px`,
      ).toBeGreaterThanOrEqual(Math.min(width - 32, 180));
      expect(geometry.titleHeight, `${route.path} heading height at ${width}px`).toBeLessThan(64);
      const toolbarIsBesideHeading = geometry.toolbarLeft >= geometry.titleRight - 1;
      const toolbarIsBelowHeading = geometry.toolbarTop >= geometry.titleBottom - 1;
      expect(toolbarIsBesideHeading || toolbarIsBelowHeading).toBe(true);
      expect(geometry.controlsRight, `${route.path} controls at ${width}px`).toBeLessThanOrEqual(
        geometry.toolbarRight + 1,
      );
      expect(
        geometry.toolbarScrollWidth,
        `${route.path} toolbar overflow at ${width}px`,
      ).toBeLessThanOrEqual(geometry.toolbarClientWidth + 1);
      expect(geometry.pageWidth, `${route.path} page overflow at ${width}px`).toBe(
        geometry.viewportWidth,
      );
    }
  }
});

test("only a stale PARSING source can be recovered from the source-document list", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", {
    sourceDocumentStatus: "PARSING",
    sourceDocumentCanRetryParse: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });

  const recoverButton = page.getByRole("button", {
    name: "Khôi phục phân tích bị gián đoạn",
  });
  await expect(recoverButton).toBeVisible();
  await recoverButton.click();

  await expect.poll(() => api.sourceParseRetryCount).toBe(1);
  expect(api.sourceParseRetryPayload).toEqual({ expected_revision: 1 });
  await expect(page.getByRole("button", { name: "Khôi phục phân tích bị gián đoạn" })).toHaveCount(
    0,
  );
});

test("degraded document indexing explains unreadable blocks and their source locations", async ({
  page,
}) => {
  await installWorkspace(page, "QA", {
    sourceDocumentIndexStatus: "DEGRADED",
    sourceUnprocessedBlocks: [
      {
        block_id: "#/pages/4/pictures/0",
        type: "picture",
        reason_code: "PICTURE_TEXT_NOT_EXTRACTED",
        page_no: 4,
        locations: [
          {
            page_no: 4,
            bbox: { x0: 10, y0: 20, x1: 130, y1: 90 },
          },
        ],
      },
    ],
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });

  await expect(
    page
      .getByRole("region", { name: "Bảng dữ liệu" })
      .getByText(/Đã lập chỉ mục một phần · còn 1 khối chưa đọc được/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Xem phần chưa đọc" }).click();
  const sourceRows = page.getByRole("region", { name: "Bảng dữ liệu" });
  await expect(
    sourceRows.getByText("Chưa trích xuất được nội dung hoặc chú thích hình"),
  ).toBeVisible();
  await expect(
    sourceRows.getByText("Trang 4 · vùng 10, 20, 130, 90 · Khối #/pages/4/pictures/0"),
  ).toBeVisible();
});

test("an active PARSING source does not expose a concurrent recovery action", async ({ page }) => {
  await installWorkspace(page, "QA", {
    sourceDocumentStatus: "PARSING",
    sourceDocumentCanRetryParse: false,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("button", { name: "Khôi phục phân tích bị gián đoạn" })).toHaveCount(
    0,
  );
});

test("a parser timeout is explained and leaves the source retryable", async ({ page }) => {
  await installWorkspace(page, "QA", {
    sourceDocumentStatus: "PARSING",
    sourceDocumentCanRetryParse: true,
    sourceDocumentRetryFailure: { parse_error_type: "TimeoutError" },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Khôi phục phân tích bị gián đoạn" }).click();

  await expect(
    page.getByText("Đã hết thời gian phân tích tài liệu; bạn có thể thử lại sau."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Thử phân tích lại" })).toBeVisible();
});

test("a Tester without extract permission cannot see source recovery actions", async ({ page }) => {
  await installWorkspace(page, "TESTER", {
    sourceDocumentStatus: "PARSING",
    sourceDocumentCanRetryParse: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("button", { name: "Khôi phục phân tích bị gián đoạn" })).toHaveCount(
    0,
  );
});

test("source successor selection preserves one source configuration and can be cancelled", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/yeu-cau/import`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Nhập tài liệu" })).toBeVisible();

  const parentSelect = page.getByLabel("Phiên bản nguồn trước (không bắt buộc)");
  await parentSelect.selectOption("RDOC-E2E-SOURCE-V1");
  await expect(page.getByRole("button", { name: "Hủy liên kết phiên bản nguồn" })).toBeVisible();
  await expect(page.getByLabel("Loại tài liệu nguồn").last()).toBeDisabled();
  await expect(page.getByLabel("Riêng tư chỉ người tạo").last()).toBeDisabled();

  await page.getByRole("button", { name: "Hủy liên kết phiên bản nguồn" }).last().click();
  await expect(page.getByLabel("Loại tài liệu nguồn").last()).toBeEnabled();
  await expect(page.getByLabel("Riêng tư chỉ người tạo").last()).toBeEnabled();
  await expect(parentSelect).toHaveValue("");
});

test("failed new Requirement extraction hides an older preview but preserves source text", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  let documentCount = 0;
  let extractionCount = 0;
  await page.route(`${apiBase}/kiem-thu/du-an/${projectId}/tai-lieu-yeu-cau`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    documentCount += 1;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          _id: `RDOC-E2E-MANUAL-${documentCount}`,
          project_id: projectId,
          filename: "requirements.md",
          format: "md",
          content_hash: `hash-${documentCount}`,
          status: "READY",
          visibility: "private",
          shared_with: [],
          ai_enabled: false,
          source_type: "SRS",
          created_by: "qa-e2e",
          revision: 1,
        },
        status: "SUCCESS",
      }),
    });
  });
  await page.route(
    `${apiBase}/kiem-thu/tai-lieu-yeu-cau/RDOC-E2E-MANUAL-1/trich-xuat`,
    async (route) => {
      extractionCount += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            _id: "REQ-IMPORT-E2E-1",
            status: "PREVIEW_READY",
            revision: 1,
            preview: [
              {
                candidate_id: "CANDIDATE-E2E-1",
                requirement_key: "REQ-E2E-OLD-PREVIEW",
                title: "Yêu cầu từ tài liệu trước",
                type: "FUNCTIONAL",
                content_doc: document("Nội dung từ nguồn trước"),
                source_refs: [],
              },
            ],
          },
          status: "SUCCESS",
        }),
      });
    },
  );
  await page.route(
    `${apiBase}/kiem-thu/tai-lieu-yeu-cau/RDOC-E2E-MANUAL-2/trich-xuat`,
    async (route) => {
      extractionCount += 1;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "TEMPORARY_EXTRACTION_FAILURE", message: "Không đọc được nguồn mới." },
        }),
      });
    },
  );
  await page.route(`${apiBase}/kiem-thu/tai-lieu-yeu-cau/RDOC-E2E-MANUAL-1`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          _id: "RDOC-E2E-MANUAL-1",
          project_id: projectId,
          filename: "requirements.md",
          format: "md",
          content_hash: "hash-1",
          status: "READY",
          visibility: "private",
          ai_enabled: false,
          source_type: "SRS",
          created_by: "qa-e2e",
          revision: 1,
        },
        status: "SUCCESS",
      }),
    });
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/yeu-cau/import`, { waitUntil: "domcontentloaded" });

  const sourceEditor = page.getByRole("textbox", { name: "nội dung nguồn" });
  await sourceEditor.fill("Nội dung nguồn đầu tiên đủ để tạo yêu cầu.");
  await page.getByRole("button", { name: "Tạo bản xem trước" }).click();
  await expect(page.getByRole("textbox", { name: "Tên ứng viên 1" })).toHaveValue(
    "Yêu cầu từ tài liệu trước",
  );

  await sourceEditor.fill("Nội dung nguồn thứ hai cần được giữ lại khi API lỗi.");
  await page.getByRole("button", { name: "Tạo bản xem trước" }).click();

  await expect(page.getByText("Không đọc được nguồn mới.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Tên ứng viên 1" })).toHaveCount(0);
  await expect(sourceEditor).toContainText("Nội dung nguồn thứ hai cần được giữ lại khi API lỗi.");
  expect(extractionCount).toBe(2);
});

test("the latest project access response restores a permission after a transient denial", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("link", { name: "Yêu cầu" })).toBeVisible();
  await page.evaluate((id) => {
    window.dispatchEvent(
      new CustomEvent("veriq-project-access-denied", {
        detail: {
          projectId: id,
          pagePath: window.location.pathname,
          permission: "requirement.read",
          code: "PROJECT_PERMISSION_DENIED",
        },
      }),
    );
  }, projectId);

  await expect(page.getByRole("link", { name: "Yêu cầu" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/du-an/${projectId}/yeu-cau$`));
});

test("mobile navigation traps focus and returns focus to its trigger when closed", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });

  const trigger = page.getByRole("button", { name: "Mở điều hướng" });
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "Điều hướng chính" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Đóng điều hướng" }).last()).toBeFocused();

  const focusable = drawer.locator(
    'button:not([disabled]):visible, a[href]:visible, input:not([disabled]):visible, select:not([disabled]):visible, textarea:not([disabled]):visible, [tabindex]:not([tabindex="-1"]):visible',
  );
  const first = focusable.first();
  const last = focusable.last();
  await first.focus();
  await page.keyboard.press("Shift+Tab");
  await expect(last).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(first).toBeFocused();

  await drawer.getByRole("button", { name: "Đóng điều hướng" }).last().click();
  await expect(drawer).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test("an unsaved merge survives a page reload while its comparison token remains current", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  const title = page.getByLabel("Bản kết quả: Tên ca kiểm thử");
  await title.fill("Bản ghép được phục hồi sau khi tải lại");

  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(
    page.getByText("Đã khôi phục bản ghép chưa lưu trên thẻ trình duyệt này."),
  ).toBeVisible();
  await expect(page.getByLabel("Bản kết quả: Tên ca kiểm thử")).toHaveValue(
    "Bản ghép được phục hồi sau khi tải lại",
  );
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(
    page.getByText("Đã lưu bản ghép. Ca cần được rà soát lại trước khi duyệt."),
  ).toBeVisible();
  expect(api.savedPayload.result.title).toBe("Bản ghép được phục hồi sau khi tải lại");
});

test("a recovered merge is preserved but locked when its comparison token has changed", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await page.getByLabel("Bản kết quả: Tên ca kiểm thử").fill("Nội dung cần giữ khi nguồn đã đổi");

  api.setComparisonToken("d".repeat(64));
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(page.getByText(/nguồn hoặc bản nháp đã đổi/)).toBeVisible();
  await expect(
    page.getByText("Nội dung cần giữ khi nguồn đã đổi", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu bản ghép" })).toBeDisabled();
  expect(api.savedPayload).toBeUndefined();
});

test("a merge draft from another account is not restored in the current account session", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  await page.addInitScript(
    ({ currentDraftId }) => {
      const oldDraft = {
        draftId: currentDraftId,
        revision: 2,
        comparisonToken: "c".repeat(64),
        result: { title: "Nội dung riêng của tài khoản trước" },
        choices: [],
        dirty: true,
      };
      sessionStorage.setItem(`veriq:test-case-merge:${currentDraftId}`, JSON.stringify(oldDraft));
      sessionStorage.setItem(
        `veriq:test-case-merge:${currentDraftId}:tester-e2e`,
        JSON.stringify(oldDraft),
      );
    },
    { currentDraftId: draftId },
  );
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  await expect(page.getByLabel("Bản kết quả: Tên ca kiểm thử")).toHaveValue(
    "Ca kiểm thử đăng nhập",
  );
  await expect(page.getByText("Nội dung riêng của tài khoản trước")).toHaveCount(0);
  const storedLegacyRecovery = await page.evaluate(
    (key) => sessionStorage.getItem(key),
    `veriq:test-case-merge:${draftId}`,
  );
  expect(storedLegacyRecovery).toBeNull();
});

test("CV extraction stays private until the member confirms profile evidence", async ({ page }) => {
  const skillProjectId = "PRJ-E2E-SKILL-PROFILE";
  const nextSkillProjectId = "PRJ-E2E-SKILL-PROFILE-NEXT";
  let savedProfile;
  let cvExtractionAttempts = 0;
  const projectPermissions = ["project.read"];
  await page
    .context()
    .addCookies([{ name: "token", value: "ui-skill-profile-session", url: appBaseUrl }]);
  await page.addInitScript(() => localStorage.setItem("veriq_token", "ui-skill-profile-session"));
  await page.route(`${apiBase}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let data = [];
    if (path === "/xac-thuc/ca-nhan") {
      data = {
        _id: "member-skill-e2e",
        email: "member@example.test",
        full_name: "Thành viên kiểm thử",
      };
    } else if (path === `/kiem-thu/du-an/${skillProjectId}`) {
      data = {
        _id: skillProjectId,
        name: "Dự án kiểm tra hồ sơ năng lực",
        planning_method: "SCRUM",
        revision: 1,
        status: "ACTIVE",
        current_membership: { user_id: "member-skill-e2e", project_role: "TESTER" },
        current_permissions: projectPermissions,
      };
    } else if (path === `/kiem-thu/du-an/${nextSkillProjectId}`) {
      data = {
        _id: nextSkillProjectId,
        name: "Dự án hồ sơ năng lực tiếp theo",
        planning_method: "SCRUM",
        revision: 1,
        status: "ACTIVE",
        current_membership: { user_id: "member-skill-e2e", project_role: "TESTER" },
        current_permissions: projectPermissions,
      };
    } else if (path === `/kiem-thu/du-an/${nextSkillProjectId}/ho-so-nang-luc/cua-toi`) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "Không thể tải hồ sơ dự án mới." } }),
      });
      return;
    } else if (path === `/kiem-thu/du-an/${skillProjectId}/ho-so-nang-luc/cua-toi`) {
      if (request.method() === "PUT") {
        savedProfile = request.postDataJSON();
        data = {
          project_id: skillProjectId,
          user_id: "member-skill-e2e",
          ...savedProfile,
          revision: 1,
        };
      } else {
        data = {
          project_id: skillProjectId,
          user_id: "member-skill-e2e",
          skills: [],
          experiences: [],
          availability: "AVAILABLE",
          revision: 0,
        };
      }
    } else if (
      path === `/kiem-thu/du-an/${skillProjectId}/ho-so-nang-luc/cua-toi/trich-xuat-cv` &&
      request.method() === "POST"
    ) {
      cvExtractionAttempts += 1;
      if (cvExtractionAttempts === 1) {
        await route.fulfill({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify({ error: { message: "Không thể trích xuất; hãy thử lại." } }),
        });
        return;
      }
      data = {
        project_id: skillProjectId,
        skills: [
          {
            name: "Kiểm thử API",
            evidence_quote: "Thiết kế kiểm thử API bằng Postman",
            source_block_id: "page-2-block-4",
            page_no: 2,
          },
        ],
        experiences: [],
        warnings: [],
        cv_persisted: false,
        indexed_in_project_knowledge: false,
      };
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data, status: "SUCCESS" }),
    });
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${skillProjectId}/cai-dat`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Hồ sơ năng lực của tôi" })).toBeVisible();
  await expect(page.getByText("Thông tin dự án", { exact: true })).toHaveCount(0);
  await page.getByLabel("Chọn CV PDF DOCX hoặc TXT").setInputFiles({
    name: "ho-so.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Thiết kế kiểm thử API bằng Postman"),
  });
  await page.getByRole("button", { name: "Trích xuất để xem trước" }).click();
  await expect(page.getByText("Không thể trích xuất; hãy thử lại.")).toBeVisible();
  expect(
    await page.getByLabel("Chọn CV PDF DOCX hoặc TXT").evaluate((input) => input.files.length),
  ).toBe(1);
  await page.getByRole("button", { name: "Trích xuất để xem trước" }).click();
  await expect(page.getByText("Kiểm thử API", { exact: true })).toBeVisible();
  await expect(page.getByText(/page-2-block-4 · trang 2/)).toBeVisible();
  await page.getByLabel("Chọn CV PDF DOCX hoặc TXT").setInputFiles({
    name: "ho-so-moi.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Kiểm thử bảo mật"),
  });
  await expect(page.getByText("Kiểm thử API", { exact: true })).toHaveCount(0);
  await page.getByLabel("Chọn CV PDF DOCX hoặc TXT").setInputFiles({
    name: "ho-so.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Thiết kế kiểm thử API bằng Postman"),
  });
  await page.getByRole("button", { name: "Trích xuất để xem trước" }).click();
  await expect(page.getByText("Kiểm thử API", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Đưa ứng viên vào bản nháp để rà soát" }).click();

  const skillCard = page
    .locator("div.rounded-xl.border")
    .filter({ hasText: "Kiểm thử API" })
    .first();
  await expect(skillCard.getByLabel("Tôi xác nhận kỹ năng này")).not.toBeChecked();
  await skillCard.getByLabel("Tôi xác nhận kỹ năng này").check();
  await page.getByRole("button", { name: "Lưu hồ sơ" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu hồ sơ năng lực." }),
  ).toBeVisible();
  expect(savedProfile).toMatchObject({
    expected_revision: 0,
    skills: [
      expect.objectContaining({
        name: "Kiểm thử API",
        confirmed: true,
        evidence: "Thiết kế kiểm thử API bằng Postman",
        source_block_id: "page-2-block-4",
        source_page_no: 2,
      }),
    ],
  });
  expect(savedProfile).not.toHaveProperty("cvFile");
  expect(savedProfile).not.toHaveProperty("raw_cv_text");
  expect(cvExtractionAttempts).toBe(3);

  await skillCard
    .getByLabel("Minh chứng hoặc kinh nghiệm liên quan")
    .fill("Kỹ năng do tôi tự mô tả");
  await expect(skillCard.getByText(/Nguồn CV:/)).toHaveCount(0);
  await page.getByRole("button", { name: "Lưu hồ sơ" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu hồ sơ năng lực." }),
  ).toBeVisible();
  expect(savedProfile.skills[0]).toMatchObject({
    evidence: "Kỹ năng do tôi tự mô tả",
    source_block_id: null,
    source_page_no: null,
  });

  await page.goto(`/du-an/${nextSkillProjectId}/cai-dat`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Năng lực của tôi" }).click();
  await expect(page.getByRole("heading", { name: "Hồ sơ năng lực của tôi" })).toBeVisible();
  await expect(page.getByText("Không thể tải hồ sơ dự án mới.")).toBeVisible();
  await expect(page.getByText("Kiểm thử API", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Kỹ năng do tôi tự mô tả", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Chưa khai báo kỹ năng.")).toBeVisible();
});

test("Tester sees read-only Test Design and receives a backend denial for QA-only field creation", async ({
  page,
}) => {
  await installWorkspace(page, "Tester");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Ca kiểm thử", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Tạo ca kiểm thử" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Thêm trường cho ca" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Duyệt nhóm/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Yêu cầu" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Hồ sơ đảm bảo" })).toHaveCount(0);
  await page.goto(`/du-an/${projectId}/ca-kiem-thu/ai`, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`/du-an/${projectId}$`));
  await expect(page.getByText("Tài khoản hiện không có quyền đọc lượt chạy AI.")).toHaveCount(0);
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Ca kiểm thử", exact: true })).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBe(dimensions.viewport);
  const response = await page.evaluate(async (project) => {
    const response = await fetch(`${apiBase}/kiem-thu/du-an/${project}/truong-ca-kiem-thu`, {
      method: "POST",
      headers: { Authorization: "Bearer ui-tester-session", "Content-Type": "application/json" },
      body: JSON.stringify({ key: "e2e_field", label: "Trường thử", value_type: "TEXT" }),
    });
    return response.status;
  }, projectId);
  expect(response).toBe(403);

  await page.goto(`/du-an/${projectId}/yeu-cau`, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`/du-an/${projectId}$`));
  await expect(page.getByRole("heading", { name: "Danh sách yêu cầu" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Tạo yêu cầu" })).toHaveCount(0);
});

test("project workspace routes remain within the viewport at all required widths", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  const routes = [
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
  const widths = [1920, 1440, 1280, 768, 390];
  const failures = [];
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of routes) {
      const pathname = `/du-an/${projectId}${route ? `/${route}` : ""}`;
      const response = await page.goto(pathname, { waitUntil: "domcontentloaded" });
      if (!response?.ok()) failures.push({ route: pathname, width, status: response?.status() });
      const dimensions = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));
      if (dimensions.document !== dimensions.viewport || dimensions.body !== dimensions.viewport) {
        failures.push({ route: pathname, width, ...dimensions });
      }
    }
  }

  expect(failures).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("a stale merge keeps local edits but requires a fresh comparison before saving", async ({
  page,
}) => {
  await installWorkspace(page, "QA", { conflictOnMerge: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  const title = page.getByLabel("Bản kết quả: Tên ca kiểm thử");
  await title.fill("Bản ghép người dùng đang sửa");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();

  const staleAlert = page.locator('div[role="alert"].rounded-control');
  await expect(staleAlert).toContainText("hãy tải lại và đối chiếu");
  await expect(page.getByText("Bản ghép người dùng đang sửa").last()).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu bản ghép" })).toBeDisabled();
  await page.getByRole("button", { name: "Tải lại dữ liệu đối chiếu" }).click();
  await expect(title).toHaveValue("Tên ca từ nguồn mới");
  await expect(staleAlert).toHaveCount(0);
});

test("a temporary 5xx keeps merged edits and retries the same idempotent operation", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", { mergeFailures: 1 });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  const title = page.getByLabel("Bản kết quả: Tên ca kiểm thử");
  await title.fill("Bản ghép cần giữ sau lỗi máy chủ");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();

  await expect(page.locator('div[role="alert"].rounded-control')).toContainText(
    "Dịch vụ tạm thời chưa phản hồi.",
  );
  await expect(title).toHaveValue("Bản ghép cần giữ sau lỗi máy chủ");
  await expect(page.getByRole("button", { name: "Lưu bản ghép" })).toBeEnabled();

  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.mergeRequests).toHaveLength(2);
  expect(api.mergeRequests[0].operation_id).toBe(api.mergeRequests[1].operation_id);
  expect(api.mergeRequests[1].result.title).toBe("Bản ghép cần giữ sau lỗi máy chủ");
});

test("a successful merge is not reported as failed when the follow-up comparison read fails", async ({
  page,
}) => {
  await installWorkspace(page, "QA", { comparisonReadFailureAfterSave: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  const title = page.getByLabel("Bản kết quả: Tên ca kiểm thử");
  await title.fill("Bản ghép đã commit ở server");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();

  await expect(page.getByText(/^Đã lưu bản ghép\./)).toBeVisible();
  await expect(page.getByText(/Bản ghép đã được lưu, nhưng chưa tải được phiên/)).toBeVisible();
  await expect(page.getByText("Bản ghép đã commit ở server").last()).toBeVisible();
  await expect(title).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Lưu bản ghép" })).toBeDisabled();
  await page.getByRole("button", { name: "Tải lại dữ liệu đối chiếu" }).click();
  await expect(page.getByText("Bản ghép đã commit ở server").last()).toBeVisible();
});

test("QA can record a reason after reviewing a possible duplicate", async ({ page }) => {
  const api = await installWorkspace(page, "QA", {
    duplicates: [
      {
        test_case_id: "TC-EXISTING",
        version_id: "TCV-EXISTING",
        test_case_key: "TC-0001",
        title: "Ca đăng nhập hiện có",
        version: 1,
        score: 0.91,
        reasons: ["Cùng liên kết yêu cầu"],
      },
    ],
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await expect(page.getByRole("heading", { name: "Ca đã có nội dung gần giống" })).toBeVisible();
  const reason = page.getByLabel("Lý do giữ ca này riêng sau khi QA rà soát trùng lặp");
  await reason.fill("Ca mới kiểm chứng một nhánh nghiệp vụ khác đã được QA xác nhận.");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.result.duplicate_reason).toBe(
    "Ca mới kiểm chứng một nhánh nghiệp vụ khác đã được QA xác nhận.",
  );
});

test("QA edits custom fields with their configured types in the comparison result", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", {
    customFields: [
      {
        _id: "TCF-BROWSER",
        key: "browser",
        label: "Trình duyệt",
        value_type: "choice",
        choices: ["Chrome", "Firefox"],
        required: false,
        status: "ACTIVE",
      },
      {
        _id: "TCF-MOBILE",
        key: "mobile",
        label: "Chạy trên điện thoại",
        value_type: "boolean",
        required: false,
        status: "ACTIVE",
      },
    ],
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();
  await page.getByLabel("Trình duyệt").selectOption("Firefox");
  await page.getByLabel("Chạy trên điện thoại").selectOption("true");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.result.custom_values).toEqual({ browser: "Firefox", mobile: true });
});

test("a choice value removed from project configuration remains visible until corrected", async ({
  page,
}) => {
  const api = await installWorkspace(page, "QA", {
    customFields: [
      {
        _id: "TCF-BROWSER",
        key: "browser",
        label: "Trình duyệt",
        value_type: "choice",
        choices: ["Chrome", "Firefox"],
        required: true,
        status: "ACTIVE",
      },
    ],
    initialCustomValues: { browser: "LegacyBrowser" },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/ca-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Đối chiếu gốc và AI" }).click();

  const browser = page.getByLabel("Trình duyệt");
  await expect(browser).toHaveValue("LegacyBrowser");
  await expect(page.getByText(/Giá trị đang lưu không còn trong lựa chọn hiện tại/)).toBeVisible();
  await browser.selectOption("");
  await expect(browser).toHaveValue("");
  await page.getByRole("button", { name: "Lưu bản ghép" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản ghép" })).toBeVisible();
  expect(api.savedPayload.result.custom_values).toEqual({});
});

test("AI event runs appear without asking the user to start them manually", async ({ page }) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await expect(page.getByText("Rà soát tài liệu sau khi tải lên")).toBeVisible({ timeout: 12000 });
  await expect(page.getByText("Lượt chạy gần đây")).toBeVisible();
  await expect(page.getByText("AUT-E2E-EVENT-1")).toBeVisible();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();
  await expect(page.getByRole("heading", { name: "Cần bổ sung thông tin" })).toBeVisible();
  await expect(page.getByText("Hệ thống xử lý thế nào khi email chưa được đăng ký?")).toBeVisible();
  await expect(page.getByText("Nguồn liên quan: DOC-E2E-1#page-4")).toBeVisible();
  await expect(page.getByRole("region", { name: "Trích dẫn nguồn đã kiểm chứng" })).toContainText(
    "Người dùng đăng nhập bằng email đã đăng ký.",
  );
  await expect(page.getByText("DOC-E2E-V1")).toBeVisible();
  await expect(
    page.getByText(/Khi nguồn được cập nhật, hệ thống sẽ tự tiếp nhận sự kiện mới/),
  ).toBeVisible();
  await expect(page.getByText("AUTOMATION_WAITING_FOR_INPUT")).toHaveCount(0);
});

test("AI run displays the descendant workflow while the root run is already completed", async ({
  page,
}) => {
  await installWorkspace(page, "QA", {
    automationRun: { status: "COMPLETED" },
    automationWorkflow: {
      root_automation_run_id: "AUT-E2E-EVENT-1",
      status: "RUNNING",
      terminal: false,
      succeeded: false,
      truncated: false,
      run_count: 2,
      active_count: 1,
      blocked_count: 0,
      failed_count: 0,
      runs: [
        { automation_run_id: "AUT-E2E-EVENT-1", status: "COMPLETED" },
        {
          automation_run_id: "AUT-E2E-DESIGN-1",
          trigger: "REQUIREMENT_CHANGED",
          status: "RUNNING",
          parent_automation_run_id: "AUT-E2E-EVENT-1",
        },
      ],
    },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  const workflow = page.getByRole("region", { name: "Trạng thái toàn luồng AI" });
  await expect(workflow).toContainText("Đang xử lý");
  await expect(workflow).toContainText("2 lượt · 1 đang chạy");
  await expect(workflow).toContainText("AUT-E2E-DESIGN-1");
});

test("the open AI run refreshes its workflow status when a new child run appears", async ({
  page,
}) => {
  const waitingWorkflow = {
    root_automation_run_id: "AUT-E2E-EVENT-1",
    status: "AWAITING_INPUT",
    terminal: false,
    succeeded: false,
    truncated: false,
    run_count: 1,
    active_count: 0,
    blocked_count: 1,
    failed_count: 0,
    runs: [{ automation_run_id: "AUT-E2E-EVENT-1", status: "AWAITING_INPUT" }],
  };
  const childRunningWorkflow = {
    root_automation_run_id: "AUT-E2E-EVENT-1",
    status: "RUNNING",
    terminal: false,
    succeeded: false,
    truncated: false,
    run_count: 2,
    active_count: 1,
    blocked_count: 1,
    failed_count: 0,
    runs: [
      { automation_run_id: "AUT-E2E-EVENT-1", status: "AWAITING_INPUT" },
      {
        automation_run_id: "AUT-E2E-DESIGN-2",
        parent_automation_run_id: "AUT-E2E-EVENT-1",
        trigger: "REQUIREMENT_CHANGED",
        status: "RUNNING",
      },
    ],
  };
  await installWorkspace(page, "QA", {
    automationRun: { status: "AWAITING_INPUT" },
    automationWorkflow: waitingWorkflow,
    automationWorkflowSnapshots: [waitingWorkflow, childRunningWorkflow],
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  const workflow = page.getByRole("region", { name: "Trạng thái toàn luồng AI" });
  await expect(workflow).toContainText("Cần bổ sung thông tin");
  await expect(workflow).toContainText("1 lượt · 0 đang chạy · 1 đang chờ");
  await expect(workflow).toContainText("AUT-E2E-DESIGN-2", { timeout: 12000 });
  await expect(workflow).toContainText("2 lượt · 1 đang chạy · 1 đang chờ");
});

test("the open AI run refreshes its own status after an event continues it", async ({ page }) => {
  await installWorkspace(page, "QA", {
    automationRunSnapshots: [
      { status: "AWAITING_INPUT", revision: 1 },
      { status: "COMPLETED", revision: 2 },
    ],
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  await expect(page.getByRole("heading", { name: "Cần bổ sung thông tin" })).toBeVisible();
  await expect(page.getByText("Đã hoàn tất").first()).toBeVisible({ timeout: 12000 });
  await expect(page.getByRole("heading", { name: "Cần bổ sung thông tin" })).toHaveCount(0);
});

test("AI run shows verified source-to-requirement-and-test-case lineage", async ({ page }) => {
  await installWorkspace(page, "QA", {
    automationRun: {
      automation_run_id: "AUT-E2E-EVENT-1",
      project_id: projectId,
      requester_user_id: "qa-e2e",
      requester_role: "QA",
      objective: "Biên dịch nghĩa vụ từ tài liệu",
      status: "COMPLETED",
      revision: 2,
    },
    automationEvidence: {
      receipt: {
        blueprint_claim_lineage: [
          {
            claim_type: "OBLIGATION",
            claim_key: "OBL-LOGIN-1",
            source_fact_ids: ["FACT-E2E-1"],
            source_quote_sha256: "a".repeat(64),
          },
          {
            claim_type: "CLARIFICATION",
            claim_key: "CLR-LOGIN-ERROR-1",
            source_fact_ids: ["FACT-E2E-1"],
            source_quote_sha256: "a".repeat(64),
          },
        ],
        blueprint_artifact_lineage: [
          {
            obligation_key: "OBL-LOGIN-1",
            source_fact_ids: ["FACT-E2E-1"],
            artifact_type: "requirement_version",
            artifact_id: "REQV-E2E-1",
          },
          {
            obligation_key: "OBL-LOGIN-1",
            source_fact_ids: ["FACT-E2E-1"],
            artifact_type: "test_case_version",
            artifact_id: "TCV-E2E-1",
          },
        ],
      },
    },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await expect(page.getByText("Biên dịch nghĩa vụ từ tài liệu")).toBeVisible({ timeout: 12000 });
  await page.getByRole("button", { name: /Biên dịch nghĩa vụ từ tài liệu/ }).click();
  const lineage = page.getByRole("region", {
    name: "Liên kết bản thiết kế kiểm thử với nguồn và kết quả",
  });
  await expect(lineage).toContainText("OBL-LOGIN-1");
  await expect(lineage).toContainText("CLR-LOGIN-ERROR-1");
  await expect(lineage).toContainText("Người dùng đăng nhập bằng email đã đăng ký.");
  await expect(lineage).toContainText("REQV-E2E-1");
  await expect(lineage).toContainText("TCV-E2E-1");
});

test("AI run details remain visible if evidence lookup is temporarily unavailable", async ({
  page,
}) => {
  await installWorkspace(page, "QA", {
    automationEvidenceFailure: true,
    automationRun: { status: "AWAITING_INPUT" },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  await expect(page.getByText("AUT-E2E-EVENT-1").last()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cần bổ sung thông tin" })).toBeVisible();
  await expect(page.getByText("Hệ thống xử lý thế nào khi email chưa được đăng ký?")).toBeVisible();
  await expect(
    page.getByRole("alert").filter({ hasText: "Không thể hoàn tất tự động hóa AI" }),
  ).toBeVisible();
  await expect(page.getByText("evidence service unavailable")).toHaveCount(0);
});

test("AI run explains an MCP discovery failure without exposing provider details", async ({
  page,
}) => {
  await installWorkspace(page, "QA", {
    automationRun: {
      status: "COMPLETED",
      result: {
        observations: [
          {
            phase: "MCP_DISCOVERY",
            connection_id: "mcp-project-source",
            tool_name: "read_contract",
            reason_code: "MCP_DISCOVERY_TIMEOUT",
            provider_error: "must never be displayed",
          },
        ],
      },
    },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  const diagnostics = page.getByRole("status", { name: "Nguồn MCP cần kiểm tra" });
  await expect(diagnostics).toContainText("Nguồn MCP không phản hồi đúng hạn");
  await expect(diagnostics).toContainText("read_contract");
  await expect(diagnostics).not.toContainText("must never be displayed");
});

test("AI run explains incomplete source extraction without exposing raw parser data", async ({
  page,
}) => {
  await installWorkspace(page, "QA", {
    automationRun: {
      status: "DEGRADED",
      error_code: "SOURCE_EXTRACTION_INCOMPLETE",
      result: {
        observations: [
          {
            tool_name: "process_ingested_requirement_document",
            result: {
              reason_code: "SOURCE_EXTRACTION_INCOMPLETE",
              source_extraction_gaps: [
                {
                  document_id: "RDOC-E2E-1",
                  reason: "SOURCE_EXTRACTION_INCOMPLETE",
                  index_status: "DEGRADED",
                  parser: "docling",
                  page_count: 18,
                  unprocessed_block_count: 1,
                  unprocessed_blocks: [
                    {
                      block_id: "table-page-7",
                      page_no: 7,
                      type: "table",
                      reason_code: "TABLE_TEXT_NOT_EXTRACTED",
                      provider_payload: "must never be displayed",
                    },
                  ],
                  unprocessed_blocks_truncated: false,
                },
              ],
            },
          },
        ],
      },
    },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  const diagnostics = page.getByRole("status", {
    name: "Phần tài liệu nguồn chưa trích xuất đầy đủ",
  });
  await expect(diagnostics).toContainText("Tài liệu chưa được đọc đầy đủ");
  await expect(diagnostics).toContainText("RDOC-E2E-1");
  await expect(diagnostics).toContainText("Trang 7");
  await expect(diagnostics).toContainText("Chưa trích xuất được nội dung bảng");
  await expect(diagnostics).not.toContainText("must never be displayed");
});

test("authorization pause explains the missing project role before retry", async ({ page }) => {
  await installWorkspace(page, "QA", {
    automationRun: {
      status: "AWAITING_AUTHORIZATION",
      error_code: "PROJECT_QA_EXECUTOR_UNAVAILABLE",
    },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/du-an/${projectId}/tu-dong-hoa`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "AI tự động hóa" }).click();
  await page.getByRole("button", { name: /AUT-E2E-EVENT-1/ }).click();

  await expect(page.getByRole("status")).toContainText(
    "Dự án chưa có thành viên QA đang hoạt động",
  );
  await expect(
    page.getByRole("alert").filter({ hasText: "Dự án chưa có thành viên QA đang hoạt động" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Thử lại sau khi bổ sung QA" })).toBeVisible();
});

test("dashboard does not show a fake task progress when the project summary is missing", async ({
  page,
}) => {
  await installWorkspace(page, "QA");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}`, { waitUntil: "domcontentloaded" });

  const progressPanel = page.getByRole("region", { name: "Tiến độ dự án" });
  await expect(progressPanel).toContainText("Chưa có công việc");
  await expect(progressPanel).not.toContainText("Tiến độ công việc 0%");
});

test("non-functional plan editor preserves structured fields without raw JSON textareas", async ({
  page,
}) => {
  const plan = {
    _id: "NFR-E2E-1",
    plan_type: "PERFORMANCE_TEST_PLAN",
    name: "Kiểm tra tải đăng nhập",
    objective: "Xác nhận phản hồi dưới tải thông thường",
    scope: ["Luồng đăng nhập"],
    approach: "Tăng tải theo từng mức đã định nghĩa",
    entry_criteria: [],
    exit_criteria: [],
    tool_refs: [],
    workload_model: { concurrent_users: 40, ramp_up_seconds: 30 },
    baseline: { p95_ms: 250 },
    load: {},
    stress: {},
    spike: {},
    soak: {},
    concurrency: { users: 40 },
    throughput_target: null,
    response_time_target: { p95_ms: 300 },
    error_rate_target: null,
    data: { account_type: "standard" },
    environment: { name: "staging" },
    test_conditions: ["COND-E2E-1"],
    test_cases: [],
    requirement_refs: [],
    status: "DRAFT",
    revision: 2,
  };
  await installWorkspace(page, "QA", {
    canManageNfr: true,
    nonFunctionalPlans: [plan],
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/du-an/${projectId}/lan-chay-kiem-thu`, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Kiểm thử phi chức năng" }).click();
  await page.getByRole("button", { name: "Mở" }).click();
  await page.getByRole("button", { name: "Chỉnh sửa" }).click();
  await page
    .getByRole("dialog", { name: "Cập nhật kế hoạch kiểm thử phi chức năng" })
    .getByRole("button", { name: "Lưu" })
    .click();

  const editor = page.getByRole("dialog", { name: "Kế hoạch kiểm thử hiệu năng" });
  await expect(editor.getByText("Mô hình tải", { exact: true })).toBeVisible();
  await expect(editor.getByText("Thông số kiểm thử hiệu năng")).toBeVisible();
  await expect(editor.getByLabel("Tên thuộc tính").first()).toHaveValue("concurrent_users");
  await expect(editor.getByLabel("Tên thuộc tính").nth(1)).toHaveValue("ramp_up_seconds");
  await expect(editor.getByLabel("Tên thuộc tính").nth(2)).toHaveValue("p95_ms");
  await expect(editor.getByLabel("Giá trị concurrent_users")).toHaveValue("40");
  await expect(editor.getByLabel("Giá trị ramp_up_seconds")).toHaveValue("30");
  await expect(editor.getByLabel("Giá trị account_type")).toHaveValue("standard");
  await expect(editor.locator("textarea")).toHaveCount(2);
});
