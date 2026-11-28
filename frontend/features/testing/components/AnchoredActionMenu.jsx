"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MoreHorizontal } from "lucide-react";

export default function AnchoredActionMenu({ label, children, className = "" }) {
  const triggerRef = useRef(null);
  const menuRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState(null);

  useLayoutEffect(() => {
    if (!open || !menuRef.current || !triggerRef.current) return undefined;
    const trigger = triggerRef.current.getBoundingClientRect();
    const menu = menuRef.current.getBoundingClientRect();
    const width = Math.min(menu.width, window.innerWidth - 24);
    const height = Math.min(menu.height, window.innerHeight - 24);
    const left = Math.max(12, Math.min(trigger.right - width, window.innerWidth - width - 12));
    const below = trigger.bottom + 8;
    const top = below + height <= window.innerHeight - 12 ? below : trigger.top - height - 8;
    setPosition({ left, top: Math.max(12, top), maxHeight: window.innerHeight - 24, width });

    const closeOnViewportChange = () => setOpen(false);
    window.addEventListener("resize", closeOnViewportChange);
    window.addEventListener("scroll", closeOnViewportChange, true);
    return () => {
      window.removeEventListener("resize", closeOnViewportChange);
      window.removeEventListener("scroll", closeOnViewportChange, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const closeOutside = (event) => {
      if (triggerRef.current?.contains(event.target) || menuRef.current?.contains(event.target))
        return;
      setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={className || "icon-button flex h-9 w-9 items-center justify-center"}
        aria-label={label}
        aria-expanded={open}
        title="Thao tác"
        onClick={(event) => {
          event.stopPropagation();
          setPosition(null);
          setOpen((value) => !value);
        }}
      >
        <MoreHorizontal size={18} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className="fixed z-[1000] max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-control border border-border bg-surface p-1 shadow-panel"
            style={{
              left: position?.left ?? -10000,
              top: position?.top ?? -10000,
              width: position?.width ?? 224,
              maxHeight: position?.maxHeight ?? "calc(100dvh - 1.5rem)",
              visibility: position ? "visible" : "hidden",
            }}
            onClick={(event) => {
              event.stopPropagation();
              if (event.target.closest("button, a[href]")) setOpen(false);
            }}
          >
            <div className="flex flex-col gap-1">{children}</div>
          </div>,
          document.body,
        )}
    </>
  );
}
