import assert from "node:assert/strict";
import test from "node:test";
import {
  automationAuthorizationGuidance,
  automationCheckpointView,
  automationMcpDiscoveryIssues,
  automationSourceExtractionGaps,
  canResumeAutomationRun,
  latestAutomationUncertainties,
  workflowForSelectedRun,
} from "./automationRun.logic.mjs";
import { messageOf, valueLabel } from "./testing.logic.mjs";

const owner = "user-1";
const safeCheckpoint = { phase: "FINALIZED", state_snapshot: { tasks: [] }, detail: {} };

test("lượt đang mở nhận trạng thái toàn luồng mới từ lần làm mới danh sách", () => {
  const workflow = { status: "RUNNING", active_count: 1, run_count: 2 };
  assert.equal(
    workflowForSelectedRun(
      [
        { automation_run_id: "other-run", workflow: { status: "COMPLETED" } },
        { automation_run_id: "selected-run", workflow },
      ],
      "selected-run",
    ),
    workflow,
  );
  assert.equal(workflowForSelectedRun([], "selected-run"), null);
  assert.equal(
    workflowForSelectedRun([{ automation_run_id: "selected-run" }], "selected-run"),
    null,
  );
});

test("nhật ký checkpoint hiển thị bước, trạng thái, thời điểm và hướng khôi phục an toàn", () => {
  const checkpoint = automationCheckpointView({
    checkpoint_sequence: 2,
    phase: "FINALIZED",
    status: "DEGRADED",
    created_at: "2026-10-25T03:04:05.000Z",
    detail: {
      reason_code: "AUTOMATION_QUEUE_UNAVAILABLE",
      retryable: true,
      resumable: true,
      dispatch_attempt: 2,
      provider_error: "must not be displayed",
    },
  });

  assert.equal(checkpoint.sequence, 2);
  assert.equal(checkpoint.phase, "Đã ghi nhận kết quả");
  assert.equal(checkpoint.status, "DEGRADED");
  assert.match(checkpoint.createdAt, /25\/10\/26/);
  assert.deepEqual(checkpoint.facts, [
    "Không gửi được lượt chạy vào hàng đợi",
    "Có thể thử lại",
    "Có thể tiếp tục từ điểm đã lưu",
    "Lần gửi thứ 2",
  ]);
  assert.equal(JSON.stringify(checkpoint).includes("provider_error"), false);
});

test("checkpoint không có chi tiết hoặc thời điểm hợp lệ vẫn hiển thị trạng thái an toàn", () => {
  assert.deepEqual(
    automationCheckpointView({ phase: "UNKNOWN_PHASE", status: "RUNNING", created_at: "invalid" }),
    {
      phase: "Bước xử lý chưa được nhận diện",
      status: "RUNNING",
      sequence: null,
      createdAt: "Thời điểm chưa được ghi nhận",
      facts: [],
    },
  );
  assert.equal(automationCheckpointView(null), null);
});

test("chủ lượt chạy có thể cấp quyền tiếp tục", () => {
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "AWAITING_AUTHORIZATION" },
      [],
      owner,
    ),
    true,
  );
});

test("hướng dẫn quyền phân biệt thiếu QA với quyền người thực hiện bị thay đổi", () => {
  assert.deepEqual(
    automationAuthorizationGuidance({ error_code: "PROJECT_QA_EXECUTOR_UNAVAILABLE" }),
    {
      message:
        "Dự án chưa có thành viên QA đang hoạt động. Hãy thêm hoặc kích hoạt QA rồi thử lại.",
      action: "Thử lại sau khi bổ sung QA",
    },
  );
  assert.match(
    automationAuthorizationGuidance({ error_code: "AUTOMATION_PRINCIPAL_ROLE_CHANGED" }).message,
    /Vai trò.*đã thay đổi/,
  );
});

test("trạng thái và checkpoint của lượt AI được hiển thị bằng tiếng Việt", () => {
  assert.equal(valueLabel("AWAITING_AUTHORIZATION"), "Cần kiểm tra quyền truy cập");
  assert.equal(valueLabel("RUNNING"), "Đang xử lý");
  assert.equal(valueLabel("RECONCILIATION_REQUIRED"), "Cần đối soát kết quả");
  assert.equal(valueLabel("FACTS_EXTRACTED"), "Đã trích xuất thông tin có nguồn");
  assert.equal(valueLabel("ACTIONS_VERIFIED"), "Đã kiểm tra kết quả");
  assert.equal(valueLabel("OBLIGATION"), "Nghĩa vụ kiểm thử");
  assert.equal(valueLabel("CLARIFICATION"), "Điểm cần làm rõ");
  assert.equal(valueLabel("test_case_version"), "Phiên bản ca kiểm thử");
});

