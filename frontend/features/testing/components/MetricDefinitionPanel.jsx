"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import MetricTrendChart from "./MetricTrendChart";
import QualityMetricCard from "./QualityMetricCard";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";

const METRICS = {
  REQUIREMENT_COVERAGE: ["Độ phủ yêu cầu", "Yêu cầu được bao phủ trên tổng yêu cầu", "%", "RATIO"],
  AC_COVERAGE: [
    "Độ phủ tiêu chí chấp nhận",
    "Tiêu chí được bao phủ trên tổng tiêu chí",
    "%",
    "RATIO",
  ],
  CONDITION_COVERAGE: [
    "Độ phủ điều kiện kiểm thử",
    "Điều kiện được bao phủ trên tổng điều kiện kiểm thử",
    "%",
    "RATIO",
  ],
  RISK_COVERAGE: ["Độ phủ rủi ro", "Rủi ro được bao phủ trên tổng rủi ro", "%", "RATIO"],
  EXECUTION_PROGRESS: ["Tiến độ thực thi", "Kết quả đã hoàn tất trên tổng kết quả", "%", "RATIO"],
  PASS_RATE: ["Tỷ lệ đạt", "Kết quả đạt trên kết quả có quyết định", "%", "RATIO"],
  BLOCKED_RATE: ["Tỷ lệ bị chặn", "Kết quả bị chặn trên kết quả có quyết định", "%", "RATIO"],
  DEFECT_REOPEN_RATE: ["Tỷ lệ mở lại lỗi", "Lỗi từng mở lại trên tổng lỗi", "%", "RATIO"],
  CRITICAL_DEFECT_AGING: [
    "Tuổi lỗi nghiêm trọng",
    "Số ngày trung bình của lỗi nghiêm trọng đang mở",
    "ngày",
    "AVERAGE",
  ],
  MEAN_TIME_TO_RETEST: [
    "Thời gian trung bình tới kiểm thử lại",
    "Thời gian từ xử lý tới kiểm thử lại",
    "giờ",
    "AVERAGE",
  ],
  STALE_TEST_RATIO: [
    "Tỷ lệ ca kiểm thử lỗi thời",
    "Ca kiểm thử cần cập nhật trên tổng ca kiểm thử",
    "%",
    "RATIO",
  ],
  REQUIREMENT_VOLATILITY: [
    "Biến động yêu cầu",
    "Yêu cầu có nhiều phiên bản trên tổng yêu cầu",
    "%",
    "RATIO",
  ],
  IMPACT_PROPOSAL_ACCEPTANCE_RATE: [
    "Tỷ lệ chấp nhận đề xuất ảnh hưởng",
    "Đề xuất được chấp nhận trên tổng đề xuất",
    "%",
    "RATIO",
  ],
  REGRESSION_EFFECTIVENESS: [
    "Hiệu quả hồi quy",
    "Lỗi phát hiện trên ca kiểm thử hồi quy được chọn",
    "%",
    "RATIO",
  ],
  AUTOMATION_COVERAGE: [
    "Độ phủ tự động hóa",
    "Ca kiểm thử tự động trên tổng ca kiểm thử",
    "%",
    "RATIO",
  ],
  AUTOMATION_STABILITY: [
    "Độ ổn định tự động hóa",
    "Lần chạy tự động đạt trên tổng lần hoàn tất",
    "%",
    "RATIO",
  ],
  ESCAPED_DEFECT_RATE: [
    "Tỷ lệ lỗi lọt",
    "Lỗi môi trường vận hành trên tổng lỗi vận hành và lỗi đã loại bỏ",
    "%",
    "RATIO",
  ],
  DEFECT_REMOVAL_EFFICIENCY: [
    "Hiệu suất loại bỏ lỗi",
    "Lỗi loại bỏ trước môi trường vận hành trên tổng lỗi",
    "%",
    "RATIO",
  ],
};

