import { useCallback, useEffect, useRef, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf, valueLabel } from "../../../lib/testing";
import { LoadingState } from "../../../components/WorkspacePrimitives";

const statusLabel = {
  OPEN: "Đang chờ cập nhật",
  RESOLVED: "Đã giải quyết",
  NOT_APPLICABLE: "Không áp dụng",
  WAIVED: "Đã chấp nhận ngoại lệ",
  SUPERSEDED: "Đã thay thế bởi phiên bản mới",
};

function sourceReferenceLabel(sourceRef) {
  const reference = String(sourceRef || "").trim();
  const businessRule = /^(?:business_rule:?)\s*(\d+)$/i.exec(reference);
  if (businessRule) return `Quy tắc nghiệp vụ ${businessRule[1]}`;
  if (/^AC[-_ ]?\d+$/i.test(reference)) return reference.toUpperCase().replace(/[ _]/g, "-");
  if (/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+\S+/i.test(reference)) return reference;
  return (
    {
      content: "Nội dung yêu cầu",
      actors: "Tác nhân",
      business_rules: "Quy tắc nghiệp vụ",
      acceptance_criteria: "Tiêu chí chấp nhận",
    }[reference] || "Nguồn yêu cầu"
  );
}

function clarificationMessageOf(reason) {
  const code = reason?.response?.data?.detail?.code || reason?.code;
  if (code === "CLARIFICATION_REQUIRES_UPDATED_REQUIREMENT") {
    return "BA cần cập nhật và lưu bản nháp yêu cầu sau khi QA yêu cầu chỉnh sửa trước khi QA xác nhận phiếu.";
  }
  if (code === "CLARIFICATION_VERSION_NOT_EDITABLE") {
    return "Phiên bản yêu cầu này không còn là bản nháp để chỉnh sửa. Hãy tạo phiên bản mới trước khi xử lý phiếu.";
  }
  if (code === "CLARIFICATION_UPDATE_REQUEST_REQUIRED") {
    return "QA cần gửi yêu cầu cập nhật cho đúng phiên bản đang mở trước khi xác nhận phiếu.";
  }
  return messageOf(reason);
}

function itemStatusLabel(item, requirementRevision, requirementVersionId) {
  if (item.status !== "ANSWERED") return statusLabel[item.status] || valueLabel(item.status);
  const requestedVersionId =
    item.change_requested_requirement_version_id || item.requirement_version_id;
  if (
    requestedVersionId !== requirementVersionId ||
    item.change_requested_requirement_revision == null
  ) {
    return "Đã có phản hồi, chờ QA yêu cầu cập nhật";
  }
  return requirementRevision > item.change_requested_requirement_revision
    ? "Đã cập nhật, chờ QA xác nhận"
    : "Đang chờ BA cập nhật bản nháp";
}

