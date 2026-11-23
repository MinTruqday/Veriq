export default function RequirementLines({ label, value, onChange, required = false }) {
  const lines = (value || "").split("\n");
  return (
    <fieldset className="space-y-2">
      <legend className="field-label">{label}</legend>
      {lines.map((line, index) => (
        <div className="flex items-center gap-2" key={index}>
          <span className="w-6 shrink-0 text-right text-sm text-ink-muted" aria-hidden="true">
            {index + 1}.
          </span>
          <div className="relative min-w-0 flex-1">
            <input
              className="apple-input w-full pr-10"
              aria-label={`${label} ${index + 1}`}
              required={required && index === 0}
              value={line}
              onChange={(event) => {
                const next = [...lines];
                next[index] = event.target.value;
                onChange(next.join("\n"));
              }}
            />
            {lines.length > 1 && (
              <button
                className="absolute inset-y-0 right-1 flex w-9 items-center justify-center text-lg text-ink-muted hover:text-danger"
                type="button"
                aria-label={`Xóa ${label} ${index + 1}`}
                title={`Xóa ${label.toLowerCase()}`}
                onClick={() =>
                  onChange(lines.filter((_, position) => position !== index).join("\n"))
                }
              >
                −
              </button>
            )}
          </div>
          <button
            className="secondary-button"
            type="button"
            aria-label={`Thêm ${label.toLowerCase()} sau dòng ${index + 1}`}
            onClick={() => {
              const next = [...lines];
              next.splice(index + 1, 0, "");
              onChange(next.join("\n"));
            }}
          >
            +
          </button>
        </div>
      ))}
    </fieldset>
  );
}
