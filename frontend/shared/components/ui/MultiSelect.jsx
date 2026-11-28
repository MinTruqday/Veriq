"use client";
import { useId, useMemo, useState } from "react";

export default function MultiSelect({
  label,
  options,
  value,
  onChange,
  searchPlaceholder = "Tìm mục",
  className = "",
  disabled = false,
  autoFocus = false,
  showSearch = true,
  compact = false,
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const selected = Array.isArray(value) ? value : [];
  const visibleOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) return options;
    return options.filter((option) =>
      `${option.label} ${option.description || ""}`.toLocaleLowerCase().includes(normalizedQuery),
    );
  }, [options, query]);

  const toggle = (optionValue) => {
    onChange(
      selected.includes(optionValue)
        ? selected.filter((item) => item !== optionValue)
        : [...selected, optionValue],
    );
  };

  if (compact) {
    const selectedLabels = options
      .filter((option) => selected.includes(option.value))
      .map((option) => option.label);
    const displayValue = selected.length
      ? selected.length === 1
        ? selectedLabels[0] || "Đã chọn 1 mục"
        : `Đã chọn ${selected.length} mục`
      : "Chọn mục";
    return (
      <div className={`min-w-0 space-y-2 ${className}`}>
        <div className="flex min-w-0 items-center justify-between gap-3">
          <p className="field-label" id={id}>
            {label}
          </p>
          <span className="shrink-0 text-xs text-ink-muted" aria-live="polite">
            Đã chọn {selected.length}
          </span>
        </div>
        <details
          className="group/select relative"
          onToggle={(event) => {
            if (!event.currentTarget.open) setQuery("");
          }}
        >
          <summary
            aria-labelledby={id}
            aria-disabled={disabled}
            className={`apple-input flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
            onClick={(event) => {
              if (disabled) event.preventDefault();
            }}
          >
            <span className="min-w-0 truncate">{displayValue}</span>
            <svg
              aria-hidden="true"
              className="h-4 w-4 shrink-0 text-ink-muted transition-transform group-open/select:rotate-180"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </summary>
          {!disabled && (
            <div className="absolute z-30 mt-1 w-full rounded-control border border-border bg-surface p-2 shadow-panel">
              <div className="mb-2 flex items-center gap-2">
                <input
                  autoFocus={autoFocus}
                  className="apple-input min-w-0 flex-1"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={searchPlaceholder}
                  type="search"
                  value={query}
                />
                {selected.length > 0 && (
                  <button
                    className="shrink-0 rounded px-2 py-1 text-xs font-semibold text-brand hover:bg-brand-soft"
                    type="button"
                    onClick={() => onChange([])}
                  >
                    Bỏ chọn
                  </button>
                )}
              </div>
              <div aria-label={label} className="max-h-56 overflow-y-auto" role="group">
                {visibleOptions.length ? (
                  visibleOptions.map((option) => (
                    <label
                      className="flex min-h-10 cursor-pointer items-start gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-quiet has-[:disabled]:opacity-60"
                      key={option.value}
                    >
                      <input
                        checked={selected.includes(option.value)}
                        className="mt-1 shrink-0"
                        disabled={option.disabled}
                        onChange={() => toggle(option.value)}
                        type="checkbox"
                      />
                      <span className="min-w-0 break-words text-ink">{option.label}</span>
                    </label>
                  ))
                ) : (
                  <p className="px-2 py-3 text-sm text-ink-muted">Không tìm thấy mục phù hợp</p>
                )}
              </div>
            </div>
          )}
        </details>
      </div>
    );
  }

  if (!showSearch) {
    const selectedLabels = options
      .filter((option) => selected.includes(option.value))
      .map((option) => option.label);
    const displayValue =
      selected.length === 0
        ? "-"
        : selectedLabels.length === selected.length
          ? selectedLabels.join(", ")
          : `Đã chọn ${selected.length} mục`;
    return (
      <div className={`min-w-0 space-y-2 ${className}`}>
        <p className="field-label" id={id}>
          {label}
        </p>
        {disabled || options.length === 0 ? (
          <select aria-labelledby={id} className="apple-input" disabled={disabled} value="">
            <option value="">{displayValue}</option>
          </select>
        ) : (
          <details className="relative">
            <summary
              aria-labelledby={id}
              className="apple-input flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden"
            >
              <span className="min-w-0 truncate">{displayValue}</span>
              <svg
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-ink-muted"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </summary>
            <div
              aria-label={label}
              className="absolute z-20 mt-1 max-h-52 w-full overflow-y-auto rounded-control border border-border bg-surface p-2 shadow-lg"
              role="group"
            >
              {options.map((option) => (
                <label
                  className="flex cursor-pointer items-start gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-quiet has-[:disabled]:opacity-60"
                  key={option.value}
                >
                  <input
                    checked={selected.includes(option.value)}
                    className="mt-1 shrink-0"
                    disabled={option.disabled}
                    onChange={() => toggle(option.value)}
                    type="checkbox"
                  />
                  <span className="min-w-0 break-words">{option.label}</span>
                </label>
              ))}
            </div>
          </details>
        )}
      </div>
    );
  }

  return (
    <div className={`min-w-0 space-y-2 ${className}`}>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <p className="field-label">{label}</p>
        {showSearch && (
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <span aria-live="polite">Đã chọn {selected.length}</span>
            {selected.length > 0 && (
              <button
                className="rounded px-1 py-0.5 font-semibold text-brand hover:bg-brand-soft disabled:opacity-50"
                disabled={disabled}
                type="button"
                onClick={() => onChange([])}
              >
                Bỏ chọn
              </button>
            )}
          </div>
        )}
      </div>
      {showSearch && (
        <>
          <label className="sr-only" htmlFor={id}>
            {searchPlaceholder}
          </label>
          <input
            id={id}
            autoFocus={autoFocus}
            className="apple-input w-full"
            disabled={disabled}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            type="search"
            value={query}
          />
        </>
      )}
      {visibleOptions.length > 0 && (
        <div
          aria-label={label}
          className={
            showSearch
              ? "max-h-52 min-w-0 space-y-1 overflow-y-auto rounded-control border border-border bg-surface p-2"
              : "flex max-h-52 flex-wrap gap-x-5 gap-y-2 overflow-y-auto"
          }
          role="group"
        >
          {visibleOptions.map((option) => (
            <label
              className={
                showSearch
                  ? "flex min-h-10 min-w-0 cursor-pointer items-start gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-quiet has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
                  : "flex min-w-0 items-center gap-2 text-sm has-[:disabled]:opacity-50"
              }
              key={option.value}
            >
              <input
                checked={selected.includes(option.value)}
                className={showSearch ? "mt-1 shrink-0" : "shrink-0"}
                disabled={disabled || option.disabled}
                onChange={() => toggle(option.value)}
                type="checkbox"
              />
              <span className="min-w-0 break-words text-ink">
                {option.label}
                {option.description && (
                  <span className="mt-0.5 block text-xs text-ink-muted">{option.description}</span>
                )}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