export default function RequirementClarificationPanel({
  requirementVersionId,
  requirementStatus,
  requirementRevision,
  ask,
  onRequirementChanged,
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
  const isUpdateRequestedForCurrentVersion = (item) =>
    (item.change_requested_requirement_version_id || item.requirement_version_id) ===
    requirementVersionId;
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
      if (sequence === loadSequence.current) setError(clarificationMessageOf(reason));
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
  }, [canRead, load, requirementRevision, requirementStatus]);
  const perform = async (action) => {
    const requestedVersionId = requirementVersionId;
    setBusy(true);
    setError("");
    try {
      await action();
      if (activeRequirementVersion.current === requestedVersionId) await load();
    } catch (reason) {
      if (activeRequirementVersion.current === requestedVersionId) {
        setError(clarificationMessageOf(reason));
      }
    } finally {
      if (activeRequirementVersion.current === requestedVersionId) setBusy(false);
    }
  };
  const requestChanges = async (item) => {
    await ask({
      title: "Yêu cầu BA cập nhật Requirement",
      description:
        requirementStatus === "IN_REVIEW"
          ? "Requirement sẽ trở về bản nháp. Ghi rõ tiêu chí cần sửa để BA cập nhật đúng nội dung trong phiếu."
          : "Ghi rõ tiêu chí cần sửa để BA cập nhật bản nháp theo phản hồi của phiếu.",
      confirmLabel: "Gửi yêu cầu cập nhật",
      fields: [
        {
          name: "review_note",
          label: "Nội dung cần BA cập nhật",
          required: true,
          minLength: 2,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        setBusy(true);
        setError("");
        try {
          await testingApi.requestRequirementClarificationChanges(item._id, {
            expected_revision: item.revision,
            expected_requirement_revision: requirementRevision,
            review_note: answer.review_note.trim(),
          });
          await onRequirementChanged?.();
          if (activeRequirementVersion.current === requirementVersionId) await load();
        } catch (reason) {
          const message = clarificationMessageOf(reason);
          setError(message);
          throw new Error(message);
        } finally {
          setBusy(false);
        }
      },
    });
  };
  if (!requirementVersionId || !canRead) return null;
  return (
    <section className="workspace-panel space-y-4 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">Phiếu làm rõ yêu cầu</h2>
          <p className="mt-1 text-sm text-ink-muted">
            QA tạo phiếu để BA trả lời. Sau khi có phản hồi, QA yêu cầu chỉnh sửa; BA cập nhật bản
            nháp rồi QA đối chiếu nội dung mới để xác nhận.
          </p>
        </div>
        {canReview && (
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={() =>
              perform(async () => {
                await testingApi.createClarificationsFromReview(requirementVersionId);
              })
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
                <strong>{itemStatusLabel(item, requirementRevision, requirementVersionId)}</strong>
                {item.source_ref && (
                  <span className="text-xs text-ink-faint">
                    Nguồn: {sourceReferenceLabel(item.source_ref)}
                  </span>
                )}
              </div>
              {item.source_quote && (
                <blockquote className="mt-3 rounded-control bg-surface-quiet px-3 py-2 text-sm text-ink-muted">
                  {item.source_quote}
                </blockquote>
              )}
              <p className="mt-3 text-sm font-medium text-ink">{item.question}</p>
              <p className="mt-1 text-sm text-ink-muted">Lý do: {item.reason}</p>
              {item.answer && (
                <p className="mt-3 text-sm text-ink-muted">Phản hồi: {item.answer}</p>
              )}
              {item.change_request_note && (
                <p className="mt-2 text-sm text-ink-muted">
                  QA yêu cầu cập nhật: {item.change_request_note}
                </p>
              )}
              {canAnswer && item.status === "OPEN" && (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    aria-label="Câu trả lời cho phiếu làm rõ"
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
              {canReview &&
                ["DRAFT", "IN_REVIEW"].includes(requirementStatus) &&
                item.status === "ANSWERED" &&
                (!isUpdateRequestedForCurrentVersion(item) ||
                  item.change_requested_requirement_revision == null ||
                  requirementRevision > item.change_requested_requirement_revision) && (
                  <button
                    type="button"
                    className="secondary-button mt-3"
                    disabled={busy}
                    onClick={() => void requestChanges(item)}
                  >
                    Yêu cầu BA cập nhật
                  </button>
                )}
              {canReview &&
                item.status === "ANSWERED" &&
                isUpdateRequestedForCurrentVersion(item) &&
                item.change_requested_requirement_revision != null &&
                requirementRevision > item.change_requested_requirement_revision && (
                  <div className="mt-3 flex flex-col gap-2">
                    <textarea
                      aria-label="Trích dẫn yêu cầu để xác nhận giải quyết"
                      className="apple-input min-h-16 w-full"
                      value={evidence[item._id] || ""}
                      onChange={(event) =>
                        setEvidence({ ...evidence, [item._id]: event.target.value })
                      }
                      placeholder={`Trích dẫn bằng chứng trong ${item.source_ref || "nguồn của phiếu"}`}
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
                      Xác nhận giải quyết
                    </button>
                  </div>
                )}
              {canReview &&
                item.status === "ANSWERED" &&
                isUpdateRequestedForCurrentVersion(item) &&
                item.change_requested_requirement_revision != null &&
                requirementRevision <= item.change_requested_requirement_revision && (
                  <p className="mt-3 text-sm text-ink-muted">
                    Chờ BA sửa nội dung nguồn và lưu bản nháp trước khi QA xác nhận bằng chứng.
                  </p>
                )}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