test("chẩn đoán MCP chỉ hiển thị mã an toàn đã biết và loại bỏ trùng lặp", () => {
  assert.deepEqual(
    automationMcpDiscoveryIssues({
      observations: [
        {
          phase: "MCP_DISCOVERY",
          reason_code: "MCP_DISCOVERY_TIMEOUT",
          connection_id: "mcp-1",
          tool_name: "read_contract",
          provider_error: "sensitive provider response",
        },
        {
          phase: "MCP_DISCOVERY",
          reason_code: "MCP_DISCOVERY_TIMEOUT",
          connection_id: "mcp-1",
          tool_name: "read_contract",
        },
        { phase: "MCP_DISCOVERY", reason_code: "UNRECOGNIZED_SECRET" },
        { phase: "PLAN", reason_code: "MCP_DISCOVERY_TIMEOUT" },
      ],
    }),
    [
      {
        reason_code: "MCP_DISCOVERY_TIMEOUT",
        message: "Nguồn kết nối không phản hồi đúng hạn.",
        tool_name: "read_contract",
      },
    ],
  );
});

test("lượt chạy AI hiển thị chẩn đoán trích xuất nguồn có giới hạn", () => {
  assert.deepEqual(
    automationSourceExtractionGaps({
      result: {
        observations: [
          {
            result: {
              reason_code: "SOURCE_EXTRACTION_INCOMPLETE",
              source_extraction_gaps: [
                {
                  document_id: "DOC-1",
                  reason: "SOURCE_EXTRACTION_INCOMPLETE",
                  index_status: "DEGRADED",
                  parser: "docling",
                  page_count: 20,
                  unprocessed_block_count: 1,
                  unprocessed_blocks: [
                    {
                      page_no: 8,
                      block_id: "table-8",
                      type: "table",
                      reason_code: "TABLE_TEXT_NOT_EXTRACTED",
                      secret: "must not pass through",
                    },
                  ],
                  unprocessed_blocks_truncated: false,
                },
              ],
            },
          },
        ],
      },
    }),
    [
      {
        document_id: "DOC-1",
        index_status: "DEGRADED",
        parser: "docling",
        page_count: 20,
        unprocessed_block_count: 1,
        unprocessed_blocks: [
          {
            block_id: "table-8",
            page_no: 8,
            type: "table",
            reason_code: "TABLE_TEXT_NOT_EXTRACTED",
          },
        ],
        unprocessed_blocks_truncated: false,
      },
    ],
  );
});

test("chỉ FAILED hoặc DEGRADED có checkpoint an toàn mới được tiếp tục", () => {
  assert.equal(
    canResumeAutomationRun({ requester_user_id: owner, status: "FAILED" }, [safeCheckpoint], owner),
    true,
  );
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "DEGRADED" },
      [safeCheckpoint],
      owner,
    ),
    true,
  );
  assert.equal(
    canResumeAutomationRun({ requester_user_id: owner, status: "FAILED" }, [], owner),
    false,
  );
});

test("queue unavailable có thể tiếp tục mà không có checkpoint", () => {
  assert.equal(
    canResumeAutomationRun(
      {
        requester_user_id: owner,
        status: "DEGRADED",
        error_code: "AUTOMATION_QUEUE_UNAVAILABLE",
      },
      [],
      owner,
    ),
    true,
  );
});

test("không tiếp tục khi checkpoint cuối có thao tác ghi chưa rõ kết quả", () => {
  const uncertainCheckpoint = {
    ...safeCheckpoint,
    phase: "ACTION_STARTED",
    detail: { action: "WRITE", task_has_mutation: true },
  };
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "FAILED" },
      [uncertainCheckpoint],
      owner,
    ),
    false,
  );
  assert.equal(
    canResumeAutomationRun(
      {
        requester_user_id: owner,
        status: "DEGRADED",
        error_code: "AUTOMATION_ACTION_OUTCOME_UNCERTAIN",
      },
      [safeCheckpoint],
      owner,
    ),
    false,
  );
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "AWAITING_AUTHORIZATION" },
      [uncertainCheckpoint],
      owner,
    ),
    false,
  );
});

