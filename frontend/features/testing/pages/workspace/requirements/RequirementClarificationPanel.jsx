import { useCallback, useEffect, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf } from "../../../lib/testing";

const statusLabel = {
  OPEN: "Đang chờ BA làm rõ",
  ANSWERED: "Đã có trả lời, chờ QA xác nhận",
  RESOLVED: "Đã giải quyết",
  NOT_APPLICABLE: "Không áp dụng",
  WAIVED: "Đã chấp nhận ngoại lệ",
  SUPERSEDED: "Đã thay thế bởi phiên bản mới",
};

export default function RequirementClarificationPanel({ requirementVersionId, role }) {
  const [items, setItems] = useState([]);
  const [answers, setAnswers] = useState({});
  const [evidence, setEvidence] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canReview = role === "QA";
  const canAnswer = role === "BA";
  const load = useCallback(async () => {
    if (!requirementVersionId) return;
    try {
      setItems(await testingApi.listRequirementClarifications(requirementVersionId));
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [requirementVersionId]);
  useEffect(() => {
    void load();
  }, [load]);
  const perform = async (action) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  if (!requirementVersionId) return null;
  return (
    <section className="workspace-panel space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Phiếu làm rõ Requirement</h2>
          <p className="mt-1 text-sm text-slate-600">
            Câu trả lời không tự sửa Requirement. BA cập nhật bản nháp, QA chỉ xác nhận khi trích
            dẫn đã xuất hiện trong phiên bản phù hợp.
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
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {items.length === 0 ? (
        <p className="text-sm text-slate-600">Chưa có Phiếu làm rõ cho phiên bản này.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item._id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong>{statusLabel[item.status] || item.status}</strong>
                {item.source_ref && (
                  <span className="text-xs text-slate-500">Nguồn: {item.source_ref}</span>
                )}
              </div>
              <p className="mt-3 text-sm font-medium text-slate-900">{item.question}</p>
              <p className="mt-1 text-sm text-slate-600">Lý do: {item.reason}</p>
              {item.answer && (
                <p className="mt-3 text-sm text-slate-700">Trả lời BA: {item.answer}</p>
              )}
              {canAnswer && item.status === "OPEN" && (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    className="apple-input min-h-20 w-full"
                    value={answers[item._id] || ""}
                    onChange={(event) => setAnswers({ ...answers, [item._id]: event.target.value })}
                    placeholder="Trả lời để làm căn cứ cập nhật bản nháp Requirement"
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
                    className="apple-input min-h-16 w-full"
                    value={evidence[item._id] || ""}
                    onChange={(event) =>
                      setEvidence({ ...evidence, [item._id]: event.target.value })
                    }
                    placeholder="Trích dẫn đã xuất hiện trong Requirement phiên bản này"
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
      )}
    </section>
  );
}
