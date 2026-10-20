"use client";
import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { hasNavigationPermission } from "@/shared/components/layout/navigation";
import HorizontalScrollCue from "@/shared/components/navigation/HorizontalScrollCue";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { messageOf, statusLabel, valueLabel } from "../lib/testing";

export function useActionDialog() {
  const titleId = useId();
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);
  const previousOverflowRef = useRef("");
  const submittingRef = useRef(false);
  const [state, setState] = useState(null);
  const [values, setValues] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const ask = useCallback(
    (options) =>
      new Promise((resolve) => {
        const fields = options.fields || [];
        submittingRef.current = false;
        setSubmitting(false);
        setSubmitError("");
        setValues(
          Object.fromEntries(
            fields.map((field) => [
              field.name,
              field.initialValue ??
                (field.multiple
                  ? []
                  : field.options?.[0]?.value !== undefined
                    ? field.options[0].value
                    : ""),
            ]),
          ),
        );
        setState({ ...options, resolve });
      }),
    [],
  );
  useEffect(() => {
    if (!state) return undefined;
    previousFocusRef.current = document.activeElement;
    previousOverflowRef.current = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const dialogElement = dialogRef.current;
    const focusableSelector =
      'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';
    const focusable = () => Array.from(dialogElement?.querySelectorAll(focusableSelector) || []);
    const initialFocus = () => {
      const firstInput = dialogElement?.querySelector(
        'input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled])',
      );
      (
        dialogElement?.querySelector("[autofocus]") ||
        firstInput ||
        focusable()[0] ||
        dialogElement
      )?.focus();
    };
    initialFocus();
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        if (
          [...document.querySelectorAll('[role="dialog"][aria-modal="true"]')].at(-1) !==
          dialogElement
        ) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (submittingRef.current) return;
        state.resolve(null);
        setState(null);
        return;
      }
      if (event.key !== "Tab") return;
      const elements = focusable();
      if (!elements.length) {
        event.preventDefault();
        dialogElement?.focus();
        return;
      }
      const firstElement = elements[0];
      const lastElement = elements[elements.length - 1];
      if (!dialogElement?.contains(document.activeElement)) {
        event.preventDefault();
        (event.shiftKey ? lastElement : firstElement).focus();
        return;
      }
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflowRef.current;
      previousFocusRef.current?.focus?.();
    };
  }, [state]);
  const close = (result) => {
    if (submittingRef.current) return;
    state?.resolve(result);
    setState(null);
    setSubmitting(false);
    submittingRef.current = false;
    setSubmitError("");
  };
  const dialog = state ? (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/30 p-4 backdrop-blur-[2px] animate-in fade-in"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !submitting) close(null);
      }}
    >
      <section
        aria-labelledby={titleId}
        aria-modal="true"
        className="max-h-[90dvh] w-full max-w-lg overflow-y-auto overscroll-contain rounded-panel bg-surface p-5 shadow-[0_24px_80px_rgba(32,32,30,0.18)] sm:p-6"
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <h2 className="text-[20px] font-semibold tracking-[-0.02em] text-ink" id={titleId}>
          {state.title}
        </h2>
        {state.description && (
          <p className="mt-2 text-[13px] leading-6 text-ink-muted">{state.description}</p>
        )}
        <form
          className="mt-5 space-y-4"
          onSubmit={async (event) => {
            event.preventDefault();
            if (submittingRef.current) return;
            if (!state.onConfirm) {
              close(values);
              return;
            }
            submittingRef.current = true;
            setSubmitting(true);
            setSubmitError("");
            try {
              await state.onConfirm(values);
              state.resolve(values);
              setState(null);
              setSubmitting(false);
              submittingRef.current = false;
            } catch (reason) {
              setSubmitError(messageOf(reason));
              setSubmitting(false);
              submittingRef.current = false;
            }
          }}
        >
          {submitError && (
            <div
              aria-live="assertive"
              className="rounded-control border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger"
              role="alert"
            >
              {submitError}
            </div>
          )}
          {(state.fields || []).map((field) =>
            field.options && field.multiple ? (
              <MultiSelect
                autoFocus={field.autoFocus}
                className="min-w-0"
                disabled={submitting}
                key={field.name}
                label={field.label}
                options={field.options}
                searchPlaceholder={`Tìm trong ${field.label.toLocaleLowerCase()}`}
                value={values[field.name] || []}
                onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}
              />
            ) : (
              <label className="field-label block" key={field.name}>
                {field.label}
                {field.options ? (
                  <select
                    autoFocus={field.autoFocus}
                    className="apple-input mt-2"
                    required={field.required}
                    value={values[field.name] ?? ""}
                    onChange={(event) =>
                      setValues((current) => ({ ...current, [field.name]: event.target.value }))
                    }
                  >
                    {field.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : field.multiline ? (
                  <textarea
                    autoFocus={field.autoFocus}
                    className="apple-input mt-2 min-h-28"
                    required={field.required}
                    value={values[field.name] || ""}
                    onChange={(event) =>
                      setValues((current) => ({ ...current, [field.name]: event.target.value }))
                    }
                  />
                ) : (
                  <input
                    autoFocus={field.autoFocus}
                    className="apple-input mt-2"
                    required={field.required}
                    type={field.type || "text"}
                    value={values[field.name] || ""}
                    onChange={(event) =>
                      setValues((current) => ({ ...current, [field.name]: event.target.value }))
                    }
                  />
                )}
              </label>
            ),
          )}
          <div className="action-dialog-footer flex flex-col-reverse items-stretch gap-2 pt-2 sm:flex-row sm:justify-end">
            <button
              className="secondary-button"
              disabled={submitting}
              type="button"
              onClick={() => close(null)}
            >
              Hủy
            </button>
            <button
              className={state.danger ? "danger-button" : "apple-button"}
              disabled={submitting}
              type="submit"
            >
              {submitting ? "Đang xử lý" : state.confirmLabel || "Xác nhận"}
            </button>
          </div>
        </form>
      </section>
    </div>
  ) : null;
  return { ask, dialog };
}

