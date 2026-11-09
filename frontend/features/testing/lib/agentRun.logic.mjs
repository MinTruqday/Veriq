const RETRYABLE_STATUSES = new Set(["FAILED", "DEGRADED"]);

const checkpointPhaseLabels = {
  QUEUED: "Đang chờ xử lý",
  WORKER_STARTED: "Đã bắt đầu xử lý lượt chạy",
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
  AUTOMATION_RESUMED_FROM_CHECKPOINT: "Đã tiếp tục từ điểm xử lý đã lưu",
  AUTOMATION_RETRY_STARTED: "Đã bắt đầu lượt thử lại",
  AUTOMATION_QUEUE_RETRY: "Hệ thống đang thử gửi lại lượt chạy",
  AUTOMATION_QUEUE_UNAVAILABLE: "Không gửi được lượt chạy vào hàng đợi",
  AUTOMATION_QUEUE_REDELIVERY: "Hệ thống đang gửi lại lượt chạy vào hàng đợi",
  AUTOMATION_WORKER_CLAIMED: "Hệ thống đã tiếp nhận lượt chạy",
  AUTOMATION_WORKER_FAILED: "Hệ thống gặp lỗi khi xử lý lượt chạy",
  AUTOMATION_ACTION_OUTCOME_UNCERTAIN: "Chưa xác định được kết quả thao tác",
  AUTOMATION_EXECUTOR_UNAVAILABLE: "Không có thành viên đủ quyền thực hiện lượt chạy",
  AI_READ_PERMISSION_REVOKED: "Quyền đọc nguồn AI đã bị thu hồi",
  AUTOMATION_CANCELLED: "Lượt chạy đã được dừng",
  TEST_DESIGN_SOURCE_EVIDENCE_MISSING: "Không đủ bằng chứng nguồn để bàn giao thiết kế kiểm thử",
  TEST_DESIGN_HANDOFF_DISPATCH_FAILED: "Không gửi được tác vụ thiết kế kiểm thử tiếp theo",
};

const agentRunErrorMessages = {
  AUTOMATION_ACTION_OUTCOME_UNCERTAIN:
    "Chưa xác định được kết quả bước trước. Hãy kiểm tra dữ liệu trước khi tiếp tục để tránh tạo trùng.",
  AUTOMATION_CHECKPOINT_IDENTITY_MISMATCH:
    "Thông tin lượt chạy không còn khớp với dữ liệu hiện tại. Hệ thống đã dừng để tránh xử lý nhầm.",
  AUTOMATION_EXECUTION_FAILED:
    "Tác vụ AI chưa hoàn tất. Hãy xem kết quả gần nhất trước khi tiếp tục.",
  AUTOMATION_LIMIT_REACHED:
    "Tác vụ AI đã chạm giới hạn xử lý. Hãy kiểm tra phần việc còn lại trước khi tiếp tục.",
  AUTOMATION_QUEUE_UNAVAILABLE:
    "Hệ thống chưa thể tiếp nhận lượt chạy. Lượt này được giữ lại và sẽ được thử lại khi có thể.",
  AUTOMATION_WORKER_FAILED:
    "Hệ thống gặp lỗi khi xử lý lượt AI. Hãy xem bước gần nhất và trạng thái tiếp tục trước khi thử lại.",
  AUTOMATION_EXECUTOR_UNAVAILABLE:
    "Không xác minh được người thực hiện có quyền cần thiết để tiếp tục lượt chạy này.",
  PROJECT_AUTHORIZATION_CHECK_FAILED:
    "Chưa xác minh được quyền dự án. Lượt chạy đang chờ kiểm tra quyền.",
  AUTHORIZATION_EXPIRED: "Phiên quyền của lượt chạy đã hết hạn; cần xác minh lại quyền hiện tại.",
};

export function agentRunErrorMessage(errorCode) {
  return (
    agentRunErrorMessages[errorCode] || "Tác vụ AI chưa hoàn tất; hãy xem kết quả các bước xử lý."
  );
}

export function workflowForSelectedAgentRun(runs, selectedRunId) {
  if (!Array.isArray(runs) || !selectedRunId) return null;
  const selected = runs.find((run) => run?.automation_run_id === selectedRunId);
  return selected?.workflow && typeof selected.workflow === "object" ? selected.workflow : null;
}

export function agentCheckpointView(checkpoint) {
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
      createdAt = new Intl.DateTimeFormat(undefined, {
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

export function agentAuthorizationGuidance(run) {
  if (run?.error_code?.endsWith("_EXECUTOR_UNAVAILABLE")) {
    return {
      message:
        "Không xác minh được người thực hiện có quyền cần thiết. Hãy kiểm tra quyền dự án rồi thử lại.",
      action: "Kiểm tra quyền và thử lại",
    };
  }
  switch (run?.error_code) {
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

export function canResumeAgentRun(run, checkpoints, currentUserId) {
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

export function latestAgentUncertainties(checkpoints) {
  const latestCheckpoint = Array.isArray(checkpoints) ? checkpoints.at(-1) : null;
  const uncertainties = latestCheckpoint?.state_snapshot?.uncertainties;
  return Array.isArray(uncertainties) ? uncertainties : [];
}

export function agentSourceExtractionGaps(run) {
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
