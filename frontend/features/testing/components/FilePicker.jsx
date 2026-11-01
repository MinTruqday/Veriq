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
  inputRef,
  stacked = false,
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
        className={`${label ? "mt-2" : ""} min-h-11 w-full min-w-0 max-w-full gap-2 overflow-hidden rounded-control border border-border-strong bg-surface px-3 py-2 ${stacked ? "flex flex-col items-stretch" : "grid grid-cols-1 items-center md:grid-cols-[max-content_minmax(0,1fr)] md:gap-3"}`}
      >
        <input
          id={inputId}
          accept={accept}
          aria-label={ariaLabel || label || buttonLabel}
          aria-required={required || undefined}
          className="peer sr-only"
          disabled={disabled}
          ref={inputRef}
          type="file"
          onChange={(event) => {
            setSelectedFileName(event.target.files?.[0]?.name || "");
            onChange?.(event);
          }}
        />
        <label
          className={`secondary-button w-fit max-w-full cursor-pointer peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand ${
            disabled ? "pointer-events-none opacity-50" : ""
          }`}
          htmlFor={inputId}
        >
          {buttonLabel}
        </label>
        <span
          className={`block min-w-0 truncate text-sm text-ink-muted ${stacked ? "w-full" : "flex-1"}`}
          title={displayedFileName || undefined}
        >
          {displayedFileName || "Chưa chọn tệp"}
        </span>
      </div>
    </div>
  );
}
