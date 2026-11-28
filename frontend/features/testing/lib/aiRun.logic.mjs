import { formatDateTime } from "../../../shared/lib/dateTime.mjs";

const RETRYABLE_STATUSES = new Set(["FAILED", "DEGRADED"]);

const failedAIRunStatuses = new Set(["FAILED", "DEGRADED"]);

const checkpointProgress = {
  QUEUED: 0,
  WORKER_STARTED: 5,
  OBSERVED: 15,
  FACTS_EXTRACTED: 25,
  UNCERTAINTY_ASSESSED: 35,
  PLAN_CREATED: 45,
  FINALIZED: 90,
  ACTIONS_VERIFIED: 95,
  GRAPH_COMPLETED: 98,
};

function uniqueTaskIds(items) {
  return new Set(
    (Array.isArray(items) ? items : [])
      .map((item) => item?.task_id)
      .filter((taskId) => typeof taskId === "string" && taskId),
  );
}

function checkpointPercent(checkpoint) {
  if (!checkpoint) return 0;
  const phase = checkpoint.phase;
  if (phase === "ACTION_STARTED" || phase === "ACTIONS_EXECUTED") {
    const runState = checkpoint.state_snapshot?.run || {};
    const plannedIds = uniqueTaskIds(runState.execution_plan);
    const completedIds = uniqueTaskIds(runState.completed_tasks);
    const completedCount = plannedIds.size
      ? [...completedIds].filter((taskId) => plannedIds.has(taskId)).length
      : Number(checkpoint.detail?.completed_task_count || 0);
    const plannedCount = plannedIds.size || Number(checkpoint.detail?.planned_task_count || 0);
    const ratio = plannedCount > 0 ? Math.min(1, completedCount / plannedCount) : 0;
    return Math.round(45 + ratio * 40);
  }
  return checkpointProgress[phase] ?? 0;
}

export function aiRunProgress(run, checkpoints) {
  const latest = Array.isArray(checkpoints) ? checkpoints.at(-1) : null;
  const latestWithSnapshot = Array.isArray(checkpoints)
    ? [...checkpoints].reverse().find((checkpoint) => checkpoint?.state_snapshot)
    : null;
  const progressCheckpoint = latestWithSnapshot || latest;
  const status = run?.status;
  const failed = failedAIRunStatuses.has(status);
  const completed = status === "COMPLETED";
  const awaitingInput = status === "AWAITING_INPUT";
  const awaitingAuthorization = status === "AWAITING_AUTHORIZATION";
  const cancelled = status === "CANCELLED";
  const phase = progressCheckpoint?.phase;
  const processingPhases = new Set([
    "ACTION_STARTED",
    "ACTIONS_EXECUTED",
    "FINALIZED",
    "ACTIONS_VERIFIED",
    "GRAPH_COMPLETED",
  ]);
  const label = completed
    ? "Hoàn thành"
    : failed
      ? "Thất bại"
      : awaitingInput
        ? "Cần bổ sung thông tin"
        : awaitingAuthorization
          ? "Cần kiểm tra quyền"
          : cancelled
            ? "Đã dừng"
            : processingPhases.has(phase) || status === "VERIFYING"
              ? "Đang xử lý"
              : "Chuẩn bị";
  const percent = completed
    ? 100
    : Math.max(0, Math.min(99, checkpointPercent(progressCheckpoint)));
  return {
    label,
    percent,
    tone: completed ? "success" : failed || cancelled ? "danger" : "warning",
  };
}

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
  AI_RUN_RESUMED_FROM_CHECKPOINT: "Đã tiếp tục từ điểm xử lý đã lưu",
  AI_RUN_RETRY_STARTED: "Đã bắt đầu lượt thử lại",
  AI_RUN_QUEUE_RETRY: "Hệ thống đang thử gửi lại lượt chạy",
  AI_RUN_QUEUE_UNAVAILABLE: "Không gửi được lượt chạy vào hàng đợi",
  AI_RUN_QUEUE_REDELIVERY: "Hệ thống đang gửi lại lượt chạy vào hàng đợi",
  AI_RUN_WORKER_CLAIMED: "Hệ thống đã tiếp nhận lượt chạy",
  AI_RUN_WORKER_FAILED: "Hệ thống gặp lỗi khi xử lý lượt chạy",
  AI_RUN_ACTION_OUTCOME_UNCERTAIN: "Chưa xác định được kết quả thao tác",
  AI_RUN_EXECUTOR_UNAVAILABLE: "Không có thành viên đủ quyền thực hiện lượt chạy",
  AI_READ_PERMISSION_REVOKED: "Quyền đọc nguồn AI đã bị thu hồi",
  AI_RUN_CANCELLED: "Lượt chạy đã được dừng",
  TEST_DESIGN_SOURCE_EVIDENCE_MISSING: "Không đủ bằng chứng nguồn để bàn giao thiết kế kiểm thử",
  TEST_DESIGN_HANDOFF_DISPATCH_FAILED: "Không gửi được tác vụ thiết kế kiểm thử tiếp theo",
};