export function WorkspacePage({ title, description, actions, children }) {
  useEffect(() => {
    document.title = `${title} | Veriq`;
  }, [title]);

  return (
    <div className="workspace-page mx-auto w-full max-w-[1480px] min-w-0 space-y-6 py-5 sm:py-6 xl:py-8">
      <header className="grid min-w-0 grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(0,auto)] 2xl:items-end">
        <div className="min-w-0">
          <h1 className="break-words text-[28px] font-semibold leading-[1.12] tracking-[-0.04em] sm:text-[32px] xl:text-[36px]">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-3xl text-[14px] leading-6 text-ink-muted">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2 2xl:max-w-[52rem] 2xl:justify-end">
            {actions}
          </div>
        )}
      </header>
      {children}
    </div>
  );
}

export function WorkspaceSectionNav({ items, current, compact = false, permissions = null }) {
  const visibleItems = items.filter((item) => hasNavigationPermission(item, permissions));
  if (visibleItems.length < 2) return null;
  return (
    <HorizontalScrollCue
      className={`border-b border-border ${compact ? "pb-3" : "pb-4"}`}
      viewportClassName="hide-scrollbar flex gap-2 overflow-x-auto overscroll-x-contain"
    >
      <nav aria-label="Điều hướng khu vực" className="flex w-max min-w-full gap-2">
        {visibleItems.map((item) => {
          const active = item.id === current;
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`shrink-0 rounded-control ${compact ? "px-2.5 py-1.5 text-[12px]" : "px-3 py-2 text-[13px]"} font-semibold transition ${
                active
                  ? "bg-brand text-white"
                  : "bg-surface-quiet text-ink-muted hover:bg-brand-soft hover:text-brand"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </HorizontalScrollCue>
  );
}

export function Panel({ title, description, actions, children, className = "" }) {
  return (
    <section className={`workspace-panel min-w-0 ${className}`}>
      {(title || actions) && (
        <div className="flex min-w-0 flex-col gap-3 border-b border-border bg-surface-raised/50 px-4 py-4 sm:px-5">
          <div className="w-full min-w-0">
            {title && (
              <h2 className="w-full min-w-0 whitespace-normal break-words font-semibold leading-6">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 w-full min-w-0 break-words text-[12px] leading-5 text-ink-muted">
                {description}
              </p>
            )}
          </div>
          {actions && <div className="w-full min-w-0 max-w-full">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatusPill({ value }) {
  return (
    <span className="inline-flex rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand">
      {valueLabel(value)}
    </span>
  );
}

export function EmptyState({ children, actionHref, actionLabel, onAction }) {
  return (
    <div
      className="flex min-h-28 min-w-0 flex-col items-center justify-center px-5 py-8 text-center text-[13px] text-ink-muted sm:px-8"
      role="status"
    >
      <p className="font-medium">{children}</p>
      {onAction ? (
        <button type="button" className="apple-button mt-4" onClick={onAction}>
          {actionLabel}
        </button>
      ) : actionHref ? (
        <Link href={actionHref} className="apple-button mt-4">
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="space-y-4 py-2" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
      <span className="sr-only">Đang tải dữ liệu</span>
      <div aria-hidden="true" className="grid gap-3 sm:grid-cols-3">
        <div className="skeleton h-20" />
        <div className="skeleton h-20" />
        <div className="skeleton h-20" />
      </div>
      <div aria-hidden="true" className="skeleton h-10 w-full" />
      <div aria-hidden="true" className="space-y-2">
        <div className="skeleton h-12 w-full" />
        <div className="skeleton h-12 w-full" />
        <div className="skeleton h-12 w-full" />
      </div>
    </div>
  );
}

export function InitialLoadState({ title, projectId, loading, error, onRetry }) {
  return (
    <WorkspacePage title={title} actions={<ProjectCrumb projectId={projectId} />}>
      {loading ? (
        <LoadingState />
      ) : (
        <div className="space-y-3">
          <ErrorState message={error || "Không thể tải dữ liệu"} />
          <button className="secondary-button" type="button" onClick={onRetry}>
            Tải lại
          </button>
        </div>
      )}
    </WorkspacePage>
  );
}

export function ErrorState({ message }) {
  return (
    <p role="alert" className="rounded-control bg-danger-soft p-4 text-[13px] text-danger">
      {message}
    </p>
  );
}

export function DegradedBanner({ mode, message }) {
  if (!mode || mode === "NORMAL") return null;
  return (
    <p
      role="status"
      className="rounded-control border border-warning/30 bg-warning-soft p-4 text-[13px] text-warning"
    >
      {message ||
        `Hệ thống đang hoạt động giới hạn do ${valueLabel(mode)} các thao tác vẫn được lưu và có thể cần kiểm tra thủ công`}
    </p>
  );
}

export function Metric({ label, value, detail }) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-[0_8px_20px_rgba(48,47,42,0.035)] sm:p-5">
      <p className="text-[30px] font-semibold tracking-[-0.04em]">{value}</p>
      <p className="mt-2 text-[12px] font-semibold leading-5 text-ink-muted">{label}</p>
      {detail && <p className="mt-2 text-[11px] text-ink-faint">{detail}</p>}
    </section>
  );
}

export function ProjectCrumb({ projectId, projectName }) {
  return (
    <Link className="text-[13px] font-semibold text-brand md:hidden" href={`/du-an/${projectId}`}>
      {projectName || "Về dự án"}
    </Link>
  );
}
