import StructuredValueEditor from "./StructuredValueEditor";

function updateScale(value, onChange, key, text) {
  const items = text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item, index) => ({ value: index + 1, label: item }));
  onChange({ ...value, [key]: items });
}

export default function RiskModelEditor({ value, onChange }) {
  return (
    <fieldset className="grid gap-4 rounded-2xl border border-border p-4 md:grid-cols-2">
      <legend className="px-2 text-sm font-semibold">Mô hình rủi ro</legend>
      <label className="field-label">
        Thang xác suất mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28"
          value={(value.probability_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) =>
            updateScale(value, onChange, "probability_scale", event.target.value)
          }
          required
        />
      </label>
      <label className="field-label">
        Thang ảnh hưởng mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28"
          value={(value.impact_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) => updateScale(value, onChange, "impact_scale", event.target.value)}
          required
        />
      </label>
      <label className="field-label md:col-span-2">
        Công thức mức phơi nhiễm rủi ro
        <input
          className="apple-input mt-2"
          value={value.risk_exposure_formula || ""}
          onChange={(event) => onChange({ ...value, risk_exposure_formula: event.target.value })}
          required
        />
      </label>
      <div className="min-w-0 space-y-2">
        <span className="field-label">Ngưỡng rủi ro</span>
        <StructuredValueEditor
          label="Danh sách ngưỡng"
          value={value.thresholds || []}
          allowedTypes={["array"]}
          itemTypes={["object"]}
          onChange={(thresholds) => onChange({ ...value, thresholds })}
        />
      </div>
      <div className="min-w-0 space-y-2">
        <span className="field-label">Độ sâu kiểm thử bắt buộc</span>
        <StructuredValueEditor
          label="Theo mức rủi ro"
          value={value.mandatory_test_depth || {}}
          fixedType="object"
          onChange={(mandatory_test_depth) => onChange({ ...value, mandatory_test_depth })}
        />
      </div>
      <label className="field-label md:col-span-2">
        Quy tắc ưu tiên hồi quy mỗi dòng một quy tắc
        <textarea
          className="apple-input mt-2 min-h-24"
          value={(value.regression_priority_rules || []).join("\n")}
          onChange={(event) =>
            onChange({
              ...value,
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
