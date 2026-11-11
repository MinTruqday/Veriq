"use client";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { formatDateOnly } from "@/shared/lib/dateTime.mjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import { docText, formatDate as formatDateValue, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";

const benchmarkPath = "project:";

function requirementCase(requirement) {
  const version = requirement.current_version || {};
  const criteria = (version.acceptance_criteria || []).filter(
    (criterion) =>
      String(criterion.status || "").toUpperCase() === "APPROVED" &&
      String(criterion.plain_text || docText(criterion.content_doc) || "").trim(),
  );
  if (!version._id || !criteria.length) return null;

  const sourceRef = String(version._id);
  const sections = [
    String(version.plain_text_projection || docText(version.content_doc) || "").trim(),
  ];
  for (const [field, label] of [
    ["actors", "Tác nhân"],
    ["business_rules", "Quy tắc nghiệp vụ"],
    ["dependencies", "Phụ thuộc"],
  ]) {
    const values = Array.isArray(version[field]) ? version[field] : [];
    if (values.length) {
      sections.push(
        `${label}:\n${values
          .map((value) => String(value).trim())
          .filter(Boolean)
          .join("\n")}`,
      );
    }
  }
  for (const [field, label] of [
    ["main_flow", "Luồng chính"],
    ["exception_flow", "Luồng ngoại lệ"],
    ["data_rules", "Quy tắc dữ liệu"],
    ["integration", "Tích hợp"],
    ["quality_measure", "Thuộc tính chất lượng"],
  ]) {
    const value = version.details?.[field];
    if (typeof value === "string" && value.trim()) sections.push(`${label}:\n${value.trim()}`);
  }
  const sources = [
    {
      source_id: String(requirement.requirement_key || version._id),
      artifact_type: "requirement_version",
      artifact_version_id: sourceRef,
      authority: "APPROVED_SOURCE",
      text: sections.filter(Boolean).join("\n\n"),
    },
    ...criteria.map((criterion) => ({
      source_id: String(criterion._id),
      artifact_type: "acceptance_criterion",
      artifact_version_id: String(criterion._id),
      authority: "APPROVED_SOURCE",
      text: String(criterion.plain_text || docText(criterion.content_doc)).trim(),
    })),
  ];

  return {
    case_id: String(requirement.requirement_key || version._id),
    task_instruction:
      "Trích xuất nghĩa vụ kiểm thử chỉ từ tiêu chí chấp nhận đã duyệt. Giữ nguyên căn cứ nguồn; không tự bổ sung hành vi hoặc điều kiện chưa được nêu.",
    sources,
  };
}

function buildAuthoredAnswerKey(item, draft) {
  const sources = item.sources || [];
  const obligations = String(draft?.obligations || "")
    .split("\n")
    .map((line) => {
      const separators = [...line.matchAll(/\|/g)].map((item) => item.index);
      if (separators.length < 3) return ["", "", "", ""];
      return [
        line.slice(0, separators[0]).trim(),
        line.slice(separators[0] + 1, separators[1]).trim(),
        line.slice(separators[1] + 1, separators[2]).trim(),
        line.slice(separators[2] + 1).trim(),
      ];
    })
    .filter(([key, meaning, sourceRef, quote]) => key && meaning && sourceRef && quote);
  const categories = String(draft?.clarifications || "")
    .split("\n")
    .map((value) => value.trim())
    .filter(Boolean);
  if (
    !obligations.length ||
    obligations.some(
      ([, meaning, sourceRef, quote]) =>
        !meaning ||
        !sources.some(
          (source) => source.artifact_version_id === sourceRef && source.text.includes(quote),
        ),
    ) ||
    new Set(obligations.map(([key]) => key)).size !== obligations.length
  )
    return null;
  const expected_source_quotes = [...new Set(obligations.map(([, , , quote]) => quote))];
  return {
    ...item,
    expected_source_quotes,
    expected_obligation_keys: obligations.map(([key]) => key),
    expected_obligation_meanings: Object.fromEntries(
      obligations.map(([key, meaning]) => [key, meaning]),
    ),
    expected_obligation_sources: Object.fromEntries(
      obligations.map(([key, , , quote]) => [key, quote]),
    ),
    expected_obligation_source_refs: Object.fromEntries(
      obligations.map(([key, , sourceRef]) => [key, sourceRef]),
    ),
    expected_source_quote_sources: Object.fromEntries(
      expected_source_quotes.map((quote) => [
        quote,
        [
          ...new Set(
            obligations.filter(([, , , value]) => value === quote).map(([, , ref]) => ref),
          ),
        ],
      ]),
    ),
    expected_clarification_categories: categories,
  };
}

