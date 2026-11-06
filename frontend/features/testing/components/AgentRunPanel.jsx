"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import {
  automationAuthorizationGuidance,
  canResumeAutomationRun,
  automationCheckpointView,
  automationRunErrorMessage,
  latestAutomationUncertainties,
  automationMcpDiscoveryIssues,
  automationSourceExtractionGaps,
  workflowForSelectedRun,
} from "../lib/automationRun.logic.mjs";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { preferredSummaryLocale } from "../lib/summaryLanguage";
import { testingApi } from "../services/testing.service";
import { ErrorState, LoadingState, Panel, StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";

const activeStatuses = new Set(["QUEUED", "RUNNING"]);
const runTitlesByTrigger = {
  DOCUMENT_INGESTED: "Rà soát tài liệu mới",
  API_OPERATION_CONFIRMED: "Rà soát đặc tả API",
  REQUIREMENT_CHANGED: "Rà soát yêu cầu đã thay đổi",
  TEST_EXECUTION_RECORDED: "Phân tích kết quả kiểm thử",
  DEFECT_RECORDED: "Phân tích lỗi mới",
  DEFECT_CHANGED: "Rà soát thay đổi lỗi",
  WORK_ITEM_CHANGED: "Rà soát công việc đã thay đổi",
  TEST_CASE_CHANGED: "Rà soát ca kiểm thử đã thay đổi",
  TEST_CASE_APPROVED: "Tiếp tục xử lý ca kiểm thử đã duyệt",
  TEST_PLAN_CHANGED: "Rà soát kế hoạch kiểm thử đã thay đổi",
  TEST_PLAN_APPROVED: "Tiếp tục xử lý kế hoạch kiểm thử đã duyệt",
  STATUS_REPORT_CREATED: "Tạo báo cáo trạng thái",
  TEST_COMPLETION_REPORT_CREATED: "Tạo báo cáo hoàn tất kiểm thử",
  PERFORMANCE_CONFIGURATION_APPROVED: "Xử lý cấu hình hiệu năng đã duyệt",
  RELEASE_CHANGED: "Rà soát bản phát hành đã thay đổi",
};

function automationTriggerLabel(run) {
  const providedLabel = String(run?.trigger_label || run?.trigger_display_name || "").trim();
  if (providedLabel) return providedLabel;
  return run?.trigger === "MANUAL" ? "Theo yêu cầu người dùng" : "Cập nhật dự án";
}

function automationRunTitle(run) {
  const internalCode = /\b[A-Z][A-Z0-9]*(?:_+[A-Z0-9]+)+\b/;
  const summary = [
    run?.display_name,
    run?.title,
    run?.result?.summary,
    run?.result?.message,
    run?.objective,
  ]
    .map((value) => String(value || "").trim())
    .find((value) => value && !internalCode.test(value));
  if (summary) return summary;
  return runTitlesByTrigger[run?.trigger] || "Hoạt động xử lý";
}

function sourceFactSummary(fact) {
  const sourceType = fact?.artifact_type ? valueLabel(fact.artifact_type) : "Tài liệu nguồn";
  const pages = Array.isArray(fact?.source_page_numbers) ? fact.source_page_numbers : [];
  return pages.length
    ? `${sourceType} · Trang ${pages.join(", ")}`
    : `${sourceType} · Đoạn trích đã xác minh`;
}

function isOlderRunSnapshot(incoming, current) {
  if (!incoming || !current) return false;
  const incomingRevision = Number(incoming.revision);
  const currentRevision = Number(current.revision);
  if (!Number.isFinite(incomingRevision) || !Number.isFinite(currentRevision)) return false;
  return (
    incomingRevision < currentRevision ||
    (incomingRevision === currentRevision && incoming.status !== current.status)
  );
}

export default function AgentRunPanel({
  project,
  compact = false,
  showPanelHeading = true,
  contextContent = null,
  onRunsStateChange,
}) {
  const { user } = useAuth();
  const currentUserId = project.current_membership?.user_id;
  const permissions = project.current_permissions || [];
  const permissionKey = permissions.join("|");
  const canReadProjectRuns = permissions.includes("proposal.read");
  const canReadOwnRuns = permissions.includes("automation.read");
  const canViewRun = (item) => canReadProjectRuns || item?.requester_user_id === currentUserId;
  const [recentRuns, setRecentRuns] = useState([]);
  const [agentCapabilities, setAgentCapabilities] = useState([]);
  const [run, setRun] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [receipt, setReceipt] = useState(null);
  const [sourceFacts, setSourceFacts] = useState([]);
  const [clarificationAnswers, setClarificationAnswers] = useState({});
  const [submittingClarification, setSubmittingClarification] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshingRuns, setRefreshingRuns] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runsRefreshError, setRunsRefreshError] = useState("");
  const [detailRefreshError, setDetailRefreshError] = useState("");
  const [initialLoadAttempt, setInitialLoadAttempt] = useState(0);
  const [agentInstruction, setAgentInstruction] = useState("");
  const [startingAgent, setStartingAgent] = useState(false);
  const [agentStartError, setAgentStartError] = useState("");
  const agentIdempotencyKey = useRef("");
  const detailRequestVersion = useRef(0);
  const runListRequestVersion = useRef(0);
  const selectedRunIdRef = useRef(null);
  const selectedRunSnapshotRef = useRef(null);

  useEffect(() => {
    let active = true;
    const listRequestVersion = ++runListRequestVersion.current;
    detailRequestVersion.current += 1;
    setLoading(true);
    setError("");
    setRunsRefreshError("");
    setDetailRefreshError("");
    setRecentRuns([]);
    setAgentCapabilities([]);
    onRunsStateChange?.({ runs: [], error: "", loading: true });
    setRun(null);
    selectedRunIdRef.current = null;
    selectedRunSnapshotRef.current = null;
    setWorkflow(null);
    setCheckpoints([]);
    setReceipt(null);
    setSourceFacts([]);
    setClarificationAnswers({});
    setSubmittingClarification("");
    Promise.allSettled([
      canReadProjectRuns || canReadOwnRuns
        ? testingApi.listAutomationRuns(project._id)
        : Promise.resolve([]),
      testingApi.listAgentCapabilities(project._id),
    ])
      .then((results) => {
        if (!active) return;
        const values = results.map((result) => (result.status === "fulfilled" ? result.value : []));
        if (listRequestVersion === runListRequestVersion.current) {
          setRecentRuns(values[0]);
          const runListError = results[0].status === "rejected" ? messageOf(results[0].reason) : "";
          onRunsStateChange?.({ runs: values[0], error: runListError, loading: false });
        }
        setAgentCapabilities(values[1]);
        setError(
          results
            .filter((result) => result.status === "rejected")
            .map((result) => messageOf(result.reason))
            .filter(Boolean)
            .join(" · "),
        );
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
      if (listRequestVersion === runListRequestVersion.current) {
        runListRequestVersion.current += 1;
      }
    };
  }, [
    canReadOwnRuns,
    canReadProjectRuns,
    currentUserId,
    initialLoadAttempt,
    onRunsStateChange,
    project._id,
    permissionKey,
  ]);

  const refreshRuns = useCallback(async () => {
    if (!canReadProjectRuns && !canReadOwnRuns) return;
    const requestVersion = ++runListRequestVersion.current;
    const selectedRunId = selectedRunIdRef.current;
    const selectionVersion = detailRequestVersion.current;
    const items = await testingApi.listAutomationRuns(project._id);
    if (requestVersion !== runListRequestVersion.current) return;
    setRecentRuns(items);
    onRunsStateChange?.({ runs: items, error: "", loading: false });
    if (
      selectedRunId === selectedRunIdRef.current &&
      selectionVersion === detailRequestVersion.current
    ) {
      const selectedWorkflow = workflowForSelectedRun(items, selectedRunId);
      const selectedSummary = items.find((item) => item.automation_run_id === selectedRunId);
      if (
        selectedWorkflow &&
        !isOlderRunSnapshot(selectedSummary, selectedRunSnapshotRef.current)
      ) {
        setWorkflow(selectedWorkflow);
      }
    }
    setRunsRefreshError("");
  }, [canReadOwnRuns, canReadProjectRuns, onRunsStateChange, project._id]);

  const refreshRunList = async () => {
    if (refreshingRuns) return;
    setRefreshingRuns(true);
    try {
      await refreshRuns();
    } catch (reason) {
      setRunsRefreshError(messageOf(reason));
    } finally {
      setRefreshingRuns(false);
    }
  };

  const loadRun = async (runId) => {
    const requestVersion = ++detailRequestVersion.current;
    if (selectedRunIdRef.current !== runId) setClarificationAnswers({});
    selectedRunIdRef.current = runId;
    selectedRunSnapshotRef.current = null;
    setSourceFacts([]);
    setDetailRefreshError("");
    if (run?.automation_run_id !== runId) {
      setRun(null);
      setWorkflow(null);
      setCheckpoints([]);
      setReceipt(null);
    }
    let detail;
    try {
      detail = await testingApi.getAutomationRun(runId);
    } catch (reason) {
      if (requestVersion !== detailRequestVersion.current) return;
      throw reason;
    }
    if (requestVersion !== detailRequestVersion.current) return;
    selectedRunSnapshotRef.current = {
      revision: detail.run.revision,
      status: detail.run.status,
    };
    setRun(detail.run);
    setWorkflow(detail.workflow || null);
    setCheckpoints(detail.checkpoints || []);
    setReceipt(detail.receipt || null);
    try {
      const evidence = await testingApi.getAutomationRunEvidence(runId);
      if (requestVersion !== detailRequestVersion.current) return;
      setReceipt(evidence.receipt || detail.receipt || null);
      setSourceFacts(evidence.source_facts || []);
    } catch (reason) {
      if (requestVersion === detailRequestVersion.current) {
        setDetailRefreshError(messageOf(reason));
      }
    }
  };

  useEffect(() => {
    if (!run || (!activeStatuses.has(run.status) && !(workflow?.active_count > 0))) {
      return undefined;
    }
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || pending) return;
      pending = true;
      const requestVersion = detailRequestVersion.current;
      try {
        const detail = await testingApi.getAutomationRun(run.automation_run_id);
        if (!active || requestVersion !== detailRequestVersion.current) return;
        if (isOlderRunSnapshot(detail.run, selectedRunSnapshotRef.current)) return;
        let evidence = null;
        let evidenceError = "";
        if (!activeStatuses.has(detail.run.status) && !(detail.workflow?.active_count > 0)) {
          try {
            evidence = await testingApi.getAutomationRunEvidence(run.automation_run_id);
          } catch (reason) {
            evidenceError = messageOf(reason);
          }
        }
        if (
          !active ||
          requestVersion !== detailRequestVersion.current ||
          selectedRunIdRef.current !== run.automation_run_id ||
          isOlderRunSnapshot(detail.run, selectedRunSnapshotRef.current)
        ) {
          return;
        }
        selectedRunSnapshotRef.current = {
          revision: detail.run.revision,
          status: detail.run.status,
        };
        setDetailRefreshError(evidenceError);
        setRun(detail.run);
        setWorkflow(detail.workflow || null);
        setCheckpoints(detail.checkpoints || []);
        setReceipt(evidence?.receipt || detail.receipt || null);
        if (evidence) {
          setSourceFacts(evidence.source_facts || []);
        } else if (evidenceError) {
          setSourceFacts([]);
        }
        if (!activeStatuses.has(detail.run.status) && !(detail.workflow?.active_count > 0)) {
          try {
            await refreshRuns();
          } catch (reason) {
            if (active) setRunsRefreshError(messageOf(reason));
          }
        }
      } catch (reason) {
        if (active) setDetailRefreshError(messageOf(reason));
      } finally {
        pending = false;
      }
    }, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [run, workflow?.active_count, refreshRuns]);

  const retry = async () => {
    if (!run) return;
    const runId = run.automation_run_id;
    const selectionVersion = detailRequestVersion.current;
    setBusy(true);
    setError("");
    try {
      try {
        await testingApi.retryAutomationRun(runId, {
          expected_revision: run.revision,
        });
      } catch (reason) {
        if (selectionVersion === detailRequestVersion.current) {
          setError(messageOf(reason));
          try {
            await loadRun(runId);
          } catch (refreshReason) {
            setDetailRefreshError(messageOf(refreshReason));
          }
        }
        return;
      }
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (selectionVersion === detailRequestVersion.current) {
        try {
          await loadRun(runId);
          setDetailRefreshError("");
        } catch (reason) {
          setDetailRefreshError(messageOf(reason));
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!run) return;
    const runId = run.automation_run_id;
    const selectionVersion = detailRequestVersion.current;
    setBusy(true);
    setError("");
    try {
      try {
        await testingApi.cancelAutomationRun(runId, {
          expected_revision: run.revision,
        });
      } catch (reason) {
        if (selectionVersion === detailRequestVersion.current) {
          setError(messageOf(reason));
          try {
            await loadRun(runId);
          } catch (refreshReason) {
            setDetailRefreshError(messageOf(refreshReason));
          }
        }
        return;
      }
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (selectionVersion === detailRequestVersion.current) {
        try {
          await loadRun(runId);
        } catch (reason) {
          setDetailRefreshError(messageOf(reason));
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const answerClarification = async (uncertainty) => {
    if (!run || !uncertainty?.code || !uncertainty.response_allowed || submittingClarification) {
      return;
    }
    const answer = clarificationAnswers[uncertainty.code]?.trim();
    if (!answer) return;
    const runId = run.automation_run_id;
    const selectionVersion = detailRequestVersion.current;
    setSubmittingClarification(uncertainty.code);
    setError("");
    try {
      await testingApi.answerAutomationClarification(runId, {
        expected_revision: run.revision,
        uncertainty_code: uncertainty.code,
        answer,
      });
      if (selectionVersion === detailRequestVersion.current) {
        setClarificationAnswers((current) => ({ ...current, [uncertainty.code]: "" }));
      }
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (selectionVersion === detailRequestVersion.current) {
        try {
          await loadRun(runId);
        } catch (reason) {
          setDetailRefreshError(messageOf(reason));
        }
      }
    } catch (reason) {
      if (selectionVersion === detailRequestVersion.current) {
        setError(messageOf(reason));
        try {
          await loadRun(runId);
        } catch (refreshReason) {
          setDetailRefreshError(messageOf(refreshReason));
        }
      }
    } finally {
      setSubmittingClarification("");
    }
  };

  const proposal = run?.result?.proposal;
  const blueprintClaims = receipt?.blueprint_claim_lineage || [];
  const blueprintArtifacts = receipt?.blueprint_artifact_lineage || [];
  const sourceFactsById = new Map(
    sourceFacts.flatMap((fact) =>
      [fact.source_fact_id, fact.artifact_id, fact.artifact_version_id]
        .filter(Boolean)
        .map((reference) => [reference, fact]),
    ),
  );
  const proposalEvidence = (proposal?.evidence_refs || [])
    .map((reference) => sourceFactsById.get(reference))
    .filter(Boolean);
  const linkedSourceFactIds = new Set(
    blueprintClaims.flatMap((claim) => claim.source_fact_ids || []),
  );
  const unlinkedSourceFacts = sourceFacts.filter(
    (fact) => !linkedSourceFactIds.has(fact.source_fact_id),
  );
  const busyRun = run && activeStatuses.has(run.status);
  const visibleRuns = recentRuns.filter(canViewRun);
  const canControlRun = run?.requester_user_id === currentUserId;
  const canAnswerClarification = permissions.includes("requirement.update");
  const canResumeRun = canControlRun && canResumeAutomationRun(run, checkpoints, currentUserId);
  const canShowRunControls = (busyRun && canControlRun) || canResumeRun;
  const uncertainties = latestAutomationUncertainties(checkpoints);
  const mcpDiscoveryIssues = automationMcpDiscoveryIssues(run);
  const sourceExtractionGaps = automationSourceExtractionGaps(run);
  const authorizationGuidance = automationAuthorizationGuidance(run);
  const showCompactEmptyState = compact && !loading && !error && visibleRuns.length === 0;
  const showRecentActivity =
    visibleRuns.length > 0 || showCompactEmptyState || (!compact && !loading && !error && !run);
  const canStartAgent = agentCapabilities.length > 0;
  const startAgentRun = async () => {
    const instruction = agentInstruction.trim();
    if (!instruction || startingAgent) return;
    setStartingAgent(true);
    setAgentStartError("");
    try {
      if (!agentIdempotencyKey.current) {
        agentIdempotencyKey.current = `agent-${crypto.randomUUID()}`;
      }
      const started = await testingApi.createAgentRun({
        project_id: project._id,
        objective: instruction,
        intent: "",
        target_artifact_ids: [],
        evidence: [],
        output_language: preferredSummaryLocale(user?.locale, project.locale, navigator.language),
        idempotency_key: agentIdempotencyKey.current,
      });
      agentIdempotencyKey.current = "";
      setAgentInstruction("");
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (started?.automation_run_id) await loadRun(started.automation_run_id);
    } catch (reason) {
      setAgentStartError(messageOf(reason));
    } finally {
      setStartingAgent(false);
    }
  };

  const recentActivityHeading = (
    <div className="flex min-w-0 items-center justify-between gap-3">
      <h3 className="text-sm font-semibold text-ink">Hoạt động gần đây</h3>
      <button
        aria-label="Tải lại hoạt động AI"
        className="icon-button h-8 w-8 shrink-0"
        disabled={loading || refreshingRuns}
        onClick={() => void refreshRunList()}
        title="Tải lại hoạt động AI"
        type="button"
      >
        <RefreshCw aria-hidden="true" className={refreshingRuns ? "animate-spin" : ""} size={16} />
      </button>
    </div>
  );

  return (
    <Panel
      title={
        !showPanelHeading ? null : compact ? (
          <span className="flex w-full flex-wrap items-center justify-between gap-3">
            <span>Hoạt động AI</span>
            <Link
              className="text-sm font-medium text-brand hover:text-brand-hover"
              href={`/du-an/${encodeURIComponent(project._id)}/ra-soat-ai`}
            >
              Xem tất cả
            </Link>
          </span>
        ) : (
          "Hoạt động AI"
        )
      }
    >
      <div className={`grid gap-3 px-4 ${compact ? "py-3" : "pb-4 pt-3"}`}>
        {contextContent}
        {!compact && canStartAgent && (
          <form
            className="grid gap-3 rounded-control border border-border p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void startAgentRun();
            }}
          >
            <label className="grid gap-2 text-sm font-medium text-ink">
              Bạn cần AI hỗ trợ việc gì?
              <textarea
                className="apple-input min-h-24"
                maxLength={4000}
                value={agentInstruction}
                onChange={(event) => setAgentInstruction(event.target.value)}
                placeholder="Mô tả kết quả cần có. AI sẽ kiểm tra căn cứ và quyền hiện tại trước khi xử lý."
              />
            </label>
            {agentStartError && <ErrorState message={agentStartError} />}
            <button
              className="primary-button justify-self-start"
              type="submit"
              disabled={startingAgent || !agentInstruction.trim()}
            >
              {startingAgent ? "Đang bắt đầu…" : "Bắt đầu xử lý bằng AI"}
            </button>
          </form>
        )}
        {error && (
          <div className="grid gap-2">
            <ErrorState message={error} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={loading}
              onClick={() => setInitialLoadAttempt((attempt) => attempt + 1)}
            >
              {loading ? "Đang tải lại…" : "Tải lại dữ liệu AI"}
            </button>
          </div>
        )}
        {runsRefreshError && (
          <div className="grid gap-2" role="status">
            <ErrorState message={`Chưa cập nhật được hoạt động AI: ${runsRefreshError}`} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={busy}
              onClick={() => void refreshRunList()}
            >
              Tải lại hoạt động AI
            </button>
          </div>
        )}
        {loading &&
          visibleRuns.length === 0 &&
          (compact ? (
            <div className="grid gap-2 py-1" role="status" aria-label="Đang tải hoạt động AI">
              <span className="sr-only">Đang tải hoạt động AI</span>
              {[0, 1, 2].map((item) => (
                <div aria-hidden="true" className="skeleton h-[58px] w-full" key={item} />
              ))}
            </div>
          ) : (
            <LoadingState />
          ))}
        {canShowRunControls && (
          <div className="flex flex-wrap gap-2">
            {busyRun && canControlRun && (
              <button className="secondary-button" type="button" disabled={busy} onClick={cancel}>
                Dừng tác vụ AI
              </button>
            )}
            {canResumeRun && (
              <button className="secondary-button" type="button" disabled={busy} onClick={retry}>
                {run.status === "AWAITING_AUTHORIZATION"
                  ? authorizationGuidance.action
                  : "Tiếp tục từ điểm an toàn"}
              </button>
            )}
          </div>
        )}
        <div
          className={`grid min-w-0 gap-4 ${!compact && run ? "lg:grid-cols-[minmax(15rem,0.75fr)_minmax(0,1.6fr)] lg:items-start" : ""}`}
        >
          {showRecentActivity && visibleRuns.length > 0 && (
            <div
              className={`grid min-w-0 content-start gap-2 text-sm ${!compact && run ? "lg:sticky lg:top-44" : ""}`}
            >
              {recentActivityHeading}
              {visibleRuns.slice(0, compact ? 3 : 10).map((item) => (
                <button
                  className={`flex flex-wrap items-center justify-between gap-3 rounded-control border p-3 text-left transition ${item.automation_run_id === run?.automation_run_id ? "border-brand/50 bg-brand-soft" : "border-border hover:bg-surface-quiet"}`}
                  key={item.automation_run_id}
                  type="button"
                  onClick={async () => {
                    try {
                      await loadRun(item.automation_run_id);
                      setError("");
                      setDetailRefreshError("");
                    } catch (reason) {
                      setDetailRefreshError(messageOf(reason));
                    }
                  }}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink">
                      {automationRunTitle(item)}
                    </span>
                    <span className="block text-xs text-ink-muted">
                      {compact
                        ? formatDate(item.created_at)
                        : `${automationTriggerLabel(item)}${item.created_at ? ` · ${formatDate(item.created_at)}` : ""}`}
                    </span>
                  </span>
                  <StatusPill
                    value={
                      item.automation_run_id === run?.automation_run_id
                        ? workflow?.status || item.workflow?.status || item.status
                        : item.workflow?.status || item.status
                    }
                  />
                </button>
              ))}
            </div>
          )}
          {showRecentActivity && visibleRuns.length === 0 && (
            <div className="grid gap-2 text-sm">
              {recentActivityHeading}
              <p className="text-ink-muted" role="status">
                Chưa có hoạt động gần đây.
              </p>
            </div>
          )}
          {run && (
            <div className="grid gap-4 pt-2 text-sm">
              {detailRefreshError && (
                <div className="grid gap-2" role="status">
                  <ErrorState
                    message={`Thông tin hoạt động AI có thể đã cũ; chưa tải được dữ liệu mới nhất: ${detailRefreshError}`}
                  />
                  <button
                    className="secondary-button justify-self-start"
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      try {
                        await loadRun(run.automation_run_id);
                      } catch (reason) {
                        setDetailRefreshError(messageOf(reason));
                      }
                    }}
                  >
                    Tải lại hoạt động và căn cứ
                  </button>
                </div>
              )}
              {workflow && (
                <section aria-label="Tiến độ xử lý AI" className="grid gap-3">
                  {workflow.truncated && (
                    <p
                      className="rounded-control border border-warning/40 bg-warning/5 p-3 text-sm text-warning"
                      role="status"
                    >
                      Chưa tải đủ lịch sử hoạt động để xác nhận toàn bộ đã hoàn tất.
                    </p>
                  )}
                  <details className="rounded-control border border-border bg-surface-quiet p-3">
                    <summary className="cursor-pointer text-sm font-medium text-ink">
                      Tiến độ hoạt động
                    </summary>
                    <div className="mt-3 grid gap-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span className="text-sm text-ink-muted">
                          {workflow.run_count} lượt · {workflow.active_count} đang chạy ·{" "}
                          {workflow.blocked_count} đang chờ · {workflow.failed_count} lỗi
                        </span>
                        <StatusPill value={workflow.status} />
                      </div>
                      {workflow.runs?.length > 1 && (
                        <ul className="grid gap-2">
                          {workflow.runs.slice(1).map((item) => (
                            <li
                              className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-border bg-surface p-3"
                              key={item.automation_run_id}
                            >
                              <span className="min-w-0 text-sm text-ink-muted">
                                {automationRunTitle(item)}
                              </span>
                              <StatusPill value={item.status} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </details>
                </section>
              )}
              {sourceExtractionGaps.length > 0 && (
                <section
                  aria-label="Phần tài liệu nguồn chưa trích xuất đầy đủ"
                  className="grid gap-3 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <div>
                    <h3 className="font-semibold text-ink">Tài liệu chưa được đọc đầy đủ</h3>
                    <p className="mt-1 text-ink-muted">
                      Agent đã dừng trước khi tạo hoặc cập nhật dữ liệu vì còn phần nguồn chưa trích
                      xuất được. Hãy xử lý tài liệu được nêu dưới đây rồi tải lại nguồn; hệ thống
                      không xem phần chưa đọc là nội dung đã kiểm tra.
                    </p>
                  </div>
                  <ul className="grid gap-2">
                    {sourceExtractionGaps.map((gap) => (
                      <li
                        className="grid min-w-0 gap-2 rounded-control border border-border bg-surface p-3"
                        key={gap.document_id}
                      >
                        <p className="font-medium text-ink">Tài liệu cần xử lý</p>
                        <p className="text-xs text-ink-muted">
                          Trạng thái {valueLabel(gap.index_status)}
                          {gap.page_count !== null ? ` · ${gap.page_count} trang` : ""}
                          {gap.unprocessed_block_count !== null
                            ? ` · ${gap.unprocessed_block_count} phần chưa đọc`
                            : ""}
                        </p>
                        {gap.unprocessed_blocks.length > 0 && (
                          <ul className="grid gap-1">
                            {gap.unprocessed_blocks.map((block, index) => (
                              <li
                                className="break-words text-sm text-ink-muted"
                                key={`${block.block_id}-${block.page_no}-${index}`}
                              >
                                {block.page_no !== null
                                  ? `Trang ${block.page_no}`
                                  : "Vị trí chưa rõ"}
                                {block.type ? ` · ${valueLabel(block.type)}` : ""}
                                {block.reason_code === "TABLE_TEXT_NOT_EXTRACTED"
                                  ? " · Chưa trích xuất được nội dung bảng"
                                  : block.reason_code === "PICTURE_TEXT_NOT_EXTRACTED"
                                    ? " · Chưa trích xuất được nội dung hình"
                                    : " · Nội dung chưa đọc đầy đủ"}
                              </li>
                            ))}
                          </ul>
                        )}
                        {gap.unprocessed_blocks_truncated && (
                          <p className="text-xs text-warning">
                            Danh sách vị trí đã được rút gọn; tổng số phần chưa đọc vẫn được giữ
                            nguyên.
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {mcpDiscoveryIssues.length > 0 && (
                <section
                  aria-label="Nguồn kết nối cần kiểm tra"
                  className="grid gap-2 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <h3 className="font-semibold text-ink">Nguồn kết nối chưa sẵn sàng</h3>
                  <p className="text-ink-muted">
                    Hệ thống không dùng nguồn gặp vấn đề làm căn cứ. Các phần việc độc lập vẫn có
                    thể tiếp tục; phần phụ thuộc nguồn này được giữ lại để xử lý an toàn.
                  </p>
                  <ul className="grid gap-2">
                    {mcpDiscoveryIssues.map((item) => (
                      <li
                        className="rounded-control border border-border bg-surface p-3 text-ink-muted"
                        key={`${item.reason_code}-${item.tool_name}`}
                      >
                        <p>{item.message}</p>
                        {item.tool_name && (
                          <p className="mt-1 text-xs">
                            Phần việc liên quan: {valueLabel(item.tool_name)}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {run.status === "AWAITING_INPUT" && (
                <section
                  aria-live="polite"
                  className="grid gap-3 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <div>
                    <h3 className="font-semibold text-ink">Cần bổ sung thông tin</h3>
                    <p className="mt-1 text-ink-muted">
                      AI đã tạm dừng vì dữ liệu hiện có chưa đủ căn cứ để tiếp tục an toàn.
                    </p>
                    <p className="mt-1 text-ink-muted">
                      Hãy bổ sung thông tin vào yêu cầu hoặc tài liệu nguồn liên quan. Khi nguồn
                      được cập nhật, hãy bấm bắt đầu xử lý bằng AI để tiếp tục.
                    </p>
                  </div>
                  {uncertainties.length > 0 ? (
                    <ul className="grid gap-3">
                      {uncertainties.map((item, index) => (
                        <li
                          className="grid gap-1 rounded-control border border-border bg-surface p-3"
                          key={`${item.code || "uncertainty"}-${index}`}
                        >
                          {item.question && <p className="font-medium text-ink">{item.question}</p>}
                          {item.reason && <p className="text-ink-muted">{item.reason}</p>}
                          {item.evidence_refs?.length > 0 && (
                            <div className="text-xs text-ink-muted">
                              <p>
                                Nguồn liên quan: {item.evidence_refs.length} trích dẫn đã xác minh
                              </p>
                            </div>
                          )}
                          {item.blocking && item.response_allowed && canAnswerClarification && (
                            <form
                              className="mt-2 grid gap-2"
                              onSubmit={(event) => {
                                event.preventDefault();
                                void answerClarification(item);
                              }}
                            >
                              <label className="grid gap-1 text-sm font-medium text-ink">
                                Thông tin trả lời
                                <textarea
                                  className="apple-input min-h-24"
                                  maxLength={4000}
                                  required
                                  value={clarificationAnswers[item.code] || ""}
                                  onChange={(event) =>
                                    setClarificationAnswers((current) => ({
                                      ...current,
                                      [item.code]: event.target.value,
                                    }))
                                  }
                                  placeholder="Bổ sung dữ kiện nghiệp vụ để AI tiếp tục xử lý"
                                />
                              </label>
                              <button
                                className="primary-button justify-self-start"
                                disabled={
                                  busy ||
                                  Boolean(submittingClarification) ||
                                  !clarificationAnswers[item.code]?.trim()
                                }
                                type="submit"
                              >
                                {submittingClarification === item.code
                                  ? "Đang gửi và tiếp tục…"
                                  : "Gửi thông tin và tiếp tục xử lý"}
                              </button>
                            </form>
                          )}
                          {item.blocking && item.response_allowed && !canAnswerClarification && (
                            <p className="mt-1 text-sm text-ink-muted">
                              Cần thành viên có quyền cập nhật yêu cầu bổ sung dữ kiện này.
                            </p>
                          )}
                          {item.blocking && !item.response_allowed && (
                            <p className="mt-1 text-sm text-ink-muted">
                              Cần cập nhật tài liệu hoặc khôi phục nguồn trước khi AI có thể tiếp
                              tục.
                            </p>
                          )}
                          {!item.blocking && item.resolution_status && (
                            <p className="mt-1 text-sm text-ink-muted">
                              Mục làm rõ này đã được xử lý trong tác vụ AI.
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-ink-muted">
                      Tác vụ AI chưa lưu câu hỏi cụ thể. Hãy mở yêu cầu hoặc tài liệu nguồn liên
                      quan để bổ sung thông tin còn thiếu.
                    </p>
                  )}
                </section>
              )}
              {run.error_code && run.status !== "AWAITING_INPUT" && (
                <ErrorState message={automationRunErrorMessage(run.error_code)} />
              )}
              {run.status === "AWAITING_AUTHORIZATION" && (
                <section
                  aria-live="polite"
                  className="grid gap-2 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <h3 className="font-semibold text-ink">Cần kiểm tra quyền thực hiện</h3>
                  <p className="text-ink-muted">{authorizationGuidance.message}</p>
                </section>
              )}
              {canControlRun && ["FAILED", "DEGRADED"].includes(run.status) && !canResumeRun && (
                <p className="rounded-control border border-warning/40 bg-warning/5 p-3 text-sm text-ink-muted">
                  Chưa thể tiếp tục an toàn vì hệ thống chưa xác minh được trạng thái thao tác
                  trước. Cần đối soát kết quả để tránh chạy lặp hoặc ghi trùng dữ liệu.
                </p>
              )}
              {proposal?.summary && (
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-ink">Kết quả xử lý</h3>
                    <ContentOriginBadge origin="ai_generated" />
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-ink-muted">{proposal.summary}</p>
                </div>
              )}
              {proposal?.evidence_refs?.length > 0 && (
                <div>
                  <h3 className="font-semibold text-ink">Căn cứ đã sử dụng</h3>
                  <p className="mt-1 text-ink-muted">
                    {proposal.evidence_refs.length} nguồn được dùng để tạo kết quả này.
                  </p>
                  {proposalEvidence.length > 0 && (
                    <ul className="mt-2 grid gap-1 text-sm text-ink-muted">
                      {proposalEvidence.map((fact) => (
                        <li key={fact.source_fact_id}>{sourceFactSummary(fact)}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {(checkpoints.length > 0 ||
                receipt ||
                blueprintClaims.length > 0 ||
                unlinkedSourceFacts.length > 0) && (
                <details className="rounded-control border border-border bg-surface-quiet p-4">
                  <summary className="cursor-pointer font-semibold text-ink">
                    Xem nguồn và quá trình tạo kết quả
                  </summary>
                  <div className="mt-4 grid gap-5">
                    {checkpoints.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-ink">Các bước đã thực hiện</h3>
                        <ol className="mt-2 grid gap-2">
                          {checkpoints.map((checkpoint) => {
                            const item = automationCheckpointView(checkpoint);
                            if (!item) return null;
                            return (
                              <li
                                className="grid min-w-0 gap-2 rounded-control border border-border bg-surface p-3"
                                key={checkpoint.checkpoint_id}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-medium text-ink">
                                    {item.sequence !== null ? `${item.sequence}. ` : ""}
                                    {item.phase}
                                  </span>
                                  <StatusPill value={item.status} />
                                </div>
                                <time
                                  className="text-xs text-ink-muted"
                                  dateTime={checkpoint.created_at || undefined}
                                >
                                  {item.createdAt}
                                </time>
                                {item.facts.length > 0 && (
                                  <ul className="grid gap-1 text-xs text-ink-muted">
                                    {item.facts.map((fact) => (
                                      <li key={fact}>{fact}</li>
                                    ))}
                                  </ul>
                                )}
                              </li>
                            );
                          })}
                        </ol>
                      </div>
                    )}
                    {receipt && (
                      <div>
                        <h3 className="font-semibold text-ink">Nguồn đã dùng</h3>
                        <p className="mt-1 text-ink-muted">
                          {receipt.source_fact_ids?.length || 0} nguồn được dùng để tạo kết quả này
                        </p>
                      </div>
                    )}
                    {blueprintClaims.length > 0 && (
                      <section
                        aria-label="Liên kết bản thiết kế kiểm thử với nguồn và kết quả"
                        className="grid gap-3"
                      >
                        <div>
                          <h3 className="font-semibold text-ink">
                            Liên kết với yêu cầu và ca kiểm thử
                          </h3>
                          <p className="mt-1 text-ink-muted">
                            Các mục dưới đây được tạo từ nội dung trích dẫn trong tài liệu.
                          </p>
                        </div>
                        <ul className="grid gap-3">
                          {blueprintClaims.map((claim) => {
                            const claimFacts = (claim.source_fact_ids || [])
                              .map((factId) => sourceFactsById.get(factId))
                              .filter(Boolean);
                            const linkedArtifacts = blueprintArtifacts.filter(
                              (artifact) =>
                                claim.claim_type === "OBLIGATION" &&
                                artifact.obligation_key === claim.claim_key &&
                                (artifact.source_fact_ids || []).some((factId) =>
                                  claim.source_fact_ids?.includes(factId),
                                ),
                            );
                            return (
                              <li
                                className="grid min-w-0 gap-3 rounded-control border border-border bg-surface p-3"
                                key={`${claim.claim_type}-${claim.claim_key}`}
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="status-badge">
                                    {claim.claim_type === "OBLIGATION"
                                      ? "Nghĩa vụ kiểm thử"
                                      : "Yêu cầu làm rõ"}
                                  </span>
                                  <span className="font-medium text-ink">
                                    {claim.claim_type === "OBLIGATION"
                                      ? "Điểm cần kiểm thử"
                                      : "Điểm cần làm rõ"}
                                  </span>
                                </div>
                                <div className="grid gap-2">
                                  <h4 className="text-sm font-semibold text-ink-muted">
                                    Căn cứ nguồn
                                  </h4>
                                  {claimFacts.length > 0 ? (
                                    claimFacts.map((fact) => (
                                      <div
                                        className="min-w-0 rounded-control bg-surface-quiet p-3"
                                        key={fact.source_fact_id}
                                      >
                                        <p className="break-words text-xs text-ink-muted">
                                          {sourceFactSummary(fact)}
                                        </p>
                                        <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                                          {fact.quote}
                                        </blockquote>
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-ink-muted">
                                      Không đọc được trích dẫn đã lưu cho nghĩa vụ này.
                                    </p>
                                  )}
                                </div>
                                {claim.claim_type === "OBLIGATION" && (
                                  <div className="grid gap-2">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <h4 className="text-sm font-semibold text-ink-muted">
                                        Đã ghi nhận trong dự án
                                      </h4>
                                      {linkedArtifacts.length > 0 && (
                                        <ContentOriginBadge
                                          origin="ai_generated"
                                          aiLabel="AI tạo · đã đọc lại"
                                        />
                                      )}
                                    </div>
                                    {linkedArtifacts.length > 0 ? (
                                      <ul className="grid gap-1">
                                        {linkedArtifacts.map((artifact) => (
                                          <li
                                            className="break-all rounded-control bg-surface-quiet px-3 py-2 text-ink"
                                            key={`${artifact.artifact_type}-${artifact.artifact_id}`}
                                          >
                                            {valueLabel(artifact.artifact_type)}
                                            <details className="mt-1 text-xs text-ink-muted">
                                              <summary className="cursor-pointer">
                                                Mã liên kết
                                              </summary>
                                              <span className="mt-1 block break-all">
                                                {artifact.artifact_id}
                                              </span>
                                            </details>
                                          </li>
                                        ))}
                                      </ul>
                                    ) : (
                                      <p className="text-ink-muted">
                                        Chưa có yêu cầu hoặc ca kiểm thử được xác minh cho nghĩa vụ
                                        này.
                                      </p>
                                    )}
                                  </div>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      </section>
                    )}
                    {unlinkedSourceFacts.length > 0 && (
                      <section aria-label="Trích dẫn nguồn đã kiểm chứng" className="grid gap-2">
                        <h3 className="font-semibold text-ink">Trích dẫn nguồn đã kiểm chứng</h3>
                        <ul className="grid gap-2">
                          {unlinkedSourceFacts.map((fact) => (
                            <li
                              className="min-w-0 rounded-control border border-border bg-surface p-3"
                              key={fact.source_fact_id}
                            >
                              <p className="break-words text-xs text-ink-muted">
                                {sourceFactSummary(fact)}
                              </p>
                              <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                                {fact.quote}
                              </blockquote>
                            </li>
                          ))}
                        </ul>
                      </section>
                    )}
                  </div>
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
