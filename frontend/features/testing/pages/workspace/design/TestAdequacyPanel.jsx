import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf, valueLabel } from "../../../lib/testing";
import { LoadingState, useActionDialog } from "../../../components/WorkspacePrimitives";

const labels = {
  UNASSESSED: "Chưa đánh giá",
  COVERED_PENDING_REVIEW: "Đã bao phủ, chờ QA rà soát",
  VERIFIED_COVERED: "Đã xác minh bao phủ",
  MISSING_INFORMATION: "Thiếu thông tin",
  NOT_APPLICABLE: "Không áp dụng",
  WAIVED: "Đã chấp nhận rủi ro",
};

const assessmentLabels = {
  DRAFT: "Chưa đủ đảm bảo",
  IN_REVIEW: "Đang QA rà soát",
  ASSURED: "Đủ đảm bảo",
  CONDITIONAL: "Đảm bảo có điều kiện",
  SUPERSEDED: "Đã thay thế",
};

function sourceReferenceLabel(item) {
  const reference = String(item.source_ref || "");
  if (item.source_type === "business_rule") {
    const businessRule = /^(?:business_rule:)?(\d+)$/i.exec(reference);
    return businessRule ? `Quy tắc nghiệp vụ ${businessRule[1]}` : "Quy tắc nghiệp vụ";
  }
  if (item.source_type === "acceptance_criterion") {
    return /^AC[-_ ]?\d+$/i.test(reference) ? reference : "Tiêu chí chấp nhận";
  }
  if (item.source_type === "api_operation") {
    return /^[A-Z]+\s+\//.test(reference) ? reference : "Thao tác API";
  }
  if (item.source_type === "requirement_version") return "Nội dung yêu cầu";
  return "Nguồn yêu cầu";
}

function waiverOwnerLabel(ownerId, members) {
  if (!ownerId) return "Chưa xác định";
  const member = members.find((item) => item.user_id === ownerId);
  if (!member) return "Thành viên dự án";
  const candidates = [member.user?.full_name, member.user?.email, member.user_label];
  return (
    candidates.find((value) => value && value !== ownerId && value !== member.user_id) ||
    "Thành viên dự án"
  );
}

function decisionActorLabel(actorId, members) {
  if (!actorId) return "Thành viên dự án";
  const member = members.find((item) => item.user_id === actorId);
  if (!member) return "Thành viên dự án";
  const candidates = [member.user?.full_name, member.user?.email, member.user_label];
  return (
    candidates.find((value) => value && value !== actorId && value !== member.user_id) ||
    "Thành viên dự án"
  );
}

