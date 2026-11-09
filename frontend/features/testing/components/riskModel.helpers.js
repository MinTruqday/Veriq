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
