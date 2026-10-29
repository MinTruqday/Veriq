"use client";
import { isValidElement } from "react";
import { useEffect, useRef } from "react";
import HorizontalScrollCue from "@/shared/components/navigation/HorizontalScrollCue";
import { EmptyState } from "./WorkspacePrimitives";

function hasRenderableContent(value) {
  if (value === null || value === undefined || value === false || value === "") return false;
  if (Array.isArray(value)) return value.some(hasRenderableContent);
  if (isValidElement(value)) {
    if (
      value.props["aria-label"] ||
      value.props.title ||
      ["a", "button", "input", "select", "textarea"].includes(value.type)
    )
      return true;
    return hasRenderableContent(value.props.children);
  }
  return true;
}

export default function DataTable({
  columns,
  items,
  empty = "Chưa có dữ liệu",
  emptyActionHref,
  emptyActionLabel,
  onSelect,
  activeRowId,
  selectedIds,
  onSelectionChange,
  selectionLabel = "Chọn mục",
  selectionDisabled = false,
  getRowKey,
  minTableWidth = 0,
  layout = "table",
}) {
  const selectable = Array.isArray(selectedIds) && typeof onSelectionChange === "function";
  const itemId = (item) => item._id ?? item.id ?? item.key ?? item.code;
  const itemLabel = (item, index) =>
    item.title ||
    item.name ||
    item.test_case_key ||
    item.requirement_key ||
    item.defect_key ||
    `dòng ${index + 1}`;
  const pageIds = (items || []).map(itemId).filter((id) => id !== undefined && id !== null);
  const allSelected =
    selectable && pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
  const someSelected = selectable && pageIds.some((id) => selectedIds.includes(id));
  const desktopSelectAllRef = useRef(null);
  const mobileSelectAllRef = useRef(null);
  useEffect(() => {
    const indeterminate = someSelected && !allSelected;
    if (desktopSelectAllRef.current) desktopSelectAllRef.current.indeterminate = indeterminate;
    if (mobileSelectAllRef.current) mobileSelectAllRef.current.indeterminate = indeterminate;
  }, [allSelected, someSelected]);
  if (!items?.length)
    return (
      <EmptyState actionHref={emptyActionHref} actionLabel={emptyActionLabel}>
        {empty}
      </EmptyState>
    );
  const visibleColumns = columns.filter(
    (column) =>
      !column.hideWhenEmpty ||
      items.some((item) => {
        const value = column.render ? column.render(item) : item[column.key];
        return hasRenderableContent(value);
      }),
  );
  const rowKey = (item, index) =>
    `${String(getRowKey?.(item, index) ?? itemId(item) ?? "dòng")}-${index}`;
  const toggleAll = () =>
    onSelectionChange(
      allSelected
        ? selectedIds.filter((id) => !pageIds.includes(id))
        : Array.from(new Set([...selectedIds, ...pageIds])),
    );
  const toggle = (id) => {
    if (id === undefined || id === null) return;
    onSelectionChange(
      selectedIds.includes(id) ? selectedIds.filter((value) => value !== id) : [...selectedIds, id],
    );
  };
  const renderValue = (column, item) =>
    column.render ? column.render(item) : String(item[column.key] ?? "");
  const renderMobileValue = (column, item) =>
    column.mobileRender ? column.mobileRender(item) : renderValue(column, item);
  const desktopTableWidth = Math.max(
    minTableWidth,
    visibleColumns.reduce((width, column) => width + (column.minWidth || 144), 0) +
      (selectable ? 48 : 0),
  );
  const selectRow = (event, item) => {
    if (
      !onSelect ||
      event.target.closest?.("button, a[href], input, select, textarea, [role='button']")
    )
      return;
    onSelect(item);
  };
  const openFromKeyboard = (event, item) => {
    if (!onSelect || event.target !== event.currentTarget) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(item);
    }
  };
  return (
    <div
      className={`data-table-responsive min-w-0 ${layout === "wide-table" ? "data-table-responsive-wide" : ""} ${layout === "cards" ? "data-table-responsive-cards" : ""}`}
    >
      <div className={`data-table-desktop ${layout === "cards" ? "hidden" : ""}`}>
        <HorizontalScrollCue
          ariaLabel="Bảng dữ liệu"
          scrollLabel="bảng dữ liệu"
          viewportClassName="min-w-0 overflow-x-auto"
        >
          <table
            className="w-full text-left text-[13px]"
            style={{ minWidth: `${desktopTableWidth}px` }}
          >
            <thead className="bg-surface-quiet text-[11px] uppercase tracking-wide text-ink-muted">
              <tr>
                {selectable && (
                  <th className="w-12 px-4 py-3">
                    <input
                      aria-label="Chọn tất cả mục trên trang"
                      checked={allSelected}
                      disabled={selectionDisabled}
                      ref={desktopSelectAllRef}
                      type="checkbox"
                      onChange={toggleAll}
                    />
                  </th>
                )}
                {visibleColumns.map((column) => (
                  <th
                    className="whitespace-nowrap px-4 py-3 font-semibold"
                    key={column.key}
                    style={column.minWidth ? { minWidth: `${column.minWidth}px` } : undefined}
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((item, index) => (
                <tr
                  key={rowKey(item, index)}
                  className={`${onSelect ? "cursor-pointer hover:bg-surface-quiet" : ""} ${activeRowId === itemId(item) ? "bg-brand-soft/60" : ""}`}
                  onClick={(event) => selectRow(event, item)}
                  onKeyDown={(event) => openFromKeyboard(event, item)}
                  tabIndex={onSelect ? 0 : undefined}
                  aria-label={onSelect ? `Mở ${itemLabel(item, index)}` : undefined}
                >
                  {selectable && (
                    <td className="w-12 px-4 py-3 align-top">
                      <input
                        aria-label={`${selectionLabel} ${itemLabel(item, index)}`}
                        checked={selectedIds.includes(itemId(item))}
                        disabled={
                          selectionDisabled || itemId(item) === undefined || itemId(item) === null
                        }
                        type="checkbox"
                        onClick={(event) => event.stopPropagation()}
                        onChange={() => toggle(itemId(item))}
                      />
                    </td>
                  )}
                  {visibleColumns.map((column) => (
                    <td
                      className="min-w-0 break-words px-4 py-3 align-top [&_button]:whitespace-nowrap"
                      key={column.key}
                      style={column.minWidth ? { minWidth: `${column.minWidth}px` } : undefined}
                    >
                      {renderValue(column, item)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </HorizontalScrollCue>
      </div>
      <div
        className={`data-table-mobile divide-y divide-border p-4 ${layout === "cards" ? "block" : ""}`}
      >
        {selectable && (
          <label
            className="flex min-h-11 items-center gap-3 pb-3 text-[12px] font-semibold text-ink-muted"
            onClick={(event) => event.stopPropagation()}
          >
            <input
              aria-label="Chọn tất cả mục trên trang"
              checked={allSelected}
              disabled={selectionDisabled}
              ref={mobileSelectAllRef}
              type="checkbox"
              onChange={toggleAll}
            />
            Chọn tất cả trên trang
          </label>
        )}
        {items.map((item, index) => (
          <article
            key={rowKey(item, index)}
            className={`py-4 first:pt-0 last:pb-0 ${activeRowId === itemId(item) || (selectable && selectedIds.includes(itemId(item))) ? "rounded-lg bg-brand-soft/40 px-3" : ""} ${onSelect ? "cursor-pointer hover:bg-surface-quiet active:bg-brand-soft/40" : ""}`}
            onClick={(event) => selectRow(event, item)}
            onKeyDown={(event) => openFromKeyboard(event, item)}
            tabIndex={onSelect ? 0 : undefined}
            aria-label={onSelect ? `Mở ${itemLabel(item, index)}` : undefined}
          >
            {selectable && (
              <label
                className="mb-3 flex min-h-11 items-center gap-2 text-[12px] font-semibold"
                onClick={(event) => event.stopPropagation()}
              >
                <input
                  aria-label={`${selectionLabel} ${itemLabel(item, index)}`}
                  checked={selectedIds.includes(itemId(item))}
                  disabled={
                    selectionDisabled || itemId(item) === undefined || itemId(item) === null
                  }
                  type="checkbox"
                  onClick={(event) => event.stopPropagation()}
                  onChange={() => toggle(itemId(item))}
                />
                Chọn
              </label>
            )}
            <dl className="space-y-3">
              {visibleColumns.map((column) => {
                const value = renderMobileValue(column, item);
                if (value === null || value === undefined || value === "") return null;
                return (
                  <div className="grid grid-cols-[minmax(0,40%)_1fr] gap-3" key={column.key}>
                    <dt className="min-w-0 break-words text-[12px] font-semibold leading-5 text-ink-muted">
                      {column.label}
                    </dt>
                    <dd className="min-w-0 break-words text-[13px] text-ink">{value}</dd>
                  </div>
                );
              })}
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
