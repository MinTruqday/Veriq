const RETRYABLE_STATUSES = new Set(["FAILED", "DEGRADED"]);

const checkpointPhaseLabels = {
  QUEUED: "Đang chờ xử lý",
  WORKER_STARTED: "Worker đã tiếp nhận lượt chạy",
  OBSERVED: "Đã tiếp nhận sự kiện",
  FACTS_EXTRACTED: "Đã trích xuất thông tin có nguồn",
  UNCERTAINTY_ASSESSED: "Đã đánh giá thông tin còn thiếu",
  PLAN_CREATED: "Đã lập kế hoạch xử lý",
  ACTION_STARTED: "Đang thực hiện tác vụ",
  ACTIONS_EXECUTED: "Đã thực hiện tác vụ",
  ACTIONS_VERIFIED: "Đã kiểm tra kết quả",
  GRAPH_COMPLETED: "Đã hoàn tất luồng xử lý",
  FINALIZED: "Đã ghi nhận kết quả",
};

const checkpointReasonLabels = {
  AUTOMATION_RESUMED_FROM_CHECKPOINT: "Đã tiếp tục từ checkpoint an toàn",
  AUTOMATION_RETRY_STARTED: "Đã bắt đầu lượt thử lại",
  AUTOMATION_QUEUE_RETRY: "Hệ thống đang thử gửi lại lượt chạy",
  AUTOMATION_QUEUE_UNAVAILABLE: "Không gửi được lượt chạy vào hàng đợi",
  AUTOMATION_QUEUE_REDELIVERY: "Hệ thống đang gửi lại lượt chạy vào hàng đợi",
  AUTOMATION_WORKER_CLAIMED: "Worker đã nhận quyền xử lý lượt chạy",
  AUTOMATION_WORKER_FAILED: "Worker gặp lỗi khi xử lý lượt chạy",
  AUTOMATION_ACTION_OUTCOME_UNCERTAIN: "Chưa xác định được kết quả thao tác",
  PROJECT_QA_EXECUTOR_UNAVAILABLE: "Chưa có QA phù hợp để thực hiện lượt chạy",
  PROJECT_BA_EXECUTOR_UNAVAILABLE: "Chưa có BA phù hợp để thực hiện lượt chạy",
  AI_READ_PERMISSION_REVOKED: "Quyền đọc nguồn AI đã bị thu hồi",
  AUTOMATION_CANCELLED: "Lượt chạy đã được dừng",
  QA_TEST_DESIGN_SOURCE_EVIDENCE_MISSING: "Không đủ bằng chứng nguồn để bàn giao thiết kế kiểm thử",
  QA_TEST_DESIGN_HANDOFF_DISPATCH_FAILED: "Không gửi được tác vụ thiết kế kiểm thử tiếp theo",
};

const automationRunErrorMessages = {
  AUTOMATION_ACTION_OUTCOME_UNCERTAIN:
    "Chưa xác định được kết quả thao tác trước. Hãy đối soát dữ liệu trước khi chạy tiếp để tránh ghi trùng.",
  AUTOMATION_CHECKPOINT_IDENTITY_MISMATCH:
    "Checkpoint không khớp với danh tính tác vụ hiện tại. Hệ thống đã từ chối khôi phục tự động để tránh chạy sai dữ liệu.",
  AUTOMATION_EXECUTION_FAILED:
    "Lượt tự động hóa gặp lỗi khi xử lý. Hãy xem nhật ký bước cuối; chỉ tiếp tục nếu hệ thống xác nhận có điểm khôi phục an toàn.",
  AUTOMATION_LIMIT_REACHED:
    "Lượt tự động hóa đã chạm giới hạn xử lý. Hãy kiểm tra phần việc còn lại và checkpoint trước khi tiếp tục.",
  AUTOMATION_QUEUE_UNAVAILABLE:
    "Hàng đợi AI chưa sẵn sàng. Lượt chạy được giữ lại và có thể thử tiếp khi hàng đợi hoạt động.",
  AUTOMATION_WORKER_FAILED:
    "Worker xử lý lượt AI gặp lỗi. Hãy xem checkpoint cuối và trạng thái tiếp tục an toàn.",
  PROJECT_BA_EXECUTOR_UNAVAILABLE:
    "Dự án chưa có thành viên BA đang hoạt động để tiếp tục lượt chạy này.",
  PROJECT_QA_EXECUTOR_UNAVAILABLE:
    "Dự án chưa có thành viên QA đang hoạt động để tiếp tục lượt chạy này.",
  PROJECT_AUTHORIZATION_CHECK_FAILED:
    "Chưa xác minh được quyền dự án. Lượt chạy đang chờ kiểm tra quyền.",
  AUTHORIZATION_EXPIRED: "Phiên quyền của lượt chạy đã hết hạn; cần xác minh lại quyền hiện tại.",
};