test("checkpoint an toàn cũ không ghi đè checkpoint cuối thiếu căn cứ", () => {
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "FAILED" },
      [safeCheckpoint, { phase: "FAILED", state_snapshot: null, detail: {} }],
      owner,
    ),
    false,
  );
});

test("không hiển thị câu hỏi làm rõ cũ nếu checkpoint mới nhất không còn snapshot", () => {
  assert.deepEqual(
    latestAutomationUncertainties([
      {
        ...safeCheckpoint,
        state_snapshot: { uncertainties: [{ question: "Câu hỏi cũ" }] },
      },
      { phase: "FAILED", state_snapshot: null, detail: {} },
    ]),
    [],
  );
  assert.deepEqual(
    latestAutomationUncertainties([
      { ...safeCheckpoint, state_snapshot: { uncertainties: [{ question: "Còn thiếu" }] } },
    ]),
    [{ question: "Còn thiếu" }],
  );
});

test("chỉ người tạo lượt chạy được phép tiếp tục và chỉ ở trạng thái kết thúc hỗ trợ", () => {
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "FAILED" },
      [safeCheckpoint],
      "user-2",
    ),
    false,
  );
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "RUNNING" },
      [safeCheckpoint],
      owner,
    ),
    false,
  );
  assert.equal(
    canResumeAutomationRun(
      { requester_user_id: owner, status: "COMPLETED" },
      [safeCheckpoint],
      owner,
    ),
    false,
  );
});

test("lỗi retry được diễn giải bằng thông báo nghiệp vụ thay vì mã nội bộ", () => {
  assert.match(
    messageOf(
      Object.assign(new Error("AUTOMATION_RETRY_REQUIRES_RECONCILIATION"), {
        code: "AUTOMATION_RETRY_REQUIRES_RECONCILIATION",
      }),
    ),
    /đối soát kết quả thao tác/,
  );
  assert.match(
    messageOf(Object.assign(new Error("REVISION_CONFLICT"), { code: "REVISION_CONFLICT" })),
    /đã tải trạng thái mới nhất/,
  );
});

test("nguồn trùng chưa sẵn sàng có hướng xử lý rõ ràng", () => {
  assert.match(
    messageOf(
      Object.assign(new Error("DUPLICATE_SOURCE_NOT_READY"), {
        code: "DUPLICATE_SOURCE_NOT_READY",
      }),
    ),
    /chờ nguồn sẵn sàng rồi thử lại/,
  );
  assert.match(
    messageOf(
      Object.assign(new Error("DUPLICATE_SOURCE_RECOVERY_PENDING"), {
        code: "DUPLICATE_SOURCE_RECOVERY_PENDING",
      }),
    ),
    /Nguồn vẫn được giữ/,
  );
  assert.match(
    messageOf(
      Object.assign(new Error("DUPLICATE_SOURCE_ARCHIVED"), {
        code: "DUPLICATE_SOURCE_ARCHIVED",
      }),
    ),
    /khôi phục tài liệu hiện có/,
  );
});

test("nguồn tài liệu chưa trích xuất đầy đủ có hướng dẫn tiếng Việt", () => {
  assert.match(
    messageOf(
      Object.assign(new Error("SOURCE_EXTRACTION_INCOMPLETE"), {
        code: "SOURCE_EXTRACTION_INCOMPLETE",
      }),
    ),
    /dừng an toàn vì còn phần tài liệu chưa trích xuất đầy đủ/,
  );
});

test("lỗi trường mở rộng hiển thị hướng dẫn tiếng Việt thay vì mã nội bộ", () => {
  assert.match(
    messageOf(
      Object.assign(new Error("TEST_CASE_CUSTOM_FIELD_VALUE_INVALID"), {
        code: "TEST_CASE_CUSTOM_FIELD_VALUE_INVALID",
      }),
    ),
    /chưa khớp kiểu dữ liệu hoặc lựa chọn/,
  );
  assert.match(
    messageOf(
      Object.assign(new Error("TEST_CASE_CUSTOM_FIELD_REQUIRED"), {
        code: "TEST_CASE_CUSTOM_FIELD_REQUIRED",
      }),
    ),
    /trường mở rộng bắt buộc/,
  );
});
