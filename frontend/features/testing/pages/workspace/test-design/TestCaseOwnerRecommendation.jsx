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
            Đề xuất dựa trên kỹ năng và kinh nghiệm đã xác nhận, mức sẵn sàng và tải kiểm thử. Bảng
            lương chỉ dùng để dự báo chi phí của kế hoạch, không dùng để xếp hạng nhân sự. Đề xuất
            không tự gán người.
          </p>
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
                    {` · ${candidate.active_case_count} ca đang được giao`}
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
              {result.status === "NO_ELIGIBLE_TESTER"
                ? "Dự án chưa có Tester đang hoạt động để đề xuất."
                : "Chưa có Tester phù hợp với kỹ năng đã xác nhận và mức sẵn sàng. Có thể chọn thủ công ở danh sách người phụ trách."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