export function automationRunErrorMessage(errorCode) {
  return (
    automationRunErrorMessages[errorCode] ||
    "Lượt tự động hóa chưa hoàn tất; hãy xem nhật ký các bước xử lý."
  );
}

export function workflowForSelectedRun(runs, selectedRunId) {
  if (!Array.isArray(runs) || !selectedRunId) return null;
  const selected = runs.find((run) => run?.automation_run_id === selectedRunId);
  return selected?.workflow && typeof selected.workflow === "object" ? selected.workflow : null;
}

export function automationCheckpointView(checkpoint) {
  if (!checkpoint || typeof checkpoint !== "object") return null;

  const detail =
    checkpoint.detail && typeof checkpoint.detail === "object" ? checkpoint.detail : {};
  const facts = [];
  const reason = checkpointReasonLabels[detail.reason_code];
  if (reason) facts.push(reason);
  if (typeof detail.retryable === "boolean") {
    facts.push(detail.retryable ? "Có thể thử lại" : "Không tự thử lại để tránh ghi trùng");
  }
  if (typeof detail.resumable === "boolean") {
    facts.push(
      detail.resumable ? "Có thể tiếp tục từ điểm đã lưu" : "Không có điểm tiếp tục an toàn",
    );
  }
  if (Number.isInteger(detail.dispatch_attempt) && detail.dispatch_attempt > 0) {
    facts.push(`Lần gửi thứ ${detail.dispatch_attempt}`);
  }
  const resumeAfterPhase = detail.resuming_after || detail.resume_after_phase;
  if (checkpointPhaseLabels[resumeAfterPhase]) {
    facts.push(`Tiếp tục sau bước: ${checkpointPhaseLabels[resumeAfterPhase]}`);
  }

  let createdAt = "Thời điểm chưa được ghi nhận";
  if (typeof checkpoint.created_at === "string" || checkpoint.created_at instanceof Date) {
    const date = new Date(checkpoint.created_at);
    if (!Number.isNaN(date.getTime())) {
      createdAt = new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(date);
    }
  }

  return {
    phase: checkpointPhaseLabels[checkpoint.phase] || "Bước xử lý chưa được nhận diện",
    status: typeof checkpoint.status === "string" ? checkpoint.status : "UNKNOWN",
    sequence: Number.isInteger(checkpoint.checkpoint_sequence)
      ? checkpoint.checkpoint_sequence
      : null,
    createdAt,
    facts,
  };
}

export function automationAuthorizationGuidance(run) {
  switch (run?.error_code) {
    case "PROJECT_QA_EXECUTOR_UNAVAILABLE":
      return {
        message:
          "Dự án chưa có thành viên QA đang hoạt động. Hãy thêm hoặc kích hoạt QA rồi thử lại.",
        action: "Thử lại sau khi bổ sung QA",
      };
    case "PROJECT_BA_EXECUTOR_UNAVAILABLE":
      return {
        message:
          "Dự án chưa có thành viên BA đang hoạt động. Hãy thêm hoặc kích hoạt BA rồi thử lại.",
        action: "Thử lại sau khi bổ sung BA",
      };
    case "AUTOMATION_PRINCIPAL_ROLE_CHANGED":
      return {
        message:
          "Vai trò của người thực hiện đã thay đổi. Hãy kiểm tra lại phân công và quyền dự án.",
        action: "Thử lại sau khi kiểm tra quyền",
      };
    case "AUTOMATION_PRINCIPAL_UNAVAILABLE":
    case "AUTOMATION_EXECUTOR_UNAVAILABLE":
      return {
        message:
          "Không còn người thực hiện hợp lệ cho lượt này. Hãy kiểm tra thành viên và phân công trong dự án.",
        action: "Thử lại sau khi kiểm tra người thực hiện",
      };
    case "AUTHORIZATION_EXPIRED":
      return {
        message:
          "Phiên ủy quyền của lượt chạy đã hết hạn. Hệ thống sẽ kiểm tra lại quyền hiện tại khi tiếp tục.",
        action: "Thử lại sau khi xác minh quyền",
      };
    case "PROJECT_AUTHORIZATION_CHECK_FAILED":
      return {
        message:
          "Hiện chưa xác minh được quyền truy cập dự án. Hãy kiểm tra lại thành viên hoặc thử lại khi dịch vụ phân quyền sẵn sàng.",
        action: "Thử lại khi dịch vụ phân quyền sẵn sàng",
      };
    default:
      return {
        message:
          "Lượt AI đang tạm dừng vì chưa xác minh được quyền thực hiện. Hãy kiểm tra quyền hiện tại trước khi tiếp tục.",
        action: "Thử lại sau khi kiểm tra quyền",
      };
  }
}

