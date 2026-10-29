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
import { formatDate, messageOf, valueLabel } from "../lib/testing";
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
  return run?.trigger === "MANUAL" ? "Theo yêu cầu người dùng" : "Sự kiện dự án";
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

export default function AgentRunPanel({ project, showDefinitions = true, compact = false }) {
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
  const [automationActions, setAutomationActions] = useState([]);
  const [definitionName, setDefinitionName] = useState("");
  const [trigger, setTrigger] = useState("");
  const [objective, setObjective] = useState("");
  const [selectedActions, setSelectedActions] = useState([]);
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
    setAutomationActions([]);
    setSelectedActions([]);
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
      canManageDefinitions ? testingApi.listAutomationActions() : Promise.resolve([]),
      canReadProjectRuns || canReadOwnRuns
        ? testingApi.listAutomationRuns(project._id)
        : Promise.resolve([]),
    ])
      .then((results) => {
        if (!active) return;
        const values = results.map((result) => (result.status === "fulfilled" ? result.value : []));
        setDefinitions(values[0]);
        setTriggers(values[1]);
        setAutomationActions(values[2]);
        if (listRequestVersion === runListRequestVersion.current) {
          setRecentRuns(values[3]);
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
      const selectedSummary = items.find((item) => item.automation_run_id === selectedRunId);
      if (
        selectedWorkflow &&
        !isOlderRunSnapshot(selectedSummary, selectedRunSnapshotRef.current)
      ) {
        setWorkflow(selectedWorkflow);
      }
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
    if ((!canReadProjectRuns && !canReadOwnRuns) || error) return undefined;
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
            const selectedSummary = items.find((item) => item.automation_run_id === selectedRunId);
            const knownSnapshot = selectedRunSnapshotRef.current;
            if (
              selectedWorkflow &&
              !isOlderRunSnapshot(selectedSummary, knownSnapshot)
            ) {
              setWorkflow(selectedWorkflow);
            }
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
              let evidence = null;
              let evidenceError = "";
              if (
                detail &&
                !activeStatuses.has(detail.run.status) &&
                !(detail.workflow?.active_count > 0)
              ) {
                try {
                  evidence = await testingApi.getAutomationRunEvidence(selectedRunId);
                } catch (reason) {
                  evidenceError = messageOf(reason);
                }
              }
              if (
                detail &&
                active &&
                requestVersion === runListRequestVersion.current &&
                selectedRunId === selectedRunIdRef.current &&
                selectionVersion === detailRequestVersion.current &&
                !isOlderRunSnapshot(detail.run, selectedRunSnapshotRef.current)
              ) {
                selectedRunSnapshotRef.current = {
                  revision: detail.run.revision,
                  status: detail.run.status,
                };
                setRun(detail.run);
                setWorkflow(detail.workflow || selectedWorkflow || null);
                setCheckpoints(detail.checkpoints || []);
                setReceipt(evidence?.receipt || detail.receipt || null);
                setSourceFacts(evidence?.source_facts || []);
                setDetailRefreshError(evidenceError);
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
  }, [canReadOwnRuns, canReadProjectRuns, error, project._id]);

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
        actions: selectedActions,
      });
      setDefinitionName("");
      setObjective("");
      setSelectedActions([]);
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
  const busyRun = run && activeStatuses.has(run.status);
  const visibleRuns = recentRuns.filter(canViewRun);
  const visibleDefinitions = canReadDefinitions ? definitions : [];
  const canControlRun = run?.requester_user_id === currentUserId;
  const canAnswerClarification = permissions.includes("requirement.update");
  const canResumeRun = canControlRun && canResumeAutomationRun(run, checkpoints, currentUserId);
  const canShowRunControls = canManageDefinitions || (busyRun && canControlRun) || canResumeRun;
  const uncertainties = latestAutomationUncertainties(checkpoints);
  const mcpDiscoveryIssues = automationMcpDiscoveryIssues(run);
  const sourceExtractionGaps = automationSourceExtractionGaps(run);
  const authorizationGuidance = automationAuthorizationGuidance(run);

  return (
    <Panel title="Hoạt động AI" className={compact ? "agent-run-panel-compact" : ""}>
      <div className={`grid px-4 ${compact ? "gap-2 pb-3 pt-2" : "gap-4 pb-4 pt-3"}`}>
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
              onClick={async () => {
                try {
                  await refreshRuns();
                } catch (reason) {
                  setRunsRefreshError(messageOf(reason));
                }
              }}
            >
              Tải lại hoạt động AI
            </button>
          </div>
        )}
        {loading &&
          (compact ? (
            <p className="py-2 text-sm text-ink-muted" role="status" aria-busy="true">
              Đang tải hoạt động…
            </p>
          ) : (
            <LoadingState />
          ))}
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
            {automationActions.length > 0 && (
              <fieldset className="grid gap-2 rounded-control border border-border p-3">
                <legend className="px-1 text-sm font-medium text-ink">Phạm vi thao tác</legend>
                <p className="text-sm text-ink-muted">
                  Luồng chính của sự kiện vẫn chạy. Các lựa chọn này chỉ cấp phép thao tác bổ sung;
                  để trống nghĩa là AI không gọi thêm công cụ.
                </p>
                {automationActions.map((action) => (
                  <label className="flex items-start gap-2 text-sm text-ink" key={action}>
                    <input
                      className="mt-1"
                      type="checkbox"
                      checked={selectedActions.includes(action)}
                      onChange={(event) => {
                        setSelectedActions((current) =>
                          event.target.checked
                            ? [...current, action]
                            : current.filter((item) => item !== action),
                        );
                      }}
                    />
                    <span>{valueLabel(action)}</span>
                  </label>
                ))}
              </fieldset>
            )}
          </>
        )}
        {canShowRunControls && (
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
        {visibleDefinitions.length > 0 && (
          <div className="grid gap-2 pt-2 text-sm">
            <h3 className="font-semibold text-ink">Quy tắc đang có</h3>
            {visibleDefinitions.map((definition) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-border p-3"
                key={definition.definition_id}
              >
                <div>
                  <p className="font-medium text-ink">{definition.name}</p>
                  <p className="text-ink-muted">{valueLabel(definition.trigger)}</p>
                  {definition.actions?.length > 0 && (
                    <p className="text-ink-muted">
                      {definition.actions.map(valueLabel).join(" · ")}
                    </p>
                  )}
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
          <div className="grid gap-2 text-sm">
            {!compact && <h3 className="font-semibold text-ink">Hoạt động gần đây</h3>}
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
                  <span className="block truncate font-medium text-ink">
                    {automationRunTitle(item)}
                  </span>
                  <span className="block text-xs text-ink-muted">
                    {item.trigger === "MANUAL" && "Chạy theo yêu cầu"}
                    {item.created_at &&
                      `${item.trigger === "MANUAL" ? " · " : ""}${formatDate(item.created_at)}`}
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
        {!loading &&
          !error &&
          !run &&
          visibleRuns.length === 0 &&
          visibleDefinitions.length === 0 && (
            <p className="py-2 text-sm text-ink-muted" role="status">
              Chưa có hoạt động gần đây.
            </p>
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
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill value={run.status} />
              <span className="min-w-0 break-words font-medium">{automationRunTitle(run)}</span>
              {run.created_at && (
                <time className="text-xs text-ink-muted" dateTime={run.created_at}>
                  {formatDate(run.created_at)}
                </time>
              )}
              <details className="text-xs text-ink-muted">
                <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                <dl className="mt-2 grid gap-1">
                  <div>
                    <dt className="inline">Nguồn khởi chạy: </dt>
                    <dd className="inline">{automationTriggerLabel(run)}</dd>
                  </div>
                  <div>
                    <dt className="inline">Vai trò yêu cầu: </dt>
                    <dd className="inline">{valueLabel(run.requester_role)}</dd>
                  </div>
                  <div>
                    <dt className="inline">Mã tham chiếu: </dt>
                    <dd className="inline break-all">{run.automation_run_id}</dd>
                  </div>
                </dl>
              </details>
            </div>
            {workflow && (
              <section
                aria-label="Tiến độ xử lý AI"
                className="grid gap-3 rounded-control border border-border bg-surface-quiet p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-ink">Tình trạng xử lý</h3>
                  </div>
                  <StatusPill value={workflow.status} />
                </div>
                <p className="text-xs text-ink-muted">
                  {workflow.run_count} lượt · {workflow.active_count} đang chạy ·{" "}
                  {workflow.blocked_count} đang chờ · {workflow.failed_count} lỗi
                </p>
                {workflow.truncated && (
                  <p className="text-xs text-warning" role="status">
                    Còn hoạt động AI chưa được tải hết nên chưa thể xác nhận toàn bộ đã hoàn tất.
                  </p>
                )}
                {workflow.runs?.length > 1 && (
                  <ul className="grid gap-2">
                    {workflow.runs.slice(1).map((item) => (
                      <li
                        className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-border bg-surface p-3"
                        key={item.automation_run_id}
                      >
                        <span className="min-w-0 text-xs text-ink-muted">
                          {automationRunTitle(item)}
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
                      <p className="font-medium text-ink">Tài liệu cần xử lý</p>
                      <details className="text-xs text-ink-muted">
                        <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                        <p className="mt-1 break-all">Mã tài liệu: {gap.document_id}</p>
                      </details>
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
                              {block.page_no !== null ? `Trang ${block.page_no}` : "Vị trí chưa rõ"}
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
                      {gap.parser && (
                        <details className="text-xs text-ink-muted">
                          <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                          <p className="mt-1 break-all">Bộ đọc: {gap.parser}</p>
                        </details>
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
                  Hệ thống không dùng nguồn gặp vấn đề làm căn cứ. Các phần việc độc lập vẫn có thể
                  tiếp tục; phần phụ thuộc nguồn này được giữ lại để xử lý an toàn.
                </p>
                <ul className="grid gap-2">
                  {mcpDiscoveryIssues.map((item) => (
                    <li
                      className="rounded-control border border-border bg-surface p-3 text-ink-muted"
                      key={`${item.reason_code}-${item.tool_name}`}
                    >
                      <p>{item.message}</p>
                      {item.tool_name && (
                        <details className="mt-2 text-xs">
                          <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                          <p className="mt-1 break-all">Tên thao tác: {item.tool_name}</p>
                        </details>
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
                          <div className="text-xs text-ink-muted">
                            <p>
                              Nguồn liên quan: {item.evidence_refs.length} trích dẫn đã xác minh
                            </p>
                            <details className="mt-1">
                              <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                              <p className="mt-1 break-all">
                                Mã nguồn: {item.evidence_refs.join(", ")}
                              </p>
                            </details>
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
                            Mục làm rõ này đã được xử lý trong tác vụ AI.
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-ink-muted">
                    Tác vụ AI chưa lưu câu hỏi cụ thể. Hãy mở yêu cầu hoặc tài liệu nguồn liên quan
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
                      <li key={fact.source_fact_id}>
                        {fact.source || valueLabel(fact.artifact_type)}
                        {fact.source_page_numbers?.length
                          ? ` · Trang ${fact.source_page_numbers.join(", ")}`
                          : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
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
                          <details className="text-xs text-ink-muted">
                            <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                            <p className="mt-1 break-all">Mã liên kết: {claim.claim_key}</p>
                          </details>
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
                                  {valueLabel(fact.artifact_type)}
                                  {fact.source_page_numbers?.length
                                    ? ` · Trang ${fact.source_page_numbers.join(", ")}`
                                    : " · Đoạn trích đã xác minh"}
                                </p>
                                <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                                  {fact.quote}
                                </blockquote>
                                {fact.source_start !== null && fact.source_start !== undefined && (
                                  <p className="mt-2 break-all text-xs text-ink-muted">
                                    Vị trí nội dung {fact.source_start}–{fact.source_end}
                                  </p>
                                )}
                                <details className="mt-2 text-xs text-ink-muted">
                                  <summary className="cursor-pointer">Thông tin nguồn</summary>
                                  <p className="mt-1 break-all">
                                    Nguồn: {fact.source} · Mã đối tượng: {fact.artifact_id}
                                    {fact.artifact_version_id
                                      ? ` · Phiên bản: ${fact.artifact_version_id}`
                                      : ""}
                                  </p>
                                </details>
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
                                    {valueLabel(artifact.artifact_type)}
                                    <details className="mt-1 text-xs text-ink-muted">
                                      <summary className="cursor-pointer">Mã liên kết</summary>
                                      <span className="mt-1 block break-all">
                                        {artifact.artifact_id}
                                      </span>
                                    </details>
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
                        {valueLabel(fact.artifact_type)}
                        {fact.source_page_numbers?.length
                          ? ` · Trang ${fact.source_page_numbers.join(", ")}`
                          : " · Đoạn trích đã xác minh"}
                      </p>
                      <blockquote className="mt-2 break-words border-l-2 border-accent/40 pl-3 text-ink">
                        {fact.quote}
                      </blockquote>
                      {fact.source_start !== null && fact.source_start !== undefined && (
                        <p className="mt-2 break-all text-xs text-ink-muted">
                          Vị trí nội dung {fact.source_start}–{fact.source_end}
                        </p>
                      )}
                      <details className="mt-2 text-xs text-ink-muted">
                        <summary className="cursor-pointer">Thông tin nguồn</summary>
                        <p className="mt-1 break-all">
                          Nguồn: {fact.source} · Mã đối tượng: {fact.artifact_id}
                          {fact.artifact_version_id
                            ? ` · Phiên bản: ${fact.artifact_version_id}`
                            : ""}
                        </p>
                      </details>
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
