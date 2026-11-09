"use client";

import { useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf } from "../../../lib/testing";

export default function TestCaseOwnerRecommendation({
  projectId,
  draftId,
  requiredSkills,
  onSelect,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const renderCandidate = (candidate, rank, isNearMatch = false) => (
    <article className="rounded-control border border-border p-3" key={candidate.user_id}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-ink">{candidate.user_label}</p>
            <span className="rounded-full bg-surface-muted px-2 py-1 text-xs text-ink-muted">
              {isNearMatch
                ? "Cần xem xét khoảng thiếu"
                : `Đề xuất AI #${candidate.recommendation_rank || rank}`}
            </span>
            <span className="text-xs text-ink-muted">
              {candidate.matched_skill_count}/{candidate.required_skill_count} yêu cầu có căn cứ
            </span>
          </div>
          <p className="mt-2 text-sm text-ink-muted">{candidate.ai_reason}</p>
          {candidate.decision_context && (
            <details className="mt-3 rounded-control border border-border p-3">
              <summary className="cursor-pointer text-sm font-medium text-ink">
                Căn cứ và giới hạn đánh giá
              </summary>
              <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
                <div>
                  <p className="font-medium text-ink">Tải hiện tại</p>
                  <p className="mt-1 text-ink-muted">
                    {candidate.decision_context.availability || "Chưa khai báo mức sẵn sàng"} ·{" "}
                    {candidate.decision_context.workload?.active_cases ?? 0} ca ·{" "}
                    {candidate.decision_context.workload?.active_runs ?? 0} lượt chạy ·{" "}
                    {candidate.decision_context.workload?.active_projects ?? 0} dự án có hoạt động
                  </p>
                </div>
                <div>
                  <p className="font-medium text-ink">Mức xác minh</p>
                  <p className="mt-1 text-ink-muted">
                    {candidate.decision_context_status?.skill_evidence ===
                    "PROFILE_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED"
                      ? "Kỹ năng trong hồ sơ chưa được đánh giá độc lập."
                      : "Không có đủ dữ liệu xác minh kỹ năng."}
                    {candidate.decision_context_status?.experience_evidence ===
                    "NO_CONFIRMED_EXPERIENCE_EVIDENCE"
                      ? " Chưa có kinh nghiệm được xác nhận trong hồ sơ."
                      : " Kinh nghiệm hồ sơ cũng chưa được xác minh độc lập."}
                  </p>
                </div>
              </div>
            </details>
          )}
          <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
            <div>
              <p className="font-medium text-ink">Kỹ năng và bằng chứng</p>
              {candidate.matched_skill_evidence?.length ? (
                <ul className="mt-1 list-inside list-disc text-ink-muted">
                  {candidate.matched_skill_evidence.map((item) => (
                    <li key={`${candidate.user_id}:${item.required_skill}:${item.name}`}>
                      {item.required_skill} ← {item.name}
                      {item.match_type === "EQUIVALENT" ? " · tương đương theo AI" : " · trùng tên"}
                      {` · ${item.evidence_status === "DOCUMENT_SUPPORTED" ? "có dẫn chứng tài liệu" : "tự khai trong hồ sơ"}`}
                      {item.level ? ` · mức tự đánh giá: ${item.level}` : " · chưa khai mức độ"}
                      {item.independently_assessed
                        ? " · đã đánh giá độc lập"
                        : " · chưa đánh giá độc lập"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-ink-muted">Chưa có kỹ năng hồ sơ đủ căn cứ cho yêu cầu.</p>
              )}
              {candidate.unmatched_required_skills?.length > 0 && (
                <p className="mt-2 text-ink-muted">
                  Chưa có căn cứ: {candidate.unmatched_required_skills.join(", ")}
                </p>
              )}
            </div>
            <div>
              <p className="font-medium text-ink">Tải và mức sẵn sàng</p>
              <p className="mt-1 text-ink-muted">
                {candidate.availability} · {candidate.active_case_count} ca đang được giao ·{" "}
                {candidate.active_run_count} lượt chạy · {candidate.active_project_count} dự án có
                hoạt động trùng lịch
              </p>
              {candidate.ai_supporting_facts?.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-ink-muted">
                  {candidate.ai_supporting_facts.map((fact, index) => (
                    <li key={`${candidate.user_id}:fact:${index}`}>{fact}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
        {!isNearMatch && (
          <button
            className="secondary-button shrink-0"
            type="button"
            onClick={() => onSelect(candidate)}
          >
            Chọn người này
          </button>
        )}
      </div>
    </article>
  );

  const recommend = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await testingApi.recommendTestCaseOwner(projectId, {
        draft_id: draftId || null,
        required_skills: String(requiredSkills || "")
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      });
      setResult(response);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-2 space-y-2">
      <button className="secondary-button" type="button" disabled={loading} onClick={recommend}>
        {loading ? "Đang tìm người phù hợp…" : "Đề xuất người phụ trách ca"}
      </button>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      {result && (
        <div className="space-y-2 rounded-control border border-border p-3">
          <p className="text-sm text-ink-muted">
            Đề xuất dựa trên kỹ năng, kinh nghiệm đã xác nhận, mức sẵn sàng và tải kiểm thử. Số dự
            án chỉ tính nơi đang có lượt kiểm thử mở; giới hạn theo nhân viên chỉ áp dụng khi đã
            được khai báo. Đề xuất không tự gán người.
          </p>
          {result.project_capacity_status === "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE" && (
            <p role="status" className="text-sm text-amber-800">
              Kỳ công suất đã khai báo không bao phủ ngày hiện tại; chưa áp dụng mức trần dự án cho
              đề xuất này.
            </p>
          )}
          {result.project_capacity_status === "AMBIGUOUS_CAPACITY_PERIOD" && (
            <p role="status" className="text-sm text-amber-800">
              Có nhiều kỳ công suất cùng áp dụng; chưa dùng mức trần cho đến khi kỳ bị trùng được xử
              lý.
            </p>
          )}
          {result.project_capacity_status === "PROJECT_LIMITS_PARTIALLY_DECLARED" && (
            <p role="status" className="text-sm text-ink-muted">
              Chỉ áp dụng mức trần đã khai báo đầy đủ cho toàn bộ kỳ; ứng viên thiếu mức ở một kỳ
              không bị giới hạn tự suy đoán.
            </p>
          )}
          {result.project_capacity_status === "PROJECT_LIMIT_NOT_DECLARED" && (
            <p role="status" className="text-sm text-ink-muted">
              Chưa khai báo mức trần dự án cho ứng viên trong kỳ này.
            </p>
          )}
          {result.candidates?.length ? (
            <div className="space-y-2">
              {result.candidates.map((candidate, index) => renderCandidate(candidate, index + 1))}
              {result.near_matches?.length > 0 && (
                <details className="rounded-control border border-border p-3">
                  <summary className="cursor-pointer font-medium text-ink">
                    Ứng viên cần xem xét thêm ({result.near_matches.length})
                  </summary>
                  <div className="mt-3 space-y-2">
                    {result.near_matches.map((candidate, index) =>
                      renderCandidate(candidate, index + 1, true),
                    )}
                  </div>
                </details>
              )}
              {result.recommendation_warnings?.map((warning, index) => (
                <p className="text-sm text-amber-800" key={`warning:${index}`}>
                  {warning}
                </p>
              ))}
            </div>
          ) : (
            <p role="status" className="text-sm text-ink-muted">
              {result.status === "PROJECT_LIMIT_REACHED"
                ? "Các ứng viên đạt kỹ năng đã chạm giới hạn dự án được cấu hình cho kỳ này. Hãy điều chỉnh giới hạn hoặc chọn người phù hợp và xem lại tải trước khi phân công."
                : result.status === "NO_ELIGIBLE_MEMBER"
                  ? "Dự án chưa có thành viên đang hoạt động được cấp quyền thực hiện kiểm thử để đề xuất."
                  : "Chưa có người phù hợp với kỹ năng đã xác nhận và mức sẵn sàng. Có thể chọn thủ công ở danh sách người phụ trách."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
