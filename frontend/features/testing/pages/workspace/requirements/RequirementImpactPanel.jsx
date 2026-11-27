"use client";

import { useEffect, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { messageOf } from "../../../lib/testing";
import { Panel } from "../../../components/WorkspacePrimitives";
import RequirementVersionDiff from "./RequirementVersionDiff";

const labels = {
  STILL_VALID: "Chưa thấy ảnh hưởng",
  POTENTIALLY_AFFECTED: "Cần xem xét",
  NEEDS_UPDATE: "Cần cập nhật",
  OBSOLETE: "Có thể không còn phù hợp",
  INSUFFICIENT_EVIDENCE: "Thiếu dữ liệu để kết luận",
};
const limitationLabels = {
  NO_LINKED_CASES: "Không tìm thấy ca kiểm thử đang hiệu lực liên kết với yêu cầu trước.",
  REQUIREMENT_CHANGE_TOO_LONG: "Phần nội dung thay đổi vượt giới hạn phân tích tự động.",
  AI_UNAVAILABLE: "AI chưa trả được kết quả; cần rà soát thủ công hoặc phân tích lại.",
};
const sections = {
  title: "Tên yêu cầu",
  content: "Nội dung yêu cầu",
  business_rules: "Quy tắc nghiệp vụ",
  acceptance_criteria: "Tiêu chí chấp nhận",
};

export default function RequirementImpactPanel({ version, project }) {
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drafts, setDrafts] = useState({});
  const [creating, setCreating] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  async function retry() {
    setRetrying(true);
    setError("");
    try {
      await testingApi.retryRequirementImpact(version._id);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setRetrying(false);
    }
  }
  async function createDraft(item) {
    if (creating) return;
    setCreating(item.case_id);
    setError("");
    try {
      const draft = await testingApi.createTestCaseVersionDraft(item.case_id, {
        expected_current_version_id: item.version_id,
        change_reason: "Rà soát sau thay đổi yêu cầu",
      });
      setDrafts((current) => ({ ...current, [item.case_id]: draft._id }));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setCreating("");
    }
  }
  useEffect(() => {
    let active = true;
    let timer;
    setImpact(null);
    setError("");
    setLoading(true);
    async function load() {
      try {
        const value = await testingApi.getRequirementImpact(version._id);
        if (!active) return;
        setImpact(value);
        if (value && ["PENDING", "RUNNING"].includes(value.status)) timer = setTimeout(load, 5000);
      } catch (reason) {
        if (active) setError(messageOf(reason));
      } finally {
        if (active) setLoading(false);
      }
    }
    if (version?._id) load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [version?._id, reloadKey]);
  return (
    <Panel title="Ảnh hưởng đến kiểm thử">
      <div className="space-y-4 p-5 text-sm">
        {error && <p role="alert">{error}</p>}
        {loading && !impact && !error && <p role="status">Đang tải phân tích ảnh hưởng…</p>}
        {!loading && !impact && !error && (
          <p className="text-ink-muted">Chưa có dữ liệu phân tích ảnh hưởng cho phiên bản này.</p>
        )}
        {["PENDING", "RUNNING"].includes(impact?.status) && <p>Đang phân tích thay đổi…</p>}
        {impact?.status === "FAILED" && (
          <p className="rounded-control border border-danger/30 bg-danger/5 p-3" role="alert">
            Chưa thể phân tích tự động. Mã lỗi: {impact.error_code}
          </p>
        )}
        {impact?.status === "STALE" && (
          <p className="rounded-control border border-border bg-surface-quiet p-3">
            Dữ liệu đã thay đổi sau khi bắt đầu phân tích. Hãy chạy lại để đối chiếu phiên bản mới.
          </p>
        )}
        {["FAILED", "PARTIAL", "STALE"].includes(impact?.status) &&
          project.current_permissions?.includes("ai.run_impact") && (
            <button type="button" className="secondary-button" disabled={retrying} onClick={retry}>
              {retrying ? "Đang gửi…" : "Phân tích lại"}
            </button>
          )}
        {impact?.status === "NO_CONTENT_CHANGE" && <p>Không có thay đổi nội dung cần phân tích.</p>}
        {["COMPLETED", "PARTIAL"].includes(impact?.status) && (
          <>
            <div className="grid gap-3 sm:grid-cols-3" aria-label="Tóm tắt ảnh hưởng">
              <div className="rounded-control border border-border p-3">
                <p className="text-xs text-ink-muted">Trạng thái phân tích</p>
                <p className="mt-1 font-semibold">
                  {impact.status === "COMPLETED" ? "Hoàn tất" : "Chưa đầy đủ"}
                </p>
              </div>
              <div className="rounded-control border border-border p-3">
                <p className="text-xs text-ink-muted">Ca kiểm thử liên quan</p>
                <p className="mt-1 font-semibold">{impact.cases?.length || 0}</p>
              </div>
              <div className="rounded-control border border-border p-3">
                <p className="text-xs text-ink-muted">Gợi ý bổ sung</p>
                <p className="mt-1 font-semibold">{impact.new_candidates?.length || 0}</p>
              </div>
            </div>
            {impact.status === "PARTIAL" && (
              <p>Phân tích chưa đầy đủ. Hãy xem các ca cần xem xét.</p>
            )}
            {impact.limitations?.length > 0 && (
              <ul className="list-disc space-y-1 pl-5">
                {impact.limitations.map((item) => (
                  <li key={item}>{limitationLabels[item] || item}</li>
                ))}
              </ul>
            )}
            <section className="overflow-hidden rounded-control border border-border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
                <div>
                  <h3 className="text-sm font-semibold">Đối chiếu thay đổi</h3>
                  <p className="mt-1 text-xs text-ink-muted">
                    {impact.comparison?.changes?.length || 0} mục được phân tích
                  </p>
                </div>
                <div className="flex gap-3 text-xs text-ink-muted" aria-label="Chú giải thay đổi">
                  <span>Thêm</span>
                  <span>Sửa</span>
                  <span>Loại bỏ</span>
                </div>
              </div>
              <RequirementVersionDiff
                changes={(impact.comparison?.changes || []).map((change) => ({
                  ...change,
                  label: sections[change.field] || change.field,
                }))}
                empty="Không có nội dung thay đổi để so sánh."
              />
            </section>
            <p className="font-medium">Ca kiểm thử liên quan ({impact.cases?.length || 0})</p>
            {!impact.cases?.length && (
              <p>Chưa có ca kiểm thử đang hiệu lực được liên kết với phiên bản trước.</p>
            )}
            {impact.cases?.map((item) => (
              <div key={item.version_id} className="rounded-control border border-border p-3">
                <p className="font-medium">
                  {item.case_key || "Ca kiểm thử"} · {item.title}
                </p>
                <p className="mt-1">{labels[item.classification] || "Cần xem xét"}</p>
                <p className="mt-1 whitespace-pre-wrap">{item.reason}</p>
                {(item.evidence?.requirement_before_quote ||
                  item.evidence?.requirement_after_quote ||
                  item.evidence?.test_case_quote) && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">Căn cứ</summary>
                    <p className="mt-2">
                      Yêu cầu trước:{" "}
                      {item.evidence.requirement_before_quote ||
                        (item.evidence.requirement_before_absent
                          ? "Không có đoạn tương ứng trong phần thay đổi."
                          : "Chưa có trích dẫn được xác nhận.")}
                    </p>
                    <p className="mt-2">
                      Yêu cầu sau:{" "}
                      {item.evidence.requirement_after_quote ||
                        (item.evidence.requirement_after_absent
                          ? "Không có đoạn tương ứng trong phần thay đổi."
                          : "Chưa có trích dẫn được xác nhận.")}
                    </p>
                    <p className="mt-2">
                      Ca kiểm thử:{" "}
                      {item.evidence.test_case_quote || "Chưa có trích dẫn được xác nhận."}
                    </p>
                  </details>
                )}
                {item.proposed_patch && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">Xem đề xuất của AI</summary>
                    {item.proposed_patch.title && <p>Tên: {item.proposed_patch.title}</p>}
                    {item.proposed_patch.objective && (
                      <p>Mục tiêu: {item.proposed_patch.objective}</p>
                    )}
                    {item.proposed_patch.preconditions && (
                      <p>Tiền điều kiện: {item.proposed_patch.preconditions}</p>
                    )}
                    {(item.proposed_patch.steps || []).map((step, index) => (
                      <p key={index} className="mt-2">
                        {index + 1}. {step.action} — Kết quả mong đợi: {step.expected}
                      </p>
                    ))}
                    {item.proposed_patch.expected && (
                      <p>Kết quả mong đợi: {item.proposed_patch.expected}</p>
                    )}
                  </details>
                )}
                {project.current_permissions?.includes("testcase.version.create") &&
                  (drafts[item.case_id] ? (
                    <p className="mt-2">
                      Đã tạo bản nháp. Mở mục Ca kiểm thử để chỉnh sửa và đối chiếu đề xuất.
                    </p>
                  ) : (
                    <button
                      className="secondary-button mt-3"
                      type="button"
                      disabled={Boolean(creating)}
                      onClick={() => createDraft(item)}
                    >
                      {creating === item.case_id ? "Đang tạo…" : "Tạo bản nháp để rà soát"}
                    </button>
                  ))}
              </div>
            ))}
            {impact.new_candidates?.length > 0 && (
              <details>
                <summary className="cursor-pointer font-medium">
                  Gợi ý ca cần xem xét bổ sung
                </summary>
                {impact.new_candidates.map((item, index) => (
                  <div key={index} className="mt-3 rounded-control border border-border p-3">
                    <p className="font-medium">{item.patch?.title}</p>
                    <p className="mt-1">{item.reason}</p>
                    <p className="mt-1">
                      Yêu cầu trước:{" "}
                      {item.requirement_before_quote ||
                        (item.requirement_before_absent
                          ? "Không có đoạn tương ứng trong phần thay đổi."
                          : "Chưa có trích dẫn được xác nhận.")}
                    </p>
                    <p className="mt-1">
                      Yêu cầu sau:{" "}
                      {item.requirement_after_quote ||
                        (item.requirement_after_absent
                          ? "Không có đoạn tương ứng trong phần thay đổi."
                          : "Chưa có trích dẫn được xác nhận.")}
                    </p>
                    {(item.patch?.steps || []).map((step, stepIndex) => (
                      <p key={stepIndex} className="mt-2">
                        {stepIndex + 1}. {step.action} — Kết quả mong đợi: {step.expected}
                      </p>
                    ))}
                  </div>
                ))}
              </details>
            )}
            {impact.plans?.length > 0 && (
              <section className="space-y-3">
                <p className="font-medium">Kế hoạch kiểm thử liên quan ({impact.plans.length})</p>
                {impact.plans.map((plan) => (
                  <div key={plan._id} className="rounded-control border border-border p-3">
                    <p className="font-medium">{plan.name}</p>
                    <p className="mt-1">{labels[plan.classification] || "Chưa có đánh giá"}</p>
                    {plan.reason && <p className="mt-1 whitespace-pre-wrap">{plan.reason}</p>}
                    {plan.suggestion && (
                      <p className="mt-1 whitespace-pre-wrap">Đề xuất: {plan.suggestion}</p>
                    )}
                    {plan.evidence?.plan_quote && (
                      <details className="mt-2">
                        <summary className="cursor-pointer">Căn cứ</summary>
                        <p className="mt-2">
                          Yêu cầu trước: {plan.evidence.requirement_before_quote || "-"}
                        </p>
                        <p className="mt-2">
                          Yêu cầu sau: {plan.evidence.requirement_after_quote || "-"}
                        </p>
                        <p className="mt-2">Kế hoạch: {plan.evidence.plan_quote}</p>
                      </details>
                    )}
                  </div>
                ))}
              </section>
            )}
            {impact.runs?.length > 0 && (
              <p>Lần chạy liên quan: {impact.runs.map((r) => r.name).join(", ")}</p>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}
