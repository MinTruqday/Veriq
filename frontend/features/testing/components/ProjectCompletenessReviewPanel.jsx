"use client";
import { useEffect, useRef, useState } from "react";
import { Panel, StatusPill } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { preferredSummaryLocale } from "../lib/summaryLanguage";
import { testingApi } from "../services/testing.service";
const stages = [
  ["REQUIREMENTS", "Làm rõ yêu cầu"],
  ["TEST_PLANNING", "Lập kế hoạch kiểm thử"],
  ["TEST_DESIGN", "Thiết kế kiểm thử"],
  ["EXECUTION_READINESS", "Chuẩn bị thực thi"],
  ["RELEASE_READINESS", "Chuẩn bị phát hành"],
];
export default function ProjectCompletenessReviewPanel({ project, user }) {
  const allowed = project.current_permissions?.includes("ai.ask_project");
  const [sources, setSources] = useState({ documents: [], requirements: [] });
  const [selected, setSelected] = useState(new Set());
  const [stage, setStage] = useState("REQUIREMENTS");
  const [scopeDescription, setScopeDescription] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const idempotencyRef = useRef(null);
  useEffect(() => {
    let active = true;
    if (!allowed) return undefined;
    Promise.all([
      testingApi.getProjectCompletenessScope(project._id),
      testingApi.getProjectCompletenessReview(project._id),
    ])
      .then(([available, latest]) => {
        if (!active) return;
        const documents = available.documents || [];
        const requirements = available.requirements || [];
        setSources({ documents, requirements });
        setSelected(
          new Set([
            ...documents.map((item) => `document:${item.id}`),
            ...requirements.map((item) => `requirement:${item.version_id}`),
          ]),
        );
        if (latest && !latest.stale) setResult(latest);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      });
    return () => {
      active = false;
    };
  }, [allowed, project._id, project.revision]);
  if (!allowed) return null;
  const toggle = (key) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const request = {
        document_ids: [...selected]
          .filter((key) => key.startsWith("document:"))
          .map((key) => key.slice(9)),
        requirement_version_ids: [...selected]
          .filter((key) => key.startsWith("requirement:"))
          .map((key) => key.slice(11)),
        stage,
        scope_description: scopeDescription,
        output_language: preferredSummaryLocale(user?.locale, project.locale, navigator.language),
      };
      const fingerprint = JSON.stringify({ project_id: project._id, ...request });
      if (idempotencyRef.current?.fingerprint !== fingerprint) {
        idempotencyRef.current = { fingerprint, key: crypto.randomUUID() };
      }
      const value = await testingApi.reviewProjectCompleteness(project._id, {
        ...request,
        idempotency_key: idempotencyRef.current.key,
      });
      idempotencyRef.current = null;
      setResult(value);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel title="Rà soát độ đầy đủ hồ sơ">
      <div className="space-y-4 p-4">
        <p className="text-sm text-ink-muted">
          Chọn nguồn và giai đoạn cần rà soát. Kết quả chỉ nêu khoảng trống trong phạm vi đã chọn.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field-label">
            Giai đoạn
            <select
              className="apple-input mt-2"
              value={stage}
              onChange={(event) => setStage(event.target.value)}
            >
              {stages.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Phạm vi cần rà soát
            <input
              className="apple-input mt-2"
              minLength={5}
              value={scopeDescription}
              onChange={(event) => setScopeDescription(event.target.value)}
              placeholder="Ví dụ: Đăng nhập bằng email và mật khẩu"
            />
          </label>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Tài liệu ({sources.documents.length})</legend>
            {sources.documents.map((item) => (
              <label className="flex gap-2 text-sm" key={item.id}>
                <input
                  type="checkbox"
                  checked={selected.has(`document:${item.id}`)}
                  onChange={() => toggle(`document:${item.id}`)}
                />
                {item.name}
              </label>
            ))}
          </fieldset>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">
              Requirement đã đặt chuẩn ({sources.requirements.length})
            </legend>
            {sources.requirements.map((item) => (
              <label className="flex gap-2 text-sm" key={item.version_id}>
                <input
                  type="checkbox"
                  checked={selected.has(`requirement:${item.version_id}`)}
                  onChange={() => toggle(`requirement:${item.version_id}`)}
                />
                {item.title || item.requirement_key}
              </label>
            ))}
          </fieldset>
        </div>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <button
          type="button"
          className="apple-button"
          disabled={busy || scopeDescription.trim().length < 5 || selected.size === 0}
          onClick={run}
        >
          {busy ? "Đang rà soát…" : "Rà soát hồ sơ"}
        </button>
        {result && (
          <div className="space-y-3 border-t border-border pt-4">
            <p className="text-sm">
              Đã rà soát nội dung trong phạm vi bạn chọn. Các đề xuất cần được xác nhận trước khi áp
              dụng.
            </p>
            {(result.suggestions || [])
              .flatMap((batch) => [
                ...(batch.coverage || []).filter((item) => item.status !== "COVERED"),
                ...(batch.findings || []),
              ])
              .map((item, index) => (
                <article
                  className="rounded-lg border border-border p-3"
                  key={`${item.area || item.kind}-${index}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <strong className="text-sm">{item.title || item.area}</strong>
                    <StatusPill value={item.priority || item.status} />
                  </div>
                  <p className="mt-1 text-sm">{item.observation || item.reason || item.gap}</p>
                  {item.requested_detail && (
                    <p className="mt-1 text-sm">Cần bổ sung: {item.requested_detail}</p>
                  )}
                  {(item.evidence_quotes || []).map((quote, index) => (
                    <blockquote
                      className="mt-2 border-l-2 border-border pl-3 text-sm text-ink-muted"
                      key={index}
                    >
                      {quote.quote}
                    </blockquote>
                  ))}
                </article>
              ))}
            <p className="text-xs text-ink-muted">
              Kết quả chỉ dựa trên những tài liệu và yêu cầu bạn đã chọn.
            </p>
          </div>
        )}
      </div>
    </Panel>
  );
}