function metricLabel(metric) {
  const labels = {
    source_quote_validity: "Tính hợp lệ của trích dẫn",
    source_quote_precision: "Độ chính xác trích dẫn nguồn (Precision)",
    source_quote_recall: "Độ bao phủ trích dẫn nguồn (Recall)",
    source_quote_source_precision: "Độ chính xác phiên bản nguồn (Precision)",
    source_quote_source_recall: "Độ bao phủ phiên bản nguồn (Recall)",
    obligation_precision: "Độ chính xác nghĩa vụ kiểm thử (Precision)",
    obligation_recall: "Độ bao phủ nghĩa vụ kiểm thử (Recall)",
    clarification_precision: "Độ chính xác câu hỏi làm rõ (Precision)",
    clarification_recall: "Độ bao phủ câu hỏi làm rõ (Recall)",
    clarification_priority_ndcg: "Điểm xếp hạng ưu tiên câu hỏi (NDCG)",
    obligation_semantic_precision: "Độ chính xác ngữ nghĩa nghĩa vụ (AI judge)",
    obligation_semantic_recall: "Độ bao phủ ngữ nghĩa nghĩa vụ (AI judge)",
    obligation_semantic_f1: "F1 ngữ nghĩa nghĩa vụ (AI judge)",
  };
  return labels[metric] || valueLabel(metric);
}

function formatMetric(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Chưa đủ dữ liệu";
}

function datasetReady(dataset) {
  if (dataset?.reference_provenance === "SELF_PREPARED_REFERENCE") {
    return Boolean(
      dataset.project_id &&
        dataset.creator_identity_verified &&
        Array.isArray(dataset.cases) &&
        dataset.cases.length,
    );
  }
  const review = dataset?.answer_key_review;
  if (
    !dataset?.creator_identity_verified ||
    !review?.reviewer_identity_verified ||
    review.reviewer_id === dataset.created_by ||
    review.decision !== "APPROVE" ||
    !Array.isArray(dataset.cases) ||
    !Array.isArray(review.case_reviews) ||
    review.case_reviews.length !== dataset.cases.length
  ) {
    return false;
  }
  const reviewed = new Map(review.case_reviews.map((item) => [item.case_id, item]));
  return dataset.cases.every((item) => {
    const reviewItem = reviewed.get(item.case_id);
    return Boolean(
      reviewItem?.source_quotes_verified &&
        reviewItem?.obligations_verified &&
        (!Object.keys(item.expected_obligation_meanings || {}).length ||
          reviewItem?.obligation_meanings_verified === true) &&
        ((!item.expected_clarification_categories?.length &&
          !item.expected_clarification_codes?.length) ||
          reviewItem.clarifications_verified),
    );
  });
}

