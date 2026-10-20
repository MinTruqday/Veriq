"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "./DataTable";
import StatisticalControlChart from "./StatisticalControlChart";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";

const lines = (value) =>
  String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

export default function ProcessImprovementPanel({ project }) {
  const [proposals, setProposals] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [definitions, setDefinitions] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [causalAnalyses, setCausalAnalyses] = useState([]);
  const [completionReports, setCompletionReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      setLoading(true);
      const permissions = new Set(project.current_permissions || []);
      const [
        proposalResult,
        analysisResult,
        definitionResult,
        snapshotResult,
        causalResult,
        completionResult,
      ] = await Promise.all([
        testingApi.listProcessImprovements(project._id),
        permissions.has("statisticalquality.read")
          ? testingApi.listStatisticalQualityAnalyses(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("measurement.read")
          ? testingApi.listMeasurementDefinitions(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("measurement.read")
          ? testingApi.listMeasurementSnapshots(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("causalanalysis.read")
          ? testingApi.listCausalAnalyses(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("testcompletion.read")
          ? testingApi.listTestCompletionReports(project._id, { page_size: 200 })
          : Promise.resolve({ items: [] }),
      ]);
      setProposals(proposalResult.items || []);
      setAnalyses(analysisResult.items || []);
      setDefinitions(definitionResult.items || []);
      setSnapshots(snapshotResult.items || []);
      setCausalAnalyses(causalResult.items || []);
      setCompletionReports(completionResult.items || []);
      setSelected((current) =>
        current
          ? (proposalResult.items || []).find((item) => item._id === current._id) || null
          : null,
      );
      setSelectedAnalysis((current) =>
        current
          ? (analysisResult.items || []).find((item) => item._id === current._id) || null
          : null,
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);
  const snapshotOptions = useMemo(
    () =>
      snapshots.map((item) => ({
        value: item._id,
        label: `${item.measurement_key || item._id} · ${item.value ?? "Chưa có giá trị"}`,
      })),
    [snapshots],
  );
  const createProposal = async () => {
    const answer = await ask({
      title: "Tạo đề xuất cải tiến quy trình",
      confirmLabel: "Tạo đề xuất",
      fields: [
        {
          name: "source",
          label: "Nguồn phát hiện",
          options: [
            { value: "LESSON_LEARNED", label: "Bài học kinh nghiệm" },
            { value: "RCA", label: "Phân tích nguyên nhân" },
            { value: "MEASUREMENT", label: "Đo lường" },
            { value: "REVIEW", label: "Rà soát" },
            { value: "MANUAL", label: "Ghi nhận thủ công" },
          ],
        },
        {
          name: "observed_problem",
          label: "Vấn đề quan sát được",
          required: true,
          multiline: true,
        },
        {
          name: "evidence_refs",
          label: "Mã bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
        },
        { name: "proposed_change", label: "Thay đổi đề xuất", required: true, multiline: true },
        { name: "expected_effect", label: "Hiệu quả kỳ vọng", required: true, multiline: true },
        { name: "experiment_scope", label: "Phạm vi thử nghiệm", required: true, multiline: true },
        {
          name: "owner_id",
          label: "Mã người phụ trách",
          required: true,
          initialValue: project.current_membership?.user_id || "",
        },
      ],
    });
    if (!answer) return;
    try {
      const value = await testingApi.createProcessImprovement(project._id, {
        idempotency_key: crypto.randomUUID(),
        source: answer.source,
        source_refs: [],
        observed_problem: answer.observed_problem,
        evidence_refs: lines(answer.evidence_refs),
        proposed_change: answer.proposed_change,
        expected_effect: answer.expected_effect,
        experiment_scope: answer.experiment_scope,
        owner_id: answer.owner_id,
      });
      await load();
      setSelected(value);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (action, title) => {
    const answer = await ask({
      title,
      confirmLabel: "Xác nhận",
      fields: [{ name: "note", label: "Ghi chú", multiline: true }],
    });
    if (!answer) return;
    try {
      const value = await action({ expected_revision: selected.revision, note: answer.note });
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const linkSources = async () => {
    const lessonOptions = completionReports.flatMap((report) =>
      (report.lessons_learned || []).map((item) => ({
        value: item.lesson_id,
        label: `${item.title || item.lesson_id} · ${report.completion_key || report._id}`,
      })),
    );
    const causalOptions = causalAnalyses.map((item) => ({
      value: item._id,
      label: item.title || item.problem_statement || item._id,
    }));
    const answer = await ask({
      title: "Liên kết nguồn cải tiến",
      confirmLabel: "Lưu liên kết",
      fields: [
        {
          name: "lesson_refs",
          label: "Bài học kinh nghiệm",
          multiple: true,
          options: lessonOptions,
          initialValue: selected.lesson_refs || [],
        },
        {
          name: "causal_analysis_refs",
          label: "Phân tích nguyên nhân",
          multiple: true,
          options: causalOptions,
          initialValue: selected.causal_analysis_refs || [],
        },
      ],
    });
    if (!answer) return;
    const lessonRefs = Array.isArray(answer.lesson_refs) ? answer.lesson_refs : [];
    const causalRefs = Array.isArray(answer.causal_analysis_refs)
      ? answer.causal_analysis_refs
      : [];
    if (!lessonRefs.length && !causalRefs.length) {
      setError("Phải chọn ít nhất một bài học hoặc phân tích nguyên nhân");
      return;
    }
    try {
      const value = await testingApi.linkProcessImprovementSources(selected._id, {
        expected_revision: selected.revision,
        lesson_refs: lessonRefs,
        causal_analysis_refs: causalRefs,
      });
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const chooseMetrics = async (mode) => {
    const answer = await ask({
      title: mode === "baseline" ? "Ghi nhận đường cơ sở" : "Đánh giá thử nghiệm",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "measurement_snapshot_refs",
          label: "Ảnh đo lường",
          required: true,
          multiple: true,
          options: snapshotOptions,
        },
        ...(mode === "result"
          ? [
              {
                name: "decision",
                label: "Đề xuất quyết định",
                options: [
                  { value: "ADOPT", label: "Áp dụng" },
                  { value: "REJECT", label: "Từ chối" },
                ],
              },
              { name: "conclusion", label: "Kết luận", required: true, multiline: true },
            ]
          : []),
        { name: "note", label: "Ghi chú", multiline: true },
      ],
    });
    if (!answer) return;
    try {
      const payload = {
        expected_revision: selected.revision,
        measurement_snapshot_refs: Array.isArray(answer.measurement_snapshot_refs)
          ? answer.measurement_snapshot_refs
          : lines(answer.measurement_snapshot_refs),
        note: answer.note,
      };
      const value =
        mode === "baseline"
          ? await testingApi.recordProcessImprovementBaseline(selected._id, payload)
          : await testingApi.evaluateProcessImprovement(selected._id, {
              ...payload,
              decision: answer.decision,
              conclusion: answer.conclusion,
            });
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createControlChart = async () => {
    const definitionOptions = definitions.map((item) => ({ value: item._id, label: item.name }));
    const answer = await ask({
      title: "Tạo biểu đồ kiểm soát",
      confirmLabel: "Tính toán",
      fields: [
        {
          name: "measurement_definition_id",
          label: "Định nghĩa đo lường",
          required: true,
          options: definitionOptions,
        },
        { name: "baseline_label", label: "Tên cửa sổ cơ sở", required: true },
        {
          name: "measurement_snapshot_refs",
          label: "Chọn tối thiểu năm ảnh đo lường",
          required: true,
          multiple: true,
          options: snapshotOptions,
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.calculateStatisticalQualityBaseline(project._id, {
        idempotency_key: crypto.randomUUID(),
        measurement_definition_id: answer.measurement_definition_id,
        measurement_snapshot_refs: Array.isArray(answer.measurement_snapshot_refs)
          ? answer.measurement_snapshot_refs
          : lines(answer.measurement_snapshot_refs),
        baseline_label: answer.baseline_label,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const compareAnalyses = async () => {
    const options = analyses.map((item) => ({ value: item._id, label: item.baseline_label }));
    const answer = await ask({
      title: "So sánh trước và sau cải tiến",
      confirmLabel: "So sánh",
      fields: [
        { name: "before_analysis_id", label: "Cửa sổ trước", required: true, options },
        { name: "after_analysis_id", label: "Cửa sổ sau", required: true, options },
        {
          name: "process_improvement_id",
          label: "Đề xuất cải tiến",
          options: [
            { value: "", label: "Không liên kết" },
            ...proposals.map((item) => ({ value: item._id, label: item.observed_problem })),
          ],
        },
      ],
    });
    if (!answer) return;
    try {
      setComparison(
        await testingApi.compareStatisticalQuality(project._id, {
          ...answer,
          process_improvement_id: answer.process_improvement_id || null,
        }),
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const annotateCause = async () => {
    const answer = await ask({
      title: "Ghi nhận nguyên nhân đặc biệt",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "measurement_snapshot_id",
          label: "Điểm đo",
          required: true,
          options: (selectedAnalysis.points || []).map((item) => ({
            value: item.snapshot_id,
            label: `${item.snapshot_id} · ${item.value}`,
          })),
        },
        { name: "cause", label: "Nguyên nhân", required: true, multiline: true },
        {
          name: "evidence_refs",
          label: "Mã bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
        },
      ],
    });
    if (!answer) return;
    try {
      const value = await testingApi.annotateStatisticalSpecialCause(selectedAnalysis._id, {
        expected_revision: selectedAnalysis.revision,
        measurement_snapshot_id: answer.measurement_snapshot_id,
        cause: answer.cause,
        evidence_refs: lines(answer.evidence_refs),
      });
      setSelectedAnalysis(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Cải tiến quy trình và kiểm soát thống kê"
      actions={
        <div className="flex flex-wrap gap-2">
          {can("statisticalquality.read") && analyses.length > 1 && (
            <button className="secondary-button" type="button" onClick={compareAnalyses}>
              So sánh trước sau
            </button>
          )}
          {can("statisticalquality.manage") && (
            <button className="secondary-button" type="button" onClick={createControlChart}>
              Tạo biểu đồ kiểm soát
            </button>
          )}
          {can("processimprovement.create") && (
            <button className="apple-button" type="button" onClick={createProposal}>
              Tạo đề xuất cải tiến
            </button>
          )}
        </div>
      }
    >
      {dialog}
      {error && (
        <div className="p-5">
          <ErrorState message={error} />
        </div>
      )}
      {loading ? (
        <LoadingState />
      ) : (
        <>
          <DataTable
            items={proposals}
            empty="Chưa có đề xuất cải tiến quy trình"
            columns={[
              { key: "observed_problem", label: "Vấn đề" },
              { key: "owner_id", label: "Người phụ trách" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "updated_at",
                label: "Cập nhật",
                render: (item) => formatDate(item.updated_at),
              },
              {
                key: "actions",
                label: "Thao tác",
                render: (item) => (
                  <button className="text-button" type="button" onClick={() => setSelected(item)}>
                    Mở
                  </button>
                ),
              },
            ]}
          />
          {selected && (
            <div className="border-t border-border p-5">
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase text-ink-muted">Thay đổi đề xuất</p>
                  <p className="mt-1 text-sm text-ink">{selected.proposed_change}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase text-ink-muted">Hiệu quả kỳ vọng</p>
                  <p className="mt-1 text-sm text-ink">{selected.expected_effect}</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {selected.status === "PROPOSED" && can("processimprovement.update") && (
                  <button className="secondary-button" type="button" onClick={linkSources}>
                    Liên kết bài học và phân tích nguyên nhân gốc
                  </button>
                )}
                {selected.status === "PROPOSED" && can("processimprovement.approve") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      transition(
                        (payload) =>
                          testingApi.approveProcessImprovementExperiment(selected._id, payload),
                        "Phê duyệt thử nghiệm",
                      )
                    }
                  >
                    Phê duyệt thử nghiệm
                  </button>
                )}
                {selected.status === "APPROVED_EXPERIMENT" && can("processimprovement.measure") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => chooseMetrics("baseline")}
                  >
                    Ghi đường cơ sở
                  </button>
                )}
                {selected.status === "APPROVED_EXPERIMENT" &&
                  selected.baseline_metrics?.length > 0 &&
                  can("processimprovement.evaluate") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        transition(
                          (payload) =>
                            testingApi.startProcessImprovementExperiment(selected._id, payload),
                          "Bắt đầu thử nghiệm",
                        )
                      }
                    >
                      Bắt đầu thử nghiệm
                    </button>
                  )}
                {selected.status === "RUNNING" && can("processimprovement.evaluate") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => chooseMetrics("result")}
                  >
                    Đánh giá kết quả
                  </button>
                )}
                {selected.status === "EVALUATED" &&
                  selected.decision === "ADOPT" &&
                  can("processimprovement.decide") && (
                    <button
                      className="apple-button"
                      type="button"
                      onClick={() =>
                        transition(
                          (payload) =>
                            testingApi.decideProcessImprovement(selected._id, payload, true),
                          "Áp dụng cải tiến",
                        )
                      }
                    >
                      Áp dụng
                    </button>
                  )}
                {selected.status === "EVALUATED" &&
                  selected.decision === "REJECT" &&
                  can("processimprovement.decide") && (
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() =>
                        transition(
                          (payload) =>
                            testingApi.decideProcessImprovement(selected._id, payload, false),
                          "Từ chối cải tiến",
                        )
                      }
                    >
                      Từ chối
                    </button>
                  )}
              </div>
              {selected.result_comparison?.length > 0 && (
                <div className="mt-5">
                  <DataTable
                    items={selected.result_comparison}
                    empty="Chưa có dữ liệu so sánh"
                    columns={[
                      { key: "measurement_key", label: "Chỉ số" },
                      { key: "baseline_value", label: "Đường cơ sở" },
                      { key: "result_value", label: "Kết quả" },
                      { key: "delta", label: "Chênh lệch" },
                      { key: "unit", label: "Đơn vị" },
                    ]}
                  />
                </div>
              )}
            </div>
          )}
          {can("statisticalquality.read") && (
            <div className="border-t border-border">
              <DataTable
                items={analyses}
                empty="Chưa đủ dữ liệu để tạo biểu đồ kiểm soát"
                columns={[
                  { key: "baseline_label", label: "Cửa sổ cơ sở" },
                  { key: "measurement_key", label: "Chỉ số" },
                  { key: "center_line", label: "Đường trung tâm" },
                  { key: "lower_control_limit", label: "Giới hạn dưới" },
                  { key: "upper_control_limit", label: "Giới hạn trên" },
                  {
                    key: "process_status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.process_status} />,
                  },
                  {
                    key: "actions",
                    label: "Thao tác",
                    render: (item) => (
                      <button
                        className="text-button"
                        type="button"
                        onClick={() => setSelectedAnalysis(item)}
                      >
                        Xem biểu đồ
                      </button>
                    ),
                  },
                ]}
              />
            </div>
          )}
          {selectedAnalysis && (
            <div className="space-y-4 border-t border-border p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{selectedAnalysis.baseline_label}</h3>
                  <p className="text-sm text-ink-muted">
                    {selectedAnalysis.measurement_key} ·{" "}
                    {valueLabel(selectedAnalysis.process_status)}
                  </p>
                </div>
                {can("statisticalquality.annotate") && (
                  <button className="secondary-button" type="button" onClick={annotateCause}>
                    Ghi nguyên nhân đặc biệt
                  </button>
                )}
              </div>
              <StatisticalControlChart analysis={selectedAnalysis} />
              <DataTable
                items={selectedAnalysis.special_causes || []}
                empty="Chưa ghi nhận nguyên nhân đặc biệt"
                columns={[
                  { key: "measurement_snapshot_id", label: "Điểm đo" },
                  { key: "cause", label: "Nguyên nhân" },
                  {
                    key: "created_at",
                    label: "Thời điểm",
                    render: (item) => formatDate(item.created_at),
                  },
                ]}
              />
            </div>
          )}
          {comparison && (
            <div className="grid gap-3 border-t border-border p-5 sm:grid-cols-3">
              <div>
                <p className="text-xs uppercase text-ink-muted">Chênh lệch trung tâm</p>
                <p className="text-lg font-semibold">{comparison.center_line_delta}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-ink-muted">Ngoại lệ trước</p>
                <p className="text-lg font-semibold">{comparison.outlier_count_before}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-ink-muted">Ngoại lệ sau</p>
                <p className="text-lg font-semibold">{comparison.outlier_count_after}</p>
              </div>
            </div>
          )}
        </>
      )}
    </Panel>
  );
}
