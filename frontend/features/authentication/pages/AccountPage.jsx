"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import NotificationPreferencesPanel from "@/features/notification/components/NotificationPreferencesPanel";
import PasswordField from "../components/PasswordField";
import { isSupportedTimeZone, timeZoneOptions } from "@/shared/lib/timeZone.mjs";
import { isSupportedLocale, safeLocale } from "@/shared/lib/locale.mjs";
import { changeMyPassword, updateMyProfile } from "../services/session.service";

export default function AccountPage() {
  const { user, logoutState, refreshUser } = useAuth();
  const [profile, setProfile] = useState({
    full_name: "",
    locale: "",
    timezone: "",
  });
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [activeSection, setActiveSection] = useState("profile");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [timezoneError, setTimezoneError] = useState("");
  const [localeError, setLocaleError] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    setProfile({
      full_name: user?.full_name || "",
      locale: user?.locale || (typeof navigator === "undefined" ? "" : navigator.language),
      timezone:
        user?.timezone ||
        (typeof Intl === "undefined" ? "" : Intl.DateTimeFormat().resolvedOptions().timeZone),
    });
    setTimezoneError("");
  }, [user]);
  const submitProfile = async (event) => {
    event.preventDefault();
    if (profile.locale && !isSupportedLocale(profile.locale)) {
      setLocaleError("Nhập mã ngôn ngữ hợp lệ, ví dụ vi-VN hoặc en-US");
      setStatus("");
      return;
    }
    if (!isSupportedTimeZone(profile.timezone)) {
      setTimezoneError("Chọn múi giờ hợp lệ từ danh sách trước khi lưu");
      setStatus("");
      return;
    }
    setSavingProfile(true);
    setStatus("");
    setError("");
    setTimezoneError("");
    setLocaleError("");
    try {
      await updateMyProfile(profile);
      await refreshUser();
      setStatus("Đã cập nhật thông tin cá nhân");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật thông tin cá nhân");
    } finally {
      setSavingProfile(false);
    }
  };
  const submitPassword = async (event) => {
    event.preventDefault();
    setSavingPassword(true);
    setStatus("");
    setError("");
    try {
      await changeMyPassword(password);
      setPassword({ current_password: "", new_password: "" });
      setStatus("Đã đổi mật khẩu");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đổi mật khẩu");
    } finally {
      setSavingPassword(false);
    }
  };
  const userTimeZoneOptions = useMemo(() => timeZoneOptions(profile.timezone), [profile.timezone]);
  const timezoneIsValid = isSupportedTimeZone(profile.timezone);
  const localeIsValid = !profile.locale || isSupportedLocale(profile.locale);
  const timezoneMessage =
    timezoneError ||
    (!timezoneIsValid
      ? "Múi giờ đã lưu không hợp lệ. Thời gian phiên đăng nhập tạm hiển thị theo thiết bị; hãy chọn múi giờ trong danh sách"
      : "");
  return (
    <div className="mx-auto w-full max-w-[1180px] min-w-0 space-y-6 py-5 sm:py-6 xl:py-8">
      <header className="border-b border-border pb-6">
        <h1 className="text-2xl font-semibold tracking-[-0.03em]">Tài khoản và bảo mật</h1>
      </header>
      {status && (
        <p role="status" className="rounded-control bg-brand-soft p-3 text-brand">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-control bg-danger-soft p-3 text-danger">
          {error}
        </p>
      )}
      <div className="grid min-w-0 gap-5 xl:grid-cols-[15rem_minmax(0,1fr)]">
        <nav
          aria-label="Nhóm cài đặt tài khoản"
          className="min-w-0 rounded-panel border border-border p-2 xl:sticky xl:top-20 xl:h-fit"
        >
          <p className="sr-only px-3 py-2 text-xs font-semibold uppercase tracking-wide text-ink-faint xl:not-sr-only">
            Tài khoản
          </p>
          <ul className="-mx-1 flex min-w-0 gap-1 overflow-x-auto px-1 pb-1 xl:mx-0 xl:grid xl:overflow-visible xl:px-0 xl:pb-0">
            {[
              ["profile", "Hồ sơ cá nhân"],
              ["security", "Mật khẩu và bảo mật"],
              ["notifications", "Thông báo"],
            ].map(([section, label]) => (
              <li className="shrink-0 xl:shrink" key={section}>
                <button
                  aria-current={activeSection === section ? "page" : undefined}
                  className={`w-full whitespace-nowrap rounded-control px-3 py-2.5 text-left text-[13px] font-medium transition ${
                    activeSection === section
                      ? "bg-brand-soft text-brand"
                      : "text-ink-muted hover:bg-surface-quiet hover:text-ink"
                  }`}
                  onClick={() => setActiveSection(section)}
                  type="button"
                >
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0">
          {activeSection === "profile" && (
            <section className="overflow-hidden rounded-panel border border-border bg-surface">
              <div className="border-b border-border bg-surface-raised px-5 py-4">
                <h2 className="font-semibold">Thông tin cá nhân</h2>
              </div>
              <form className="grid gap-5 p-5 sm:grid-cols-2" onSubmit={submitProfile}>
                <label className="field-label">
                  Tên hiển thị
                  <input
                    className="apple-input mt-2 w-full"
                    value={profile.full_name}
                    onChange={(event) => setProfile({ ...profile, full_name: event.target.value })}
                    required
                  />
                </label>
                <div>
                  <span className="field-label">Email</span>
                  <p className="mt-2 font-semibold">{user?.email}</p>
                </div>
                <div>
                  <span className="field-label">Vai trò hệ thống</span>
                  <p className="mt-2 font-semibold">
                    {user?.system_role === "ADMIN" ? "Quản trị viên" : "Người dùng"}
                  </p>
                </div>
                <label className="field-label">
                  Ngôn ngữ
                  <input
                    className="apple-input mt-2 w-full"
                    value={profile.locale}
                    aria-invalid={!localeIsValid || Boolean(localeError)}
                    aria-describedby={localeError ? "account-locale-error" : undefined}
                    onChange={(event) => {
                      setProfile({ ...profile, locale: event.target.value });
                      setLocaleError("");
                    }}
                  />
                  {localeError && (
                    <span
                      className="mt-2 block text-sm text-danger"
                      id="account-locale-error"
                      role="alert"
                    >
                      {localeError}
                    </span>
                  )}
                </label>
                <label className="field-label">
                  Múi giờ
                  <select
                    className="apple-input mt-2 w-full"
                    aria-invalid={!timezoneIsValid || Boolean(timezoneError)}
                    aria-describedby={timezoneMessage ? "account-timezone-error" : undefined}
                    value={profile.timezone}
                    onChange={(event) => {
                      setProfile({ ...profile, timezone: event.target.value });
                      setTimezoneError("");
                    }}
                  >
                    {userTimeZoneOptions.map((option) => (
                      <option key={option.value} value={option.value} disabled={!option.valid}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {timezoneMessage && (
                    <span
                      id="account-timezone-error"
                      className={`mt-2 block text-sm ${timezoneError ? "text-danger" : "text-warning"}`}
                      role={timezoneError ? "alert" : "status"}
                    >
                      {timezoneMessage}
                    </span>
                  )}
                </label>
                <div className="sm:col-span-2">
                  <button className="apple-button" type="submit" disabled={savingProfile}>
                    {savingProfile ? "Đang lưu" : "Lưu thông tin"}
                  </button>
                </div>
              </form>
            </section>
          )}
          {activeSection === "security" && (
            <section className="rounded-panel border border-border bg-surface p-5">
              <h2 className="font-semibold">Đổi mật khẩu</h2>
              <p className="mt-1 text-sm text-ink-muted">Mật khẩu mới cần có ít nhất 12 ký tự</p>
              <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={submitPassword}>
                <PasswordField
                  id="account-current-password"
                  name="current_password"
                  label="Mật khẩu hiện tại"
                  autoComplete="current-password"
                  value={password.current_password}
                  onChange={(event) =>
                    setPassword({ ...password, current_password: event.target.value })
                  }
                  required
                />
                <PasswordField
                  id="account-new-password"
                  name="new_password"
                  label="Mật khẩu mới"
                  autoComplete="new-password"
                  value={password.new_password}
                  onChange={(event) =>
                    setPassword({ ...password, new_password: event.target.value })
                  }
                  minLength={12}
                  required
                />
                <div className="sm:col-span-2">
                  <button className="secondary-button" type="submit" disabled={savingPassword}>
                    {savingPassword ? "Đang cập nhật" : "Đổi mật khẩu"}
                  </button>
                </div>
              </form>
            </section>
          )}
          {activeSection === "notifications" && <NotificationPreferencesPanel />}
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link className="secondary-button" href="/du-an">
          Về không gian kiểm thử
        </Link>
        <button className="secondary-button text-danger" type="button" onClick={logoutState}>
          Đăng xuất
        </button>
      </div>
    </div>
  );
}
