import { useRef, useState } from "react";
import Link from "next/link";
import { Panel, ErrorState } from "./WorkspacePrimitives";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { testingApi } from "../services/testing.service";
import { docText, messageOf } from "../lib/testing";

export default function ManualTestGenerationPanel({ projectId, requirements, mode, onSaved }) {
  const [versionId, setVersionId] = useState("");
  const [instruction, setInstruction] = useState("");
  const [limit, setLimit] = useState(10);
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inFlight = useRef(false);
  const source = requirements.find((item) => item.current_version_id === versionId);
  const generate = async () => {
    if (inFlight.current || !versionId) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    setPreview(null);
    try {
      const payload = { instruction, max_cases: limit, preview_only: true };
      if (mode === "scenarios") {
        const result = await testingApi.generateScenarios(versionId, payload);
        setPreview(result);
        setSelected((result.items || []).map((_, index) => index));
      } else {
        const result = await testingApi.generateTestCases(versionId, payload);
        setPreview(result);
        setSelected(
          (result.items || []).flatMap((item, index) =>
            item.similar_cases?.length ? [] : [index],
          ),
        );
      }
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };
  const save = async () => {
    if (inFlight.current || !selected.length) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const items = selected.map((index) => preview.items[index].draft);
      if (mode === "scenarios") {
        await testingApi.createGeneratedScenarioDrafts(projectId, items);
      } else {
        await testingApi.createGeneratedTestDrafts(projectId, items);
      }
      setPreview(null);
      setSelected([]);
      setNotice(
        mode === "scenarios"
          ? `Đã lưu ${items.length} kịch bản nháp để chỉnh sửa và duyệt.`
          : `Đã lưu ${items.length} ca nháp để chỉnh sửa và duyệt.`,
      );
      await onSaved();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };
  return (
    <Panel
      title={mode === "scenarios" ? "Đề xuất kịch bản bằng AI" : "Đề xuất ca kiểm thử bằng AI"}
    >
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        {notice && (
          <p role="status" className="text-sm">
            {notice}
          </p>
        )}
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_9rem_auto] md:items-end">
          <label className="field-label">
            Yêu cầu đã duyệt
            <select
              className="apple-input mt-2"
              disabled={busy}
              value={versionId}
              onChange={(event) => {
                setVersionId(event.target.value);
                setPreview(null);
                setSelected([]);
                setNotice("");
              }}
            >
              <option value="">Chọn yêu cầu</option>
              {requirements.map((item) => (
                <option key={item._id} value={item.current_version_id}>
                  {item.requirement_key} · {item.current_version?.title || item.title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Số lượng tối đa
            <input
              className="apple-input mt-2"
              type="number"
              min="1"
              max="100"
              value={limit}
              disabled={busy}
              onChange={(event) => setLimit(Number(event.target.value))}
            />
          </label>
          <button
            className="secondary-button border-violet-300 text-violet-800"
            type="button"
            disabled={busy || !versionId || limit < 1 || limit > 100}
            onClick={generate}
          >
            {busy ? "Đang xử lý" : "Tạo đề xuất"}
          </button>
        </div>
        <label className="field-label block">
          Yêu cầu bổ sung cho AI
          <textarea
            className="apple-input mt-2 min-h-20"
            value={instruction}
            disabled={busy}
            onChange={(event) => setInstruction(event.target.value)}
          />
        </label>
        {source && (
          <Link
            className="text-sm text-brand underline"
            href={`/du-an/${projectId}/yeu-cau/${source._id}`}
          >
            Mở yêu cầu nguồn
          </Link>
        )}
        {preview && (
          <div className="space-y-3">
            <ContentOriginBadge origin="ai_generated" />
            {!preview.items?.length && (
              <p className="text-sm text-ink-muted">Chưa có đề xuất phù hợp với nguồn đã chọn.</p>
            )}
            {preview.items?.map((item, index) => (
              <div key={index} className="space-y-2 rounded-control border border-border p-4">
                <label className="flex items-start gap-3 font-medium">
                  <input
                    className="mt-1"
                    type="checkbox"
                    checked={selected.includes(index)}
                    disabled={busy}
                    onChange={(event) =>
                      setSelected((current) =>
                        event.target.checked
                          ? [...current, index]
                          : current.filter((value) => value !== index),
                      )
                    }
                  />
                  {item.draft.title}
                </label>
                <p className="text-sm">
                  {mode === "scenarios" ? item.draft.objective : docText(item.draft.objective_doc)}
                </p>
                {item.similar_cases?.length > 0 && (
                  <p className="text-sm text-ink-muted">
                    Cần đối chiếu với:{" "}
                    {item.similar_cases.map((candidate) => candidate.title).join("; ")}
                  </p>
                )}
                <details className="text-sm">
                  <summary className="cursor-pointer">
                    {mode === "scenarios" ? "Luồng kịch bản và căn cứ" : "Bước kiểm thử và căn cứ"}
                  </summary>
                  {mode === "scenarios" ? (
                    <div className="mt-3 space-y-2">
                      {item.draft.business_flow && <p>{item.draft.business_flow}</p>}
                      {item.draft.expected_outcome && (
                        <p className="text-ink-muted">
                          Kết quả mong đợi: {item.draft.expected_outcome}
                        </p>
                      )}
                      <p className="text-ink-muted">
                        Tiêu chí liên quan:{" "}
                        {(item.draft.acceptance_criterion_ids || []).join(", ") || "Chưa liên kết"}
                      </p>
                    </div>
                  ) : (
                    <ol className="mt-3 list-decimal space-y-2 pl-5">
                      {item.draft.steps?.map((step) => (
                        <li key={step.id}>
                          {docText(step.action_doc)}
                          <p className="text-ink-muted">
                            Kết quả mong đợi: {docText(step.expected_doc)}
                          </p>
                        </li>
                      ))}
                    </ol>
                  )}
                  {item.evidence_quotes?.map((quote, quoteIndex) => (
                    <blockquote key={quoteIndex} className="mt-3 border-l-2 border-violet-300 pl-3">
                      {quote.quote}
                    </blockquote>
                  ))}
                </details>
              </div>
            ))}
            {preview.items?.length > 0 && (
              <button
                type="button"
                className="apple-button"
                disabled={busy || !selected.length}
                onClick={save}
              >
                {busy
                  ? "Đang lưu"
                  : `Lưu ${selected.length} ${mode === "scenarios" ? "kịch bản" : "ca kiểm thử"} nháp đã chọn`}
              </button>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
