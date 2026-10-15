import { useCallback, useEffect, useMemo, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf } from "../../../lib/testing";
import { useActionDialog } from "../../../components/WorkspacePrimitives";

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

export default function TestAdequacyPanel({ requirementVersionId, canReview = false }) {
  const { ask, dialog } = useActionDialog();
  const [assessment, setAssessment] = useState(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!requirementVersionId) return;
    setError("");
    try {
      setAssessment(await testingApi.getTestAdequacy(requirementVersionId));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [requirementVersionId]);
  useEffect(() => {
    void load();
  }, [load]);
  const items = useMemo(
    () => (assessment?.coverage_items || []).filter((item) => !filter || item.status === filter),
    [assessment, filter],
  );
  const update = async (work) => {
    setBusy(true);
    setError("");
    try {
      setAssessment(await work());
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  const decide = async (item, status) => {
    const waiver = status === "WAIVED";
    const value = await ask({
      title: waiver ? "Chấp nhận có điều kiện" : "Xác nhận không áp dụng",
      description: waiver
        ? "Waiver chỉ còn hiệu lực đến hạn đã chọn và sẽ buộc Hồ sơ quay lại rà soát khi hết hạn"
        : "QA xác nhận Nghĩa vụ này không áp dụng cho Requirement hiện tại",
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
      setAssessment(
        await testingApi.decideTestAdequacyItem(assessment._id, item.coverage_item_id, {
          expected_revision: assessment.revision,
          status: "MISSING_INFORMATION",
          reason: value.reason,
          clarification_id: clarification._id,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  if (!requirementVersionId) return null;
  return (
    <>
      <section className="workspace-panel space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Độ đầy đủ kiểm thử</h2>
            <p className="mt-1 text-sm text-slate-600">
              Hồ sơ liên kết điểm cần kiểm thử với nguồn Requirement và ca kiểm thử đang hiệu lực
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() =>
                update(() =>
                  testingApi.refreshTestAdequacy(requirementVersionId, assessment?.revision),
                )
              }
            >
              Cập nhật hồ sơ
            </button>
            {assessment?.status === "DRAFT" && (
              <button
                className="secondary-button"
                disabled={busy}
                onClick={() =>
                  update(() => testingApi.submitTestAdequacy(assessment._id, assessment.revision))
                }
              >
                Gửi rà soát
              </button>
            )}
            {assessment?.status === "IN_REVIEW" && canReview && (
              <button
                className="primary-button"
                disabled={busy}
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
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}
        {assessment && (
          <>
            <div className="flex flex-wrap gap-3 text-sm text-slate-700">
              <span>
                Trạng thái Hồ sơ:{" "}
                <strong>{assessmentLabels[assessment.status] || assessment.status}</strong>
              </span>
              <span>Đã chứng minh: {assessment.coverage_summary?.verified || 0}</span>
              <span>Có điều kiện: {assessment.coverage_summary?.conditional || 0}</span>
              <span>Chưa xử lý: {assessment.coverage_summary?.outstanding || 0}</span>
              <select
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                className="form-select"
              >
                <option value="">Tất cả trạng thái</option>
                {Object.entries(labels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-slate-600">
                    <th className="p-2">Nguồn và trích dẫn</th>
                    <th className="p-2">Kỹ thuật và ca kiểm thử</th>
                    <th className="p-2">Bằng chứng và giả thuyết</th>
                    <th className="p-2">Trạng thái</th>
                    <th className="p-2">Quyết định QA</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.coverage_item_id} className="border-b align-top">
                      <td className="p-2">
                        <div className="font-medium">{item.source_ref}</div>
                        <div className="mt-1 max-w-sm text-slate-600">{item.source_quote}</div>
                      </td>
                      <td className="p-2">
                        {item.test_case_versions?.length
                          ? item.test_case_versions.map((test) => (
                              <div key={test.id} className="mb-2">
                                <div>
                                  {test.key} {test.title}
                                </div>
                                <div className="text-slate-600">
                                  {test.techniques?.join(", ") || "Chưa chọn kỹ thuật"}
                                </div>
                                {!test.assurance_evidence_complete && (
                                  <div className="text-amber-700">
                                    Ca này chưa đủ nguồn, dữ liệu hoặc kết quả mong đợi để chứng
                                    minh Nghĩa vụ
                                  </div>
                                )}
                              </div>
                            ))
                          : "Chưa có ca kiểm thử hiệu lực"}
                      </td>
                      <td className="p-2">
                        {item.test_case_versions
                          ?.flatMap((test) => test.challenge_hypotheses || [])
                          .map((challenge, index) => (
                            <div key={index}>{challenge.hypothetical_fault}</div>
                          )) || ""}
                      </td>
                      <td className="p-2">
                        <span className="status-badge">{labels[item.status]}</span>
                      </td>
                      <td className="p-2">
                        {item.decision?.reason || ""}
                        {item.decision?.clarification_id && (
                          <div className="mt-1 text-xs text-slate-600">
                            Phiếu làm rõ: {item.decision.clarification_id}
                          </div>
                        )}
                        {item.status === "WAIVED" && (
                          <div className="mt-1 text-xs text-slate-600">
                            Phụ trách: {item.decision?.waiver_owner_id || "Chưa xác định"}
                            <br />
                            Rà soát lại:{" "}
                            {item.decision?.waiver_review_at
                              ? new Date(item.decision.waiver_review_at).toLocaleDateString("vi-VN")
                              : "Chưa có"}
                            <br />
                            Hết hạn:{" "}
                            {item.decision?.waiver_expires_at
                              ? new Date(item.decision.waiver_expires_at).toLocaleDateString(
                                  "vi-VN",
                                )
                              : "Chưa có"}
                            {item.decision?.waiver_expired_at && (
                              <>
                                <br />
                                Waiver đã hết hạn
                              </>
                            )}
                          </div>
                        )}
                        {canReview &&
                          !["ASSURED", "CONDITIONAL", "SUPERSEDED"].includes(assessment.status) && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              <button
                                className="secondary-button text-xs"
                                disabled={busy}
                                onClick={() => createClarification(item)}
                              >
                                Tạo Phiếu làm rõ
                              </button>
                              <button
                                className="secondary-button text-xs"
                                disabled={busy}
                                onClick={() => decide(item, "NOT_APPLICABLE")}
                              >
                                Không áp dụng
                              </button>
                              <button
                                className="secondary-button text-xs"
                                disabled={busy}
                                onClick={() => decide(item, "WAIVED")}
                              >
                                Chấp nhận rủi ro
                              </button>
                            </div>
                          )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
      {dialog}
    </>
  );
}
