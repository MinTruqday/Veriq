"use client";
import { useCallback, useEffect, useState } from "react";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { toggleNotificationSelection } from "./notificationSelection.mjs";

const DEFAULT_PREFERENCES = {
  revision: 0,
  digest_frequency: "immediate",
  channels: ["in_app"],
  muted_events: [],
  quiet_hours_start: "",
  quiet_hours_end: "",
  timezone: "Asia/Ho_Chi_Minh",
};

const DEFAULT_RULES = {
  revision: 0,
  enabled_events: [],
  channels: ["in_app"],
  target_roles: ["QA"],
  escalation_minutes: "",
};

export default function ProjectNotificationsPanel({ project }) {
  const [watches, setWatches] = useState([]);
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [rules, setRules] = useState(DEFAULT_RULES);
  const [artifactType, setArtifactType] = useState("requirement");
  const [artifactId, setArtifactId] = useState("");
  const [error, setError] = useState("");
  const can = (permission) => project.current_permissions?.includes(permission);
  const canManageWatches = can("notification.watch.manage");
  const canManagePreferences = can("notification.preferences.manage");
  const canManageRules = project.current_permissions?.includes("notification.project_rule.manage");
  const load = useCallback(async () => {
    try {
      const tasks = [];
      if (canManageWatches) {
        tasks.push(testingApi.listProjectNotificationWatches(project._id));
      }
      if (canManagePreferences) {
        tasks.push(testingApi.getProjectNotificationPreferences(project._id));
      }
      if (canManageRules) {
        tasks.push(testingApi.getProjectNotificationRules(project._id));
      }
      const values = await Promise.all(tasks);
      let index = 0;
      if (canManageWatches) setWatches(values[index++]);
      if (canManagePreferences) {
        setPreferences({ ...DEFAULT_PREFERENCES, ...values[index++] });
      }
      const ruleValues = canManageRules ? values[index] : null;
      if (ruleValues) setRules({ ...DEFAULT_RULES, ...ruleValues });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canManagePreferences, canManageRules, canManageWatches, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const addWatch = async (event) => {
    event.preventDefault();
    try {
      await testingApi.setProjectNotificationWatch(project._id, artifactType, artifactId, true);
      setArtifactId("");
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const savePreferences = async (event) => {
    event.preventDefault();
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
      setPreferences({ ...DEFAULT_PREFERENCES, ...value });
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const saveRules = async (event) => {
    event.preventDefault();
    try {
      const value = await testingApi.updateProjectNotificationRules(project._id, {
        expected_revision: rules.revision,
        enabled_events: rules.enabled_events,
        channels: rules.channels,
        target_roles: rules.target_roles,
        escalation_minutes: rules.escalation_minutes ? Number(rules.escalation_minutes) : null,
      });
      setRules({ ...DEFAULT_RULES, ...value });
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!canManageWatches && !canManagePreferences && !canManageRules) {
    return null;
  }
  return (
    <Panel title="Thông báo dự án">
      {error && <ErrorState message={error} />}
      <div className="grid gap-5 p-5 xl:grid-cols-3">
        {can("notification.watch.manage") && (
          <div className="space-y-3">
            <h3 className="font-medium text-ink">Dữ liệu đang theo dõi</h3>
            <form className="space-y-2" onSubmit={addWatch}>
              <select
                aria-label="Loại dữ liệu theo dõi"
                className="apple-input"
                value={artifactType}
                onChange={(event) => setArtifactType(event.target.value)}
              >
                <option value="requirement">Yêu cầu</option>
                <option value="test_case">Ca kiểm thử</option>
                <option value="test_run">Lần chạy kiểm thử</option>
                <option value="defect">Lỗi</option>
              </select>
              <input
                aria-label="Mã dữ liệu theo dõi"
                className="apple-input"
                required
                placeholder="Mã dữ liệu"
                value={artifactId}
                onChange={(event) => setArtifactId(event.target.value)}
              />
              <button className="secondary-button" type="submit">
                Theo dõi
              </button>
            </form>
            <div className="space-y-2">
              {watches.length === 0 && (
                <p className="text-sm text-ink-muted">Chưa theo dõi dữ liệu nào</p>
              )}
              {watches.map((item) => (
                <div className="flex items-center justify-between gap-2 text-sm" key={item._id}>
                  <span className="min-w-0 truncate">
                    {valueLabel(item.artifact_type)}{" "}
                    {item.artifact_label || "Đối tượng đang theo dõi"}
                  </span>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await testingApi.setProjectNotificationWatch(
                          project._id,
                          item.artifact_type,
                          item.artifact_id,
                          false,
                        );
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Bỏ theo dõi
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
        {can("notification.preferences.manage") && (
          <form className="space-y-3" onSubmit={savePreferences}>
            <h3 className="font-medium text-ink">Tùy chọn cá nhân</h3>
            <select
              aria-label="Tần suất bản tổng hợp"
              className="apple-input"
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
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={preferences.channels.includes("email")}
                onChange={(event) =>
                  setPreferences({
                    ...preferences,
                    channels: event.target.checked ? ["in_app", "email"] : ["in_app"],
                  })
                }
              />
              Nhận qua thư điện tử
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                aria-label="Bắt đầu giờ yên lặng"
                className="apple-input"
                type="time"
                value={preferences.quiet_hours_start || ""}
                onChange={(event) =>
                  setPreferences({ ...preferences, quiet_hours_start: event.target.value })
                }
              />
              <input
                aria-label="Kết thúc giờ yên lặng"
                className="apple-input"
                type="time"
                value={preferences.quiet_hours_end || ""}
                onChange={(event) =>
                  setPreferences({ ...preferences, quiet_hours_end: event.target.value })
                }
              />
            </div>
            <button className="apple-button" type="submit">
              Lưu tùy chọn
            </button>
          </form>
        )}
        {can("notification.project_rule.manage") && (
          <form className="space-y-3" onSubmit={saveRules}>
            <h3 className="font-medium text-ink">Quy tắc dự án</h3>
            <fieldset className="space-y-2">
              <legend className="field-label">Kênh gửi</legend>
              {[
                ["in_app", "Trong ứng dụng"],
                ["email", "Thư điện tử"],
                ["webhook", "Webhook"],
              ].map(([channel, label]) => (
                <label className="flex items-center gap-2 text-sm" key={channel}>
                  <input
                    type="checkbox"
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
            <fieldset className="space-y-2">
              <legend className="field-label">Vai trò nhận thông báo</legend>
              {[
                ["QA", "QA"],
                ["TESTER", "Kiểm thử viên"],
                ["BA", "Phân tích nghiệp vụ"],
                ["DEVELOPER", "Lập trình viên"],
                ["VIEWER", "Người xem"],
              ].map(([role, label]) => (
                <label className="flex items-center gap-2 text-sm" key={role}>
                  <input
                    type="checkbox"
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
                  {label}
                </label>
              ))}
            </fieldset>
            <textarea
              aria-label="Sự kiện thông báo"
              className="apple-input min-h-24"
              placeholder="Nhập mã sự kiện cần thông báo, mỗi dòng một mã"
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
            <input
              aria-label="Thời gian leo thang"
              className="apple-input"
              min="1"
              max="10080"
              type="number"
              placeholder="Số phút trước khi leo thang"
              value={rules.escalation_minutes || ""}
              onChange={(event) => setRules({ ...rules, escalation_minutes: event.target.value })}
            />
            <button className="apple-button" type="submit">
              Lưu quy tắc
            </button>
          </form>
        )}
      </div>
    </Panel>
  );
}
