"use client";
import { useCallback, useEffect, useRef, useState } from "react";
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
  ["enable_comment_notifications", "Thông báo khi có bình luận"],
  ["enable_mention_notifications", "Thông báo khi được nhắc tên"],
  ["enable_system_notifications", "Thông báo hệ thống"],
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
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_8px_24px_rgba(48,47,42,0.04)]">
      <div className="border-b border-border bg-surface-raised px-5 py-4">
        <h2 className="font-semibold">Cài đặt thông báo</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Chọn loại thông báo muốn nhận trong tài khoản.
        </p>
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
      ) : (
        <form className="space-y-5 p-5" onSubmit={save}>
          {error && (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          )}
          <fieldset disabled={loading || saving} className="space-y-4">
            <legend className="sr-only">Loại thông báo</legend>
            {settingOptions.map(([key, label]) => (
              <label className="flex min-h-11 items-center gap-3 text-sm" key={key}>
                <input
                  type="checkbox"
                  checked={Boolean(settings[key])}
                  onChange={(event) => {
                    setSettings((current) => ({ ...current, [key]: event.target.checked }));
                    setSaved(false);
                  }}
                />
                <span>{label}</span>
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={loading || saving}>
              {loading ? "Đang tải" : saving ? "Đang lưu" : "Lưu cài đặt"}
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
