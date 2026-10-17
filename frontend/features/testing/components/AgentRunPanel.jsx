"use client";

import { useEffect, useState } from "react";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";

const activeStatuses = new Set(["QUEUED", "RUNNING"]);

export default function AgentRunPanel({ project }) {
  const [intents, setIntents] = useState([]);
  const [intent, setIntent] = useState("");
  const [objective, setObjective] = useState("");
  const [targetIds, setTargetIds] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
      .catch((reason) => active && setError(messageOf(reason)));
    return () => {
      active = false;
    };
  }, [project._id]);

  useEffect(() => {
    if (!run || !activeStatuses.has(run.status)) return undefined;
    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const detail = await testingApi.getAutomationRun(run.automation_run_id);
        if (active) setRun(detail.run);
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
    }, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [run]);

  const execute = async () => {
    if (!objective.trim()) return;
    setBusy(true);
    setError("");
    try {
      setRun(
        await testingApi.runAutomation({
          project_id: project._id,
          objective: objective.trim(),
          intent,
          target_artifact_ids: targetIds
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      );
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
      setRun(
        await testingApi.retryAutomationRun(run.automation_run_id, {
          expected_revision: run.revision,
        }),
      );
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
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const decide = async (decision) => {
    if (!run || !decisionNote.trim()) return;
    setBusy(true);
    setError("");
    try {
      setRun(
        await testingApi.decideAutomationRun(run.automation_run_id, {
          decision,
          expected_revision: run.revision,
          note: decisionNote.trim(),
          action_edits: [],
        }),
      );
      setDecisionNote("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  if (!intents.length && !error) return null;

  const proposal = run?.result?.proposal;
  const busyRun = run && activeStatuses.has(run.status);

  return (
    <Panel title="AI Automation">
      <div className="grid gap-4 p-4">
        {error && <ErrorState message={error} />}
        <p className="text-sm text-ink-muted">
          Hệ thống tạo đề xuất có bằng chứng và chỉ chuyển sang bước quyết định của người dùng khi
          cần
        </p>
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
        <div className="flex flex-wrap gap-2">
          <button
            className="apple-button"
            type="button"
            disabled={busy || busyRun || !objective.trim()}
            onClick={execute}
          >
            {busy || busyRun ? "AI đang xử lý" : "Bắt đầu tự động hóa"}
          </button>
          {busyRun && (
            <button className="secondary-button" type="button" disabled={busy} onClick={cancel}>
              Dừng lượt chạy
            </button>
          )}
          {run?.status === "AWAITING_AUTHORIZATION" && (
            <button className="secondary-button" type="button" disabled={busy} onClick={retry}>
              Cấp quyền và tiếp tục
            </button>
          )}
        </div>
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
            {run.status === "AWAITING_HUMAN_DECISION" && (
              <div className="grid gap-3 rounded-control border border-border p-3">
                <p className="text-ink-muted">
                  Đề xuất cần quyết định của người có thẩm quyền trước khi hệ thống áp dụng thay đổi
                </p>
                <label className="grid gap-2 text-sm font-medium text-ink">
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
                    disabled={busy || !decisionNote.trim()}
                    onClick={() => decide("REJECT")}
                  >
                    Từ chối
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
