"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import { ErrorState, LoadingState, Panel, StatusPill } from "../components/WorkspacePrimitives";
import { formatDate, messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";

const pipelineLabels = {
  compiler: "Lập bản thiết kế kiểm thử",
  direct_generation: "Sinh ca kiểm thử trực tiếp",
  clarification_without_obligation_planning: "Chỉ lập câu hỏi làm rõ",
};

const metricLabels = {
  source_quote_recall: "Độ bao phủ trích dẫn nguồn",
  obligation_recall: "Độ bao phủ nghĩa vụ kiểm thử",
  clarification_recall: "Độ bao phủ câu hỏi làm rõ",
  clarification_priority_ndcg: "Thứ tự ưu tiên câu hỏi",
};

function percent(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Chưa có điểm";
}

function benchmarkStatus(value) {
  return value === "COMPLETE" ? "COMPLETED" : value === "PARTIAL" ? "PARTIAL_EXECUTION" : value;
}

function reportRows(report) {
  return Object.entries(report?.pipeline_statistics || {}).flatMap(([pipeline, summary]) =>
    Object.entries(summary.metrics || {}).map(([metric, stats]) => ({
      _id: `${pipeline}-${metric}`,
      pipeline: pipelineLabels[pipeline] || pipeline,
      metric: metricLabels[metric] || metric,
      mean: percent(stats.mean),
      spread:
        typeof stats.minimum === "number" && typeof stats.maximum === "number"
          ? `${percent(stats.minimum)} – ${percent(stats.maximum)}`
          : "Chưa đủ dữ liệu",
      runs: `${stats.observed_runs || 0}/${report.requested_repetitions}`,
      cases: stats.stable_case_count ?? stats.paired_case_count ?? "—",
    })),
  );
}

function pairedReportRows(report) {
  return Object.entries(report?.paired_pipeline_statistics || {}).flatMap(([comparison, summary]) =>
    [
      ["left_metrics", summary.left_pipeline],
      ["right_metrics", summary.right_pipeline],
    ].flatMap(([side, pipeline]) =>
      Object.entries(summary[side] || {})
        .filter(([metric]) => metricLabels[metric])
        .map(([metric, stats]) => ({
          _id: `${comparison}-${pipeline}-${metric}`,
          comparison: `${pipelineLabels[summary.left_pipeline] || summary.left_pipeline} / ${pipelineLabels[summary.right_pipeline] || summary.right_pipeline}`,
          pipeline: pipelineLabels[pipeline] || pipeline,
          metric: metricLabels[metric],
          mean: percent(stats.mean),
          spread:
            typeof stats.minimum === "number" && typeof stats.maximum === "number"
              ? `${percent(stats.minimum)} – ${percent(stats.maximum)}`
              : "Chưa đủ dữ liệu",
          runs: `${stats.observed_runs || 0}/${report.requested_repetitions}`,
          cases: stats.paired_case_count ?? 0,
        })),
    ),
  );
}

export default function TestabilityBenchmarkPanel() {
  const [runs, setRuns] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const loadRuns = useCallback(async () => {
    setError("");
    try {
      setRuns(await testingApi.listSyntheticTestabilityBenchmarkRuns(20));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  const runBenchmark = async () => {
    setRunning(true);
    setError("");
    setReport(null);
    try {
      setReport(await testingApi.runSyntheticTestabilityBenchmark());
      await loadRuns();
    } catch (reason) {
      setError(messageOf(reason));
      await loadRuns();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      <Panel
        title="Kiểm tra AI trên tình huống thử"
        actions={
          <button
            type="button"
            className="primary-button"
            disabled={running}
            onClick={() => void runBenchmark()}
          >
            {running ? "Đang so sánh các cách xử lý…" : "Chạy đánh giá"}
          </button>
        }
      >
        <div className="space-y-3 text-sm text-ink-muted">
          <p>
            Bộ thử gồm 30 tình huống tạo sẵn: 10 tình huống đủ căn cứ, 10 thiếu hoặc mơ hồ, và 10
            trùng lặp hoặc mâu thuẫn. Mỗi cách xử lý được chạy ba lần.
          </p>
          <p>
            Đáp án chuẩn được tạo cùng các tình huống, chưa được chuyên gia độc lập xác nhận. Kết
            quả chỉ mô tả cách AI xử lý bộ thử này; không chứng minh chất lượng ngoài thực tế hoặc
            ưu thế so với sản phẩm khác. Việc chạy gọi các cách xử lý AI thật nên có thể mất vài
            phút.
          </p>
          <p>
            Một số tình huống có nhiều điểm thiếu. Tiêu chí “Thứ tự ưu tiên câu hỏi” so sánh thứ tự
            AI hỏi với thứ tự đã ghi trong đáp án chuẩn; đây chưa phải đánh giá độc lập của giảng
            viên hoặc chuyên gia.
          </p>
          {report && (
            <div className="rounded-xl border border-line bg-surface-quiet p-4 text-ink">
              <div className="flex flex-wrap items-center gap-3">
                <StatusPill value={benchmarkStatus(report.execution_status)} />
                <span>
                  {report.completed_repetitions}/{report.requested_repetitions} lượt hoàn tất
                </span>
                <span>{report.failed_repetitions} lượt lỗi</span>
                <span>{report.benchmark_design?.case_count || 30} tình huống</span>
              </div>
              {report.repetition_failures?.length > 0 && (
                <p className="mt-3 text-sm text-danger">
                  Có lượt lỗi; các lượt còn lại vẫn được giữ trong lịch sử.
                </p>
              )}
            </div>
          )}
        </div>
      </Panel>

      {report && (
        <Panel title="Kết quả theo từng cách xử lý">
          <p className="mb-3 text-sm text-ink-muted">
            Mỗi cách xử lý dùng các tình huống được chấp nhận ổn định qua cả ba lượt; nhóm tình
            huống giữa các cách xử lý có thể khác nhau.
          </p>
          <DataTable
            items={reportRows(report)}
            empty="Chưa có tiêu chí đủ điều kiện để chấm"
            columns={[
              { key: "pipeline", label: "Cách xử lý" },
              { key: "metric", label: "Tiêu chí" },
              { key: "mean", label: "Trung bình" },
              { key: "spread", label: "Khoảng điểm thấp–cao" },
              { key: "runs", label: "Lượt có điểm" },
              { key: "cases", label: "Số tình huống đủ điều kiện" },
            ]}
          />
        </Panel>
      )}

      {report && (
        <Panel title="So sánh công bằng trên cùng tình huống">
          <p className="mb-3 text-sm text-ink-muted">
            Chỉ so điểm trên tình huống mà cả hai cách xử lý đều được chấp nhận qua mọi lượt; số
            tình huống ghép cặp được hiển thị để thấy mẫu số thực tế.
          </p>
          <DataTable
            items={pairedReportRows(report)}
            empty="Chưa có đủ tình huống được cả hai cách xử lý chấp nhận ổn định để so sánh"
            columns={[
              { key: "comparison", label: "Cặp so sánh" },
              { key: "pipeline", label: "Cách xử lý" },
              { key: "metric", label: "Tiêu chí" },
              { key: "mean", label: "Trung bình" },
              { key: "spread", label: "Khoảng điểm thấp–cao" },
              { key: "runs", label: "Lượt có điểm" },
              { key: "cases", label: "Số tình huống so sánh được" },
            ]}
          />
        </Panel>
      )}

      <Panel title="Lịch sử các lượt đánh giá">
        {loading ? (
          <LoadingState />
        ) : (
          <DataTable
            items={runs}
            empty="Chưa có lượt đánh giá tổng hợp"
            columns={[
              {
                key: "dataset_id",
                label: "Bộ tình huống",
                render: () => "Bộ tình huống tổng hợp",
              },
              {
                key: "created_at",
                label: "Thời điểm",
                render: (item) => formatDate(item.created_at),
              },
              {
                key: "execution_status",
                label: "Kết quả xử lý",
                render: (item) => <StatusPill value={benchmarkStatus(item.execution_status)} />,
              },
              { key: "total_cases", label: "Số tình huống" },
              {
                key: "pipeline_failures",
                label: "Cách xử lý lỗi",
                render: (item) => item.pipeline_failures?.length || 0,
              },
              {
                key: "pipeline_rejections",
                label: "Đầu ra bị từ chối",
                render: (item) => item.pipeline_rejections?.length || 0,
              },
            ]}
          />
        )}
      </Panel>
    </div>
  );
}
