export default function AuthField({ label, error, helper, className = "", ...props }) {
  return (
    <div className="min-w-0">
      <label htmlFor={props.id} className="mb-2 block text-[13px] font-semibold text-ink">
        {label}
      </label>
      <input
        {...props}
        className={`apple-input w-full min-w-0 max-w-full ${error ? "border-danger focus:border-danger focus:ring-danger-soft" : ""} ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error || helper ? `${props.id}-detail` : undefined}
      />
      {(error || helper) && (
        <p
          id={`${props.id}-detail`}
          className={`mt-2 text-[12px] ${error ? "text-danger" : "text-ink-muted"}`}
          role={error ? "alert" : undefined}
        >
          {error || helper}
        </p>
      )}
    </div>
  );
}