export function canResumeAutomationRun(run, checkpoints, currentUserId) {
  if (!run || !currentUserId || run.requester_user_id !== currentUserId) return false;
  if (run.error_code === "AUTOMATION_ACTION_OUTCOME_UNCERTAIN") return false;

  const latestCheckpoint = Array.isArray(checkpoints) ? checkpoints.at(-1) : null;
  const detail = latestCheckpoint?.detail || {};
  if (
    latestCheckpoint?.phase === "ACTION_STARTED" &&
    (detail.action !== "READ" || detail.task_has_mutation === true)
  ) {
    return false;
  }

  if (run.status === "AWAITING_AUTHORIZATION") return true;
  if (!RETRYABLE_STATUSES.has(run.status)) return false;
  if (run.error_code === "AUTOMATION_QUEUE_UNAVAILABLE") return true;
  return Boolean(latestCheckpoint?.state_snapshot);
}

export function latestAutomationUncertainties(checkpoints) {
  const latestCheckpoint = Array.isArray(checkpoints) ? checkpoints.at(-1) : null;
  const uncertainties = latestCheckpoint?.state_snapshot?.uncertainties;
  return Array.isArray(uncertainties) ? uncertainties : [];
}

const MCP_DISCOVERY_MESSAGES = {
  MCP_PROJECT_AUTHORIZATION_UNAVAILABLE:
    "Chưa xác minh được quyền đọc dự án; hệ thống không kết nối tới nguồn MCP.",
  MCP_PROJECT_ACCESS_REVOKED: "Quyền đọc dự án đã bị thu hồi; hệ thống không gọi nguồn MCP.",
  MCP_CONNECTION_DISCOVERY_UNAVAILABLE: "Chưa đọc được cấu hình nguồn MCP của dự án.",
  MCP_CREDENTIAL_UNAVAILABLE: "Nguồn MCP thiếu thông tin xác thực trên máy chủ.",
  MCP_DISCOVERY_TIMEOUT: "Nguồn MCP không phản hồi đúng hạn.",
  MCP_DISCOVERY_FAILED: "Không thể khám phá công cụ từ nguồn MCP.",
  MCP_TOOL_SCHEMA_UNSUPPORTED:
    "Công cụ MCP có cấu trúc tham số chưa được hỗ trợ nên không được đưa vào kế hoạch.",
  MCP_ALLOWED_TOOLS_NOT_ADVERTISED: "Nguồn MCP chưa công bố công cụ đọc được cho phép trong dự án.",
};

export function automationMcpDiscoveryIssues(run) {
  const observations = Array.isArray(run?.result?.observations)
    ? run.result.observations
    : Array.isArray(run?.observations)
      ? run.observations
      : [];
  const issues = new Map();
  for (const item of observations) {
    if (item?.phase !== "MCP_DISCOVERY" || !MCP_DISCOVERY_MESSAGES[item.reason_code]) continue;
    const key = [item.reason_code, item.connection_id, item.tool_name].join(":");
    issues.set(key, {
      reason_code: item.reason_code,
      message: MCP_DISCOVERY_MESSAGES[item.reason_code],
      tool_name: typeof item.tool_name === "string" ? item.tool_name : "",
    });
  }
  return [...issues.values()];
}

export function automationSourceExtractionGaps(run) {
  const observations = Array.isArray(run?.result?.observations)
    ? run.result.observations
    : Array.isArray(run?.observations)
      ? run.observations
      : [];
  const gapsByDocument = new Map();
  for (const observation of observations) {
    const result = observation?.result;
    if (result?.reason_code !== "SOURCE_EXTRACTION_INCOMPLETE") continue;
    const gaps = Array.isArray(result.source_extraction_gaps) ? result.source_extraction_gaps : [];
    for (const gap of gaps) {
      if (
        gap?.reason !== "SOURCE_EXTRACTION_INCOMPLETE" ||
        typeof gap.document_id !== "string" ||
        !gap.document_id.trim()
      ) {
        continue;
      }
      const blocks = Array.isArray(gap.unprocessed_blocks)
        ? gap.unprocessed_blocks
            .filter((block) => block && typeof block === "object")
            .slice(0, 100)
            .map((block) => ({
              block_id: typeof block.block_id === "string" ? block.block_id.slice(0, 160) : "",
              page_no: Number.isInteger(block.page_no) ? block.page_no : null,
              type: typeof block.type === "string" ? block.type.slice(0, 80) : "",
              reason_code:
                typeof block.reason_code === "string" ? block.reason_code.slice(0, 100) : "",
            }))
        : [];
      gapsByDocument.set(gap.document_id, {
        document_id: gap.document_id.slice(0, 160),
        index_status: typeof gap.index_status === "string" ? gap.index_status : "UNKNOWN",
        parser: typeof gap.parser === "string" ? gap.parser.slice(0, 100) : "",
        page_count: Number.isInteger(gap.page_count) ? gap.page_count : null,
        unprocessed_block_count: Number.isInteger(gap.unprocessed_block_count)
          ? gap.unprocessed_block_count
          : null,
        unprocessed_blocks: blocks,
        unprocessed_blocks_truncated: gap.unprocessed_blocks_truncated === true,
      });
    }
  }
  return [...gapsByDocument.values()];
}
