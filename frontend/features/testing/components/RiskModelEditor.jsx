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
    <fieldset className="grid min-w-0 gap-4 rounded-2xl border border-border p-4 md:grid-cols-2">
      <legend className="px-2 text-sm font-semibold">Mô hình rủi ro</legend>
      <label className="field-label">
        Thang xác suất mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
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
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(value.impact_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) => updateScale(value, onChange, "impact_scale", event.target.value)}
          required
        />
      </label>
      <label className="field-label">
        Mức độ lỗi mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(value.severity_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) => updateScale(value, onChange, "severity_scale", event.target.value)}
        />
      </label>
      <label className="field-label">
        Thang ưu tiên mỗi mức một dòng
        <textarea
          className="apple-input mt-2 min-h-28 w-full min-w-0"
          value={(value.priority_scale || []).map((item) => item.label).join("\n")}
          onChange={(event) => updateScale(value, onChange, "priority_scale", event.target.value)}
        />
      </label>
      {[
        ["blocking_severities", "Mức độ lỗi chặn phát hành"],
        ["critical_severities", "Mức độ lỗi nghiêm trọng cần chủ sở hữu rủi ro"],
      ].map(([key, label]) => (
        <fieldset key={key} className="min-w-0 space-y-2 rounded-xl border border-border p-3">
          <legend className="px-1 text-sm font-medium">{label}</legend>
          {(value.severity_scale || []).map((item) => {
            const labelValue = String(item.label || "");
            const selected = (value[key] || []).some(
              (entry) => String(entry).toLocaleLowerCase() === labelValue.toLocaleLowerCase(),
            );
            return (
              <label key={item.label} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={(event) => {
                    const current = value[key] || [];
                    const next = event.target.checked
                      ? [...current, labelValue]
                      : current.filter(
                          (entry) =>
                            String(entry).toLocaleLowerCase() !== labelValue.toLocaleLowerCase(),
                        );
                    onChange({ ...value, [key]: next });
                  }}
                />
                {item.label}
              </label>
            );
          })}
          {!value.severity_scale?.length && (
            <p className="text-sm text-muted">Hãy khai báo thang mức độ lỗi trước.</p>
          )}
        </fieldset>
      ))}
      <label className="field-label md:col-span-2">
        Công thức tính mức phơi nhiễm rủi ro
        <input
          className="apple-input mt-2 w-full min-w-0"
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
          className="apple-input mt-2 min-h-24 w-full min-w-0"
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
