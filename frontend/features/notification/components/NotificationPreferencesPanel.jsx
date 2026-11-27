"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { AtSign, Bell, MessageSquare } from "lucide-react";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import {
  getAnnouncementSettingsAPI,
  updateAnnouncementSettingsAPI,
} from "../services/announcement.service";

const initialSettings = {
  enable_comment_notifications: true,
  enable_mention_notifications: true,
  enable_system_notifications: true,
};

const settingOptions = [
  {
    key: "enable_comment_notifications",
    label: "Bình luận",
    description: "Nhận thông báo khi có bình luận mới liên quan đến bạn.",
    Icon: MessageSquare,
  },
  {
    key: "enable_mention_notifications",
    label: "Được nhắc tên",
    description: "Theo dõi những lần thành viên nhắc đến bạn trong nội dung.",
    Icon: AtSign,
  },
  {
    key: "enable_system_notifications",
    label: "Thông báo hệ thống",
    description: "Nhận cập nhật hệ thống và thông tin vận hành tài khoản.",
    Icon: Bell,
  },
];

export default function NotificationPreferencesPanel() {
  const requestId = useRef(0);
  const [settings, setSettings] = useState(initialSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setLoadFailed(false);
    setError("");
    setSaved(false);
    try {
      const result = await getAnnouncementSettingsAPI();
      if (requestId.current !== currentRequest) return;
      setSettings({ ...initialSettings, ...(result || {}) });
    } catch (reason) {
      if (requestId.current !== currentRequest) return;
      setLoadFailed(true);
      setError(reason instanceof Error ? reason.message : "Không thể tải cài đặt thông báo");
    } finally {
      if (requestId.current === currentRequest) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    return () => {
      requestId.current += 1;
    };
  }, [load]);

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await updateAnnouncementSettingsAPI(settings);
      setSaved(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể lưu cài đặt thông báo");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-panel border border-border bg-surface">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-surface-raised px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Tùy chọn cá nhân
          </p>
          <h2 className="mt-1 font-semibold">Cài đặt thông báo</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Chọn các sự kiện sẽ gửi thông báo đến tài khoản của bạn.
          </p>
        </div>
        {!loading && !loadFailed && (
          <span className="rounded-control border border-border bg-surface px-2.5 py-1 text-xs text-ink-muted">
            {settingOptions.filter(({ key }) => settings[key]).length}/{settingOptions.length} đang
            bật
          </span>
        )}
      </div>
      {loadFailed ? (
        <div className="p-5">
          <InlineState
            title="Không thể tải cài đặt thông báo"
            detail={error}
            tone="danger"
            action={
              <Button variant="secondary" onClick={() => void load()}>
                Tải lại
              </Button>
            }
          />
        </div>
      ) : loading ? (
        <p className="p-5 text-sm text-ink-muted" role="status" aria-live="polite">
          Đang tải cài đặt thông báo
        </p>
      ) : (
        <form className="grid gap-5 p-5" onSubmit={save}>
          {error && (
            <p
              className="rounded-control border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger"
              role="alert"
            >
              {error}
            </p>
          )}
          <fieldset disabled={saving} className="grid gap-3 lg:grid-cols-3">
            <legend className="sr-only">Loại thông báo</legend>
            {settingOptions.map(({ key, label, description, Icon }) => {
              const enabled = Boolean(settings[key]);
              return (
                <label
                  className={`group flex min-h-32 cursor-pointer flex-col justify-between gap-5 rounded-panel border p-4 transition-colors ${
                    enabled
                      ? "border-brand/40 bg-brand-soft/40"
                      : "border-border bg-surface hover:bg-surface-quiet"
                  }`}
                  key={key}
                >
                  <div className="flex items-start gap-3">
                    <span className="grid size-9 shrink-0 place-items-center rounded-control border border-border bg-surface text-ink-muted">
                      <Icon aria-hidden="true" className="size-4" />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-ink">{label}</span>
                      <span className="mt-1 block text-xs leading-5 text-ink-muted">
                        {description}
                      </span>
                    </span>
                  </div>
                  <span className="flex items-center justify-between gap-3 border-t border-border/70 pt-3">
                    <span className="text-xs font-medium text-ink-muted">
                      {enabled ? "Đang bật" : "Đang tắt"}
                    </span>
                    <span className="relative inline-flex shrink-0">
                      <input
                        type="checkbox"
                        role="switch"
                        aria-label={label}
                        checked={enabled}
                        className="peer sr-only"
                        onChange={(event) => {
                          setSettings((current) => ({ ...current, [key]: event.target.checked }));
                          setSaved(false);
                        }}
                      />
                      <span
                        aria-hidden="true"
                        className="h-5 w-9 rounded-full bg-border transition-colors peer-checked:bg-brand peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand"
                      />
                      <span
                        aria-hidden="true"
                        className="pointer-events-none absolute left-0.5 top-0.5 size-4 rounded-full bg-surface shadow-sm transition-transform peer-checked:translate-x-4"
                      />
                    </span>
                  </span>
                </label>
              );
            })}
          </fieldset>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="text-xs text-ink-faint">Thay đổi chỉ có hiệu lực sau khi lưu.</p>
            <Button type="submit" disabled={saving}>
              {saving ? "Đang lưu" : "Lưu cài đặt"}
            </Button>
            {saved && (
              <p className="text-sm text-brand" role="status">
                Đã lưu cài đặt thông báo
              </p>
            )}
          </div>
        </form>
      )}
    </section>
  );
}
