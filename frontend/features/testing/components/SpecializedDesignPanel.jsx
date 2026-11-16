"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { RefreshCw } from "lucide-react";

function CandidateList({ title, results, getCandidates, renderCandidate, empty }) {
  return (
    <section className="space-y-3">
      <h3 className="font-medium text-ink">{title}</h3>
      {results.length === 0 ? (
        <p className="rounded-xl border border-border px-4 py-5 text-sm text-ink-muted">{empty}</p>
      ) : (
        results.map((result) => {
          const candidates = getCandidates(result);
          return (
            <article className="rounded-xl border border-border p-4" key={result._id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-ink">
                  {result.name || `${candidates.length} đề xuất`}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  {result.source_event_id && <ContentOriginBadge origin="ai_generated" />}
                  <StatusPill value={result.generation_status || result.status} />
                </div>
              </div>
              {result.objective && (
                <p className="mt-2 text-sm text-ink-muted">{result.objective}</p>
              )}
              <div className="mt-3 space-y-2">{candidates.map(renderCandidate)}</div>
              {result.source_event_id && (
                <details className="mt-3 text-xs text-ink-faint">
                  <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                  <p className="mt-1 break-all">Mã sự kiện: {result.source_event_id}</p>
                </details>
              )}
              {result.human_confirmation_required === true && (
                <p className="mt-2 text-xs text-ink-muted">
                  Đây là đề xuất; chưa tạo hoặc chạy ca kiểm thử.
                </p>
              )}
            </article>
          );
        })
      )}
    </section>
  );
}

export default function SpecializedDesignPanel({ project }) {
  const [securityResults, setSecurityResults] = useState([]);
  const [performancePlans, setPerformancePlans] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const pendingRef = useRef(false);
  const canReadSecurity = project.current_permissions?.includes("ai.generate_security_tests");
  const canReadPerformance = project.current_permissions?.includes("ai.generate_performance_plan");

  const load = useCallback(async () => {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setLoading(true);
    try {
      const [securityValues, performanceValues] = await Promise.all([
        canReadSecurity ? testingApi.listSecurityTestSuggestions(project._id) : Promise.resolve([]),
        canReadPerformance
          ? testingApi.listPerformancePlanDrafts(project._id)
          : Promise.resolve([]),
      ]);
      setSecurityResults(securityValues);
      setPerformancePlans(performanceValues);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      pendingRef.current = false;
      setLoading(false);
    }
  }, [canReadPerformance, canReadSecurity, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!canReadSecurity && !canReadPerformance) return null;

  return (
    <Panel
      title="Đề xuất kiểm thử chuyên sâu"
      actions={
        <button
          aria-label="Tải lại đề xuất kiểm thử chuyên sâu"
          className="icon-button h-9 w-9 shrink-0"
          disabled={loading}
          onClick={() => void load()}
          title="Tải lại đề xuất kiểm thử chuyên sâu"
          type="button"
        >
          <RefreshCw aria-hidden="true" className={loading ? "animate-spin" : ""} size={16} />
        </button>
      }
    >
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        <div className="grid gap-6 xl:grid-cols-2">
          {canReadSecurity && (
            <CandidateList
              title="Đề xuất kiểm thử bảo mật"
              results={securityResults}
              getCandidates={(result) => result.candidates || []}
              empty="Chưa có đề xuất được tạo từ sự kiện thay đổi yêu cầu phù hợp."
              renderCandidate={(candidate) => (
                <div
                  className="rounded-lg bg-surface-quiet p-3 text-sm"
                  key={candidate.candidate_id}
                >
                  <p className="font-medium text-ink">{candidate.title}</p>
                  <p className="mt-1 text-ink-muted">{valueLabel(candidate.category)}</p>
                  <p className="mt-1">Thao tác: {candidate.action}</p>
                  <p className="mt-1">Kết quả dự kiến: {candidate.expected}</p>
                  {(candidate.evidence_quotes || []).map((quote, index) => (
                    <p
                      className="mt-2 border-l-2 border-border pl-3 text-xs text-ink-muted"
                      key={`${quote.evidence_ref}-${index}`}
                    >
                      Nguồn {quote.evidence_ref}: “{quote.quote}”
                    </p>
                  ))}
                </div>
              )}
            />
          )}
          {canReadPerformance && (
            <CandidateList
              title="Kế hoạch kiểm thử hiệu năng"
              results={performancePlans}
              getCandidates={(plan) => plan.scenarios || []}
              empty="Chưa có kế hoạch hiệu năng được ghi nhận. Chỉ dùng ngưỡng hiệu năng nếu tài liệu yêu cầu có nêu; AI không tự đặt ngưỡng."
              renderCandidate={(scenario) => (
                <div className="rounded-lg bg-surface-quiet p-3 text-sm" key={scenario.scenario_id}>
                  <p className="font-medium text-ink">{scenario.title}</p>
                  <p className="mt-1 text-ink-muted">
                    {scenario.virtual_users} người dùng · {scenario.duration_minutes} phút
                  </p>
                  <p className="mt-1">{scenario.expected}</p>
                </div>
              )}
            />
          )}
        </div>
      </div>
    </Panel>
  );
}
