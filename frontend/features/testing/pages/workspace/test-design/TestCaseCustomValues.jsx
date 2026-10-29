export default function TestCaseCustomValues({ fields = [], values = {}, onChange }) {
  if (!fields.length) return null;
  return (
    <section className="space-y-3 rounded-control border border-border p-4">
      <div>
        <h3 className="font-medium">Thông tin mở rộng</h3>
        <p className="text-sm text-ink-muted">
          Trường do QA cấu hình cho dự án; trường bắt buộc cần hoàn tất trước khi duyệt.
        </p>
      </div>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2">
        {fields.map((field) => {
          const value = values[field.key] ?? "";
          const setValue = (next) => {
            const updated = { ...values };
            if (next === "" || next === null) delete updated[field.key];
            else updated[field.key] = next;
            onChange(updated);
          };
          return (
            <label className="field-label min-w-0" key={field._id}>
              {field.label}
              {field.required && <span className="text-danger"> *</span>}
              {field.value_type === "boolean" ? (
                <select
                  className="apple-input mt-2 w-full min-w-0"
                  value={value === "" ? "" : String(value)}
                  onChange={(event) =>
                    setValue(event.target.value === "" ? "" : event.target.value === "true")
                  }
                >
                  <option value="">Chưa chọn</option>
                  <option value="true">Có</option>
                  <option value="false">Không</option>
                </select>
              ) : field.value_type === "choice" ? (
                <select
                  className="apple-input mt-2 w-full min-w-0"
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                >
                  <option value="">Chưa chọn</option>
                  {(field.choices || []).map((choice) => (
                    <option key={choice} value={choice}>
                      {choice}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="apple-input mt-2 w-full min-w-0"
                  type={field.value_type === "number" ? "number" : field.value_type}
                  step={field.value_type === "number" ? "any" : undefined}
                  value={value}
                  onChange={(event) =>
                    setValue(
                      field.value_type === "number" && event.target.value !== ""
                        ? Number(event.target.value)
                        : event.target.value,
                    )
                  }
                />
              )}
            </label>
          );
        })}
      </div>
    </section>
  );
}
