"use client";
import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
function cn(...inputs) {
  return twMerge(clsx(inputs));
}
export function Modal({
  isOpen,
  onClose,
  children,
  className,
  showCloseButton = true,
  ariaLabel = "Hộp thoại",
}) {
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);
  const previousOverflowRef = useRef("");
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;
      previousOverflowRef.current = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      const frame = requestAnimationFrame(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        const focusableSelector =
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
        const firstInput = dialog.querySelector(
          'input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled])',
        );
        const firstFocusable = dialog.querySelector(focusableSelector);
        (dialog.querySelector("[autofocus]") || firstInput || firstFocusable || dialog).focus();
      });
      const handleKeyDown = (event) => {
        if (event.key === "Escape") {
          if (
            [...document.querySelectorAll('[role="dialog"][aria-modal="true"]')].at(-1) !==
            dialogRef.current
          ) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          onCloseRef.current();
        }
        if (event.key !== "Tab" || !dialogRef.current) return;
        const focusable = dialogRef.current.querySelectorAll(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (!focusable.length) {
          event.preventDefault();
          dialogRef.current.focus();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!dialogRef.current.contains(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
          return;
        }
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      };
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        cancelAnimationFrame(frame);
        document.removeEventListener("keydown", handleKeyDown);
        document.body.style.overflow = previousOverflowRef.current;
        previousFocusRef.current?.focus();
      };
    }
  }, [isOpen]);
  if (!isOpen) return null;
  return createPortal(
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-ink/30 p-4 backdrop-blur-[2px] animate-in fade-in"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        tabIndex={-1}
        className={cn(
          "modal-dialog hide-scrollbar relative max-h-[90dvh] w-full max-w-md overflow-x-hidden overflow-y-auto overscroll-contain rounded-panel bg-surface p-0 shadow-[0_24px_80px_rgba(32,32,30,0.18)] outline-none animate-in zoom-in-95",
          className,
        )}
      >
        {showCloseButton && (
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-control text-ink-muted transition-colors hover:bg-surface-quiet hover:text-ink"
            aria-label="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        )}
        {children}
      </div>
    </div>,
    document.body,
  );
}
export function ModalHeader({ children, className }) {
  return <div className={cn("border-b border-border p-6 pr-16", className)}>{children}</div>;
}
export function ModalTitle({ children, className }) {
  return (
    <h3 className={cn("text-[20px] font-semibold tracking-[-0.02em] text-ink", className)}>
      {children}
    </h3>
  );
}
export function ModalDescription({ children, className }) {
  return (
    <p className={cn("mt-1 text-[14px] leading-relaxed text-ink-muted", className)}>{children}</p>
  );
}
export function ModalContent({ children, className }) {
  return <div className={cn("space-y-4 bg-surface p-6", className)}>{children}</div>;
}
export function ModalFooter({ children, className }) {
  return (
    <div
      className={cn(
        "sticky bottom-0 z-10 flex flex-col-reverse items-stretch gap-2 border-t border-border bg-surface-raised p-4 shadow-[0_-8px_14px_rgba(32,32,30,0.06)] [&>*]:w-full sm:flex-row sm:items-center sm:justify-end sm:gap-3 sm:p-6 sm:[&>*]:w-auto",
        className,
      )}
    >
      {children}
    </div>
  );
}
