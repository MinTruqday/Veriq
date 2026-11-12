import StructuredValueEditor from "./StructuredValueEditor";

function normalized(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase();
}

function configuredSelections(values, options) {
  const byLabel = new Map(options.map((label) => [normalized(label), label]));
  const selected = new Map();
  for (const value of Array.isArray(values) ? values : []) {
    const raw = String(value || "").trim();
    const exact = byLabel.get(normalized(raw));
    if (exact) {
      selected.set(normalized(exact), exact);
      continue;
    }
    for (const part of raw.split(/[;,\n]+/)) {
      const label = byLabel.get(normalized(part));
      if (label) selected.set(normalized(label), label);
    }
  }
  return [...selected.values()];
}

export function createDefaultRiskModel() {
  return {
    probability_scale: [
      { value: 1, label: "Rất thấp" },
      { value: 2, label: "Thấp" },
      { value: 3, label: "Trung bình" },
      { value: 4, label: "Cao" },
      { value: 5, label: "Rất cao" },
    ],
    impact_scale: [
      { value: 1, label: "Không đáng kể" },
      { value: 2, label: "Nhẹ" },
      { value: 3, label: "Trung bình" },
      { value: 4, label: "Nghiêm trọng" },
      { value: 5, label: "Rất nghiêm trọng" },
    ],
    severity_scale: [
      { value: 1, label: "Nhỏ" },
      { value: 2, label: "Trung bình" },
      { value: 3, label: "Lớn" },
      { value: 4, label: "Nghiêm trọng" },
      { value: 5, label: "Chặn phát hành" },
    ],
    blocking_severities: ["Chặn phát hành"],
    critical_severities: ["Nghiêm trọng", "Chặn phát hành"],
    priority_scale: [
      { value: 1, label: "Thấp" },
      { value: 2, label: "Bình thường" },
      { value: 3, label: "Cao" },
      { value: 4, label: "Khẩn cấp" },
    ],
    risk_exposure_formula: "probability * impact",
    thresholds: [
      { level: "Thấp", min: 1, max: 4 },
      { level: "Trung bình", min: 5, max: 9 },
      { level: "Cao", min: 10, max: 16 },
      { level: "Rất cao", min: 17, max: 25 },
    ],
    mandatory_test_depth: {
      Thấp: ["Kiểm thử chức năng cơ bản"],
      "Trung bình": ["Kiểm thử chức năng", "Kiểm thử hồi quy liên quan"],
      Cao: ["Kiểm thử chức năng", "Kiểm thử tích hợp", "Kiểm thử hồi quy"],
      "Rất cao": ["Kiểm thử chức năng", "Kiểm thử tích hợp", "Kiểm thử hồi quy mở rộng"],
    },
    regression_priority_rules: [
      "Ưu tiên luồng nghiệp vụ có mức phơi nhiễm rủi ro cao",
      "Ưu tiên khu vực có lỗi nghiêm trọng hoặc lỗi tái mở",
    ],
    ranking_weights: {
      risk_weight: 0.45,
      priority_weight: 0.25,
      unassessed_score: 0.5,
      staleness_penalty: 0.2,
      failure_penalty_per_occurrence: 0.1,
      failure_penalty_cap: 0.4,
      maximum_score: 1,
    },
  };
}

export function normalizeRiskModel(value = {}) {
  const severityLabels = (Array.isArray(value.severity_scale) ? value.severity_scale : [])
    .map((item) => String(item?.label || "").trim())
    .filter(Boolean);
  return {
    ...value,
    blocking_severities: configuredSelections(value.blocking_severities, severityLabels),
    critical_severities: configuredSelections(value.critical_severities, severityLabels),
  };
}

export function withRiskModelDefaults(value = {}) {
  const source = value && typeof value === "object" ? value : {};
  const defaults = createDefaultRiskModel();
  const result = { ...defaults, ...source };
  const defaultedScales = [
    ["probability_scale", "label"],
    ["impact_scale", "label"],
    ["severity_scale", "label"],
    ["priority_scale", "label"],
    ["thresholds", "level"],
  ];
  for (const [key, labelKey] of defaultedScales) {
    const configured = source[key];
    const defaultItems = defaults[key];
    if (!Array.isArray(configured) || configured.length === 0) {
      result[key] = defaultItems;
      continue;
    }
    const standardLabels = new Set(defaultItems.map((item) => normalized(item[labelKey])));
    const configuredLabels = configured.map((item) => normalized(item?.[labelKey]));
    if (
      configured.length < defaultItems.length &&
      configuredLabels.every((label) => label && standardLabels.has(label))
    ) {
      result[key] = defaultItems;
    }
  }
  for (const key of ["blocking_severities", "critical_severities", "regression_priority_rules"]) {
    if (!Array.isArray(source[key]) || source[key].length === 0) result[key] = defaults[key];
  }
  if (!String(source.risk_exposure_formula || "").trim()) {
    result.risk_exposure_formula = defaults.risk_exposure_formula;
  }
  if (!source.mandatory_test_depth || !Object.keys(source.mandatory_test_depth).length) {
    result.mandatory_test_depth = defaults.mandatory_test_depth;
  }
  result.ranking_weights = Object.fromEntries(
    Object.entries(defaults.ranking_weights).map(([key, defaultValue]) => [
      key,
      source.ranking_weights?.[key] ?? defaultValue,
    ]),
  );
  return normalizeRiskModel(result);
}

export function updateRiskScale(value, key, text) {
  const items = text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((label, index) => ({ value: index + 1, label }));
  return normalizeRiskModel({ ...value, [key]: items });
}