function benchmarkResultRows(report) {
  const pipelineRows = Object.entries(report?.pipeline_statistics || {}).flatMap(
    ([pipeline, summary]) =>
      Object.entries(summary.metrics || {}).map(([metric, value]) => ({
        _id: `${pipeline}-${metric}`,
        pipeline:
          {
            compiler: "Lập bản đồ điều kiện kiểm thử",
            blueprint_before_self_review: "Blueprint trước Self-review",
            blueprint_after_self_review: "Blueprint sau Self-review",
            blueprint_self_review: "Self-review Blueprint",
            direct_generation: "Sinh ca kiểm thử trực tiếp",
            clarification_without_obligation_planning: "Chỉ hỏi làm rõ",
          }[pipeline] || valueLabel(pipeline),
        metric: metricLabel(metric),
        mean: formatMetric(value.mean),
        spread:
          typeof value.minimum === "number" && typeof value.maximum === "number"
            ? `${formatMetric(value.minimum)} – ${formatMetric(value.maximum)}`
            : "Chưa đủ dữ liệu",
        cases: summary.stable_case_count ?? value.paired_case_count ?? "—",
        runs: `${value.observed_runs || 0}/${report.requested_repetitions || 0}`,
      })),
  );
  const semantic = report?.semantic_obligation_comparison || {};
  const semanticRows = ["before_self_review", "after_self_review"].flatMap((side) =>
    ["precision", "recall", "f1"].map((metric) => {
      const value = semantic[side]?.[metric];
      return {
        _id: `semantic-${side}-${metric}`,
        pipeline:
          side === "before_self_review"
            ? "Ngữ nghĩa · trước Self-review (AI judge)"
            : "Ngữ nghĩa · sau Self-review (AI judge)",
        metric: metricLabel(`obligation_semantic_${metric}`),
        mean: formatMetric(typeof value === "number" ? value : value?.mean),
        spread:
          typeof value?.minimum === "number" && typeof value?.maximum === "number"
            ? `${formatMetric(value.minimum)} – ${formatMetric(value.maximum)}`
            : "Chưa đủ dữ liệu",
        cases:
          typeof semantic.scored_case_run_count === "number"
            ? `${semantic.scored_case_run_count}/${semantic.requested_case_run_count} lượt ca`
            : (semantic.scored_case_count ?? "—"),
        runs: `${semantic.observed_runs || 0}/${report?.requested_repetitions || 0}`,
      };
    }),
  );
  return [...pipelineRows, ...semanticRows];
}

