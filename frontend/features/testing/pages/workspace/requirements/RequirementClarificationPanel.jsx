import { useCallback, useEffect, useRef, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf, valueLabel } from "../../../lib/testing";
import { LoadingState } from "../../../components/WorkspacePrimitives";

const statusLabel = {
  OPEN: "Đang chờ BA làm rõ",
  ANSWERED: "Đã có trả lời, chờ QA xác nhận",
  RESOLVED: "Đã giải quyết",
  NOT_APPLICABLE: "Không áp dụng",
  WAIVED: "Đã chấp nhận ngoại lệ",
  SUPERSEDED: "Đã thay thế bởi phiên bản mới",
};

export default function RequirementClarificationPanel({
  requirementVersionId,
  role,
  roles,
  permissions = [],
}) {
  const [items, setItems] = useState([]);
  const [answers, setAnswers] = useState({});
  const [evidence, setEvidence] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const loadSequence = useRef(0);
  const activeRequirementVersion = useRef(requirementVersionId);
  activeRequirementVersion.current = requirementVersionId;
  const canRead = permissions.includes("requirement.read");
  const memberRoles = Array.isArray(roles) && roles.length ? roles : [role].filter(Boolean);
  const canReview = memberRoles.includes("QA") && permissions.includes("requirement.review");
  const canAnswer = memberRoles.includes("BA") && permissions.includes("requirement.update");
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    if (!requirementVersionId || !canRead) return;
    setLoading(true);
    try {
      const result = await testingApi.listRequirementClarifications(requirementVersionId);
      if (sequence !== loadSequence.current) return;
      setItems(result);
      setError("");
    } catch (reason) {
      if (sequence === loadSequence.current) setError(messageOf(reason));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [canRead, requirementVersionId]);
  useEffect(() => {
    setItems([]);
    setAnswers({});
    setEvidence({});
    setError("");
    setBusy(false);
    setLoading(true);
    if (!canRead) {
      loadSequence.current += 1;
      return undefined;
    }
    void load();
    return () => {
      loadSequence.current += 1;
    };
  }, [canRead, load]);
  const perform = async (action) => {
    const requestedVersionId = requirementVersionId;
    setBusy(true);
    setError("");
    try {
      await action();
      if (activeRequirementVersion.current === requestedVersionId) await load();
    } catch (reason) {
      if (activeRequirementVersion.current === requestedVersionId) setError(messageOf(reason));
    } finally {
      if (activeRequirementVersion.current === requestedVersionId) setBusy(false);
    }
  };
  if (!requirementVersionId || !canRead) return null;
  return (
    <section className="workspace-panel space-y-4 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Phiếu làm rõ yêu cầu</h2>
          <p className="mt-1 text-sm text-ink-muted">
            BA cập nhật yêu cầu; QA xác nhận khi phiên bản mới có dẫn chứng.
          </p>
        </div>
        {canReview && (
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={() =>
              perform(() => testingApi.createClarificationsFromReview(requirementVersionId))
            }
          >
            Rà soát và tạo phiếu
          </button>
        )}
      </div>
      {error && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
          <span>{error}</span>
          <button
            className="secondary-button"
            type="button"
            disabled={loading}
            onClick={() => void load()}
          >
            Tải lại
          </button>
        </div>
      )}
      {loading ? (
        <LoadingState />
      ) : items.length === 0 && !error ? (
        <p className="text-sm text-ink-muted">Chưa có Phiếu làm rõ cho phiên bản này</p>
      ) : items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item._id} className="rounded-panel border border-border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong>{statusLabel[item.status] || valueLabel(item.status)}</strong>
                {item.source_ref && (
                  <span className="text-xs text-ink-faint">Nguồn: {item.source_ref}</span>
                )}
              </div>
              <p className="mt-3 text-sm font-medium text-ink">{item.question}</p>
              <p className="mt-1 text-sm text-ink-muted">Lý do: {item.reason}</p>
              {item.answer && (
                <p className="mt-3 text-sm text-ink-muted">Trả lời BA: {item.answer}</p>
              )}
              {canAnswer && item.status === "OPEN" && (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    aria-label="Câu trả lời của BA cho phiếu làm rõ"
                    className="apple-input min-h-20 w-full"
                    value={answers[item._id] || ""}
                    onChange={(event) => setAnswers({ ...answers, [item._id]: event.target.value })}
                    placeholder="Trả lời để làm căn cứ cập nhật bản nháp yêu cầu"
                  />
                  <button
                    type="button"
                    className="apple-button self-start"
                    disabled={busy || !(answers[item._id] || "").trim()}
                    onClick={() =>
                      perform(() =>
                        testingApi.answerRequirementClarification(item._id, {
                          expected_revision: item.revision,
                          answer: answers[item._id].trim(),
                        }),
                      )
                    }
                  >
                    Gửi trả lời
                  </button>
                </div>
              )}
              {canReview && item.status === "ANSWERED" && (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    aria-label="Trích dẫn yêu cầu để QA xác nhận giải quyết"
                    className="apple-input min-h-16 w-full"
                    value={evidence[item._id] || ""}
                    onChange={(event) =>
                      setEvidence({ ...evidence, [item._id]: event.target.value })
                    }
                    placeholder="Trích dẫn đã xuất hiện trong phiên bản yêu cầu này"
                  />
                  <button
                    type="button"
                    className="apple-button self-start"
                    disabled={busy || !(evidence[item._id] || "").trim()}
                    onClick={() =>
                      perform(() =>
                        testingApi.resolveRequirementClarification(item._id, {
                          expected_revision: item.revision,
                          requirement_version_id: requirementVersionId,
                          evidence_quote: evidence[item._id].trim(),
                        }),
                      )
                    }
                  >
                    QA xác nhận giải quyết
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
