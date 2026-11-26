import { useState } from "react";

const techniques = [
  ["equivalence_partitioning", "Phân vùng tương đương", "black_box"],
  ["boundary_value", "Phân tích giá trị biên", "black_box"],
  ["decision_table", "Bảng quyết định", "black_box"],
  ["state_transition", "Chuyển đổi trạng thái", "black_box"],
  ["error_guessing", "Đoán lỗi", "experience"],
];

export function TechniqueSelector({ value, onChange }) {
  const selected = String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const options = [
    ...techniques,
    ...selected
      .filter((item) => !techniques.some(([id]) => id === item))
      .map((item) => [item, item, "legacy"]),
  ];
  return (
    <fieldset className="space-y-2 lg:col-span-2">
      <legend className="field-label">Kỹ thuật kiểm thử</legend>
      {[
        ["black_box", "Hộp đen", "Đặc tả hành vi"],
        ["experience", "Dựa trên kinh nghiệm", ""],
        ["legacy", "Giá trị cũ", ""],
      ].map(([group, heading, description]) => {
        const groupOptions = options.filter(([, , category]) => category === group);
        if (!groupOptions.length) return null;
        return (
          <div className="space-y-2" key={group}>
            <p className="text-sm font-medium">
              {heading}
              {description && (
                <span className="ml-2 font-normal text-ink-muted">{description}</span>
              )}
            </p>
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {groupOptions.map(([id, label]) => (
                <label className="flex items-center gap-2 text-sm" key={id}>
                  <input
                    type="checkbox"
                    checked={selected.includes(id)}
                    onChange={(event) =>
                      onChange(
                        (event.target.checked
                          ? [...selected, id]
                          : selected.filter((item) => item !== id)
                        ).join(", "),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </fieldset>
  );
}

export function TestDataEntries({ label, entries, onChange }) {
  const rows = entries.length ? entries : [{ name: "", value: "" }];
  const change = (index, patch) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  return (
    <fieldset className="space-y-3">
      <legend className="field-label">{label}</legend>
      {rows.map((entry, index) => (
        <div className="space-y-3 rounded-control border border-border p-4" key={entry.id || index}>
          <div className="flex items-center justify-between">
            <span className="font-medium">{index + 1}.</span>
            <div className="flex gap-2">
              <button
                type="button"
                className="icon-button h-9 w-9"
                aria-label={`Xóa dữ liệu ${index + 1}`}
                onClick={() => onChange(rows.filter((_, i) => i !== index))}
              >
                −
              </button>
              <button
                type="button"
                className="icon-button h-9 w-9"
                aria-label="Thêm dữ liệu"
                onClick={() =>
                  onChange([...rows, { id: crypto.randomUUID(), name: "", value: "" }])
                }
              >
                +
              </button>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field-label">
              Tên
              <input
                className="apple-input mt-2"
                value={entry.name}
                onChange={(event) => change(index, { name: event.target.value })}
              />
            </label>
            <label className="field-label">
              Giá trị
              <input
                className="apple-input mt-2"
                value={typeof entry.value === "string" ? entry.value : JSON.stringify(entry.value)}
                onChange={(event) => change(index, { value: event.target.value })}
              />
            </label>
          </div>
        </div>
      ))}
    </fieldset>
  );
}

export function ObjectTestDataEntries({ value, onChange, label = "Dữ liệu kiểm thử chung" }) {
  const [rows, setRows] = useState(() =>
    Object.entries(value || {}).map(([name, entryValue]) => ({
      id: crypto.randomUUID(),
      name,
      value: entryValue,
    })),
  );
  const update = (next) => {
    setRows(next);
    onChange(
      Object.fromEntries(
        next.filter((item) => item.name.trim()).map((item) => [item.name, item.value]),
      ),
    );
  };
  return <TestDataEntries label={label} entries={rows} onChange={update} />;
}

export function TestTypeSelector({ value, onChange }) {
  const options = [
    ["", "-"],
    ["functional", "Chức năng"],
    ["non_functional", "Phi chức năng"],
    ["black_box", "Hộp đen"],
    ["white_box", "Hộp trắng"],
  ];
  const legacyLabels = {
    confirmation: "Xác nhận (dữ liệu cũ)",
    regression: "Hồi quy (dữ liệu cũ)",
  };
  if (value && !options.some(([id]) => id === value)) {
    options.push([value, legacyLabels[value] || `${value} (dữ liệu cũ)`]);
  }
  return (
    <label className="field-label">
      Loại kiểm thử
      <select
        className="apple-input mt-2"
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([id, label]) => (
          <option value={id} key={id}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