const aiRunErrorMessages = {
  INSUFFICIENT_EVIDENCE:
    "Tác vụ AI chưa đủ căn cứ để hoàn tất. Hãy xem chi tiết các bước xử lý để biết nguồn hoặc thao tác nào chưa được xác minh",
  AI_RUN_ACTION_OUTCOME_UNCERTAIN:
    "Chưa xác định được kết quả bước trước. Hãy kiểm tra dữ liệu trước khi tiếp tục để tránh tạo trùng",
  AI_RUN_CHECKPOINT_IDENTITY_MISMATCH:
    "Thông tin lượt chạy không còn khớp với dữ liệu hiện tại. Hệ thống đã dừng để tránh xử lý nhầm",
  AI_RUN_EXECUTION_FAILED: "Tác vụ AI chưa hoàn tất. Hãy xem kết quả gần nhất trước khi tiếp tục",
  AI_RUN_LIMIT_REACHED:
    "Tác vụ AI đã chạm giới hạn xử lý. Hãy kiểm tra phần việc còn lại trước khi tiếp tục",
  AI_RUN_QUEUE_UNAVAILABLE:
    "Hệ thống chưa thể tiếp nhận lượt chạy. Lượt này được giữ lại và sẽ được thử lại khi có thể",
  AI_RUN_WORKER_FAILED:
    "Hệ thống gặp lỗi khi xử lý lượt AI. Hãy xem bước gần nhất và trạng thái tiếp tục trước khi thử lại",
  AI_RUN_EXECUTOR_UNAVAILABLE:
    "Không xác minh được người thực hiện có quyền cần thiết để tiếp tục lượt chạy này",
  PROJECT_AUTHORIZATION_CHECK_FAILED:
    "Chưa xác minh được quyền dự án. Lượt chạy đang chờ kiểm tra quyền",
  AUTHORIZATION_EXPIRED: "Phiên quyền của lượt chạy đã hết hạn; cần xác minh lại quyền hiện tại",
};

export function aiRunErrorMessage(errorCode) {
  return aiRunErrorMessages[errorCode] || "Tác vụ AI chưa hoàn tất; hãy xem kết quả các bước xử lý";
}

export function agentCheckpointView(checkpoint, dateTimeOptions = {}) {
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
      createdAt = formatDateTime(date, {
        ...dateTimeOptions,
        options: { dateStyle: "short", timeStyle: "medium" },
      });
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
        "Không xác minh được người thực hiện có quyền cần thiết. Hãy kiểm tra quyền dự án rồi thử lại",
      action: "Kiểm tra quyền và thử lại",
    };
  }
  switch (run?.error_code) {
    case "AI_RUN_PRINCIPAL_ROLE_CHANGED":
      return {
        message:
          "Vai trò của người thực hiện đã thay đổi. Hãy kiểm tra lại phân công và quyền dự án",
        action: "Thử lại sau khi kiểm tra quyền",
      };
    case "AI_RUN_PRINCIPAL_UNAVAILABLE":
    case "AI_RUN_EXECUTOR_UNAVAILABLE":
      return {
        message:
          "Không còn người thực hiện hợp lệ cho lượt này. Hãy kiểm tra thành viên và phân công trong dự án",
        action: "Thử lại sau khi kiểm tra người thực hiện",
      };
    case "AUTHORIZATION_EXPIRED":
      return {
        message:
          "Phiên ủy quyền của lượt chạy đã hết hạn. Hệ thống sẽ kiểm tra lại quyền hiện tại khi tiếp tục",
        action: "Thử lại sau khi xác minh quyền",
      };
    case "PROJECT_AUTHORIZATION_CHECK_FAILED":
      return {
        message:
          "Hiện chưa xác minh được quyền truy cập dự án. Hãy kiểm tra lại thành viên hoặc thử lại khi dịch vụ phân quyền sẵn sàng",
        action: "Thử lại khi dịch vụ phân quyền sẵn sàng",
      };
    default:
      return {
        message:
          "Lượt AI đang tạm dừng vì chưa xác minh được quyền thực hiện. Hãy kiểm tra quyền hiện tại trước khi tiếp tục",
        action: "Thử lại sau khi kiểm tra quyền",
      };
  }
}

export function canResumeAIRun(run, checkpoints, currentUserId) {
  if (!run || !currentUserId || run.requester_user_id !== currentUserId) return false;
  if (run.error_code === "AI_RUN_ACTION_OUTCOME_UNCERTAIN") return false;

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
  if (run.error_code === "AI_RUN_QUEUE_UNAVAILABLE") return true;
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
