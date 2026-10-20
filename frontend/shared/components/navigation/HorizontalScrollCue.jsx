"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

export default function HorizontalScrollCue({
  children,
  className = "",
  viewportClassName = "",
  ariaLabel,
  scrollLabel = "vùng nội dung",
}) {
  const viewportRef = useRef(null);
  const [edges, setEdges] = useState({ overflow: false, start: true, end: true });

  const updateEdges = useCallback(() => {
    const element = viewportRef.current;
    if (!element) return;
    const maxScroll = element.scrollWidth - element.clientWidth;
    setEdges({
      overflow: maxScroll > 4,
      start: element.scrollLeft <= 4,
      end: element.scrollLeft >= maxScroll - 4,
    });
  }, []);

  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(updateEdges);
    observer.observe(element);
    Array.from(element.children).forEach((child) => observer.observe(child));
    element.addEventListener("scroll", updateEdges, { passive: true });
    updateEdges();
    return () => {
      observer.disconnect();
      element.removeEventListener("scroll", updateEdges);
    };
  }, [children, updateEdges]);

  const scroll = (direction) => {
    viewportRef.current?.scrollBy({
      left: direction * Math.max(viewportRef.current.clientWidth * 0.75, 180),
      behavior: "smooth",
    });
  };

  return (
    <div
      className={`grid min-w-0 items-center gap-1 ${className}`}
      role={ariaLabel ? "region" : undefined}
      aria-label={ariaLabel}
      style={{
        gridTemplateColumns: edges.overflow
          ? `${edges.start ? "minmax(0, 1fr)" : "2rem minmax(0, 1fr)"}${edges.end ? "" : " 2rem"}`
          : "minmax(0, 1fr)",
      }}
    >
      {edges.overflow && !edges.start && (
        <button
          aria-label={`Cuộn ${scrollLabel} sang trái`}
          className="flex h-8 w-8 items-center justify-center rounded-control bg-surface text-ink-muted shadow-card"
          onClick={() => scroll(-1)}
          type="button"
        >
          <ChevronLeft aria-hidden="true" size={16} />
        </button>
      )}
      <div
        className={viewportClassName}
        ref={viewportRef}
        onScroll={updateEdges}
        tabIndex={edges.overflow ? 0 : undefined}
      >
        {children}
      </div>
      {edges.overflow && !edges.end && (
        <button
          aria-label={`Cuộn ${scrollLabel} sang phải`}
          className="flex h-8 w-8 items-center justify-center rounded-control bg-surface text-ink-muted shadow-card"
          onClick={() => scroll(1)}
          type="button"
        >
          <ChevronRight aria-hidden="true" size={16} />
        </button>
      )}
    </div>
  );
}