export default function RealTestabilityBenchmarkPanel({ project }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const { user } = useAuth();
  const canManageBenchmark = user?.system_role === "ADMIN";
  const [requirements, setRequirements] = useState([]);
  const [selectedRequirementIds, setSelectedRequirementIds] = useState([]);
  const [answerKeyDrafts, setAnswerKeyDrafts] = useState({});
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [report, setReport] = useState(null);
  const [runHistory, setRunHistory] = useState([]);
  const [reviewRationale, setReviewRationale] = useState("");
  const [referenceProvenance, setReferenceProvenance] = useState("SELF_PREPARED_REFERENCE");
  const [reviewedCaseIds, setReviewedCaseIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const eligibleRequirements = useMemo(
    () => requirements.map(requirementCase).filter(Boolean),
    [requirements],
  );
  const selectedCases = useMemo(() => {
    const selected = new Set(selectedRequirementIds);
    return eligibleRequirements.filter((item) => selected.has(item.case_id));
  }, [eligibleRequirements, selectedRequirementIds]);
  const preparedCases = useMemo(
    () => selectedCases.map((item) => buildAuthoredAnswerKey(item, answerKeyDrafts[item.case_id])),
    [answerKeyDrafts, selectedCases],
  );
  const ownedDatasets = useMemo(
    () => datasets.filter((item) => item.dataset_id.startsWith(`${benchmarkPath}${project._id}:`)),
    [datasets, project._id],
  );
  const isIndependentReviewer = Boolean(
    selectedDataset && selectedDataset.created_by !== (user?._id || user?.id),
  );
  const selectedDatasetReady = datasetReady(selectedDataset);

  const loadDatasets = useCallback(async () => {
    const values = await testingApi.listTestabilityBenchmarkDatasets(100);
    setDatasets(Array.isArray(values) ? values : []);
  }, []);

  const loadProjectInputs = useCallback(async () => {
    setLoading(true);
    setError("");
    if (!canManageBenchmark) {
      setRequirements([]);
      setDatasets([]);
      setLoading(false);
      return;
    }
    try {
      const [requirementsPage] = await Promise.all([
        testingApi.listRequirementPage(project._id, {
          status: "BASELINED",
          page: 1,
          page_size: 500,
          include_acceptance_criteria: true,
          sort: "requirement_key",
        }),
        loadDatasets(),
      ]);
      setRequirements(requirementsPage.items || []);
      setSelectedRequirementIds([]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [canManageBenchmark, loadDatasets, project._id]);

  useEffect(() => {
    setSelectedDataset(null);
    setReport(null);
    setRunHistory([]);
    void loadProjectInputs();
  }, [loadProjectInputs]);

  const openDataset = async (datasetId) => {
    if (!datasetId) {
      setSelectedDataset(null);
      setReport(null);
      setReviewedCaseIds([]);
      return;
    }
    setError("");
    try {
      setSelectedDataset(await testingApi.getTestabilityBenchmarkDataset(datasetId));
      setReport(null);
      setReviewedCaseIds([]);
      const runs = await testingApi.listTestabilityBenchmarkDatasetRuns(datasetId, 1);
      setRunHistory(Array.isArray(runs) ? runs : []);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const toggleRequirement = (caseId) => {
    setSelectedRequirementIds((current) =>
      current.includes(caseId) ? current.filter((item) => item !== caseId) : [...current, caseId],
    );
  };

  const createDataset = async () => {
    if (!selectedCases.length || preparedCases.some((item) => !item)) return;
    setSaving(true);
    setError("");
    try {
      const dataset = await testingApi.createTestabilityBenchmarkDataset({
        dataset_id: `${benchmarkPath}${project._id}:${crypto.randomUUID()}`,
        title: `Yêu cầu đã duyệt · ${project.name || project.key || project._id} · ${formatDateOnly(new Date(), dateTimeOptions)}`,
        project_id: project._id,
        reference_provenance: referenceProvenance,
        cases: preparedCases,
      });
      await loadDatasets();
      setSelectedDataset(dataset);
      setReport(null);
      setRunHistory([]);
      setReviewedCaseIds([]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };

  const reviewDataset = async () => {
    if (!selectedDataset || !reviewRationale.trim()) return;
    setSaving(true);
    setError("");
    try {
      const dataset = await testingApi.reviewTestabilityBenchmarkDataset(
        selectedDataset.dataset_id,
        {
          expected_revision: selectedDataset.revision,
          decision: "APPROVE",
          rationale: reviewRationale.trim(),
          case_reviews: selectedDataset.cases.map((item) => ({
            case_id: item.case_id,
            source_quotes_verified: true,
            obligations_verified: true,
            obligation_meanings_verified: item.expected_obligation_meanings ? true : null,
            clarifications_verified: item.expected_clarification_categories?.length ? true : null,
            rationale: reviewRationale.trim().slice(0, 2000),
          })),
        },
      );
      setSelectedDataset(dataset);
      setReviewRationale("");
      await loadDatasets();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };

  const runDataset = async () => {
    if (!selectedDataset?.dataset_id) return;
    setRunning(true);
    setError("");
    setReport(null);
    try {
      const result = await testingApi.repeatTestabilityBenchmarkDataset(
        selectedDataset.dataset_id,
        3,
      );
      setReport(result);
      await loadDatasets();
      const runs = await testingApi.listTestabilityBenchmarkDatasetRuns(
        selectedDataset.dataset_id,
        9,
      );
      setRunHistory(Array.isArray(runs) ? runs : []);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <LoadingState />;

  if (!canManageBenchmark) {
    return (
      <Panel title="Đánh giá thực nghiệm trên yêu cầu đã duyệt">
        <p className="p-4 text-sm leading-6 text-ink-muted">
          Phần tạo bộ dữ liệu, rà soát đáp án và chạy thực nghiệm cần tài khoản quản trị hệ thống.
          Số liệu hoạt động AI của dự án được hiển thị ở phần phía trên.
        </p>
      </Panel>
    );
  }

  const allCasesReviewed = Boolean(
    selectedDataset?.cases?.length &&
      selectedDataset.cases.every((item) => reviewedCaseIds.includes(item.case_id)),
  );

  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      <Panel title="Đánh giá thực nghiệm trên yêu cầu đã duyệt">
        <div className="space-y-3 p-4 text-sm leading-6 text-ink-muted">
          <p>
            Nguồn lấy từ phiên bản yêu cầu đã duyệt. Người tạo tự biên soạn mô tả ý nghĩa và căn cứ;
            hệ thống không biến tiêu chí chấp nhận thành đáp án chuẩn tự động.
          </p>
          <p>
            Chấm trích dẫn, phiên bản nguồn và độ bao phủ nghĩa vụ. Đối chiếu ý nghĩa nghĩa vụ dùng
            AI judge dựa trên mô tả do người biên soạn nhập; đây là ước lượng, không phải xác minh
            độc lập. Bộ dữ liệu thiếu nhãn câu hỏi làm rõ thì các chỉ số đó được để trống.
          </p>
          <p>
            Bạn có thể chạy bộ tham chiếu tự chuẩn bị ngay để thử nghiệm cá nhân; kết quả sẽ được
            ghi rõ là chưa xác thực độc lập. Nếu chọn đánh giá độc lập, một thành viên khác cần rà
            từng nhãn trước khi chạy. Kết quả không tự chứng minh độ đúng ngoài thực tế.
          </p>
        </div>
      </Panel>

      <Panel title="Tạo bộ đánh giá từ dự án này">
        <div className="space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">
              Có {eligibleRequirements.length} yêu cầu đã duyệt làm nguồn. Đáp án tham chiếu được
              nhập thủ công.
            </p>
            <label className="field-label min-w-64">
              Cách sử dụng bộ tham chiếu
              <select
                className="apple-input mt-2"
                value={referenceProvenance}
                disabled={saving}
                onChange={(event) => setReferenceProvenance(event.target.value)}
              >
                <option value="SELF_PREPARED_REFERENCE">
                  Thử nghiệm cá nhân · chưa xác thực độc lập
                </option>
                <option value="INDEPENDENT_REFERENCE">
                  Đánh giá độc lập · cần người khác rà soát
                </option>
              </select>
            </label>
            <button
              className="apple-button"
              type="button"
              disabled={saving || !selectedCases.length || preparedCases.some((item) => !item)}
              onClick={() => void createDataset()}
            >
              {saving ? "Đang lưu bộ dữ liệu…" : `Tạo bộ dữ liệu (${selectedCases.length} ca)`}
            </button>
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto rounded-xl border border-border p-3">
            {eligibleRequirements.map((item) => {
              const requirement = requirements.find(
                (value) =>
                  String(value.requirement_key || value.current_version_id) === item.case_id,
              );
              const checked = selectedRequirementIds.includes(item.case_id);
              return (
                <label
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3"
                  key={item.case_id}
                >
                  <input
                    className="mt-1"
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleRequirement(item.case_id)}
                  />
                  <span className="min-w-0">
                    <span className="block font-medium text-ink">{item.case_id}</span>
                    <span className="block text-sm text-ink-muted">
                      {requirement?.current_version?.title || "Yêu cầu"} · Nguồn đã duyệt
                    </span>
                  </span>
                </label>
              );
            })}
            {!eligibleRequirements.length && (
              <p className="p-3 text-sm text-ink-muted">
                Chưa có yêu cầu đã duyệt kèm tiêu chí chấp nhận; chưa thể tạo đáp án kỳ vọng từ dữ
                liệu dự án.
              </p>
            )}
          </div>
          {selectedCases.map((item, index) => (
            <section className="space-y-2 rounded-lg border border-border p-3" key={item.case_id}>
              <h4 className="font-medium">Đáp án tham chiếu · {item.case_id}</h4>
              <p className="text-xs text-ink-muted">
                Mỗi dòng ghi{" "}
                <code>
                  Mã nghĩa vụ | ý nghĩa cần kiểm thử | mã phiên bản nguồn | trích dẫn nguyên văn
                </code>
                . Ý nghĩa do người biên soạn xác định; chỉ trích dẫn đúng nội dung của phiên bản
                nguồn bên dưới.
              </p>
              <div className="flex flex-wrap gap-2">
                {item.sources.map((source) => (
                  <code
                    className="rounded bg-surface-muted px-2 py-1 text-xs"
                    key={source.artifact_version_id}
                  >
                    {source.artifact_type}: {source.artifact_version_id}
                  </code>
                ))}
              </div>
              <label className="field-label block">
                Nghĩa vụ kiểm thử
                <textarea
                  className="apple-input mt-2 min-h-24 w-full"
                  value={answerKeyDrafts[item.case_id]?.obligations || ""}
                  onChange={(event) =>
                    setAnswerKeyDrafts((current) => ({
                      ...current,
                      [item.case_id]: { ...current[item.case_id], obligations: event.target.value },
                    }))
                  }
                  placeholder="AUTH-01 | khóa tài khoản sau đủ số lần đăng nhập sai liên tiếp | mã phiên bản nguồn | trích dẫn chính xác"
                />
              </label>
              <label className="field-label block">
                Nhóm vấn đề cần làm rõ (nếu có, mỗi dòng một nhãn)
                <textarea
                  className="apple-input mt-2 min-h-16 w-full"
                  value={answerKeyDrafts[item.case_id]?.clarifications || ""}
                  onChange={(event) =>
                    setAnswerKeyDrafts((current) => ({
                      ...current,
                      [item.case_id]: {
                        ...current[item.case_id],
                        clarifications: event.target.value,
                      },
                    }))
                  }
                />
              </label>
              {!preparedCases[index] && (
                <p className="text-xs text-warning">
                  Cần mã nghĩa vụ duy nhất, mô tả ý nghĩa nghiệp vụ và trích dẫn nguyên văn đúng
                  phiên bản nguồn.
                </p>
              )}
            </section>
          ))}
        </div>
      </Panel>

      <Panel title="Bộ đánh giá và kết quả">
        <div className="space-y-4 p-4">
          <label className="field-label block">
            Bộ dữ liệu của dự án
            <select
              className="apple-input mt-2 w-full"
              value={selectedDataset?.dataset_id || ""}
              onChange={(event) => void openDataset(event.target.value)}
            >
              <option value="">Chọn bộ dữ liệu</option>
              {ownedDatasets.map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.title} · {dataset.case_count} ca ·{" "}
                  {dataset.reference_provenance === "SELF_PREPARED_REFERENCE"
                    ? "Tự chuẩn bị · chưa xác thực độc lập"
                    : dataset.ready_for_run
                      ? "Đã rà soát độc lập"
                      : "Chờ rà soát độc lập"}
                </option>
              ))}
            </select>
          </label>

          {selectedDataset && !selectedDatasetReady && isIndependentReviewer && (
            <div className="space-y-3 rounded-xl border border-border bg-surface-quiet p-4">
              <p className="text-sm leading-6 text-ink-muted">
                Đối chiếu riêng từng ca với phiên bản yêu cầu, ý nghĩa của từng nghĩa vụ, tiêu chí
                chấp nhận và căn cứ nguồn. Chỉ đánh dấu sau khi đã kiểm tra ca đó; đây là bước rà
                soát nhãn chuẩn, không phải xác nhận đầu ra AI.
              </p>
              <p className="text-xs text-ink-faint">
                Đã rà soát {reviewedCaseIds.length}/{selectedDataset.cases.length} ca
              </p>
              <div className="max-h-96 space-y-2 overflow-y-auto rounded-lg border border-border bg-surface p-3">
                {selectedDataset.cases.map((item) => {
                  const checked = reviewedCaseIds.includes(item.case_id);
                  return (
                    <label
                      className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3"
                      key={item.case_id}
                    >
                      <input
                        className="mt-1"
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setReviewedCaseIds((current) =>
                            checked
                              ? current.filter((caseId) => caseId !== item.case_id)
                              : [...current, item.case_id],
                          )
                        }
                      />
                      <span className="min-w-0 space-y-1">
                        <span className="block font-medium text-ink">{item.case_id}</span>
                        <span className="block text-xs text-ink-muted">
                          {item.expected_obligation_keys?.length || 0} nghĩa vụ kiểm thử ·{" "}
                          {item.expected_source_quotes?.length || 0} căn cứ nguồn
                        </span>
                        <span className="block whitespace-pre-wrap text-sm text-ink-muted">
                          {item.sources?.[0]?.text || "Không có nội dung nguồn"}
                        </span>
                        <span className="block whitespace-pre-wrap text-xs text-ink-muted">
                          {Object.entries(item.expected_obligation_meanings || {})
                            .map(([key, meaning]) => `${key}: ${meaning}`)
                            .join(" · ")}
                        </span>
                        <span className="block text-xs text-ink-faint">
                          {Object.values(item.expected_obligation_sources || {}).join(" · ")}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
              <label className="field-label block">
                Ghi chú về cách đối chiếu đáp án
                <textarea
                  className="apple-input mt-2 min-h-24 w-full"
                  value={reviewRationale}
                  maxLength={2000}
                  onChange={(event) => setReviewRationale(event.target.value)}
                  placeholder="Nêu cách đối chiếu tiêu chí đã duyệt với nội dung yêu cầu…"
                />
              </label>
              <button
                className="apple-button"
                type="button"
                disabled={saving || !allCasesReviewed || reviewRationale.trim().length < 20}
                onClick={() => void reviewDataset()}
              >
                {saving ? "Đang lưu rà soát…" : "Xác nhận đã rà soát từng ca"}
              </button>
            </div>
          )}

          {selectedDataset && !selectedDatasetReady && !isIndependentReviewer && (
            <p className="rounded-lg border border-warning/40 bg-warning-soft p-3 text-sm text-warning">
              Người tạo không thể tự rà soát đáp án. Cần một quản trị viên khác kiểm tra từng ca
              trước khi chạy.
            </p>
          )}

          {selectedDatasetReady && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface-quiet p-4">
              <p className="text-sm text-ink-muted">
                Phiên bản {selectedDataset.revision} · {selectedDataset.cases.length} ca · bốn
                pipeline (có cặp trước/sau Self-review) · ba lượt mỗi pipeline ·{" "}
                {selectedDataset.reference_provenance === "SELF_PREPARED_REFERENCE"
                  ? "đáp án tự chuẩn bị, chưa được kiểm chứng độc lập."
                  : "đáp án đã được rà soát độc lập."}
              </p>
              <button
                className="apple-button"
                type="button"
                disabled={running}
                onClick={() => void runDataset()}
              >
                {running ? "Đang chạy đánh giá…" : "Chạy đánh giá thực nghiệm"}
              </button>
            </div>
          )}

          {report && (
            <div className="space-y-3">
              <p className="text-sm text-ink-muted">
                {report.completed_repetitions}/{report.requested_repetitions} lượt hoàn tất ·{" "}
                {report.failed_repetitions} lượt lỗi · {selectedDataset.cases.length} ca.
              </p>
              <p className="text-xs text-ink-faint">
                Điểm ngữ nghĩa là ước lượng của AI judge so với mô tả nghĩa vụ do người biên soạn
                nhập; không phải xác nhận độc lập.
              </p>
              <DataTable
                items={benchmarkResultRows(report)}
                empty="Chưa có chỉ số đủ dữ liệu để hiển thị"
                columns={[
                  { key: "pipeline", label: "Phương pháp" },
                  { key: "metric", label: "Chỉ số" },
                  { key: "mean", label: "Trung bình" },
                  { key: "spread", label: "Khoảng thấp–cao" },
                  { key: "cases", label: "Số ca chấm được" },
                  { key: "runs", label: "Lượt có điểm" },
                ]}
              />
            </div>
          )}

          <DataTable
            items={runHistory.map((item) => ({ ...item, _id: item.run_id }))}
            empty="Bộ dữ liệu này chưa có lượt chạy"
            columns={[
              {
                key: "created_at",
                label: "Thời điểm",
                render: (item) => formatDate(item.created_at),
              },
              { key: "total_cases", label: "Số ca" },
              {
                key: "execution_status",
                label: "Trạng thái",
                render: (item) => valueLabel(item.execution_status),
              },
              {
                key: "pipeline_failures",
                label: "Phương pháp lỗi",
                render: (item) => item.pipeline_failures?.length || 0,
              },
              {
                key: "pipeline_rejections",
                label: "Đầu ra bị từ chối",
                render: (item) => item.pipeline_rejections?.length || 0,
              },
            ]}
          />

          <DataTable
            items={ownedDatasets.map((dataset) => ({
              ...dataset,
              status: dataset.ready_for_run ? "Đã duyệt" : "Chờ duyệt độc lập",
            }))}
            empty="Chưa có bộ đánh giá trên dữ liệu thực tế nào cho dự án"
            columns={[
              { key: "title", label: "Bộ dữ liệu" },
              { key: "case_count", label: "Số ca" },
              { key: "status", label: "Trạng thái" },
              {
                key: "created_at",
                label: "Tạo lúc",
                render: (item) => formatDate(item.created_at),
              },
            ]}
          />
        </div>
      </Panel>
    </div>
  );
}
