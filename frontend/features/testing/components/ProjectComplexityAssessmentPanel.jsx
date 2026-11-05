"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../routes";

const dimensions = {
  SCOPE: "Phạm vi và phân rã",
  BUSINESS_RULES: "Quy tắc nghiệp vụ",
  REQUIREMENT_TESTABILITY: "Độ rõ của yêu cầu",
  INTEGRATIONS: "Tích hợp và phụ thuộc",
  DATA_LIFECYCLE: "Dữ liệu và vòng đời",
  SECURITY_COMPLIANCE: "Bảo mật và tuân thủ",
  NON_FUNCTIONAL: "Yêu cầu phi chức năng",
  ARCHITECTURE_ENVIRONMENT: "Kiến trúc và môi trường",
  TEST_COMBINATORICS: "Tổ hợp kiểm thử",
  AUTOMATION_OBSERVABILITY: "Tự động hóa và khả năng quan sát",
  BUSINESS_RISK: "Rủi ro kinh doanh",
  UNCERTAINTY_CHANGE: "Bất định và thay đổi",
};

const levels = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  INSUFFICIENT_EVIDENCE: "Chưa đủ căn cứ",
};

const followUps = {
  REQUIREMENT_CLARIFICATION: ["Yêu cầu", "yeu-cau"],
  TEST_OBLIGATION_ANALYSIS: ["Phân tích nghĩa vụ kiểm thử", "ca-kiem-thu"],
  TEST_PLAN_DRAFT: ["Kế hoạch kiểm thử", "ke-hoach-kiem-thu"],
  SCENARIO_OR_TEST_CASE_DRAFT: ["Thiết kế kiểm thử", "ca-kiem-thu"],
  CHANGE_IMPACT_REVIEW: ["Phân tích thay đổi", "thay-doi"],
  STAFFING_AND_COST_COMPARISON: ["Nhân sự và dự toán", "ke-hoach-kiem-thu"],
};

