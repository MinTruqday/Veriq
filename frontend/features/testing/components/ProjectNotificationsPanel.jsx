"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { toggleNotificationSelection } from "./notificationSelection.mjs";
import { isSupportedTimeZone, timeZoneOptions } from "@/shared/lib/timeZone.mjs";
import { RefreshCw } from "lucide-react";

const DEFAULT_PREFERENCES = {
  revision: 0,
  digest_frequency: "immediate",
  channels: ["in_app"],
  muted_events: [],
  quiet_hours_start: "",
  quiet_hours_end: "",
};

const DEFAULT_RULES = {
  revision: 0,
  enabled_events: [],
  channels: ["in_app"],
  target_roles: [],
  escalation_minutes: "",
};

export default function ProjectNotificationsPanel({ project }) {
  const [watches, setWatches] = useState([]);
  const [preferences, setPreferences] = useState({
    ...DEFAULT_PREFERENCES,
    timezone: project.timezone || "",
  });
  const [rules, setRules] = useState(DEFAULT_RULES);
  const [artifactType, setArtifactType] = useState("requirement");
  const [artifactId, setArtifactId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState({ watches: false, preferences: false, rules: false });
  const [loaded, setLoaded] = useState({ watches: false, preferences: false, rules: false });
  const [loadErrors, setLoadErrors] = useState({});
  const [saving, setSaving] = useState({ watches: false, preferences: false, rules: false });
  const loadSequence = useRef(0);
  const can = (permission) => project.current_permissions?.includes(permission);
  const canManageWatches = can("notification.watch.manage");
  const canManagePreferences = can("notification.preferences.manage");
  const canManageRules = project.current_permissions?.includes("notification.project_rule.manage");
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    const requested = [
      canManageWatches && ["watches", () => testingApi.listProjectNotificationWatches(project._id)],
      canManagePreferences && [
        "preferences",
        () => testingApi.getProjectNotificationPreferences(project._id),
      ],
      canManageRules && ["rules", () => testingApi.getProjectNotificationRules(project._id)],
    ].filter(Boolean);
    setError("");
    setLoadErrors({});
    setLoading(Object.fromEntries(requested.map(([section]) => [section, true])));
    setLoaded(Object.fromEntries(requested.map(([section]) => [section, false])));
    const results = await Promise.allSettled(requested.map(([, request]) => request()));
    if (sequence !== loadSequence.current) return false;
    const nextErrors = {};
    const nextLoaded = {};
    results.forEach((result, index) => {
      const section = requested[index][0];
      nextLoaded[section] = result.status === "fulfilled";
      if (result.status === "rejected") {
        nextErrors[section] = messageOf(result.reason);
        return;
      }
      const value = result.value;
      if (section === "watches") setWatches(value || []);
      if (section === "preferences") {
        setPreferences({
          ...DEFAULT_PREFERENCES,
          ...value,
          timezone:
            value?.timezone || project.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        });
      }
      if (section === "rules") setRules({ ...DEFAULT_RULES, ...value });
    });
    setLoading(Object.fromEntries(requested.map(([section]) => [section, false])));
    setLoaded((current) => ({ ...current, ...nextLoaded }));
    setLoadErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }, [canManagePreferences, canManageRules, canManageWatches, project._id, project.timezone]);
  useEffect(() => {
    setLoaded({ watches: false, preferences: false, rules: false });
    void load();
    return () => {
      loadSequence.current += 1;
    };
  }, [load]);
  const addWatch = async (event) => {
    event.preventDefault();
    if (!loaded.watches || saving.watches) return;
    setError("");
    setNotice("");
    setSaving((current) => ({ ...current, watches: true }));
    try {
      await testingApi.setProjectNotificationWatch(project._id, artifactType, artifactId, true);
      setArtifactId("");
      if (await load()) setNotice("Đã thêm nội dung vào danh sách đang theo dõi");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving((current) => ({ ...current, watches: false }));
    }
  };
  const savePreferences = async (event) => {
    event.preventDefault();
    if (!loaded.preferences || saving.preferences) return;
    setError("");
    setNotice("");
    if (!isSupportedTimeZone(preferences.timezone)) {
      setError("Hãy chọn một múi giờ IANA hợp lệ trước khi lưu giờ yên lặng");
      return;
    }
    setSaving((current) => ({ ...current, preferences: true }));
    try {
      const value = await testingApi.updateProjectNotificationPreferences(project._id, {
        expected_revision: preferences.revision,
        digest_frequency: preferences.digest_frequency,
        channels: preferences.channels,
        muted_events: preferences.muted_events,
        quiet_hours_start: preferences.quiet_hours_start || null,
        quiet_hours_end: preferences.quiet_hours_end || null,
        timezone: preferences.timezone,
      });
      setPreferences({
        ...DEFAULT_PREFERENCES,
        timezone: project.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        ...value,
      });
      setNotice("Đã lưu tùy chọn thông báo");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving((current) => ({ ...current, preferences: false }));
    }
  };
  const saveRules = async (event) => {
    event.preventDefault();
    if (!loaded.rules || saving.rules) return;
    setError("");
    setNotice("");
    setSaving((current) => ({ ...current, rules: true }));
    try {
      const value = await testingApi.updateProjectNotificationRules(project._id, {
        expected_revision: rules.revision,
        enabled_events: rules.enabled_events,
        channels: rules.channels,
        target_roles: rules.target_roles,
        escalation_minutes: rules.escalation_minutes ? Number(rules.escalation_minutes) : null,
      });
      setRules({ ...DEFAULT_RULES, ...value });
      setNotice("Đã lưu quy tắc thông báo dự án");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving((current) => ({ ...current, rules: false }));
    }
  };
  if (!canManageWatches && !canManagePreferences && !canManageRules) {
    return null;
  }
  return (
    <Panel
      title="Thông báo dự án"
      actions={
        <button
          aria-label="Tải lại cài đặt thông báo"
          className="icon-button h-9 w-9"
          disabled={Object.values(loading).some(Boolean)}
          onClick={() => void load()}
          title="Tải lại cài đặt thông báo"
          type="button"
        >
          <RefreshCw aria-hidden="true" className="size-4" />
        </button>
      }
    >
      {error && <ErrorState message={error} />}
      {notice && (
        <p className="border-b border-border px-5 py-3 text-sm text-ink-muted" role="status">
          {notice}
        </p>
      )}
      <div className="grid gap-4 p-4 xl:grid-cols-2 xl:gap-5 xl:p-5">
        {can("notification.watch.manage") && (
          <section className="min-w-0 space-y-4 rounded-panel border border-border bg-surface p-4">
            <header className="space-y-1">
              <h3 className="font-semibold text-ink">Dữ liệu đang theo dõi</h3>
              <p className="text-sm leading-5 text-ink-muted">
                Theo dõi một đối tượng để nhận cập nhật liên quan
              </p>
            </header>
            {loading.watches && (
              <p className="text-sm text-ink-muted">Đang tải danh sách theo dõi…</p>
            )}
            {loadErrors.watches && <ErrorState message={loadErrors.watches} />}
            <form className="space-y-3" onSubmit={addWatch}>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="field-label">
                  Loại dữ liệu
                  <select
                    aria-label="Loại dữ liệu theo dõi"
                    className="apple-input mt-2 w-full"
                    value={artifactType}
                    disabled={!loaded.watches || saving.watches}
                    onChange={(event) => setArtifactType(event.target.value)}
                  >
                    <option value="requirement">Yêu cầu</option>
                    <option value="test_case">Ca kiểm thử</option>
                    <option value="test_run">Lần chạy kiểm thử</option>
                    <option value="defect">Lỗi</option>
                  </select>
                </label>
                <label className="field-label">
                  Mã đối tượng
                  <input
                    aria-label="Mã dữ liệu theo dõi"
                    className="apple-input mt-2 w-full"
                    required
                    value={artifactId}
                    disabled={!loaded.watches || saving.watches}
                    onChange={(event) => setArtifactId(event.target.value)}
                  />
                </label>
              </div>
              <button
                className="secondary-button"
                disabled={!loaded.watches || saving.watches}
                type="submit"
              >
                {saving.watches ? "Đang cập nhật…" : "Theo dõi"}
              </button>
            </form>
            <div className="divide-y divide-border">
              {loaded.watches && watches.length === 0 && (
                <p className="text-sm text-ink-muted">Chưa theo dõi dữ liệu nào</p>
              )}
              {watches.map((item) => (
                <div
                  className="flex items-center justify-between gap-2 py-2 text-sm"
                  key={item._id}
                >
                  <span className="min-w-0 truncate">
                    {valueLabel(item.artifact_type)}{" "}
                    {item.artifact_label || "Đối tượng đang theo dõi"}
                  </span>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={saving.watches}
                    onClick={async () => {
                      setSaving((current) => ({ ...current, watches: true }));
                      try {
                        await testingApi.setProjectNotificationWatch(
                          project._id,
                          item.artifact_type,
                          item.artifact_id,
                          false,
                        );
                        const refreshed = await load();
                        if (refreshed) {
                          setError("");
                          setNotice("Đã bỏ theo dõi nội dung này");
                        } else {
                          setNotice("");
                        }
                      } catch (reason) {
                        setNotice("");
                        setError(messageOf(reason));
                      } finally {
                        setSaving((current) => ({ ...current, watches: false }));
                      }
                    }}
                  >
                    Bỏ theo dõi
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}
        {can("notification.preferences.manage") && (
          <form
            className="min-w-0 space-y-4 rounded-panel border border-border bg-surface p-4"
            onSubmit={savePreferences}
          >
            <header className="space-y-1">
              <h3 className="font-semibold text-ink">Tùy chọn cá nhân</h3>
              <p className="text-sm leading-5 text-ink-muted">
                Chọn tần suất, kênh nhận và khung giờ áp dụng cho tài khoản của bạn
              </p>
            </header>
            {loading.preferences && <p className="text-sm text-ink-muted">Đang tải tùy chọn…</p>}
            {loadErrors.preferences && <ErrorState message={loadErrors.preferences} />}
            <label className="field-label block">
              Tần suất bản tổng hợp
              <select
                aria-label="Tần suất bản tổng hợp"
                className="apple-input mt-2 w-full"
                disabled={!loaded.preferences || saving.preferences}
                value={preferences.digest_frequency}
                onChange={(event) =>
                  setPreferences({ ...preferences, digest_frequency: event.target.value })
                }
              >
                <option value="immediate">Ngay lập tức</option>
                <option value="daily">Hằng ngày</option>
                <option value="weekly">Hằng tuần</option>
                <option value="off">Tắt bản tổng hợp</option>
              </select>
            </label>
            <fieldset className="space-y-2 rounded-control border border-border p-3">
              <legend className="field-label px-1">Kênh cá nhân</legend>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  disabled={!loaded.preferences || saving.preferences}
                  checked={preferences.channels.includes("email")}
                  onChange={(event) =>
                    setPreferences({
                      ...preferences,
                      channels: event.target.checked ? ["in_app", "email"] : ["in_app"],
                    })
                  }
                />
                Nhận qua Email
              </label>
            </fieldset>
            <fieldset className="space-y-3 rounded-control border border-border p-3">
              <legend className="field-label px-1">Khung giờ yên lặng</legend>
              <p className="text-xs leading-5 text-ink-muted">
                Thời gian được tính theo múi giờ đã chọn bên dưới
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="field-label">
                  Bắt đầu giờ yên lặng
                  <input
                    aria-label="Bắt đầu giờ yên lặng"
                    className="apple-input mt-2"
                    disabled={!loaded.preferences || saving.preferences}
                    type="time"
                    value={preferences.quiet_hours_start || ""}
                    onChange={(event) =>
                      setPreferences({ ...preferences, quiet_hours_start: event.target.value })
                    }
                  />
                </label>
                <label className="field-label">
                  Kết thúc giờ yên lặng
                  <input
                    aria-label="Kết thúc giờ yên lặng"
                    className="apple-input mt-2"
                    disabled={!loaded.preferences || saving.preferences}
                    type="time"
                    value={preferences.quiet_hours_end || ""}
                    onChange={(event) =>
                      setPreferences({ ...preferences, quiet_hours_end: event.target.value })
                    }
                  />
                </label>
              </div>
            </fieldset>
            <label className="grid gap-1 text-sm">
              <span className="field-label">Múi giờ áp dụng</span>
              <select
                className="apple-input"
                disabled={!loaded.preferences || saving.preferences}
                aria-invalid={!isSupportedTimeZone(preferences.timezone)}
                value={preferences.timezone || ""}
                onChange={(event) => {
                  setPreferences({ ...preferences, timezone: event.target.value });
                  setError("");
                }}
              >
                {timeZoneOptions(preferences.timezone).map((option) => (
                  <option key={option.value} value={option.value} disabled={!option.valid}>
                    {option.label}
                  </option>
                ))}
              </select>
              {!isSupportedTimeZone(preferences.timezone) && (
                <span className="text-xs text-danger">
                  Múi giờ đã lưu không hợp lệ. Chọn múi giờ IANA để tiếp tục
                </span>
              )}
            </label>
            <button
              className="apple-button"
              disabled={!loaded.preferences || saving.preferences}
              type="submit"
            >
              {saving.preferences ? "Đang lưu…" : "Lưu tùy chọn"}
            </button>
          </form>
        )}
        {can("notification.project_rule.manage") && (
          <form
            className="min-w-0 space-y-4 rounded-panel border border-border bg-surface p-4 xl:col-span-2"
            onSubmit={saveRules}
          >
            <header className="space-y-1">
              <h3 className="font-semibold text-ink">Quy tắc dự án</h3>
              <p className="text-sm leading-5 text-ink-muted">
                Chọn sự kiện cần gửi, người nhận và thời gian leo thang nếu được cấu hình
              </p>
            </header>
            {loading.rules && <p className="text-sm text-ink-muted">Đang tải quy tắc…</p>}
            {loadErrors.rules && <ErrorState message={loadErrors.rules} />}
            <div className="grid gap-4 sm:grid-cols-2">
              <fieldset className="space-y-2 rounded-control border border-border p-3">
                <legend className="field-label px-1">Kênh gửi</legend>
                {[
                  ["in_app", "Trong ứng dụng"],
                  ["email", "Email"],
                ].map(([channel, label]) => (
                  <label className="flex items-center gap-2 text-sm" key={channel}>
                    <input
                      type="checkbox"
                      disabled={!loaded.rules || saving.rules}
                      checked={rules.channels.includes(channel)}
                      onChange={(event) =>
                        setRules((current) => ({
                          ...current,
                          channels: toggleNotificationSelection(
                            current.channels,
                            channel,
                            event.target.checked,
                          ),
                        }))
                      }
                    />
                    {label}
                  </label>
                ))}
              </fieldset>
              <fieldset className="space-y-2 rounded-control border border-border p-3">
                <legend className="field-label px-1">Vai trò nhận thông báo</legend>
                {(project.available_project_roles || []).map((role) => (
                  <label className="flex items-center gap-2 text-sm" key={role}>
                    <input
                      type="checkbox"
                      disabled={!loaded.rules || saving.rules}
                      checked={rules.target_roles.includes(role)}
                      onChange={(event) =>
                        setRules((current) => ({
                          ...current,
                          target_roles: toggleNotificationSelection(
                            current.target_roles,
                            role,
                            event.target.checked,
                          ),
                        }))
                      }
                    />
                    {valueLabel(role)}
                  </label>
                ))}
              </fieldset>
            </div>
            <label className="field-label block">
              Sự kiện cần thông báo
              <textarea
                aria-label="Sự kiện thông báo"
                className="apple-input mt-2 min-h-24 w-full"
                disabled={!loaded.rules || saving.rules}
                value={rules.enabled_events.join("\n")}
                onChange={(event) =>
                  setRules({
                    ...rules,
                    enabled_events: event.target.value
                      .split("\n")
                      .map((value) => value.trim())
                      .filter(Boolean),
                  })
                }
              />
              <span className="mt-1 block text-xs font-normal text-ink-muted">
                Nhập mã sự kiện, mỗi dòng một mã
              </span>
            </label>
            <label className="field-label block max-w-sm">
              Thời gian trước khi leo thang (phút)
              <input
                aria-label="Thời gian leo thang"
                className="apple-input mt-2 w-full"
                disabled={!loaded.rules || saving.rules}
                min="1"
                max="10080"
                type="number"
                value={rules.escalation_minutes || ""}
                onChange={(event) => setRules({ ...rules, escalation_minutes: event.target.value })}
              />
            </label>
            <button className="apple-button" disabled={!loaded.rules || saving.rules} type="submit">
              {saving.rules ? "Đang lưu…" : "Lưu quy tắc"}
            </button>
          </form>
        )}
      </div>
    </Panel>
  );
}
