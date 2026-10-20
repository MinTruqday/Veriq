"use client";

import { useEffect, useId, useState } from "react";

export default function FilePicker({
  label,
  accept,
  disabled = false,
  required = false,
  buttonLabel = "Chọn tệp",
  ariaLabel,
  fileName,
  resetKey = 0,
  className = "",
  onChange,
}) {
  const inputId = useId();
  const [selectedFileName, setSelectedFileName] = useState("");
  const displayedFileName = fileName ?? selectedFileName;

  useEffect(() => {
    setSelectedFileName("");
  }, [resetKey]);

  return (
    <div className={`min-w-0 ${className}`}>
      {label && <span className="field-label block">{label}</span>}
      <div
        className={`${label ? "mt-2" : ""} flex min-h-11 min-w-0 max-w-full items-center gap-3 rounded-control border border-border-strong bg-surface px-3 py-2`}
      >
        <input
          id={inputId}
          accept={accept}
          aria-label={ariaLabel || label || buttonLabel}
          aria-required={required || undefined}
          className="peer sr-only"
          disabled={disabled}
          type="file"
          onChange={(event) => {
            setSelectedFileName(event.target.files?.[0]?.name || "");
            onChange?.(event);
          }}
        />
        <label
          className={`secondary-button max-w-full shrink-0 cursor-pointer peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand ${
            disabled ? "pointer-events-none opacity-50" : ""
          }`}
          htmlFor={inputId}
        >
          {buttonLabel}
        </label>
        <span
          className="min-w-0 truncate text-sm text-ink-muted"
          title={displayedFileName || undefined}
        >
          {displayedFileName || "Chưa chọn tệp"}
        </span>
      </div>
    </div>
  );
}