export default function TestAdequacyPanel({
  requirementVersionId,
  members = [],
  canDecide = false,
  canCreateClarification = false,
  canApprove = false,
  canSubmit = false,
}) {
  const { ask, dialog } = useActionDialog();
  const [assessment, setAssessment] = useState(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const loadSequence = useRef(0);
  const activeRequirementVersion = useRef(requirementVersionId);
  activeRequirementVersion.current = requirementVersionId;
  const load = useCallback(async () => {
    if (!requirementVersionId) return;
    const sequence = ++loadSequence.current;
    setError("");
    setLoading(true);
    try {
      const result = await testingApi.getTestAdequacy(requirementVersionId);
      if (sequence === loadSequence.current) setAssessment(result);
    } catch (reason) {
      if (sequence === loadSequence.current) setError(messageOf(reason));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [requirementVersionId]);
  useEffect(() => {
    setAssessment(null);
    setFilter("");
    setError("");
    void load();
    return () => {
      loadSequence.current += 1;
    };
  }, [load]);
  const items = useMemo(
    () => (assessment?.coverage_items || []).filter((item) => !filter || item.status === filter),
    [assessment, filter],
  );
  const update = async (work) => {
    const requestedVersionId = requirementVersionId;
    setBusy(true);
    setError("");
    try {
      const result = await work();
      if (activeRequirementVersion.current === requestedVersionId) setAssessment(result);
    } catch (reason) {
      if (activeRequirementVersion.current === requestedVersionId) setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  const decide = async (item, status) => {
    const waiver = status === "WAIVED";
    const value = await ask({
      title: waiver ? "Chấp nhận có điều kiện" : "Xác nhận không áp dụng",
      description: waiver
        ? "Quyết định chấp nhận rủi ro chỉ còn hiệu lực đến ngày đã chọn; hồ sơ sẽ cần rà soát lại khi hết hạn"
        : "QA xác nhận Nghĩa vụ này không áp dụng cho yêu cầu hiện tại",
      confirmLabel: "Xác nhận quyết định",
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
        ...(waiver
          ? [
              {
                name: "waiver_owner_id",
                label: "Email người chịu trách nhiệm",
                required: true,
                type: "email",
              },
              {
                name: "waiver_review_at",
                label: "Ngày rà soát lại",
                required: true,
                type: "date",
              },
              {
                name: "waiver_expires_at",
                label: "Hạn hiệu lực waiver",
                required: true,
                type: "date",
              },
            ]
          : []),
      ],
    });
    if (!value) return;
    await update(() =>
      testingApi.decideTestAdequacyItem(assessment._id, item.coverage_item_id, {
        expected_revision: assessment.revision,
        status,
        ...value,
      }),
    );
  };
  const createClarification = async (item) => {
    const requestedVersionId = requirementVersionId;
    const requestedAssessmentId = assessment?._id;
    const value = await ask({
      title: "Tạo Phiếu làm rõ",
      description: "Phiếu gắn với đúng Nghĩa vụ này và chỉ BA mới có thể trả lời",
      confirmLabel: "Tạo phiếu",
      fields: [
        {
          name: "question",
          label: "Câu hỏi cần làm rõ",
          required: true,
          multiline: true,
          autoFocus: true,
        },
        { name: "reason", label: "Lý do cần làm rõ", required: true, multiline: true },
      ],
    });
    if (!value) return;
    setBusy(true);
    setError("");
    try {
      const clarification = await testingApi.createRequirementClarification(requirementVersionId, {
        ...value,
        coverage_item_id: item.coverage_item_id,
        source_ref: item.source_ref,
        source_quote: item.source_quote,
      });
      const result = await testingApi.decideTestAdequacyItem(
        assessment._id,
        item.coverage_item_id,
        {
          expected_revision: assessment.revision,
          status: "MISSING_INFORMATION",
          reason: value.reason,
          clarification_id: clarification._id,
        },
      );
      if (
        activeRequirementVersion.current === requestedVersionId &&
        assessment?._id === requestedAssessmentId
      ) {
        setAssessment(result);
      }
    } catch (reason) {
      if (activeRequirementVersion.current === requestedVersionId) setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  const source = (item) => (
    <>
      <div className="font-medium text-ink">{sourceReferenceLabel(item)}</div>
      {item.source_quote && <div className="mt-1 max-w-sm text-ink-muted">{item.source_quote}</div>}
    </>
  );
  const linkedTests = (item) =>
    item.test_case_versions?.length
      ? item.test_case_versions.map((test) => (
          <div key={test.id} className="mb-2 last:mb-0">
            <div className="font-medium text-ink">
              {test.key} {test.title}
            </div>
            <div className="text-ink-muted">
              {test.techniques?.join(", ") || "Chưa chọn kỹ thuật"}
            </div>
            {!test.assurance_evidence_complete && (
              <div className="mt-1 text-warning">
                {test.assurance_evidence_gaps?.length
                  ? test.assurance_evidence_gaps.join(" · ")
                  : "Ca này chưa đủ căn cứ để chứng minh Nghĩa vụ"}
              </div>
            )}
          </div>
        ))
      : "Chưa có ca kiểm thử hiệu lực";
  const challenges = (item) => {
    const values =
      item.test_case_versions?.flatMap((test) => test.challenge_hypotheses || []) || [];
    const evidence =
      item.test_case_versions?.flatMap((test) =>
        (test.evidence_quotes || []).map((entry) => ({
          key: `${test.id}:${entry.evidence_ref}`,
          testKey: test.key,
          quote: entry.quote,
        })),
      ) || [];
    return (
      <div className="space-y-3">
        <div>
          <p className="text-xs font-medium text-ink">Trích dẫn trong ca kiểm thử</p>
          {evidence.length ? (
            evidence.map((entry) => (
              <p className="mt-1 break-words" key={entry.key}>
                {entry.testKey}: “{entry.quote}”
              </p>
            ))
          ) : (
            <p className="mt-1">Chưa có trích dẫn trong ca kiểm thử</p>
          )}
        </div>
        <div>
          <p className="text-xs font-medium text-ink">Giả thuyết phản chứng</p>
          {values.length ? (
            values.map((challenge, index) => (
              <p
                className="mt-1 break-words"
                key={`${challenge.technique || "challenge"}:${index}`}
              >
                {challenge.hypothetical_fault}
              </p>
            ))
          ) : (
            <p className="mt-1">Chưa có giả thuyết phản chứng</p>
          )}
        </div>
      </div>
    );
  };
  const decision = (item) => (
    <>
      <div className="whitespace-pre-wrap break-words">
        {item.decision?.reason || "Chưa có quyết định"}
      </div>
      {item.decision?.decided_at && (
        <div className="mt-1 text-xs text-ink-muted">
          Quyết định bởi {decisionActorLabel(item.decision.decided_by, members)} ·{" "}
          {new Date(item.decision.decided_at).toLocaleString("vi-VN")}
        </div>
      )}
      {item.decision?.clarification_id && (
        <div className="mt-1 text-xs text-ink-muted">Đã liên kết phiếu làm rõ</div>
      )}
      {item.status === "WAIVED" && (
        <div className="mt-2 text-xs leading-5 text-ink-muted">
          <div>Phụ trách {waiverOwnerLabel(item.decision?.waiver_owner_id, members)}</div>
          <div>
            Rà soát lại{" "}
            {item.decision?.waiver_review_at
              ? new Date(item.decision.waiver_review_at).toLocaleDateString("vi-VN")
              : "Chưa có"}
          </div>
          <div>
            Hết hạn{" "}
            {item.decision?.waiver_expires_at
              ? new Date(item.decision.waiver_expires_at).toLocaleDateString("vi-VN")
              : "Chưa có"}
          </div>
          {item.decision?.waiver_expired_at && <div>Chấp nhận có điều kiện đã hết hạn</div>}
        </div>
      )}
    </>
  );
  const actions = (item) => {
    const canChangeItem = canDecide || canCreateClarification;
    if (!canChangeItem || ["ASSURED", "CONDITIONAL", "SUPERSEDED"].includes(assessment.status))
      return null;
    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {canCreateClarification && (
          <button
            className="secondary-button text-xs"
            disabled={busy}
            type="button"
            onClick={() => createClarification(item)}
          >
            Tạo Phiếu làm rõ
          </button>
        )}
        {canDecide && (
          <>
            <button
              className="secondary-button text-xs"
              disabled={busy}
              type="button"
              onClick={() => decide(item, "NOT_APPLICABLE")}
            >
              Không áp dụng
            </button>
            <button
              className="secondary-button text-xs"
              disabled={busy}
              type="button"
              onClick={() => decide(item, "WAIVED")}
            >
              Chấp nhận rủi ro
            </button>
          </>
        )}
      </div>
    );
  };
  if (!requirementVersionId) return null;
  return (
    <>
      <section className="space-y-5">
        <div className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-[22px] font-semibold tracking-[-0.025em] text-ink">
              Nghĩa vụ kiểm thử
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="secondary-button"
              disabled={busy}
              type="button"
              onClick={() =>
                update(() =>
                  testingApi.refreshTestAdequacy(requirementVersionId, assessment?.revision),
                )
              }
            >
              Cập nhật hồ sơ
            </button>
            {assessment?.status === "DRAFT" && canSubmit && (
              <button
                className="secondary-button"
                disabled={busy}
                type="button"
                onClick={() =>
                  update(() => testingApi.submitTestAdequacy(assessment._id, assessment.revision))
                }
              >
                Gửi rà soát
              </button>
            )}
            {assessment?.status === "IN_REVIEW" && canApprove && (
              <button
                className="primary-button"
                disabled={busy}
                type="button"
                onClick={() =>
                  update(() => testingApi.approveTestAdequacy(assessment._id, assessment.revision))
                }
              >
                QA xác nhận Hồ sơ
              </button>
            )}
          </div>
        </div>
        {error && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger">
            {error}
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
        {loading && <LoadingState />}
        {!loading && !assessment && !error && (
          <p className="rounded-control bg-surface-quiet p-4 text-sm text-ink-muted">
            Chưa có hồ sơ đảm bảo cho phiên bản yêu cầu này.
          </p>
        )}
        {assessment && (
          <>
            <div className="grid gap-3 rounded-2xl border border-border bg-surface p-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.25fr)_repeat(3,minmax(0,.65fr))_minmax(210px,.9fr)] xl:items-center">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
                  Trạng thái hồ sơ
                </p>
                <p className="mt-1 text-[15px] font-semibold text-ink">
                  {assessmentLabels[assessment.status] || valueLabel(assessment.status)}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
                  Đã chứng minh
                </p>
                <p className="mt-1 text-[20px] font-semibold text-ink">
                  {assessment.coverage_summary?.verified || 0}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
                  Có điều kiện
                </p>
                <p className="mt-1 text-[20px] font-semibold text-ink">
                  {assessment.coverage_summary?.conditional || 0}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
                  Chưa xử lý
                </p>
                <p className="mt-1 text-[20px] font-semibold text-ink">
                  {assessment.coverage_summary?.outstanding || 0}
                </p>
              </div>
              <label className="field-label">
                Lọc nghĩa vụ
                <select
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                  className="apple-input mt-1 w-full"
                >
                  <option value="">Tất cả trạng thái</option>
                  {Object.entries(labels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="grid gap-4">
              {items.map((item) => (
                <article
                  className="rounded-2xl border border-border bg-surface p-5 shadow-[0_6px_20px_rgba(48,47,42,0.035)]"
                  key={item.coverage_item_id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        Nguồn và trích dẫn
                      </p>
                      <div className="mt-1">{source(item)}</div>
                    </div>
                    <span className="status-badge max-w-full break-words text-center">
                      {labels[item.status] || valueLabel(item.status)}
                    </span>
                  </div>
                  <div className="mt-5 grid gap-5 border-y border-border py-5 lg:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        Kỹ thuật và ca kiểm thử
                      </p>
                      <div className="mt-1 text-ink-muted">{linkedTests(item)}</div>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        Bằng chứng và giả thuyết
                      </p>
                      <div className="mt-1 text-ink-muted">{challenges(item)}</div>
                    </div>
                  </div>
                  <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        Quyết định QA
                      </p>
                      <div className="mt-1 text-ink-muted">{decision(item)}</div>
                    </div>
                    {actions(item)}
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </section>
      {dialog}
    </>
  );
}
