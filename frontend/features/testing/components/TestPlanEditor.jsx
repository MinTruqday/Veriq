import { useState } from "react";

const listFields = [
  ["scope_in", "Trong phạm vi"],
  ["scope_out", "Ngoài phạm vi"],
  ["entry_criteria", "Tiêu chí đầu vào"],
  ["exit_criteria", "Tiêu chí đầu ra"],
  ["risks", "Rủi ro"],
  ["test_types", "Loại kiểm thử"],
  ["members", "Thành viên"],
  ["assumptions", "Giả định"],
  ["constraints", "Ràng buộc"],
  ["suspension_criteria", "Tiêu chí đình chỉ"],
  ["resumption_criteria", "Tiêu chí tiếp tục"],
];

const jsonFields = [
  ["dependencies", "Phụ thuộc"],
  ["stakeholders", "Các bên liên quan"],
  ["responsibility_matrix", "Ma trận trách nhiệm"],
  ["estimation", "Ước lượng"],
  ["schedule", "Lịch biểu"],
  ["milestones", "Mốc"],
  ["deliverables", "Sản phẩm bàn giao"],
  ["tools", "Công cụ"],
  ["monitoring_metrics", "Chỉ số giám sát"],
  ["quality_targets", "Mục tiêu chất lượng"],
  ["risk_register", "Sổ đăng ký rủi ro"],
  ["communication_plan", "Kế hoạch truyền thông"],
];

const defaults = {
  name: "",
  objective: "",
  strategy_version_id: "",
  test_level: "SYSTEM",
  test_approach: "",
  environment: "staging",
  scope_in: [],
  scope_out: [],
  requirement_version_ids: [],
  test_suite_ids: [],
  test_case_version_ids: [],
  entry_criteria: [],
  exit_criteria: [],
  risks: [],
  test_types: ["FUNCTIONAL"],
  members: [],
  assumptions: [],
  constraints: [],
  suspension_criteria: [],
  resumption_criteria: [],
  dependencies: [],
  stakeholders: [],
  responsibility_matrix: [],
  estimation: { method: "expert_judgment", planned_effort_hours: 0, planned_people: 0, notes: "" },
  schedule: {},
  milestones: [],
  deliverables: [],
  tools: [],
  monitoring_metrics: [],
  quality_targets: [],
  risk_register: [],
  communication_plan: {},
};

export default function TestPlanEditor({
  projectId,
  strategies,
  requirements,
  suites,
  tests,
  onSave,
  onCancel,
}) {
  const [value, setValue] = useState(defaults);
  const [error, setError] = useState("");
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));
  return (
    <form
      className="space-y-5 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          const payload = {
            project_id: projectId,
            ...value,
            strategy_version_id: value.strategy_version_id || null,
            release: "",
            release_id: null,
            build: "",
            build_id: null,
            environment_id: null,
          };
          for (const [key] of jsonFields)
            payload[key] = JSON.parse(value[`${key}_text`] ?? JSON.stringify(value[key]));
          Object.keys(payload)
            .filter((key) => key.endsWith("_text"))
            .forEach((key) => delete payload[key]);
          await onSave(payload);
        } catch (reason) {
          setError(reason.message || "Dữ liệu kế hoạch không hợp lệ");
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <label className="field-label">
          Tên kế hoạch
          <input
            className="apple-input mt-2"
            value={value.name}
            onChange={(event) => setField("name", event.target.value)}
            required
          />
        </label>
        <label className="field-label">
          Phiên bản chiến lược đã phê duyệt
          <select
            className="apple-input mt-2"
            value={value.strategy_version_id}
            onChange={(event) => setField("strategy_version_id", event.target.value)}
          >
            <option value="">Tự động dùng chiến lược đang áp dụng</option>
            {strategies
              .filter((item) => item.status === "APPROVED")
              .map((item) => (
                <option key={item._id} value={item._id}>
                  {item.key} phiên bản {item.version}
                </option>
              ))}
          </select>
        </label>
        <label className="field-label">
          Cấp kiểm thử
          <input
            className="apple-input mt-2"
            value={value.test_level}
            onChange={(event) => setField("test_level", event.target.value)}
            required
          />
        </label>
        <label className="field-label">
          Môi trường mặc định
          <input
            className="apple-input mt-2"
            value={value.environment}
            onChange={(event) => setField("environment", event.target.value)}
            required
          />
        </label>
        <label className="field-label md:col-span-2">
          Mục tiêu
          <textarea
            className="apple-input mt-2 min-h-24"
            value={value.objective}
            onChange={(event) => setField("objective", event.target.value)}
          />
        </label>
        <label className="field-label md:col-span-2">
          Cách tiếp cận kiểm thử
          <textarea
            className="apple-input mt-2 min-h-24"
            value={value.test_approach}
            onChange={(event) => setField("test_approach", event.target.value)}
          />
        </label>
        <label className="field-label">
          Phiên bản Requirement trong phạm vi
          <select
            className="apple-input mt-2 min-h-28"
            multiple
            value={value.requirement_version_ids}
            onChange={(event) =>
              setField(
                "requirement_version_ids",
                Array.from(event.target.selectedOptions, (item) => item.value),
              )
            }
          >
            {requirements.map((item) => (
              <option key={item.current_version_id} value={item.current_version_id}>
                {item.requirement_key} {item.title}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Test Set trong phạm vi
          <select
            className="apple-input mt-2 min-h-28"
            multiple
            value={value.test_suite_ids}
            onChange={(event) =>
              setField(
                "test_suite_ids",
                Array.from(event.target.selectedOptions, (item) => item.value),
              )
            }
          >
            {suites.map((item) => (
              <option key={item._id} value={item._id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label md:col-span-2">
          Phiên bản Test Case trong phạm vi
          <select
            className="apple-input mt-2 min-h-36"
            multiple
            value={value.test_case_version_ids}
            onChange={(event) =>
              setField(
                "test_case_version_ids",
                Array.from(event.target.selectedOptions, (item) => item.value),
              )
            }
          >
            {tests.map((item) => (
              <option key={item.current_version_id} value={item.current_version_id}>
                {item.test_case_key} {item.title}
              </option>
            ))}
          </select>
        </label>
        {listFields.map(([key, label]) => (
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
        {jsonFields.map(([key, label]) => (
          <label className="field-label" key={key}>
            {label} dạng JSON
            <textarea
              className="apple-input mt-2 min-h-32 font-mono text-xs"
              value={value[`${key}_text`] ?? JSON.stringify(value[key], null, 2)}
              onChange={(event) => setField(`${key}_text`, event.target.value)}
            />
          </label>
        ))}
      </div>
      <div className="flex justify-end gap-3">
        <button className="secondary-button" type="button" onClick={onCancel}>
          Hủy
        </button>
        <button className="apple-button" type="submit">
          Lưu kế hoạch
        </button>
      </div>
    </form>
  );
}
