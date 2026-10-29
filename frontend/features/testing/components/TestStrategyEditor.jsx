import { useEffect, useState } from "react";
import RiskModelEditor from "./RiskModelEditor";
import StructuredValueEditor from "./StructuredValueEditor";

const emptyRisk = {
  probability_scale: [
    { value: 1, label: "Thấp" },
    { value: 2, label: "Trung bình" },
    { value: 3, label: "Cao" },
  ],
  impact_scale: [
    { value: 1, label: "Thấp" },
    { value: 2, label: "Trung bình" },
    { value: 3, label: "Cao" },
  ],
  risk_exposure_formula: "probability * impact",
  thresholds: [
    { level: "HIGH", min: 6 },
    { level: "MEDIUM", min: 3 },
    { level: "LOW", min: 1 },
  ],
  mandatory_test_depth: {},
  regression_priority_rules: [],
};

const emptyValue = {
  key: "",
  name: "",
  objective: "",
  test_levels: ["SYSTEM"],
  test_types: ["FUNCTIONAL"],
  approach: "",
  risk_model: emptyRisk,
  technique_policy: {},
  automation_policy: {},
  environment_policy: {},
  test_data_policy: {},
  defect_policy: {},
  review_policy: {},
  entry_criteria_defaults: [],
  exit_criteria_defaults: [],
  suspension_criteria: [],
  resumption_criteria: [],
  deliverables: [],
  reporting_policy: { cadence: "WEEKLY" },
  quality_objectives: [{ key: "PASS_RATE", target: 95 }],
  standards_refs: [],
  tailoring_rationale: "",
  reviewer_ids: [],
};

const arrayFields = [
  ["test_levels", "Cấp kiểm thử"],
  ["test_types", "Loại kiểm thử"],
  ["entry_criteria_defaults", "Tiêu chí đầu vào mặc định"],
  ["exit_criteria_defaults", "Tiêu chí đầu ra mặc định"],
  ["suspension_criteria", "Tiêu chí đình chỉ"],
  ["resumption_criteria", "Tiêu chí tiếp tục"],
  ["deliverables", "Sản phẩm bàn giao"],
  ["standards_refs", "Tiêu chuẩn tham chiếu"],
  ["reviewer_ids", "Mã thành viên rà soát"],
];

const objectFields = [
  ["technique_policy", "Chính sách kỹ thuật kiểm thử"],
  ["automation_policy", "Chính sách tự động hóa"],
  ["environment_policy", "Chính sách môi trường"],
  ["test_data_policy", "Chính sách dữ liệu kiểm thử"],
  ["defect_policy", "Chính sách lỗi"],
  ["review_policy", "Chính sách rà soát"],
  ["reporting_policy", "Chính sách báo cáo"],
  ["quality_objectives", "Mục tiêu chất lượng"],
];

export default function TestStrategyEditor({ strategy, onSave, onCancel }) {
  const [value, setValue] = useState(emptyValue);
  const [error, setError] = useState("");
  useEffect(() => {
    setValue(
      strategy
        ? { ...emptyValue, ...strategy, risk_model: { ...emptyRisk, ...strategy.risk_model } }
        : emptyValue,
    );
  }, [strategy]);
  const setField = (key, fieldValue) => setValue((current) => ({ ...current, [key]: fieldValue }));
  return (
    <form
      className="space-y-5 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          const risk = value.risk_model;
          const payload = {
            ...value,
            risk_model: {
              probability_scale: risk.probability_scale,
              impact_scale: risk.impact_scale,
              risk_exposure_formula: risk.risk_exposure_formula,
              thresholds: risk.thresholds,
              mandatory_test_depth: risk.mandatory_test_depth,
              regression_priority_rules: risk.regression_priority_rules,
            },
          };
          delete payload._id;
          delete payload.project_id;
          delete payload.lineage_id;
          delete payload.status;
          delete payload.version;
          delete payload.revision;
          delete payload.active_approved;
          delete payload.reviewed_by;
          delete payload.approval_history;
          delete payload.created_by;
          delete payload.created_at;
          delete payload.updated_at;
          delete payload.approved_by;
          delete payload.approved_at;
          delete payload.approved_snapshot;
          delete payload.snapshot_hash;
          if (strategy) {
            delete payload.key;
            payload.expected_revision = strategy.revision;
          }
          await onSave(payload);
        } catch (reason) {
          setError(reason.message || "Không thể lưu chiến lược kiểm thử");
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {!strategy && (
          <label className="field-label">
            Mã chiến lược
            <input
              className="apple-input mt-2"
              value={value.key}
              onChange={(event) => setField("key", event.target.value.toUpperCase())}
              required
            />
          </label>
        )}
        <label className="field-label">
          Tên chiến lược
          <input
            className="apple-input mt-2"
            value={value.name}
            onChange={(event) => setField("name", event.target.value)}
            required
          />
        </label>
        <label className="field-label md:col-span-2">
          Mục tiêu
          <textarea
            className="apple-input mt-2 min-h-24"
            value={value.objective}
            onChange={(event) => setField("objective", event.target.value)}
            required
          />
        </label>
        <label className="field-label md:col-span-2">
          Cách tiếp cận
          <textarea
            className="apple-input mt-2 min-h-32"
            value={value.approach}
            onChange={(event) => setField("approach", event.target.value)}
            required
          />
        </label>
        {arrayFields.map(([key, label]) => (
          <label className="field-label" key={key}>
            {label} mỗi dòng một giá trị
            <textarea
              className="apple-input mt-2 min-h-24"
              value={(value[key] || []).join("\n")}
              onChange={(event) =>
                setField(
                  key,
                  event.target.value
                    .split("\n")
                    .map((item) => item.trim())
                    .filter(Boolean),
                )
              }
            />
          </label>
        ))}
      </div>
      <RiskModelEditor
        value={value.risk_model}
        onChange={(riskModel) => setField("risk_model", riskModel)}
      />
      <div className="grid gap-4 md:grid-cols-2">
        {objectFields.map(([key, label]) => (
          <div className="min-w-0 space-y-2" key={key}>
            <p className="field-label">{label}</p>
            <StructuredValueEditor
              label={label}
              value={value[key] ?? emptyValue[key]}
              fixedType={key === "quality_objectives" ? "array" : "object"}
              itemTypes={key === "quality_objectives" ? ["object"] : undefined}
              onChange={(nextValue) => setField(key, nextValue)}
            />
          </div>
        ))}
        <label className="field-label md:col-span-2">
          Lý do điều chỉnh
          <textarea
            className="apple-input mt-2 min-h-24"
            value={value.tailoring_rationale}
            onChange={(event) => setField("tailoring_rationale", event.target.value)}
          />
        </label>
      </div>
      <div className="flex justify-end gap-3">
        <button className="secondary-button" type="button" onClick={onCancel}>
          Hủy
        </button>
        <button className="apple-button" type="submit">
          Lưu chiến lược
        </button>
      </div>
    </form>
  );
}
