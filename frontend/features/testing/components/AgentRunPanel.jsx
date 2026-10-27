"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { EmptyState, ErrorState, LoadingState, Panel, StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";

const activeStatuses = new Set(["QUEUED", "RUNNING"]);

export default function AgentRunPanel({ project, showDefinitions = true }) {
  const currentUserId = project.current_membership?.user_id;
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const permissions = project.current_permissions || [];
  const canManageDefinitions =
    showDefinitions &&
    memberRoles.some((role) => ["BA", "QA"].includes(role)) &&
    permissions.includes("automation.create");
  const canReadProjectRuns = permissions.includes("proposal.read");
  const canReadOwnRuns = permissions.includes("automation.read");
  const canReadDefinitions = showDefinitions && permissions.includes("automation.read");
  const canViewRun = (item) => canReadProjectRuns || item?.requester_user_id === currentUserId;
  const [definitions, setDefinitions] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [definitionName, setDefinitionName] = useState("");
  const [trigger, setTrigger] = useState("");
  const [objective, setObjective] = useState("");
  const [run, setRun] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [receipt, setReceipt] = useState(null);
  const [sourceFacts, setSourceFacts] = useState([]);
  const [clarificationAnswers, setClarificationAnswers] = useState({});
  const [submittingClarification, setSubmittingClarification] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runsRefreshError, setRunsRefreshError] = useState("");
  const [detailRefreshError, setDetailRefreshError] = useState("");
  const [initialLoadAttempt, setInitialLoadAttempt] = useState(0);
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
    setDefinitions([]);
    setRecentRuns([]);
    setTriggers([]);
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
      canReadDefinitions ? testingApi.listAutomationDefinitions(project._id) : Promise.resolve([]),
      canManageDefinitions ? testingApi.listAutomationTriggers() : Promise.resolve([]),
      canReadProjectRuns || canReadOwnRuns
        ? testingApi.listAutomationRuns(project._id)
        : Promise.resolve([]),
    ])
      .then((results) => {
        if (!active) return;
        const values = results.map((result) => (result.status === "fulfilled" ? result.value : []));
        setDefinitions(values[0]);
        setTriggers(values[1]);
        if (listRequestVersion === runListRequestVersion.current) {
          setRecentRuns(values[2]);
        }
        setError(
          results
            .filter((result) => result.status === "rejected")
            .map((result) => messageOf(result.reason))
            .filter(Boolean)
            .join(" · "),
        );
        const availableTriggers = values[1];
        setTrigger((current) => current || availableTriggers[0] || "");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
      if (listRequestVersion === runListRequestVersion.current) {
        runListRequestVersion.current += 1;
      }
    };
  }, [
    canManageDefinitions,
    canReadOwnRuns,
    canReadProjectRuns,
    canReadDefinitions,
    currentUserId,
    initialLoadAttempt,
    project._id,
  ]);

  const refreshDefinitions = async () => {
    if (!canReadDefinitions) return;
    const values = await testingApi.listAutomationDefinitions(project._id);
    setDefinitions(values);
  };

  const refreshRuns = useCallback(async () => {
    if (!canReadProjectRuns && !canReadOwnRuns) return;
    const requestVersion = ++runListRequestVersion.current;
    const selectedRunId = selectedRunIdRef.current;
    const selectionVersion = detailRequestVersion.current;
    const items = await testingApi.listAutomationRuns(project._id);
    if (requestVersion !== runListRequestVersion.current) return;
    setRecentRuns(items);
    if (
      selectedRunId === selectedRunIdRef.current &&
      selectionVersion === detailRequestVersion.current
    ) {
      const selectedWorkflow = workflowForSelectedRun(items, selectedRunId);
      if (selectedWorkflow) setWorkflow(selectedWorkflow);
    }
    setRunsRefreshError("");
  }, [canReadOwnRuns, canReadProjectRuns, project._id]);

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
    if (!canReadProjectRuns && !canReadOwnRuns) return undefined;
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || pending) return;
      pending = true;
      const requestVersion = ++runListRequestVersion.current;
      const selectedRunId = selectedRunIdRef.current;
      const selectionVersion = detailRequestVersion.current;
      try {
        const items = await testingApi.listAutomationRuns(project._id);
        if (active && requestVersion === runListRequestVersion.current) {
          setRecentRuns(items);
          if (
            selectedRunId === selectedRunIdRef.current &&
            selectionVersion === detailRequestVersion.current
          ) {
            const selectedWorkflow = workflowForSelectedRun(items, selectedRunId);
            if (selectedWorkflow) setWorkflow(selectedWorkflow);
            const selectedSummary = items.find((item) => item.automation_run_id === selectedRunId);
            const knownSnapshot = selectedRunSnapshotRef.current;
            if (
              selectedSummary &&
              (!knownSnapshot ||
                selectedSummary.revision !== knownSnapshot.revision ||
                selectedSummary.status !== knownSnapshot.status)
            ) {
              let detail;
              try {
                detail = await testingApi.getAutomationRun(selectedRunId);
              } catch (reason) {
                if (
                  active &&
                  requestVersion === runListRequestVersion.current &&
                  selectedRunId === selectedRunIdRef.current &&
                  selectionVersion === detailRequestVersion.current
                ) {
                  setDetailRefreshError(messageOf(reason));
                }
              }
              if (
                detail &&
                active &&
                requestVersion === runListRequestVersion.current &&
                selectedRunId === selectedRunIdRef.current &&
                selectionVersion === detailRequestVersion.current
              ) {
                setDetailRefreshError("");
                selectedRunSnapshotRef.current = {
                  revision: detail.run.revision,
                  status: detail.run.status,
                };
                setRun(detail.run);
                setWorkflow(detail.workflow || selectedWorkflow || null);
                setCheckpoints(detail.checkpoints || []);
                setReceipt(detail.receipt || null);
                if (
                  !activeStatuses.has(detail.run.status) &&
                  !(detail.workflow?.active_count > 0)
                ) {
                  try {
                    const evidence = await testingApi.getAutomationRunEvidence(selectedRunId);
                    if (
                      active &&
                      requestVersion === runListRequestVersion.current &&
                      selectedRunId === selectedRunIdRef.current &&
                      selectionVersion === detailRequestVersion.current
                    ) {
                      setReceipt(evidence.receipt || detail.receipt || null);
                      setSourceFacts(evidence.source_facts || []);
                    }
                  } catch (reason) {
                    if (
                      active &&
                      requestVersion === runListRequestVersion.current &&
                      selectedRunId === selectedRunIdRef.current &&
                      selectionVersion === detailRequestVersion.current
                    ) {
                      setDetailRefreshError(messageOf(reason));
                    }
                  }
                }
              }
            }
          }
          setRunsRefreshError("");
        }
      } catch (reason) {
        if (active && requestVersion === runListRequestVersion.current) {
          setRunsRefreshError(messageOf(reason));
        }
      } finally {
        pending = false;
      }
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [canReadOwnRuns, canReadProjectRuns, project._id]);

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
        setDetailRefreshError("");
        setRun(detail.run);
        setWorkflow(detail.workflow || null);
        setCheckpoints(detail.checkpoints || []);
        setReceipt(detail.receipt || null);
        if (!activeStatuses.has(detail.run.status) && !(detail.workflow?.active_count > 0)) {
          const provenance = await testingApi.getAutomationRunEvidence(run.automation_run_id);
          if (active) {
            setReceipt(provenance.receipt || detail.receipt || null);
            setSourceFacts(provenance.source_facts || []);
            setDetailRefreshError("");
          }
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

  const saveDefinition = async () => {
    if (!definitionName.trim() || !objective.trim() || !trigger) return;
    setBusy(true);
    setError("");
    try {
      await testingApi.createAutomationDefinition({
        project_id: project._id,
        name: definitionName.trim(),
        trigger,
        objective: objective.trim(),
      });
      setDefinitionName("");
      setObjective("");
      await refreshDefinitions();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const toggleDefinition = async (definition) => {
    setBusy(true);
    setError("");
    try {
      await testingApi.updateAutomationDefinition(definition.definition_id, {
        expected_revision: definition.revision,
        enabled: !definition.enabled,
      });
      await refreshDefinitions();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

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
    setSubmittingClarification(uncertainty.code);
    setError("");
    try {
      await testingApi.answerAutomationClarification(runId, {
        expected_revision: run.revision,
        uncertainty_code: uncertainty.code,
        answer,
      });
      setClarificationAnswers((current) => ({ ...current, [uncertainty.code]: "" }));
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      try {
        await loadRun(runId);
      } catch (reason) {
        setDetailRefreshError(messageOf(reason));
      }
    } catch (reason) {
      setError(messageOf(reason));
      try {
        await loadRun(runId);
      } catch (refreshReason) {
        setDetailRefreshError(messageOf(refreshReason));
      }
    } finally {
      setSubmittingClarification("");
    }
  };

  const proposal = run?.result?.proposal;
  const blueprintClaims = receipt?.blueprint_claim_lineage || [];
  const blueprintArtifacts = receipt?.blueprint_artifact_lineage || [];
  const sourceFactsById = new Map(sourceFacts.map((fact) => [fact.source_fact_id, fact]));
  const busyRun = run && activeStatuses.has(run.status);
  const visibleRuns = recentRuns.filter(canViewRun);
  const visibleDefinitions = canReadDefinitions ? definitions : [];
  const canControlRun = run?.requester_user_id === currentUserId;
  const canAnswerClarification = permissions.includes("requirement.update");
  const canResumeRun = canControlRun && canResumeAutomationRun(run, checkpoints, currentUserId);
  const uncertainties = latestAutomationUncertainties(checkpoints);
  const mcpDiscoveryIssues = automationMcpDiscoveryIssues(run);
  const sourceExtractionGaps = automationSourceExtractionGaps(run);
  const authorizationGuidance = automationAuthorizationGuidance(run);

  return (
    <Panel title={showDefinitions ? "Quy tắc theo sự kiện và lượt chạy" : "Lịch sử lượt chạy AI"}>
      <div className="grid gap-4 p-4">
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
            <ErrorState message={`Chưa cập nhật được danh sách lượt chạy: ${runsRefreshError}`} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={busy}
              onClick={async () => {
                try {
                  await refreshRuns();
                } catch (reason) {
                  setRunsRefreshError(messageOf(reason));
                }
              }}
            >
              Tải lại danh sách lượt chạy
            </button>
          </div>
        )}
        {loading && <LoadingState />}
        {canManageDefinitions && (
          <>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Tên quy tắc tự động hóa
              <input
                className="apple-input"
                value={definitionName}
                onChange={(event) => setDefinitionName(event.target.value)}
                placeholder="Rà soát yêu cầu khi có thay đổi"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Sự kiện kích hoạt
              <select
                className="apple-input"
                value={trigger}
                onChange={(event) => setTrigger(event.target.value)}
              >
                {triggers.map((item) => (
                  <option value={item} key={item}>
                    {valueLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Phạm vi AI xử lý
              <textarea
                className="apple-input min-h-24"
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                placeholder="Mô tả kết quả quy tắc cần tạo từ sự kiện này"
              />
            </label>
          </>
        )}
        <div className="flex flex-wrap gap-2">
          {canManageDefinitions && (
            <button
              className="secondary-button"
              type="button"
              disabled={busy || !definitionName.trim() || !objective.trim() || !trigger}
              onClick={saveDefinition}
            >
              Lưu quy tắc tự động hóa
            </button>
          )}
          {busyRun && canControlRun && (
            <button className="secondary-button" type="button" disabled={busy} onClick={cancel}>
              Dừng lượt chạy
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
        {visibleDefinitions.length > 0 && (
          <div className="grid gap-2 border-t border-border pt-4 text-sm">
            <h3 className="font-semibold text-ink">Quy tắc đang có</h3>
            {visibleDefinitions.map((definition) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-border p-3"
                key={definition.definition_id}
              >
                <div>
                  <p className="font-medium text-ink">{definition.name}</p>
                  <p className="text-ink-muted">{valueLabel(definition.trigger)}</p>
                </div>
                {definition.owner_user_id === currentUserId && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busy}
                    onClick={() => toggleDefinition(definition)}
                  >
                    {definition.enabled ? "Tạm dừng" : "Kích hoạt"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        {visibleRuns.length > 0 && (
          <div className="grid gap-2 border-t border-border pt-4 text-sm">
            <h3 className="font-semibold text-ink">Lượt chạy gần đây</h3>
            {visibleRuns.slice(0, 10).map((item) => (
              <button
                className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-border p-3 text-left hover:bg-surface-quiet"
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
                  <span className="block truncate font-medium text-ink">{item.objective}</span>
                  <span className="block text-xs text-ink-muted">{item.automation_run_id}</span>
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
        {!loading &&
          !error &&
          !run &&
          visibleRuns.length === 0 &&
          visibleDefinitions.length === 0 && (
            <EmptyState>
              Chưa có lượt chạy AI. Lượt chạy sẽ xuất hiện khi có sự kiện được hệ thống tự động xử
              lý.
            </EmptyState>
          )}
        {run && (
          <div className="grid gap-4 border-t border-border pt-4 text-sm">
            {detailRefreshError && (
              <div className="grid gap-2" role="status">
                <ErrorState
                  message={`Thông tin lượt chạy có thể đã cũ; chưa tải được dữ liệu mới nhất: ${detailRefreshError}`}
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
                  Tải lại lượt chạy và bằng chứng
                </button>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill value={run.status} />
              <span>{run.automation_run_id}</span>
              <span>Vai trò {valueLabel(run.requester_role)}</span>
            </div>
            {workflow && (
              <section
                aria-label="Trạng thái toàn luồng AI"
                className="grid gap-3 rounded-control border border-border bg-surface-quiet p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-ink">Trạng thái toàn luồng</h3>
                    <p className="mt-1 text-xs text-ink-muted">
                      Gồm lượt này và các lượt được nó kích hoạt; trạng thái lượt cha có thể hoàn
                      tất trước các lượt tiếp theo.
                    </p>
                  </div>
                  <StatusPill value={workflow.status} />
                </div>
                <p className="text-xs text-ink-muted">
                  {workflow.run_count} lượt · {workflow.active_count} đang chạy ·{" "}
                  {workflow.blocked_count} đang chờ · {workflow.failed_count} lỗi
                </p>
                {workflow.truncated && (
                  <p className="text-xs text-warning" role="status">
                    Danh sách luồng vượt giới hạn đọc; chưa thể kết luận luồng đã hoàn tất.
                  </p>
                )}
                {workflow.runs?.length > 1 && (
                  <ul className="grid gap-2">
                    {workflow.runs.slice(1).map((item) => (
                      <li
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-border bg-surface p-3"
                        key={item.automation_run_id}
                      >
                        <span className="min-w-0 break-all text-xs text-ink-muted">
                          {valueLabel(item.trigger)} · {item.automation_run_id}
                        </span>
                        <StatusPill value={item.status} />
                      </li>
                    ))}
                  </ul>
                )}
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
                    Lượt tự động hóa đã dừng trước khi tạo hoặc cập nhật dữ liệu vì còn phần nguồn
                    chưa trích xuất được. Hãy xử lý tài liệu được nêu dưới đây rồi tải lại nguồn; hệ
                    thống không xem phần chưa đọc là nội dung đã kiểm tra.
                  </p>
                </div>
                <ul className="grid gap-2">
                  {sourceExtractionGaps.map((gap) => (
                    <li
                      className="grid min-w-0 gap-2 rounded-control border border-border bg-surface p-3"
                      key={gap.document_id}
                    >
                      <p className="break-all font-medium text-ink">Tài liệu {gap.document_id}</p>
                      <p className="text-xs text-ink-muted">
                        Trạng thái {valueLabel(gap.index_status)}
                        {gap.parser ? ` · Bộ đọc ${gap.parser}` : ""}
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
                              {block.page_no !== null ? `Trang ${block.page_no}` : "Vị trí chưa rõ"}
                              {block.type ? ` · ${valueLabel(block.type)}` : ""}
                              {block.reason_code === "TABLE_TEXT_NOT_EXTRACTED"
                                ? " · Chưa trích xuất được nội dung bảng"
                                : block.reason_code === "PICTURE_TEXT_NOT_EXTRACTED"
                                  ? " · Chưa trích xuất được nội dung hình"
                                  : block.reason_code
                                    ? ` · ${valueLabel(block.reason_code)}`
                                    : " · Khối chưa đọc đầy đủ"}
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
                aria-label="Nguồn MCP cần kiểm tra"
                className="grid gap-2 rounded-control border border-warning/40 bg-warning/5 p-4"
                role="status"
              >
                <h3 className="font-semibold text-ink">Nguồn MCP chưa sẵn sàng</h3>
                <p className="text-ink-muted">
                  AI không dùng nguồn gặp vấn đề làm bằng chứng. Các phần việc độc lập vẫn có thể
                  tiếp tục; phần phụ thuộc nguồn này được giữ lại để xử lý an toàn.
                </p>
                <ul className="grid gap-2">
                  {mcpDiscoveryIssues.map((item) => (
                    <li
                      className="rounded-control border border-border bg-surface p-3 text-ink-muted"
                      key={`${item.reason_code}-${item.tool_name}`}
                    >
                      {item.message}
                      {item.tool_name && (
                        <span className="ml-1">
                          Công cụ <code>{item.tool_name}</code>.
                        </span>
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
                    Hãy bổ sung thông tin vào yêu cầu hoặc tài liệu nguồn liên quan. Khi nguồn được
                    cập nhật, hệ thống sẽ tự tiếp nhận sự kiện mới để xử lý tiếp; không cần khởi
                    chạy lại từng bước.
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
                          <p className="text-xs text-ink-muted">
                            Nguồn liên quan: {item.evidence_refs.join(", ")}
                          </p>
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
                                : "Trả lời và tiếp tục tự động"}
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
                            Cần cập nhật tài liệu hoặc khôi phục nguồn trước khi AI có thể tiếp tục.
                          </p>
                        )}
                        {!item.blocking && item.resolution_status && (
                          <p className="mt-1 text-sm text-ink-muted">
                            Mục làm rõ này đã được xử lý trong lượt chạy.
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-ink-muted">
                    Lượt chạy chưa lưu câu hỏi cụ thể. Hãy mở yêu cầu hoặc tài liệu nguồn liên quan
                    để bổ sung thông tin còn thiếu.
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
                Chưa thể tiếp tục an toàn vì hệ thống chưa xác minh được trạng thái thao tác trước.
                Cần đối soát kết quả để tránh chạy lặp hoặc ghi trùng dữ liệu.
              </p>
            )}
            {proposal?.summary && (
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-ink">Kết quả của lượt tự động hóa</h3>
                  <ContentOriginBadge origin="ai_generated" />
                </div>
                <p className="mt-1 whitespace-pre-wrap text-ink-muted">{proposal.summary}</p>
              </div>
            )}
            {proposal?.evidence_refs?.length > 0 && (
              <div>
                <h3 className="font-semibold text-ink">Bằng chứng đã dùng</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {proposal.evidence_refs.map((item) => (
                    <span
                      className="rounded-full border border-border bg-surface px-3 py-1 text-xs"
                      key={item}
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {checkpoints.length > 0 && (
              <div>
                <h3 className="font-semibold text-ink">Nhật ký các bước xử lý</h3>
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
                <h3 className="font-semibold text-ink">Dấu vết bằng chứng</h3>
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
                  <h3 className="font-semibold text-ink">Từ nguồn đến yêu cầu và ca kiểm thử</h3>
                  <p className="mt-1 text-ink-muted">
                    Mỗi nghĩa vụ dưới đây được nối với trích dẫn đã kiểm chứng và kết quả được đọc
                    lại từ dự án.
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
                          <StatusPill value={claim.claim_type} />
                          <span className="break-all font-medium text-ink">{claim.claim_key}</span>
                        </div>
                        <div className="grid gap-2">
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                            Căn cứ nguồn
                          </h4>
                          {claimFacts.length > 0 ? (
                            claimFacts.map((fact) => (
                              <div
                                className="min-w-0 rounded-control bg-surface-quiet p-3"
                                key={fact.source_fact_id}
                              >
                                <p className="break-words text-xs text-ink-muted">
                                  {valueLabel(fact.artifact_type)} · {fact.artifact_id}
                                  {fact.artifact_version_id ? ` · ${fact.artifact_version_id}` : ""}
                                </p>
                                <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                                  {fact.quote}
                                </blockquote>
                                <p className="mt-2 break-all text-xs text-ink-muted">
                                  {fact.source}
                                  {fact.source_start !== null && fact.source_start !== undefined
                                    ? ` · Vị trí ${fact.source_start}–${fact.source_end}`
                                    : ""}
                                </p>
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
                              <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                                Kết quả đã xác minh trong dự án
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
                                    {valueLabel(artifact.artifact_type)} · {artifact.artifact_id}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-ink-muted">
                                Chưa có yêu cầu hoặc ca kiểm thử được xác minh cho nghĩa vụ này.
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
            {sourceFacts.length > 0 && (
              <section aria-label="Trích dẫn nguồn đã kiểm chứng" className="grid gap-2">
                <h3 className="font-semibold text-ink">Trích dẫn nguồn đã kiểm chứng</h3>
                <ul className="grid gap-2">
                  {sourceFacts.map((fact) => (
                    <li
                      className="min-w-0 rounded-control border border-border bg-surface p-3"
                      key={fact.source_fact_id}
                    >
                      <p className="break-words text-xs text-ink-muted">
                        {valueLabel(fact.artifact_type)} · {fact.artifact_id}
                        {fact.artifact_version_id ? ` · ${fact.artifact_version_id}` : ""}
                      </p>
                      <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                        {fact.quote}
                      </blockquote>
                      <p className="mt-2 break-all text-xs text-ink-muted">
                        {fact.source}
                        {fact.source_start !== null && fact.source_start !== undefined
                          ? ` · Vị trí ${fact.source_start}–${fact.source_end}`
                          : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
