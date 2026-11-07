import { Search } from "lucide-react";

export default function SearchField({
  label,
  ariaLabel,
  placeholder,
  value,
  onChange,
  disabled = false,
  className = "",
  inputClassName = "",
  ...inputProps
}) {
  return (
    <label className={`field-label flex min-w-0 flex-col gap-2 ${className}`}>
      {label ? label : <span className="sr-only">{ariaLabel}</span>}
      <span className="relative block min-w-0">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
          size={17}
        />
        <input
          {...inputProps}
          aria-label={ariaLabel}
          className={`apple-input pl-10 ${inputClassName}`}
          disabled={disabled}
          onChange={onChange}
          placeholder={placeholder}
          value={value}
        />
      </span>
    </label>
  );
}
