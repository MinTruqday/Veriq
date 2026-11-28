import { useEffect, useRef, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { Panel, ErrorState } from "./WorkspacePrimitives";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { testingApi } from "../services/testing.service";
import { docText, isApprovedCurrentRequirement, messageOf, valueLabel } from "../lib/testing";

function assessmentLabel(value) {
  return valueLabel(value || "unassessed");
}

export default function ManualTestGenerationPanel({
  projectId,
  requirements,
  onSaved,
  canGenerate = false,
}) {
  const [versionId, setVersionId] = useState("");
  const [instruction, setInstruction] = useState("");
  const [limit, setLimit] = useState(10);
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inFlight = useRef(false);
  const saveIdempotencyKey = useRef(null);
  useEffect(() => {
    setVersionId("");
    setPreview(null);
    setSelected([]);
  }, [projectId]);
  const approvedRequirements = requirements.filter(isApprovedCurrentRequirement);
  const source = approvedRequirements.find((item) => item.current_version_id === versionId);
  const generate = async () => {
    if (inFlight.current || !versionId || !canGenerate) return;
    inFlight.current = true;
    setBusy(true);
    setBusyAction("generate");
    setError("");
    setNotice("");
    setPreview(null);
    setSelected([]);
    saveIdempotencyKey.current = null;
    try {
      const payload = {
        instruction,
        max_cases: limit,
        preview_only: true,
      };
      const result = await testingApi.generateTestCases(versionId, payload);
      setPreview(result);
      const eligibleIndexes = (result.items || []).flatMap((item, index) =>
        item.similar_cases?.length ? [] : [index],
      );
      setSelected(eligibleIndexes);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      inFlight.current = false;
      setBusy(false);
      setBusyAction("");
    }
  };
  const save = async () => {
    if (inFlight.current || !selected.length) return;
    inFlight.current = true;
    setBusy(true);
    setBusyAction("save");
    setError("");
    try {
      const items = selected.map((index) => preview.items[index].draft);
      saveIdempotencyKey.current ||= window.crypto.randomUUID();
      await testingApi.createGeneratedTestDrafts(projectId, items, saveIdempotencyKey.current);
      saveIdempotencyKey.current = null;
      setPreview(null);
      setSelected([]);
      setNotice(`Đã lưu ${items.length} ca nháp để chỉnh sửa và duyệt`);
      await onSaved();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      inFlight.current = false;
      setBusy(false);
      setBusyAction("");
    }
  };
  return (
    <Panel title="Tạo ca kiểm thử bằng AI">
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
                saveIdempotencyKey.current = null;
                setNotice("");
              }}
            >
              <option value="">Chọn yêu cầu</option>
              {approvedRequirements.map((item) => (
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
            className="apple-button"
            type="button"
            disabled={!canGenerate || busy || !versionId || limit < 1 || limit > 100}
            aria-busy={busy}
            onClick={generate}
          >
            {busy ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
            ) : (
              <Sparkles aria-hidden="true" size={17} />
            )}
            {busyAction === "generate"
              ? "Đang tạo bản xem trước…"
              : busyAction === "save"
                ? "Đang lưu bản nháp…"
                : "Tạo bản xem trước bằng AI"}
          </button>
        </div>
        {!canGenerate && (
          <p className="-mt-2 text-sm text-warning" role="status">
            Bạn chưa được cấp quyền tạo ca kiểm thử bằng AI trong dự án này
          </p>
        )}
        {!approvedRequirements.length ? (
          <p className="-mt-2 text-sm text-ink-muted">
            Chưa có yêu cầu đã duyệt để AI tạo bản xem trước
          </p>
        ) : (
          !versionId && (
            <p className="-mt-2 text-sm text-ink-muted">Chọn yêu cầu đã duyệt để bật gợi ý</p>
          )
        )}
        {source && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
            <p className="min-w-0 truncate text-sm text-ink-muted">
              Nguồn đang chọn: {source.requirement_key} ·{" "}
              {source.current_version?.title || source.title}
            </p>
            <Link
              className="secondary-button shrink-0"
              href={`/du-an/${projectId}/yeu-cau/${source._id}`}
            >
              Mở yêu cầu nguồn
            </Link>
          </div>
        )}
        {source && !(source.current_version?.acceptance_criteria || []).length && (
          <p className="text-sm text-ink-muted">
            AI sẽ dựa trên nội dung yêu cầu và trích dẫn nội dung làm căn cứ
          </p>
        )}
        <label className="field-label block">
          Yêu cầu bổ sung cho AI
          <textarea
            className="apple-input mt-2 min-h-20"
            value={instruction}
            disabled={busy}
            onChange={(event) => setInstruction(event.target.value)}
          />
        </label>
        {preview && (
          <div className="space-y-3">
            <ContentOriginBadge origin="ai_generated" />
            {preview.warnings?.length > 0 && (
              <ul className="rounded-control border border-border bg-surface-quiet px-4 py-3 text-sm text-ink-muted">
                {preview.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
            {!preview.items?.length && (
              <p className="text-sm text-ink-muted">Chưa có đề xuất phù hợp với nguồn đã chọn</p>
            )}
            {preview.items?.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-border bg-surface-quiet px-3 py-2">
                <p className="text-sm text-ink-muted" aria-live="polite">
                  Đã chọn {selected.length}/{preview.items.length} đề xuất
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={busy || selected.length === preview.items.length}
                    onClick={() => {
                      saveIdempotencyKey.current = null;
                      setSelected(preview.items.map((_, index) => index));
                    }}
                  >
                    Chọn tất cả
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={busy || !selected.length}
                    onClick={() => {
                      saveIdempotencyKey.current = null;
                      setSelected([]);
                    }}
                  >
                    Bỏ chọn
                  </button>
                </div>
              </div>
            )}
            {preview.items?.map((item, index) => (
              <div key={index} className="space-y-2 rounded-control border border-border p-4">
                <label className="flex items-start gap-3 font-medium">
                  <input
                    className="mt-1"
                    type="checkbox"
                    checked={selected.includes(index)}
                    disabled={busy}
                    onChange={(event) => {
                      saveIdempotencyKey.current = null;
                      setSelected((current) =>
                        event.target.checked
                          ? [...current, index]
                          : current.filter((value) => value !== index),
                      );
                    }}
                  />
                  {item.draft.title}
                </label>
                <p className="text-sm">{docText(item.draft.objective_doc)}</p>
                <dl className="grid gap-x-6 gap-y-2 text-xs text-ink-muted sm:grid-cols-2">
                  <div>
                    <dt>Nhóm kiểm thử</dt>
                    <dd className="mt-0.5 font-medium text-ink">
                      {valueLabel(item.draft.category || item.draft.type || "Chưa phân loại")}
                    </dd>
                  </div>
                  <div>
                    <dt>Ưu tiên</dt>
                    <dd className="mt-0.5 font-medium text-ink">
                      {assessmentLabel(item.draft.priority)}
                    </dd>
                  </div>
                </dl>
                {item.similar_cases?.length > 0 && (
                  <p className="text-sm text-ink-muted">
                    Cần đối chiếu với:{" "}
                    {item.similar_cases.map((candidate) => candidate.title).join("; ")}
                  </p>
                )}
                <details className="text-sm">
                  <summary className="cursor-pointer">Bước kiểm thử và căn cứ</summary>
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
                  {item.evidence_quotes?.map((quote, quoteIndex) => (
                    <blockquote
                      key={`${quote.evidence_ref || "source"}-${quoteIndex}`}
                      className="mt-3 border-l-2 border-violet-300 pl-3"
                    >
                      <p>{quote.quote}</p>
                      {source && quote.evidence_ref && (
                        <Link
                          className="mt-1 inline-flex text-xs font-medium text-brand underline"
                          href={
                            source.current_version?.acceptance_criteria?.some(
                              (criterion) => criterion._id === quote.evidence_ref,
                            )
                              ? `/du-an/${projectId}/yeu-cau/${source._id}?acceptanceCriterionId=${encodeURIComponent(quote.evidence_ref)}#acceptance-criterion-${encodeURIComponent(quote.evidence_ref)}`
                              : `/du-an/${projectId}/yeu-cau/${source._id}`
                          }
                        >
                          {source.current_version?.acceptance_criteria?.some(
                            (criterion) => criterion._id === quote.evidence_ref,
                          )
                            ? "Mở đúng tiêu chí nguồn"
                            : "Mở yêu cầu nguồn"}
                        </Link>
                      )}
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
                {busy ? "Đang lưu" : `Lưu ${selected.length} ca kiểm thử đã chọn thành bản nháp`}
              </button>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
