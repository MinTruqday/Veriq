export default function CompactDraftEditor({ draft, onChange, onSave, saveState }) {
  const steps = draft.steps || [];
  const changeStep = (index, change) =>
    onChange({
      steps: steps.map((step, position) => (position === index ? { ...step, ...change } : step)),
    });
  return (
    <div className="test-design-form space-y-4 p-5">
      <label className="field-label">
        Tên ca kiểm thử
        <input
          className="apple-input mt-2"
          value={draft.title}
          onChange={(event) => onChange({ title: event.target.value })}
        />
      </label>
      <div className="flex items-center justify-between">
        <p className="font-semibold">Các bước kiểm thử</p>
        <button
          className="icon-button h-9 w-9 text-lg"
          type="button"
          aria-label="Thêm bước"
          onClick={() =>
            onChange({
              steps: [...steps, { id: crypto.randomUUID(), action: "", data: {}, expected: "" }],
            })
          }
        >
          +
        </button>
      </div>
      {steps.map((step, index) => (
        <div key={step.id || index} className="space-y-3 rounded-control border border-border p-4">
          <div className="flex items-center justify-between">
            <span>{index + 1}.</span>
            {steps.length > 1 && (
              <button
                className="icon-button h-9 w-9 text-lg"
                type="button"
                aria-label={`Xóa bước ${index + 1}`}
                onClick={() => onChange({ steps: steps.filter((_, i) => i !== index) })}
              >
                −
              </button>
            )}
          </div>
          <label className="field-label">
            Thao tác và dữ liệu
            <textarea
              className="apple-input mt-2 min-h-20"
              value={step.action}
              onChange={(event) => changeStep(index, { action: event.target.value })}
            />
          </label>
          {step.data && Object.keys(step.data).length > 0 && (
            <div className="text-sm">
              <p className="field-label">Dữ liệu của bước</p>
              {Object.entries(step.data).map(([name, value]) => (
                <p key={name} className="break-words">
                  {name}: {typeof value === "string" ? value : JSON.stringify(value)}
                </p>
              ))}
            </div>
          )}
          <label className="field-label">
            Kết quả mong đợi
            <textarea
              className="apple-input mt-2 min-h-20"
              value={step.expected}
              onChange={(event) => changeStep(index, { expected: event.target.value })}
            />
          </label>
        </div>
      ))}
      <div className="flex items-center gap-3">
        <button
          className="secondary-button"
          type="button"
          disabled={saveState === "saving"}
          onClick={onSave}
        >
          Lưu bản nháp
        </button>
        <span className="text-xs text-ink-muted" aria-live="polite">
          {saveState === "saving"
            ? "Đang tự động lưu"
            : saveState === "pending"
              ? "Có thay đổi chưa lưu"
              : saveState === "error"
                ? "Tự động lưu thất bại"
                : "Đã tự động lưu"}
        </span>
      </div>
    </div>
  );
}
