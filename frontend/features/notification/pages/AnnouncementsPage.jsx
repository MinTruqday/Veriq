"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import EmptyState from "@/shared/components/common/EmptyState";
import PageLoader from "@/shared/components/common/PageLoader";
import { Button } from "@/shared/components/ui/Button";
import InlineState from "@/shared/components/common/InlineState";
import PageHeader from "@/shared/components/layout/PageHeader";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import { useAnnouncementsPage } from "../hooks/useAnnouncements";
function formatDate(value) {
  if (!value) return "Chưa ghi nhận";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Chưa ghi nhận"
    : new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}
export default function AnnouncementsPage() {
  const [filter, setFilter] = useState("all");
  const {
    items,
    unread,
    loading,
    processing,
    error,
    loadFailed,
    reload,
    markRead,
    markAllRead,
    remove,
  } = useAnnouncementsPage();
  const visible = useMemo(
    () => (filter === "unread" ? items.filter((item) => !item.is_read) : items),
    [filter, items],
  );
  if (loading) return <PageLoader rows={6} />;
  return (
    <div className="mx-auto w-full max-w-[1480px] min-w-0">
      <PageHeader
        title="Thông báo"
        meta={`${unread} chưa đọc`}
        actions={
          <Button variant="secondary" onClick={markAllRead} disabled={!unread || processing}>
            {processing ? "Đang xử lý" : "Đánh dấu đã đọc"}
          </Button>
        }
      />

      {error && (
        <div className="mb-6">
          <InlineState
            title={loadFailed ? "Không thể tải thông báo" : "Không thể cập nhật thông báo"}
            detail={error}
            tone="danger"
            action={
              <Button variant="secondary" onClick={reload}>
                Tải lại
              </Button>
            }
          />
        </div>
      )}

      <div className="mb-5">
        <SegmentedTabs
          label="Lọc thông báo"
          value={filter}
          onChange={setFilter}
          tabs={[
            { id: "all", label: "Tất cả", count: items.length },
            { id: "unread", label: "Chưa đọc", count: unread },
          ]}
        />
      </div>

      {loadFailed ? null : visible.length === 0 ? (
        <EmptyState
          text={filter === "unread" ? "Không có thông báo chưa đọc" : "Chưa có thông báo"}
          bordered
        />
      ) : (
        <div className="overflow-hidden rounded-panel border border-border bg-surface">
          {visible.map((item) => {
            const id = item._id || item.id || "";
            return (
              <article
                key={id}
                className={`border-b border-border px-4 py-4 last:border-b-0 md:px-5 ${item.is_read ? "" : "border-l-2 border-l-brand bg-brand-soft/40"}`}
              >
                <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <h2 className="min-w-0 break-words text-[15px] font-semibold text-ink">
                        {item.title || "Thông báo"}
                      </h2>
                      {!item.is_read && (
                        <span className="rounded-full bg-brand px-2 py-0.5 text-[11px] font-semibold text-white">
                          Chưa đọc
                        </span>
                      )}
                    </div>
                    <p className="mt-1 max-w-[72ch] break-words text-[14px] leading-relaxed text-ink-muted">
                      {item.message || item.body || "Không có nội dung"}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-4 text-[13px]">
                      {item.link && (
                        <Link
                          href={item.link}
                          className="font-semibold text-brand underline-offset-4 hover:text-brand-hover hover:underline"
                        >
                          Mở nội dung
                        </Link>
                      )}
                      {!item.is_read && (
                        <button
                          type="button"
                          onClick={() => markRead(id)}
                          className="font-semibold text-ink-muted underline-offset-4 hover:text-ink hover:underline"
                        >
                          Đánh dấu đã đọc
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => remove(id)}
                        disabled={processing}
                        className="font-semibold text-ink-muted underline-offset-4 hover:text-danger hover:underline disabled:opacity-50"
                      >
                        Xóa
                      </button>
                    </div>
                  </div>
                  <time className="shrink-0 text-[12px] text-ink-faint sm:pt-1">
                    {formatDate(item.created_at)}
                  </time>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
