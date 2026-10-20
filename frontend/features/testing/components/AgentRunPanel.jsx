"use client";

import { useCallback, useEffect, useState } from "react";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";

const activeStatuses = new Set(["QUEUED", "RUNNING"]);

export default function AgentRunPanel({ project }) {
  const currentUserId = project.current_membership?.user_id;
  const currentRole = project.current_membership?.project_role;
  const permissions = project.current_permissions || [];
  const canManageDefinitions =
    ["BA", "QA"].includes(currentRole) && permissions.includes("automation.create");
  const canReadAllRuns = permissions.includes("proposal.read");
  const canReadDefinitions = permissions.includes("automation.read");
  const canViewRun = (item) => canReadAllRuns || item?.requester_user_id === currentUserId;
  const [definitions, setDefinitions] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [capabilities, setCapabilities] = useState([]);
  const [definitionName, setDefinitionName] = useState("");
  const [trigger, setTrigger] = useState("");
  const [intent, setIntent] = useState("");
  const [objective, setObjective] = useState("");
  const [targetIds, setTargetIds] = useState("");
  const [run, setRun] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [receipt, setReceipt] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      canReadDefinitions ? testingApi.listAutomationDefinitions(project._id) : Promise.resolve([]),
      canManageDefinitions ? testingApi.listAutomationTriggers() : Promise.resolve([]),
      canReadAllRuns ? testingApi.listAutomationRuns(project._id) : Promise.resolve([]),
      testingApi.listAgentCapabilities(project._id),
    ])
      .then(([items, availableTriggers, runs, availableCapabilities]) => {
        if (!active) return;
        setDefinitions(items);
        setTriggers(availableTriggers);
        setRecentRuns(runs);
        setCapabilities(availableCapabilities);
        setTrigger((current) => current || availableTriggers[0] || "");
      })
      .catch((reason) => active && setError(messageOf(reason)));
    return () => {
      active = false;
    };
  }, [canManageDefinitions, canReadAllRuns, canReadDefinitions, project._id]);

  const refreshDefinitions = async () => {
    if (!canReadDefinitions) return;
    const values = await testingApi.listAutomationDefinitions(project._id);
    setDefinitions(values);
  };

  const refreshRuns = useCallback(async () => {
    if (!canReadAllRuns) return;
    setRecentRuns(await testingApi.listAutomationRuns(project._id));
  }, [canReadAllRuns, project._id]);

  useEffect(() => {
    if (!run || !activeStatuses.has(run.status)) return undefined;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const detail = await testingApi.getAutomationRun(run.automation_run_id);
        if (!active) return;
        setRun(detail.run);
        setCheckpoints(detail.checkpoints || []);
        setReceipt(detail.receipt || null);
        if (!activeStatuses.has(detail.run.status)) {
          const provenance = await testingApi.getAutomationEvidence(run.automation_run_id);
          if (active) setReceipt(provenance.receipt || null);
          await refreshRuns();
        }
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
    }, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [run, refreshRuns]);

  const execute = async () => {
    if (!objective.trim()) return;
    setBusy(true);
    setError("");
    try {
      const created = await testingApi.runAutomation({
        project_id: project._id,
        objective: objective.trim(),
        intent: intent || undefined,
        target_artifact_ids: targetIds
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setRun(created);
      await refreshRuns();
      setCheckpoints([]);
      setReceipt(null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

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
        intent,
      });
      setDefinitionName("");
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
    setBusy(true);
    setError("");
    try {
      const updated = await testingApi.retryAutomationRun(run.automation_run_id, {
        expected_revision: run.revision,
      });
      setRun(updated);
      await refreshRuns();
      setCheckpoints([]);
      setReceipt(null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!run) return;
    setBusy(true);
    setError("");
    try {
      setRun(
        await testingApi.cancelAutomationRun(run.automation_run_id, {
          expected_revision: run.revision,
        }),
      );
      await refreshRuns();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const proposal = run?.result?.proposal;
  const busyRun = run && activeStatuses.has(run.status);
  const visibleRuns = recentRuns.filter(canViewRun);
  const visibleDefinitions = canReadDefinitions ? definitions : [];
  const canStartRun = capabilities.length > 0;
  const canControlRun = run?.requester_user_id === currentUserId;

  return (
    <Panel title="Quy tắc và lượt chạy">
      <div className="grid gap-4 p-4">
        {error && <ErrorState message={error} />}
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
          </>
        )}
        {canStartRun && (
          <>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Việc cần AI thực hiện
              <textarea
                className="apple-input min-h-24"
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                placeholder="Ví dụ: rà soát yêu cầu đăng nhập và nêu các điểm còn thiếu"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Tác vụ (không bắt buộc)
              <select
                className="apple-input"
                value={intent}
                onChange={(event) => setIntent(event.target.value)}
              >
                <option value="">AI tự chọn theo yêu cầu</option>
                {capabilities.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              Mã tài liệu hoặc đối tượng liên quan (không bắt buộc)
              <input
                className="apple-input"
                value={targetIds}
                onChange={(event) => setTargetIds(event.target.value)}
                placeholder="REQ-105, RUN-204"
              />
              <span className="text-xs font-normal text-ink-muted">
                Nhập một hoặc nhiều mã, phân tách bằng dấu phẩy
              </span>
            </label>
          </>
        )}
        <div className="flex flex-wrap gap-2">
          {canStartRun && (
            <button
              className="apple-button"
              type="button"
              disabled={busy || busyRun || !objective.trim()}
              onClick={execute}
            >
              {busy || busyRun ? "AI đang xử lý" : "Chạy một lượt"}
            </button>
          )}
          {canManageDefinitions && canStartRun && (
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
          {run?.status === "AWAITING_AUTHORIZATION" && canControlRun && (
            <button className="secondary-button" type="button" disabled={busy} onClick={retry}>
              Cấp quyền và tiếp tục
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
                    const detail = await testingApi.getAutomationRun(item.automation_run_id);
                    setRun(detail.run);
                    setCheckpoints(detail.checkpoints || []);
                    setReceipt(detail.receipt || null);
                    setError("");
                  } catch (reason) {
                    setError(messageOf(reason));
                  }
                }}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-ink">{item.objective}</span>
                  <span className="block text-xs text-ink-muted">{item.automation_run_id}</span>
                </span>
                <StatusPill value={item.status} />
              </button>
            ))}
          </div>
        )}
        {run && (
          <div className="grid gap-4 border-t border-border pt-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill value={run.status} />
              <span>{run.automation_run_id}</span>
              <span>Vai trò {valueLabel(run.requester_role)}</span>
            </div>
            {run.error_code && <ErrorState message={valueLabel(run.error_code)} />}
            {proposal?.summary && (
              <div>
                <h3 className="font-semibold text-ink">Kết quả đề xuất</h3>
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
                <h3 className="font-semibold text-ink">Tiến trình đã ghi nhận</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {checkpoints.map((checkpoint) => (
                    <span
                      className="rounded-full border border-border bg-surface px-3 py-1 text-xs"
                      key={checkpoint.checkpoint_id}
                    >
                      {valueLabel(checkpoint.phase)}
                    </span>
                  ))}
                </div>
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
          </div>
        )}
      </div>
    </Panel>
  );
}
