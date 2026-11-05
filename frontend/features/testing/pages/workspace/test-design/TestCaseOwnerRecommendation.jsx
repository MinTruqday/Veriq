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
            án chỉ tính nơi đang có lượt kiểm thử mở; giới hạn theo nhân viên chỉ áp dụng khi Admin
            đã khai báo. Bảng lương chỉ dùng dự báo chi phí kế hoạch. Đề xuất không tự gán người.
          </p>
          {result.project_capacity_status === "CAPACITY_PERIOD_NOT_COVERING_SCHEDULE" && (
            <p role="status" className="text-sm text-amber-800">
              Kỳ công suất đã khai báo không bao phủ ngày hiện tại; chưa áp dụng mức trần dự án cho
              đề xuất này.
            </p>
          )}
          {result.project_capacity_status === "AMBIGUOUS_CAPACITY_PERIOD" && (
            <p role="status" className="text-sm text-amber-800">
              Có nhiều kỳ công suất cùng áp dụng; chưa dùng mức trần cho đến khi Admin xử lý kỳ bị
              trùng.
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
            result.candidates.slice(0, 3).map((candidate) => (
              <div
                className="flex flex-wrap items-center justify-between gap-2"
                key={candidate.user_id}
              >
                <div className="min-w-0 text-sm">
                  <p className="font-medium">{candidate.user_label}</p>
                  <p className="text-ink-muted">
                    {candidate.matched_skills.length
                      ? `Kỹ năng phù hợp: ${candidate.matched_skills.join(", ")}`
                      : "Chưa khai báo kỹ năng cần thiết"}
                    {` · ${candidate.active_case_count} ca đang được giao · ${candidate.active_project_count} dự án có lượt mở`}
                    {candidate.max_concurrent_projects != null &&
                      ` · giới hạn ${candidate.max_concurrent_projects} dự án`}
                  </p>
                </div>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onSelect(candidate)}
                >
                  Chọn người này
                </button>
              </div>
            ))
          ) : (
            <p role="status" className="text-sm text-ink-muted">
              {result.status === "PROJECT_LIMIT_REACHED"
                ? "Các ứng viên đạt kỹ năng đã chạm giới hạn dự án được Admin khai báo cho kỳ này. Hãy điều chỉnh giới hạn hoặc chọn người có quyền và xem lại tải trước khi phân công."
                : result.status === "NO_ELIGIBLE_TESTER"
                  ? "Dự án chưa có người phụ trách kiểm thử đang hoạt động để đề xuất."
                  : "Chưa có người phù hợp với kỹ năng đã xác nhận và mức sẵn sàng. Có thể chọn thủ công ở danh sách người phụ trách."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
