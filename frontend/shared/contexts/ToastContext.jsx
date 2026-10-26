"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
const ToastContext = createContext(undefined);
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const removeToast = useCallback((id) => {
    setToasts((items) => items.filter((item) => item.id !== id));
  }, []);
  const showToast = useCallback(
    (message, type = "info") => {
      const id = crypto.randomUUID();
      setToasts((items) => [...items, { id, message, type }]);
      window.setTimeout(() => removeToast(id), 4000);
    },
    [removeToast],
  );
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {mounted && toasts.length > 0 && (
        <div
          className="pointer-events-none fixed bottom-4 right-4 z-[2500] flex max-h-[70dvh] w-[min(380px,calc(100vw-2rem))] flex-col gap-2 overflow-y-auto overscroll-contain sm:bottom-5 sm:right-6"
          aria-live="polite"
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-panel border bg-surface px-4 py-3 shadow-[0_12px_36px_rgba(32,32,30,0.12)] ${toast.type === "error" ? "border-danger/40" : toast.type === "success" ? "border-brand/40" : "border-border-strong"}`}
              role={toast.type === "error" ? "alert" : "status"}
            >
              <p className="min-w-0 flex-1 text-[13px] font-medium leading-5 text-ink">
                {toast.message}
              </p>
              <button
                type="button"
                onClick={() => removeToast(toast.id)}
                className="-mr-2 -mt-1 flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-control px-2 text-[12px] font-semibold text-ink-muted hover:bg-surface-quiet hover:text-ink"
              >
                Đóng
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("ToastProvider chưa được khởi tạo");
  return context;
}
