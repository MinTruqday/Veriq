"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import TestabilityPipelineBenchmarkPanel from "./TestabilityPipelineBenchmarkPanel";

const benchmarkPath = "project:";

function requirementCase(requirement) {
  const version = requirement.current_version || {};
  const criteria = (version.acceptance_criteria || []).filter(
    (criterion) => criterion.status === "approved" && String(criterion.plain_text || "").trim(),
  );
  if (!version._id || !criteria.length) return null;

  const sourceRef = String(version._id);
  const sourceQuotes = [...new Set(criteria.map((criterion) => criterion.plain_text.trim()))];
  const obligationSources = Object.fromEntries(
    criteria.map((criterion, index) => [
      String(criterion._id || `${requirement.requirement_key}-AC-${index + 1}`),
      criterion.plain_text.trim(),
    ]),
  );
  const sourceText = [
    version.title,
    version.plain_text_projection,
    ...criteria.map((criterion) => criterion.plain_text),
  ]
    .filter((value) => typeof value === "string" && value.trim())
    .join("\n");

  return {
    case_id: String(requirement.requirement_key || version._id),
    task_instruction:
      "Trích xuất nghĩa vụ kiểm thử chỉ từ tiêu chí chấp nhận đã duyệt. Giữ nguyên căn cứ nguồn; không tự bổ sung hành vi hoặc điều kiện chưa được nêu.",
    sources: [
      {
        source_id: String(requirement.requirement_key || version._id),
        artifact_type: "requirement_version",
        artifact_version_id: sourceRef,
        authority: "APPROVED_SOURCE",
        text: sourceText,
      },
    ],
    expected_source_quotes: sourceQuotes,
    expected_source_quote_sources: Object.fromEntries(
      sourceQuotes.map((quote) => [quote, [sourceRef]]),
    ),
    expected_obligation_keys: Object.keys(obligationSources),
    expected_obligation_sources: obligationSources,
    expected_obligation_source_refs: Object.fromEntries(
      Object.keys(obligationSources).map((key) => [key, sourceRef]),
    ),
  };
}

function metricLabel(metric) {
  const labels = {
    source_quote_validity: "Tính hợp lệ của trích dẫn",
    source_quote_precision: "Precision trích dẫn nguồn",
    source_quote_recall: "Recall trích dẫn nguồn",
    source_quote_source_precision: "Precision phiên bản nguồn",
    source_quote_source_recall: "Recall phiên bản nguồn",
    obligation_precision: "Precision nghĩa vụ kiểm thử",
    obligation_recall: "Recall nghĩa vụ kiểm thử",
    clarification_precision: "Precision câu hỏi làm rõ",
    clarification_recall: "Recall câu hỏi làm rõ",
    clarification_priority_ndcg: "NDCG ưu tiên câu hỏi",
  };
  return labels[metric] || valueLabel(metric);
}

function formatMetric(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Chưa đủ dữ liệu";
}

function datasetReady(dataset) {
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
        ((!item.expected_clarification_categories?.length &&
          !item.expected_clarification_codes?.length) ||
          reviewItem.clarifications_verified),
    );
  });
}

function benchmarkResultRows(report) {
  return Object.entries(report?.pipeline_statistics || {}).flatMap(([pipeline, summary]) =>
    Object.entries(summary.metrics || {}).map(([metric, value]) => ({
      _id: `${pipeline}-${metric}`,
      pipeline:
        {
          compiler: "Bộ biên dịch khả năng kiểm thử",
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
}

export default function RealTestabilityBenchmarkPanel({ project }) {
  const { user } = useAuth();
  const canManageBenchmark = user?.system_role === "ADMIN";
  const [requirements, setRequirements] = useState([]);
  const [selectedRequirementIds, setSelectedRequirementIds] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [report, setReport] = useState(null);
  const [runHistory, setRunHistory] = useState([]);
  const [reviewRationale, setReviewRationale] = useState("");
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
    if (!selectedCases.length) return;
    setSaving(true);
    setError("");
    try {
      const dataset = await testingApi.createTestabilityBenchmarkDataset({
        dataset_id: `${benchmarkPath}${project._id}:${crypto.randomUUID()}`,
        title: `Requirement đã duyệt · ${project.name || project.key || project._id} · ${new Date().toLocaleDateString("vi-VN")}`,
        cases: selectedCases,
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
      <TestabilityPipelineBenchmarkPanel project={project} requirements={requirements} />
      {error && <ErrorState message={error} />}
      <Panel title="Đánh giá thực nghiệm trên yêu cầu đã duyệt">
        <div className="space-y-3 p-4 text-sm leading-6 text-ink-muted">
          <p>
            Mỗi ca lấy từ phiên bản yêu cầu đã duyệt và tiêu chí chấp nhận đã lưu trong dự án. Đáp
            án kỳ vọng là tiêu chí đã duyệt; không lấy đầu ra của AI làm đáp án để tự chấm.
          </p>
          <p>
            Chỉ chấm trích dẫn nguồn và độ bao phủ nghĩa vụ kiểm thử. Bộ dữ liệu không có nhãn độc
            lập cho câu hỏi làm rõ nên các chỉ số đó được để trống, không suy đoán.
          </p>
          <p>
            Bộ đáp án được một quản trị viên khác kiểm tra một lần trước lần chạy đầu. Sau đó có thể
            chạy lại ba phương pháp và lưu kết quả theo phiên bản bộ dữ liệu.
          </p>
        </div>
      </Panel>

      <Panel title="Tạo bộ đánh giá từ dự án này">
        <div className="space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">
              Có {eligibleRequirements.length} yêu cầu đã duyệt kèm tiêu chí chấp nhận để đưa vào bộ
              đánh giá.
            </p>
            <button
              className="apple-button"
              type="button"
              disabled={saving || !selectedCases.length}
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
                      {requirement?.current_version?.title || "Yêu cầu"} ·{" "}
                      {item.expected_obligation_keys.length} tiêu chí chấp nhận
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
                  {dataset.ready_for_run ? "Đã duyệt" : "Chờ duyệt"}
                </option>
              ))}
            </select>
          </label>

          {selectedDataset && !selectedDatasetReady && isIndependentReviewer && (
            <div className="space-y-3 rounded-xl border border-border bg-surface-quiet p-4">
              <p className="text-sm leading-6 text-ink-muted">
                Đối chiếu riêng từng ca với phiên bản yêu cầu, tiêu chí chấp nhận và căn cứ nguồn.
                Chỉ đánh dấu sau khi đã kiểm tra ca đó; đây là bước rà soát nhãn chuẩn, không phải
                xác nhận đầu ra AI.
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
                Phiên bản {selectedDataset.revision} · {selectedDataset.cases.length} ca · ba phương
                pháp · ba lượt mỗi phương pháp.
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
