"use client";

import { useEffect, useState } from "react";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";

export default function AgentRunPanel({ project }) {
  const [intents, setIntents] = useState([]);
  const [intent, setIntent] = useState("");
  const [objective, setObjective] = useState("");
  const [targetIds, setTargetIds] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [actionEdits, setActionEdits] = useState([]);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canRun = Boolean(intent);

  useEffect(() => {
    let active = true;
    testingApi
      .listAgentCapabilities(project._id)
      .then((values) => {
        if (!active) return;
        setIntents(values);
        setIntent((current) =>
          values.some((item) => item.name === current) ? current : values[0]?.name || "",
        );
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      });
    return () => {
      active = false;
    };
  }, [project._id]);

  const execute = async () => {
    if (!objective.trim()) return;
    setBusy(true);
    setError("");
    try {
      const nextRun = await testingApi.runAgent({
        project_id: project._id,
        objective: objective.trim(),
        intent,
        target_artifact_ids: targetIds
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setRun(nextRun);
      setActionEdits(nextRun.proposal?.actions || []);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const decide = async (decision) => {
    setBusy(true);
    setError("");
    if (!decisionNote.trim()) {
      setError("Cần nhập ghi chú quyết định");
      setBusy(false);
      return;
    }
    try {
      const edits = decision === "EDIT" ? actionEdits : [];
      if (decision === "EDIT" && edits.length === 0) {
        setError("Cần ít nhất một hành động được chỉnh sửa");
        setBusy(false);
        return;
      }
      const nextRun = await testingApi.decideAgentRun(run.run_id, {
        decision,
        expected_revision: run.revision,
        note: decisionNote.trim(),
        action_edits: edits,
      });
      setRun(nextRun);
      setActionEdits(nextRun.proposal?.actions || []);
      setDecisionNote("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  if (!canRun) {
    return error ? (
      <Panel title="Tác tử kiểm thử">
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      </Panel>
    ) : null;
  }

  const updateActionArgument = (actionIndex, name, value) => {
    setActionEdits((items) =>
      items.map((item, index) =>
        index === actionIndex ? { ...item, arguments: { ...item.arguments, [name]: value } } : item,
      ),
    );
  };

  const outcomes = Array.isArray(run?.agent_results) ? run.agent_results : [];

  return (
    <Panel title="Tác tử kiểm thử">
      <div className="grid gap-4 p-4">
        {error && <ErrorState message={error} />}
        <label className="grid gap-2 text-sm font-medium text-ink">
          Năng lực
          <select
            className="apple-input"
            value={intent}
            onChange={(event) => setIntent(event.target.value)}
          >
            {intents.map((item) => (
              <option value={item.name} key={item.name}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Mục tiêu
          <textarea
            className="apple-input min-h-24"
            value={objective}
            onChange={(event) => setObjective(event.target.value)}
            placeholder="Phân tích rủi ro và đề xuất phạm vi kiểm thử"
          />
        </label>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Mã hiện vật liên quan
          <input
            className="apple-input"
            value={targetIds}
            onChange={(event) => setTargetIds(event.target.value)}
            placeholder="REQ-105, RUN-204"
          />
        </label>
        <div>
          <button
            className="apple-button"
            type="button"
            disabled={busy || !objective.trim()}
            onClick={execute}
          >
            {busy ? "Đang xử lý" : "Chạy tác tử"}
          </button>
        </div>
        {run && (
          <div className="grid gap-4 border-t border-border pt-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill value={run.status} />
              <span>{run.run_id}</span>
              <span>Vai trò {valueLabel(run.role)}</span>
            </div>
            {outcomes.length > 0 && (
              <div>
                <h3 className="font-semibold text-ink">Trạng thái kết quả</h3>
                <div className="mt-2 grid gap-2">
                  {outcomes.map((outcome) => (
                    <div
                      className="flex flex-wrap items-center gap-2 rounded-control border border-border bg-surface px-3 py-2"
                      key={outcome.task_id}
                    >
                      <StatusPill value={outcome.status} />
                      {outcome.summary && <span className="text-ink-muted">{outcome.summary}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {run.proposal?.summary && (
              <div>
                <h3 className="font-semibold text-ink">Kết quả</h3>
                <p className="mt-1 whitespace-pre-wrap text-ink-muted">{run.proposal.summary}</p>
              </div>
            )}
            {run.evidence_refs?.length > 0 && (
              <div>
                <h3 className="font-semibold text-ink">Bằng chứng</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {run.evidence_refs.map((item) => (
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
            {run.proposal?.warnings?.length > 0 && (
              <div>
                <h3 className="font-semibold text-ink">Cảnh báo</h3>
                <ul className="mt-2 grid gap-1 text-ink-muted">
                  {run.proposal.warnings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {run.status === "APPROVAL_REQUIRED" && (
              <div className="grid gap-3">
                <div className="grid gap-3">
                  <p className="font-medium text-ink">Hành động đề xuất</p>
                  {actionEdits.map((action, actionIndex) => (
                    <fieldset
                      className="grid gap-3 rounded-control border border-border p-3"
                      key={`${action.task_id}-${action.tool_name}-${actionIndex}`}
                    >
                      <legend className="px-1 text-sm font-medium">
                        Hành động {actionIndex + 1}
                      </legend>
                      {Object.entries(action.arguments || {}).map(([name, value]) => {
                        const editable =
                          value === null || ["string", "number", "boolean"].includes(typeof value);
                        if (!editable) {
                          return (
                            <p className="text-sm text-ink-muted" key={name}>
                              {valueLabel(name)} sẽ được giữ nguyên vì có cấu trúc nhiều phần
                            </p>
                          );
                        }
                        if (typeof value === "boolean") {
                          return (
                            <label className="flex items-center gap-2 text-sm" key={name}>
                              <input
                                checked={value}
                                type="checkbox"
                                onChange={(event) =>
                                  updateActionArgument(actionIndex, name, event.target.checked)
                                }
                              />
                              {valueLabel(name)}
                            </label>
                          );
                        }
                        return (
                          <label className="grid gap-2 text-sm" key={name}>
                            {valueLabel(name)}
                            <input
                              className="apple-input"
                              type={typeof value === "number" ? "number" : "text"}
                              value={value ?? ""}
                              onChange={(event) =>
                                updateActionArgument(
                                  actionIndex,
                                  name,
                                  typeof value === "number"
                                    ? Number(event.target.value)
                                    : event.target.value,
                                )
                              }
                            />
                          </label>
                        );
                      })}
                    </fieldset>
                  ))}
                </div>
                <label className="grid gap-2 font-medium text-ink">
                  Ghi chú quyết định
                  <textarea
                    className="apple-input min-h-20"
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                  />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    className="apple-button"
                    type="button"
                    disabled={busy || !decisionNote.trim()}
                    onClick={() => decide("APPROVE")}
                  >
                    Duyệt và áp dụng
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busy || !decisionNote.trim() || !actionEdits.length}
                    onClick={() => decide("EDIT")}
                  >
                    Lưu chỉnh sửa
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busy || !decisionNote.trim()}
                    onClick={() => decide("REJECT")}
                  >
                    Từ chối
                  </button>
                </div>
              </div>
            )}
            {run.proposal?.verification && (
              <div>
                <h3 className="font-semibold text-ink">Xác minh</h3>
                <p className="mt-1 text-ink-muted">
                  {run.proposal.verification.verified
                    ? "Đã xác minh kết quả"
                    : "Xác minh kết quả chưa đạt"}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
