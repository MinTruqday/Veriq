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
  };
}

export function withRiskModelDefaults(value = {}) {
  const source = value && typeof value === "object" ? value : {};
  const defaults = createDefaultRiskModel();
  const result = { ...defaults, ...source };
  const defaultedLists = [
    "probability_scale",
    "impact_scale",
    "severity_scale",
    "blocking_severities",
    "critical_severities",
    "priority_scale",
    "thresholds",
    "regression_priority_rules",
  ];
  for (const key of defaultedLists) {
    if (!Array.isArray(source[key]) || source[key].length === 0) result[key] = defaults[key];
  }
  if (!String(source.risk_exposure_formula || "").trim()) {
    result.risk_exposure_formula = defaults.risk_exposure_formula;
  }
  if (!source.mandatory_test_depth || !Object.keys(source.mandatory_test_depth).length) {
    result.mandatory_test_depth = defaults.mandatory_test_depth;
  }
  return normalizeRiskModel(result);
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

export function updateRiskScale(value, key, text) {
  const items = text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((label, index) => ({ value: index + 1, label }));
  return normalizeRiskModel({ ...value, [key]: items });
}