export default function RiskModelEditor({ value, onChange }) {
  const riskModel = normalizeRiskModel(value);
  return (
    <fieldset className="grid min-w-0 gap-4 rounded-2xl border border-border p-4 md:grid-cols-2">
      <legend className="px-2 text-sm font-semibold">Mô hình rủi ro</legend>
      <label className="field-label">
        Thang xác suất mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(riskModel.probability_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) =>
            onChange(updateRiskScale(riskModel, "probability_scale", event.target.value))
          }
          required
        />
      </label>
      <label className="field-label">
        Thang ảnh hưởng mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(riskModel.impact_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) =>
            onChange(updateRiskScale(riskModel, "impact_scale", event.target.value))
          }
          required
        />
      </label>
      <label className="field-label">
        Mức độ lỗi mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(riskModel.severity_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) =>
            onChange(updateRiskScale(riskModel, "severity_scale", event.target.value))
          }
        />
      </label>
      <label className="field-label">
        Thang ưu tiên mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(riskModel.priority_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) =>
            onChange(updateRiskScale(riskModel, "priority_scale", event.target.value))
          }
        />
      </label>
      <fieldset className="grid min-w-0 gap-3 rounded-control border border-border p-3 md:col-span-2 md:grid-cols-3">
        <legend className="px-2 text-sm font-semibold">Trọng số xếp hạng hồi quy</legend>
        {[
          ["risk_weight", "Trọng số rủi ro"],
          ["priority_weight", "Trọng số ưu tiên"],
          ["unassessed_score", "Điểm khi chưa có mức đánh giá"],
          ["staleness_penalty", "Điểm cộng khi ca cần cập nhật"],
          ["failure_penalty_per_occurrence", "Điểm cộng mỗi lần thất bại"],
          ["failure_penalty_cap", "Giới hạn điểm do thất bại"],
          ["maximum_score", "Điểm tối đa"],
        ].map(([key, label]) => (
          <label className="field-label" key={key}>
            {label}
            <input
              className="apple-input mt-2 w-full min-w-0"
              type="number"
              min={key === "maximum_score" ? "0.000001" : "0"}
              max="1"
              step="0.01"
              value={riskModel.ranking_weights?.[key] ?? ""}
              onChange={(event) => {
                const nextValue = event.target.value;
                onChange({
                  ...riskModel,
                  ranking_weights: {
                    ...(riskModel.ranking_weights || {}),
                    [key]: nextValue === "" ? null : Number(nextValue),
                  },
                });
              }}
            />
          </label>
        ))}
        <p className="text-sm text-ink-muted md:col-span-3">
          Đây là giá trị mặc định của hệ thống; có thể chỉnh riêng theo chiến lược kiểm thử.
        </p>
      </fieldset>
      {[
        ["blocking_severities", "Mức độ lỗi chặn phát hành"],
        ["critical_severities", "Mức độ lỗi nghiêm trọng cần chủ sở hữu rủi ro"],
      ].map(([key, label]) => (
        <fieldset key={key} className="min-w-0 space-y-2 rounded-xl border border-border p-3">
          <legend className="px-1 text-sm font-medium">{label}</legend>
          {(riskModel.severity_scale || []).map((item) => {
            const labelValue = String(item.label || "");
            const selected = (riskModel[key] || []).some(
              (entry) => String(entry).toLocaleLowerCase() === labelValue.toLocaleLowerCase(),
            );
            return (
              <label key={item.label} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={(event) => {
                    const current = riskModel[key] || [];
                    const next = event.target.checked
                      ? [...current, labelValue]
                      : current.filter(
                          (entry) =>
                            String(entry).toLocaleLowerCase() !== labelValue.toLocaleLowerCase(),
                        );
                    onChange(normalizeRiskModel({ ...riskModel, [key]: next }));
                  }}
                />
                {item.label}
              </label>
            );
          })}
          {!riskModel.severity_scale?.length && (
            <p className="text-sm text-muted">Hãy khai báo thang mức độ lỗi trước.</p>
          )}
        </fieldset>
      ))}
      <label className="field-label md:col-span-2">
        Công thức tính mức phơi nhiễm rủi ro
        <input
          className="apple-input mt-2 w-full min-w-0"
          value={riskModel.risk_exposure_formula || ""}
          onChange={(event) =>
            onChange({ ...riskModel, risk_exposure_formula: event.target.value })
          }
          required
        />
      </label>
      <div className="min-w-0 space-y-2">
        <span className="field-label">Ngưỡng rủi ro</span>
        <StructuredValueEditor
          label="Danh sách ngưỡng"
          value={riskModel.thresholds || []}
          allowedTypes={["array"]}
          itemTypes={["object"]}
          onChange={(thresholds) => onChange({ ...riskModel, thresholds })}
        />
      </div>
      <div className="min-w-0 space-y-2">
        <span className="field-label">Độ sâu kiểm thử bắt buộc</span>
        <StructuredValueEditor
          label="Theo mức rủi ro"
          value={riskModel.mandatory_test_depth || {}}
          fixedType="object"
          onChange={(mandatory_test_depth) => onChange({ ...riskModel, mandatory_test_depth })}
        />
      </div>
      <label className="field-label md:col-span-2">
        Quy tắc ưu tiên hồi quy mỗi dòng một quy tắc
        <textarea
          className="apple-input mt-2 min-h-24 w-full min-w-0"
          value={(riskModel.regression_priority_rules || []).join("\n")}
          onChange={(event) =>
            onChange({
              ...riskModel,
              regression_priority_rules: event.target.value
                .split("\n")
                .map((item) => item.trim())
                .filter(Boolean),
            })
          }
        />
      </label>
    </fieldset>
  );
}
