"use client";
import { useId, useMemo, useState } from "react";

export default function MultiSelect({
  label,
  options,
  value,
  onChange,
  searchPlaceholder = "Tìm mục",
  emptyMessage = "Không có mục phù hợp",
  className = "",
  disabled = false,
  autoFocus = false,
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

  return (
    <div className={`min-w-0 space-y-2 ${className}`}>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <p className="field-label">{label}</p>
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
      </div>
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
      <div
        aria-label={label}
        className="max-h-52 min-w-0 space-y-1 overflow-y-auto rounded-control border border-border bg-surface p-2"
        role="group"
      >
        {visibleOptions.length ? (
          visibleOptions.map((option) => (
            <label
              className="flex min-h-10 min-w-0 cursor-pointer items-start gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-quiet has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
              key={option.value}
            >
              <input
                checked={selected.includes(option.value)}
                className="mt-1 shrink-0"
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
          ))
        ) : (
          <p className="px-2 py-3 text-sm text-ink-muted">{emptyMessage}</p>
        )}
      </div>
    </div>
  );
}