function AssessmentResult({ projectId, result }) {
  const suggestion = result?.suggestions?.[0];
  const citations = result?.citations || [];
  const gaps = result?.scope_summary || {};
  const commercial = result?.commercial_feasibility;
  if (!suggestion && !result?.stale) return null;
  return (
    <div className="space-y-4 border-t border-border p-5">
      {result.stale && (
        <p className="rounded-control border border-amber-300 bg-amber-50 px-4 py-3 text-[13px] text-ink">
          Tài liệu hoặc yêu cầu đã thay đổi. Hãy đánh giá lại trước khi dùng kết quả này.
        </p>
      )}
      {suggestion && (
        <>
          <div>
            <h3 className="font-semibold">Mức sẵn sàng kiểm thử</h3>
            <p className="mt-1 whitespace-pre-wrap text-[13px] leading-6 text-ink-muted">
              {suggestion.readiness_summary}
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(suggestion.dimensions || []).map((item) => (
              <article className="rounded-control border border-border p-4" key={item.dimension_id}>
                <div className="flex items-start justify-between gap-3">
                  <h4 className="text-[13px] font-semibold">
                    {dimensions[item.dimension_id] || item.dimension_id}
                  </h4>
                  <span className="shrink-0 rounded-full bg-surface-quiet px-2.5 py-1 text-[11px]">
                    {levels[item.level] || item.level}
                  </span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-[12px] leading-5 text-ink-muted">
                  {item.explanation}
                </p>
                {item.uncertainty?.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-[12px] text-ink-muted">
                    {item.uncertainty.map((value, index) => (
                      <li key={`${item.dimension_id}-u-${index}`}>{value}</li>
                    ))}
                  </ul>
                )}
                {item.testing_impacts?.length > 0 && (
                  <div className="mt-3 border-t border-border pt-3">
                    <p className="text-[11px] font-medium">Ảnh hưởng đến kiểm thử</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4 text-[12px] text-ink-muted">
                      {item.testing_impacts.map((value, index) => (
                        <li key={`${item.dimension_id}-i-${index}`}>{value}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ))}
          </div>
          {(suggestion.unresolved_questions?.length > 0 ||
            suggestion.source_gaps?.length > 0 ||
            citations.length > 0 ||
            gaps.extraction_gaps?.length > 0) && (
            <details className="rounded-control border border-border p-4">
              <summary className="cursor-pointer text-[13px] font-medium">
                Khoảng trống, câu hỏi và nguồn dẫn
              </summary>
              {suggestion.source_gaps?.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-[12px] leading-5 text-ink-muted">
                  {suggestion.source_gaps.map((value, index) => (
                    <li key={`g-${index}`}>{value}</li>
                  ))}
                </ul>
              )}
              {gaps.extraction_gaps?.length > 0 && (
                <p className="mt-3 text-[12px] leading-5 text-ink-muted">
                  Có {gaps.extraction_gaps.length} tài liệu còn khối chưa xử lý hoặc cảnh báo trích
                  xuất; kết quả không bao phủ đầy đủ các phần đó.
                </p>
              )}
              {suggestion.unresolved_questions?.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-[12px] leading-5 text-ink-muted">
                  {suggestion.unresolved_questions.map((value, index) => (
                    <li key={`q-${index}`}>{value}</li>
                  ))}
                </ul>
              )}
              {citations.length > 0 && (
                <ul className="mt-3 space-y-2">
                  {citations.map((citation, index) => (
                    <li
                      className="rounded-control bg-surface-quiet p-3 text-[12px] leading-5"
                      key={`${citation.evidence_ref}-${index}`}
                    >
                      <p>“{citation.quote}”</p>
                      {citation.artifact_type === "requirement_document" ? (
                        <Link
                          className="mt-1 inline-block text-brand underline"
                          href={projectRoute(
                            projectId,
                            PROJECT_SECTION_SLUGS.documentReader,
                            citation.artifact_id,
                          )}
                        >
                          Mở tài liệu nguồn
                        </Link>
                      ) : (
                        <span className="mt-1 inline-block text-ink-muted">
                          Yêu cầu đã duyệt · {citation.artifact_id}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </details>
          )}
          <p className="text-[12px] text-ink-muted">
            Đã xét {gaps.current_ai_readable_documents || 0} tài liệu được phép dùng AI và{" "}
            {gaps.baselined_requirements || 0} yêu cầu đã duyệt. Giá khách hàng và bảng lương không
            được gửi vào AI; khả thi ngân sách cần được đối chiếu riêng bằng dữ liệu tài chính có
            quyền.
          </p>
          {commercial && (
            <div className="rounded-control border border-border p-4">
              <h3 className="text-[13px] font-semibold">Áp lực ngân sách và nhân công</h3>
              {commercial.status === "FORECAST_ONLY" ? (
                <>
                  <p className="mt-2 text-[12px] leading-5 text-ink-muted">
                    {commercial.comparison === "BELOW_LABOR_COST"
                      ? "Giá khách hàng thấp hơn chi phí nhân công dự kiến. Đây là rủi ro triển khai cần người có quyền xem xét."
                      : "Giá khách hàng đang đủ bù chi phí nhân công dự kiến trước các chi phí khác."}
                  </p>
                  <dl className="mt-3 grid gap-3 text-[12px] sm:grid-cols-3">
                    <div>
                      <dt className="text-ink-muted">Giá khách hàng</dt>
                      <dd className="mt-1 font-medium">
                        {commercial.customer_price} {commercial.currency}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-muted">Nhân công dự kiến</dt>
                      <dd className="mt-1 font-medium">
                        {commercial.estimated_labor_cost} {commercial.currency}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-muted">Chênh lệch trước chi phí khác</dt>
                      <dd className="mt-1 font-medium">
                        {commercial.variance_before_other_costs} {commercial.currency}
                      </dd>
                    </div>
                  </dl>
                  <p className="mt-2 text-[11px] text-ink-muted">
                    Dựa trên Test Plan đã duyệt; chưa tính chi phí khác, thuế hoặc lợi nhuận thực
                    tế.
                  </p>
                </>
              ) : (
                <p className="mt-2 text-[12px] leading-5 text-ink-muted">
                  {{
                    MISSING_CUSTOMER_PRICE: "Chưa có giá khách hàng.",
                    MISSING_APPROVED_TEST_PLAN:
                      "Chưa có Test Plan được duyệt để làm căn cứ ước lượng.",
                    APPROVED_PLAN_EFFORT_INCOMPLETE:
                      "Test Plan đã duyệt chưa có ước lượng giờ công đầy đủ.",
                    APPROVED_PLAN_START_DATE_MISSING:
                      "Test Plan chưa có ngày bắt đầu để đối chiếu bảng đơn giá.",
                    MISSING_LABOR_RATES:
                      "Chưa có đơn giá còn hiệu lực cho một số phân bổ nhân lực.",
                    FINANCIAL_DATA_INVALID: "Dữ liệu tài chính chưa hợp lệ để tính đối chiếu.",
                  }[commercial.status] || "Chưa đủ dữ liệu tài chính để đối chiếu."}
                </p>
              )}
            </div>
          )}
          {Object.values(gaps.excluded_sources || {}).some((count) => Number(count) > 0) && (
            <p className="text-[12px] text-ink-muted">
              Nguồn chưa đưa vào đánh giá:{" "}
              {Object.entries(gaps.excluded_sources)
                .filter(([, count]) => Number(count) > 0)
                .map(
                  ([key, count]) =>
                    `${count} ${{ not_readable: "không có quyền đọc", ai_not_allowed: "chưa cho phép AI", not_ready: "chưa xử lý xong", empty: "không có nội dung" }[key] || key}`,
                )
                .join(" · ")}
              .
            </p>
          )}
          {suggestion.recommended_follow_ups?.length > 0 && (
            <div className="border-t border-border pt-4">
              <p className="text-[13px] font-medium">Bước tiếp theo</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {[...new Set(suggestion.recommended_follow_ups)].map((key) => {
                  const followUp = followUps[key];
                  if (!followUp) return null;
                  return (
                    <Link
                      className="secondary-button"
                      href={`/du-an/${projectId}/${followUp[1]}`}
                      key={key}
                    >
                      {followUp[0]}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ProjectComplexityAssessmentPanel({ project }) {
  const { user } = useAuth();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [scopeError, setScopeError] = useState("");
  const [scopeLoading, setScopeLoading] = useState(true);
  const [scopeOptions, setScopeOptions] = useState({
    documents: [],
    requirements: [],
    excluded: {},
  });
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [selectedRequirementVersionIds, setSelectedRequirementVersionIds] = useState([]);
  const [instruction, setInstruction] = useState("");
  const pendingRequest = useRef(null);
  const canAssess = (project.current_permissions || []).includes("ai.ask_project");

  useEffect(() => {
    let active = true;
    if (!canAssess) {
      setLoading(false);
      return undefined;
    }
    Promise.allSettled([
      testingApi.getProjectComplexityAssessment(project._id),
      testingApi.getProjectComplexityScope(project._id),
    ])
      .then(([assessment, scope]) => {
        if (!active) return;
        if (assessment.status === "fulfilled") setResult(assessment.value);
        else if (assessment.reason?.status !== 404) setError(messageOf(assessment.reason));
        if (scope.status === "fulfilled") {
          const value = scope.value || {};
          const documents = value.documents || [];
          const requirements = value.requirements || [];
          setScopeOptions({ ...value, documents, requirements });
          setSelectedDocumentIds(documents.map((item) => item.id));
          setSelectedRequirementVersionIds(requirements.map((item) => item.version_id));
        } else {
          setScopeError(messageOf(scope.reason));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
          setScopeLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [canAssess, project._id]);

  if (!canAssess) return null;

  async function assess() {
    setRunning(true);
    setError("");
    try {
      const documentIds = [...selectedDocumentIds].sort();
      const requirementVersionIds = [...selectedRequirementVersionIds].sort();
      const outputLanguage = user?.locale || project.locale || "en";
      const fingerprint = JSON.stringify({
        instruction,
        document_ids: documentIds,
        requirement_version_ids: requirementVersionIds,
        output_language: outputLanguage,
      });
      if (!pendingRequest.current || pendingRequest.current.fingerprint !== fingerprint) {
        pendingRequest.current = {
          fingerprint,
          payload: {
            instruction,
            document_ids: documentIds,
            requirement_version_ids: requirementVersionIds,
            output_language: outputLanguage,
            idempotency_key: crypto.randomUUID(),
          },
        };
      }
      setResult(
        await testingApi.assessProjectComplexity(project._id, pendingRequest.current.payload),
      );
      pendingRequest.current = null;
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Panel
      title="Độ phức tạp và mức sẵn sàng kiểm thử"
      description="Đánh giá chỉ chạy khi bạn yêu cầu. Kết quả là đề xuất có dẫn chứng, không tự tạo hoặc thay đổi kế hoạch kiểm thử."
      actions={
        <button
          className="primary-button"
          disabled={
            running ||
            loading ||
            scopeLoading ||
            (!selectedDocumentIds.length && !selectedRequirementVersionIds.length)
          }
          onClick={assess}
          type="button"
        >
          {running ? "Đang đánh giá…" : result ? "Đánh giá lại" : "Đánh giá bằng AI"}
        </button>
      }
    >
      <div className="space-y-3 border-b border-border p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-[13px] font-semibold">Nguồn dùng để đánh giá</h3>
            <p className="mt-1 text-[12px] text-ink-muted">
              Chỉ chọn tài liệu đã cho phép AI đọc và yêu cầu đang được duyệt làm mốc.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="secondary-button"
              disabled={running || scopeLoading}
              onClick={() => {
                setSelectedDocumentIds(scopeOptions.documents.map((item) => item.id));
                setSelectedRequirementVersionIds(
                  scopeOptions.requirements.map((item) => item.version_id),
                );
              }}
              type="button"
            >
              Chọn tất cả
            </button>
            <button
              className="secondary-button"
              disabled={running || scopeLoading}
              onClick={() => {
                setSelectedDocumentIds([]);
                setSelectedRequirementVersionIds([]);
              }}
              type="button"
            >
              Bỏ chọn
            </button>
          </div>
        </div>
        {scopeLoading ? (
          <p className="text-[12px] text-ink-muted">Đang tải nguồn có thể dùng…</p>
        ) : scopeError ? (
          <ErrorState message={scopeError} />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            <fieldset className="min-w-0 space-y-2">
              <legend className="mb-2 text-[12px] font-medium">
                Tài liệu ({selectedDocumentIds.length}/{scopeOptions.documents.length})
              </legend>
              {scopeOptions.documents.length ? (
                scopeOptions.documents.map((item) => (
                  <label className="flex min-w-0 items-start gap-2 text-[12px]" key={item.id}>
                    <input
                      checked={selectedDocumentIds.includes(item.id)}
                      disabled={running}
                      onChange={(event) =>
                        setSelectedDocumentIds((current) =>
                          event.target.checked
                            ? [...current, item.id]
                            : current.filter((id) => id !== item.id),
                        )
                      }
                      type="checkbox"
                    />
                    <span className="min-w-0 break-words">
                      {item.filename}{" "}
                      <span className="text-ink-muted">· phiên bản {item.source_version}</span>
                    </span>
                  </label>
                ))
              ) : (
                <p className="text-[12px] text-ink-muted">Không có tài liệu đủ điều kiện.</p>
              )}
            </fieldset>
            <fieldset className="min-w-0 space-y-2">
              <legend className="mb-2 text-[12px] font-medium">
                Yêu cầu đã duyệt ({selectedRequirementVersionIds.length}/
                {scopeOptions.requirements.length})
              </legend>
              {scopeOptions.requirements.length ? (
                scopeOptions.requirements.map((item) => (
                  <label
                    className="flex min-w-0 items-start gap-2 text-[12px]"
                    key={item.version_id}
                  >
                    <input
                      checked={selectedRequirementVersionIds.includes(item.version_id)}
                      disabled={running}
                      onChange={(event) =>
                        setSelectedRequirementVersionIds((current) =>
                          event.target.checked
                            ? [...current, item.version_id]
                            : current.filter((id) => id !== item.version_id),
                        )
                      }
                      type="checkbox"
                    />
                    <span className="min-w-0 break-words">
                      {[item.requirement_key, item.title].filter(Boolean).join(" · ") ||
                        item.requirement_id}
                      {item.revision ? (
                        <span className="text-ink-muted"> · phiên bản {item.revision}</span>
                      ) : null}
                    </span>
                  </label>
                ))
              ) : (
                <p className="text-[12px] text-ink-muted">Không có yêu cầu đã duyệt.</p>
              )}
            </fieldset>
          </div>
        )}
        {Object.values(scopeOptions.excluded || {}).some(Boolean) && (
          <p className="text-[12px] text-ink-muted">
            Có nguồn chưa đủ điều kiện, chưa cho phép AI đọc hoặc chưa trích xuất xong; các nguồn đó
            không được đưa vào lượt đánh giá.
          </p>
        )}
      </div>
      <div className="space-y-2 border-b border-border p-5">
        <label className="field-label block" htmlFor={`complexity-instruction-${project._id}`}>
          Phạm vi cần lưu ý
        </label>
        <textarea
          className="apple-input min-h-20 w-full"
          id={`complexity-instruction-${project._id}`}
          maxLength={5000}
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder="Nêu module, giai đoạn hoặc bối cảnh cần ưu tiên khi đánh giá"
          disabled={running}
        />
      </div>
      {loading ? (
        <p className="p-5 text-[13px] text-ink-muted">Đang tải đánh giá gần nhất…</p>
      ) : null}
      {error ? (
        <div className="p-5">
          <ErrorState message={error} />
        </div>
      ) : null}
      {!result && !loading && !error && (
        <p className="p-5 text-[13px] text-ink-muted">
          Chưa có đánh giá. Bấm “Đánh giá bằng AI” để xem 12 chiều và căn cứ nguồn.
        </p>
      )}
      {result && <AssessmentResult projectId={project._id} result={result} />}
    </Panel>
  );
}