export default function MetricDefinitionPanel({ project }) {
  const [definitions, setDefinitions] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [releases, setReleases] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [selectedKey, setSelectedKey] = useState("");
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      const canReadReleases = project.current_permissions?.includes("release.read");
      const [definitionResult, snapshotResult, releaseValues, alertResult] = await Promise.all([
        testingApi.listMeasurementDefinitions(project._id),
        testingApi.listMeasurementSnapshots(project._id),
        canReadReleases ? testingApi.listReleases(project._id) : Promise.resolve([]),
        testingApi.listMeasurementThresholdAlerts(project._id),
      ]);
      setDefinitions(definitionResult.items || []);
      setSnapshots(snapshotResult.items || []);
      setReleases(releaseValues || []);
      setAlerts(alertResult.items || []);
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    const answer = await ask({
      title: "Tạo định nghĩa đo lường",
      confirmLabel: "Tạo",
      fields: [
        {
          name: "key",
          label: "Chỉ số",
          options: Object.entries(METRICS).map(([value, item]) => ({ value, label: item[0] })),
        },
        { name: "objective", label: "Mục tiêu", required: true, multiline: true },
        { name: "target", label: "Mục tiêu số", type: "number" },
        { name: "warning", label: "Ngưỡng cảnh báo", type: "number" },
        { name: "critical", label: "Ngưỡng nghiêm trọng", type: "number" },
      ],
    });
    if (!answer) return;
    const metric = METRICS[answer.key];
    try {
      await testingApi.createMeasurementDefinition(project._id, {
        idempotency_key: crypto.randomUUID(),
        key: answer.key,
        name: metric[0],
        objective: answer.objective,
        description: metric[1],
        formula_type: "BUILT_IN",
        formula: answer.key,
        unit: metric[2],
        data_sources: ["testing-domain"],
        dimensions: ["release"],
        aggregation: metric[3],
        period: "RELEASE",
        target: answer.target === "" ? null : Number(answer.target),
        warning_threshold: answer.warning === "" ? null : Number(answer.warning),
        critical_threshold: answer.critical === "" ? null : Number(answer.critical),
        owner_role: "QA",
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const compareReleases = async () => {
    const options = releases.map((item) => ({
      value: item._id,
      label: item.name || item.version || item._id,
    }));
    const answer = await ask({
      title: "So sánh số liệu giữa bản phát hành",
      confirmLabel: "So sánh",
      fields: [
        { name: "release_a", label: "Bản phát hành gốc", required: true, options },
        { name: "release_b", label: "Bản phát hành đối chiếu", required: true, options },
      ],
    });
    if (!answer) return;
    try {
      setComparison(
        await testingApi.compareMeasurementReleases(
          project._id,
          answer.release_a,
          answer.release_b,
        ),
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const latestByDefinition = Object.fromEntries(
    snapshots.map((item) => [item.measurement_definition_id, item]),
  );
  const selectedSnapshots = snapshots.filter(
    (item) => !selectedKey || item.measurement_key === selectedKey,
  );
  return (
    <Panel
      title="Đo lường chất lượng"
      actions={
        <div className="flex flex-wrap gap-2">
          {releases.length > 1 && (
            <button className="secondary-button" type="button" onClick={compareReleases}>
              So sánh bản phát hành
            </button>
          )}
          {can("measurement.manage") && (
            <button className="apple-button" type="button" onClick={create}>
              Tạo định nghĩa
            </button>
          )}
        </div>
      }
    >
      {dialog}
      {error && (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      )}
      {alerts.length > 0 && (
        <div className="p-5">
          <DataTable
            items={alerts.map((item) => ({ ...item, _id: item.definition_id }))}
            empty="Không có cảnh báo ngưỡng"
            columns={[
              { key: "measurement_key", label: "Chỉ số" },
              {
                key: "level",
                label: "Mức cảnh báo",
                render: (item) => <StatusPill value={item.level} />,
              },
              { key: "value", label: "Giá trị" },
            ]}
          />
        </div>
      )}
      <div className="grid gap-3 p-5 lg:grid-cols-3">
        {definitions
          .filter((item) => item.status === "ACTIVE")
          .map((item) => (
            <QualityMetricCard
              definition={item}
              snapshot={latestByDefinition[item._id]}
              key={item._id}
            />
          ))}
      </div>
      <DataTable
        items={definitions}
        empty="Chưa có định nghĩa đo lường"
        columns={[
          { key: "name", label: "Chỉ số" },
          { key: "version", label: "Phiên bản" },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "actions",
            label: "Thao tác",
            hideWhenEmpty: true,
            render: (item) => (
              <div className="flex flex-wrap gap-2">
                {item.status === "DRAFT" && can("measurement.manage") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      await testingApi.transitionMeasurementDefinition(item._id, {
                        expected_revision: item.revision,
                        status: "ACTIVE",
                        note: "Kích hoạt định nghĩa",
                      });
                      await load();
                    }}
                  >
                    Kích hoạt
                  </button>
                )}
                {item.status === "ACTIVE" && can("measurement.snapshot.create") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await testingApi.createMeasurementSnapshot(project._id, {
                          definition_id: item._id,
                          idempotency_key: crypto.randomUUID(),
                          dimensions: {},
                        });
                        setSelectedKey(item.key);
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Đo ngay
                  </button>
                )}
                {can("measurement.manage") && item.status !== "ARCHIVED" && (
                  <>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={async () => {
                        await testingApi.versionMeasurementDefinition(item._id, {
                          expected_revision: item.revision,
                          idempotency_key: crypto.randomUUID(),
                          note: "Tạo phiên bản chỉnh sửa",
                        });
                        await load();
                      }}
                    >
                      Tạo phiên bản
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={async () => {
                        await testingApi.transitionMeasurementDefinition(item._id, {
                          expected_revision: item.revision,
                          status: "ARCHIVED",
                          note: "Lưu trữ định nghĩa",
                        });
                        await load();
                      }}
                    >
                      Lưu trữ
                    </button>
                  </>
                )}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const result = await testingApi.validateMeasurementDefinition(item._id);
                    setError(result.valid ? "" : "Công thức hoặc nguồn dữ liệu không hợp lệ");
                  }}
                >
                  Xác thực
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    testingApi
                      .pinMeasurementToDashboard(item._id, true)
                      .catch((reason) => setError(messageOf(reason)))
                  }
                >
                  Ghim
                </button>
                {can("report.export") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      testingApi
                        .exportMeasurementData(item._id, item.key)
                        .catch((reason) => setError(messageOf(reason)))
                    }
                  >
                    Xuất CSV
                  </button>
                )}
              </div>
            ),
          },
        ]}
      />
      <div className="p-5">
        <MetricTrendChart snapshots={selectedSnapshots} />
      </div>
      {comparison && (
        <div className="p-5">
          <DataTable
            items={comparison.items || []}
            empty="Không có số liệu chung để so sánh"
            columns={[
              { key: "measurement_key", label: "Chỉ số" },
              {
                key: "release_a",
                label: "Giá trị gốc",
                render: (item) => item.release_a?.value ?? "Không có",
              },
              {
                key: "release_b",
                label: "Giá trị đối chiếu",
                render: (item) => item.release_b?.value ?? "Không có",
              },
              { key: "delta", label: "Chênh lệch" },
            ]}
          />
        </div>
      )}
    </Panel>
  );
}
