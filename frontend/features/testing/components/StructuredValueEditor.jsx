"use client";

function valueType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object") return "object";
  return typeof value;
}

function valueForType(type) {
  return { string: "", number: 0, boolean: false, object: {}, array: [], null: null }[type];
}

export default function StructuredValueEditor({
  label,
  value,
  onChange,
  depth = 0,
  fixedType,
  allowedTypes,
  itemTypes,
}) {
  const type = valueType(value);
  const types = allowedTypes || ["string", "number", "boolean", "object", "array", "null"];
  return (
    <div
      className={`min-w-0 space-y-2 ${depth ? "rounded-control border border-border/70 p-3" : ""}`}
    >
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        {label && <span className="text-sm font-medium text-ink">{label}</span>}
        {!fixedType && (
          <select
            aria-label={`Kiểu dữ liệu ${label || "giá trị"}`}
            className="apple-input min-w-32 w-auto"
            value={type}
            onChange={(event) => onChange(valueForType(event.target.value))}
          >
            {types.includes("string") && <option value="string">Văn bản</option>}
            {types.includes("number") && <option value="number">Số</option>}
            {types.includes("boolean") && <option value="boolean">Đúng/Sai</option>}
            {types.includes("object") && <option value="object">Nhóm thuộc tính</option>}
            {types.includes("array") && <option value="array">Danh sách</option>}
            {types.includes("null") && <option value="null">Không có giá trị</option>}
          </select>
        )}
      </div>
      {type === "string" && (
        <textarea
          aria-label={`Giá trị ${label || "văn bản"}`}
          className="apple-input min-h-16 w-full"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {type === "number" && (
        <input
          aria-label={`Giá trị ${label || "số"}`}
          className="apple-input w-full"
          type="number"
          step="any"
          value={value}
          onChange={(event) => onChange(event.target.value === "" ? 0 : Number(event.target.value))}
        />
      )}
      {type === "boolean" && (
        <select
          aria-label={`Giá trị ${label || "đúng/sai"}`}
          className="apple-input w-full"
          value={String(value)}
          onChange={(event) => onChange(event.target.value === "true")}
        >
          <option value="true">Đúng</option>
          <option value="false">Sai</option>
        </select>
      )}
      {type === "null" && <p className="text-xs text-ink-muted">Giá trị được lưu là null.</p>}
      {type === "object" && (
        <div className="space-y-2">
          {Object.entries(value).map(([key, item]) => (
            <div
              className="grid min-w-0 gap-2 sm:grid-cols-[minmax(8rem,0.7fr)_minmax(0,1.3fr)_auto]"
              key={key}
            >
              <input
                aria-label="Tên thuộc tính"
                className="apple-input min-w-0 w-full"
                value={key}
                onChange={(event) => {
                  const nextKey = event.target.value;
                  if (!nextKey || (nextKey !== key && Object.hasOwn(value, nextKey))) return;
                  const next = { ...value };
                  delete next[key];
                  next[nextKey] = item;
                  onChange(next);
                }}
              />
              <StructuredValueEditor
                label={key}
                value={item}
                depth={depth + 1}
                onChange={(nextValue) => onChange({ ...value, [key]: nextValue })}
              />
              <button
                aria-label={`Xóa thuộc tính ${key}`}
                className="secondary-button self-start"
                type="button"
                onClick={() => {
                  const next = { ...value };
                  delete next[key];
                  onChange(next);
                }}
              >
                Xóa
              </button>
            </div>
          ))}
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              let key = "thuoc_tinh_moi";
              let index = 2;
              while (Object.hasOwn(value, key)) key = `thuoc_tinh_moi_${index++}`;
              onChange({ ...value, [key]: "" });
            }}
          >
            Thêm thuộc tính
          </button>
        </div>
      )}
      {type === "array" && (
        <div className="space-y-2">
          {value.map((item, index) => (
            <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]" key={index}>
              <StructuredValueEditor
                label={`Mục ${index + 1}`}
                value={item}
                depth={depth + 1}
                allowedTypes={itemTypes}
                onChange={(nextValue) =>
                  onChange(
                    value.map((entry, entryIndex) => (entryIndex === index ? nextValue : entry)),
                  )
                }
              />
              <button
                aria-label={`Xóa mục ${index + 1}`}
                className="secondary-button self-start"
                type="button"
                onClick={() => onChange(value.filter((_, entryIndex) => entryIndex !== index))}
              >
                Xóa
              </button>
            </div>
          ))}
          <button
            className="secondary-button"
            type="button"
            onClick={() => onChange([...value, valueForType(itemTypes?.[0] || "string")])}
          >
            Thêm mục
          </button>
        </div>
      )}
    </div>
  );
}

export function StructuredValueView({ value }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-muted">Chưa có giá trị</span>;
  }
  if (typeof value !== "object") return <span className="break-words">{String(value)}</span>;
  const entries = Array.isArray(value)
    ? value.map((item, index) => [String(index + 1), item])
    : Object.entries(value);
  if (!entries.length) return <span className="text-ink-muted">Chưa có dữ liệu</span>;
  return (
    <dl className="min-w-0 space-y-2">
      {entries.map(([key, item]) => (
        <div
          className="grid min-w-0 gap-1 sm:grid-cols-[minmax(8rem,0.45fr)_minmax(0,1fr)]"
          key={key}
        >
          <dt className="break-words text-sm font-medium text-ink-muted">{key}</dt>
          <dd className="min-w-0 break-words text-sm text-ink">
            {item !== null && typeof item === "object" ? (
              <StructuredValueView value={item} />
            ) : item === null ? (
              <span className="text-ink-muted">Không có giá trị</span>
            ) : (
              String(item)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
