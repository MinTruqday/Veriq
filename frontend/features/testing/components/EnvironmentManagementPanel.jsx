"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw, X } from "lucide-react";
import { ErrorState, LoadingState, Panel, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

const blankEnvironment = {
  name: "",
  environment_type: "",
  base_url: "",
  availability: "AVAILABLE",
  capabilitiesText: "{}",
  secretRefsText: "{}",
};

const availabilityLabels = {
  AVAILABLE: "Sẵn sàng",
  UNAVAILABLE: "Không khả dụng",
  MAINTENANCE: "Đang bảo trì",
};

function parseObject(value, label) {
  let parsed;
  try {
    parsed = JSON.parse(value || "{}");
  } catch {
    throw new Error(`${label} phải là JSON hợp lệ.`);
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${label} phải là một đối tượng JSON.`);
  }
  return parsed;
}

export default function EnvironmentManagementPanel({ project }) {
  const permissions = new Set(project.current_permissions || []);
  const can = (permission) => permissions.has(permission);
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [value, setValue] = useState(blankEnvironment);
  const [editing, setEditing] = useState(null);
  const [showEditor, setShowEditor] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await testingApi.listEnvironments(project._id));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  const beginCreate = () => {
    setEditing(null);
    setValue({ ...blankEnvironment });
    setError("");
    setShowEditor(true);
  };

  const beginEdit = (item) => {
    setEditing(item);
    setValue({
      name: item.name || "",
      environment_type: item.environment_type || "",
      base_url: item.base_url || "",
      availability: item.availability || "AVAILABLE",
      capabilitiesText: JSON.stringify(item.capabilities || {}, null, 2),
      secretRefsText: "{}",
    });
    setError("");
    setShowEditor(true);
  };

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        name: value.name.trim(),
        environment_type: value.environment_type.trim(),
        base_url: value.base_url.trim() || null,
        availability: value.availability,
        capabilities: parseObject(value.capabilitiesText, "Thuộc tính môi trường"),
      };
      let saved;
      if (editing) {
        saved = await testingApi.updateEnvironment(editing._id, {
          ...payload,
          expected_revision: editing.revision,
        });
        const secretRefs = can("environment.secret_ref.manage")
          ? parseObject(value.secretRefsText, "Tham chiếu bí mật")
          : {};
        if (Object.keys(secretRefs).length) {
          saved = await testingApi.updateEnvironmentSecretRefs(editing._id, {
            expected_revision: saved.revision,
            secret_refs: secretRefs,
          });
        }
      } else {
        payload.secret_refs = can("environment.secret_ref.manage")
          ? parseObject(value.secretRefsText, "Tham chiếu bí mật")
          : {};
        saved = await testingApi.createEnvironment(project._id, payload);
      }
      setItems((current) => {
        const next = current.filter((item) => item._id !== saved._id);
        return [...next, saved].sort((left, right) => left.name.localeCompare(right.name));
      });
      setShowEditor(false);
      setEditing(null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };

  const archive = async (item) => {
    const answer = await ask({
      title: "Lưu trữ môi trường",
      description: `Môi trường ${item.name} sẽ không còn xuất hiện trong lựa chọn mới. Lịch sử lần chạy vẫn được giữ.`,
      confirmLabel: "Lưu trữ",
      fields: [{ name: "reason", label: "Lý do", required: true, multiline: true }],
    });
    if (!answer) return;
    setError("");
    try {
      await testingApi.archiveEnvironment(item._id, {
        expected_revision: item.revision,
        reason: answer.reason.trim(),
      });
      setItems((current) => current.filter((entry) => entry._id !== item._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  return (
    <>
      <Panel
        title="Môi trường kiểm thử"
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" type="button" onClick={() => void load()}>
              <RefreshCw aria-hidden="true" className="mr-2 inline size-4" />
              Tải lại
            </button>
            {can("environment.create") && (
              <button className="primary-button" type="button" onClick={beginCreate}>
                <Plus aria-hidden="true" className="mr-2 inline size-4" />
                Thêm môi trường
              </button>
            )}
          </div>
        }
      >
        <div className="space-y-4 p-5">
          <p className="text-sm text-ink-muted">
            Khai báo môi trường để chọn trong kế hoạch và lần chạy. Chỉ nhập địa chỉ tham chiếu bí
            mật dạng <code>secret://…</code>; không nhập giá trị mật khẩu hoặc token.
          </p>
          {error && <ErrorState message={error} />}
          {loading ? (
            <LoadingState />
          ) : items.length ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {items.map((item) => (
                <article className="rounded-2xl border border-border bg-surface p-4" key={item._id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="break-words font-semibold text-ink">{item.name}</h3>
                      <p className="mt-1 text-sm text-ink-muted">
                        {item.environment_type}
                        {item.base_url ? ` · ${item.base_url}` : ""}
                      </p>
                    </div>
                    <span className="status-badge">
                      {availabilityLabels[item.availability] || item.availability}
                    </span>
                  </div>
                  {item.secret_ref_names?.length > 0 && (
                    <p className="mt-3 text-xs text-ink-muted">
                      Tham chiếu bí mật: {item.secret_ref_names.join(", ")}
                    </p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
                    {can("environment.update") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => beginEdit(item)}
                      >
                        Chỉnh sửa
                      </button>
                    )}
                    {can("environment.archive") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => void archive(item)}
                      >
                        Lưu trữ
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-ink-muted">
              Chưa có môi trường kiểm thử. Người có quyền có thể tạo môi trường để dùng trong kế
              hoạch và lần chạy.
            </div>
          )}
          {showEditor && (
            <form
              className="space-y-4 rounded-2xl border border-border bg-surface-quiet p-4"
              onSubmit={save}
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-ink">
                  {editing ? "Chỉnh sửa môi trường" : "Thêm môi trường"}
                </h3>
                <button
                  aria-label="Đóng biểu mẫu môi trường"
                  className="icon-button"
                  disabled={saving}
                  type="button"
                  onClick={() => setShowEditor(false)}
                >
                  <X aria-hidden="true" className="size-4" />
                </button>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="field-label">
                  Tên môi trường
                  <input
                    className="apple-input mt-2 w-full"
                    minLength={2}
                    required
                    value={value.name}
                    onChange={(event) =>
                      setValue((current) => ({ ...current, name: event.target.value }))
                    }
                  />
                </label>
                <label className="field-label">
                  Loại môi trường
                  <input
                    className="apple-input mt-2 w-full"
                    required
                    value={value.environment_type}
                    onChange={(event) =>
                      setValue((current) => ({ ...current, environment_type: event.target.value }))
                    }
                  />
                </label>
                <label className="field-label md:col-span-2">
                  Địa chỉ cơ sở
                  <input
                    className="apple-input mt-2 w-full"
                    type="url"
                    value={value.base_url}
                    onChange={(event) =>
                      setValue((current) => ({ ...current, base_url: event.target.value }))
                    }
                  />
                </label>
                <label className="field-label">
                  Trạng thái khả dụng
                  <select
                    className="apple-input mt-2 w-full"
                    value={value.availability}
                    onChange={(event) =>
                      setValue((current) => ({ ...current, availability: event.target.value }))
                    }
                  >
                    {Object.entries(availabilityLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field-label md:col-span-2">
                  Thuộc tính môi trường dạng JSON
                  <textarea
                    className="apple-input mt-2 min-h-24 w-full font-mono text-sm"
                    value={value.capabilitiesText}
                    onChange={(event) =>
                      setValue((current) => ({ ...current, capabilitiesText: event.target.value }))
                    }
                  />
                </label>
                {can("environment.secret_ref.manage") && (
                  <label className="field-label md:col-span-2">
                    Tham chiếu bí mật dạng JSON
                    {editing && (
                      <span className="ml-2 text-xs font-normal text-ink-muted">
                        Để {} để giữ nguyên tham chiếu hiện có.
                      </span>
                    )}
                    <textarea
                      className="apple-input mt-2 min-h-20 w-full font-mono text-sm"
                      value={value.secretRefsText}
                      onChange={(event) =>
                        setValue((current) => ({ ...current, secretRefsText: event.target.value }))
                      }
                    />
                  </label>
                )}
              </div>
              {error && <p className="text-sm text-danger">{error}</p>}
              <div className="flex justify-end gap-2">
                <button
                  className="secondary-button"
                  disabled={saving}
                  type="button"
                  onClick={() => setShowEditor(false)}
                >
                  Hủy
                </button>
                <button className="primary-button" disabled={saving} type="submit">
                  {saving ? "Đang lưu…" : "Lưu môi trường"}
                </button>
              </div>
            </form>
          )}
        </div>
      </Panel>
      {dialog}
    </>
  );
}
