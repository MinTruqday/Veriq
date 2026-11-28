"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { ErrorState, LoadingState, Panel, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";

const blankEnvironment = {
  name: "",
  base_url: "",
  environment_type: "OTHER",
  operating_system: "",
  browser: "",
  browser_version: "",
  device: "",
  availability: "AVAILABLE",
};

const environmentTypes = [
  ["WEB", "Web"],
  ["API", "API"],
  ["MOBILE", "Di động"],
  ["DESKTOP", "Máy tính"],
  ["OTHER", "Khác"],
];

const environmentTemplates = [
  {
    name: "Web · Chrome · Windows",
    values: { environment_type: "WEB", operating_system: "Windows", browser: "Chrome" },
  },
  {
    name: "Web · Firefox · Windows",
    values: { environment_type: "WEB", operating_system: "Windows", browser: "Firefox" },
  },
  {
    name: "Web · Safari · macOS",
    values: { environment_type: "WEB", operating_system: "macOS", browser: "Safari" },
  },
  {
    name: "Mobile · Android",
    values: { environment_type: "MOBILE", operating_system: "Android" },
  },
  {
    name: "Mobile · iOS",
    values: { environment_type: "MOBILE", operating_system: "iOS" },
  },
  { name: "API · Kiểm thử", values: { environment_type: "API" } },
];

function environmentSummary(item) {
  return [
    environmentTypes.find(([key]) => key === item.environment_type)?.[1],
    item.operating_system,
    [item.browser, item.browser_version].filter(Boolean).join(" "),
    item.device,
  ]
    .filter(Boolean)
    .join(" · ");
}

const availabilityLabels = {
  AVAILABLE: "Sẵn sàng",
  UNAVAILABLE: "Không khả dụng",
  MAINTENANCE: "Đang bảo trì",
};

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
      base_url: item.base_url || "",
      environment_type: item.environment_type || "OTHER",
      operating_system: item.operating_system || "",
      browser: item.browser || "",
      browser_version: item.browser_version || "",
      device: item.device || "",
      availability: item.availability || "AVAILABLE",
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
        base_url: value.base_url.trim() || null,
        environment_type: value.environment_type,
        operating_system: value.operating_system.trim(),
        browser: value.browser.trim(),
        browser_version: value.browser_version.trim(),
        device: value.device.trim(),
        availability: value.availability,
      };
      let saved;
      if (editing) {
        saved = await testingApi.updateEnvironment(editing._id, {
          ...payload,
          expected_revision: editing.revision,
        });
      } else {
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
      description: `Môi trường ${item.name} sẽ không còn xuất hiện trong lựa chọn mới. Lịch sử lần chạy vẫn được giữ`,
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
            Tạo môi trường để chọn trong kế hoạch và lần chạy
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
                      {environmentSummary(item) && (
                        <p className="mt-1 text-sm text-ink-muted">{environmentSummary(item)}</p>
                      )}
                      <p className="mt-1 text-sm text-ink-muted">{item.base_url || "-"}</p>
                    </div>
                    <span className="status-badge">
                      {availabilityLabels[item.availability] || item.availability}
                    </span>
                  </div>
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
              hoạch và lần chạy
            </div>
          )}
          <Modal
            ariaLabel={editing ? "Chỉnh sửa môi trường" : "Thêm môi trường"}
            isOpen={showEditor}
            onClose={() => {
              if (!saving) setShowEditor(false);
            }}
            placement="right"
            showCloseButton={!saving}
          >
            <form className="flex min-h-full flex-col" onSubmit={save}>
              <ModalHeader>
                <ModalTitle>{editing ? "Chỉnh sửa môi trường" : "Thêm môi trường"}</ModalTitle>
              </ModalHeader>
              <ModalContent className="flex-1">
                <label className="field-label block">
                  Mẫu môi trường
                  <select
                    className="apple-input mt-2 w-full"
                    value=""
                    onChange={(event) => {
                      const template = environmentTemplates[Number(event.target.value)];
                      if (!template) return;
                      setValue((current) => ({
                        ...current,
                        ...blankEnvironment,
                        ...template.values,
                        name: template.name,
                      }));
                    }}
                  >
                    <option value="">Chọn mẫu để điền nhanh</option>
                    {environmentTemplates.map((template, index) => (
                      <option key={template.name} value={index}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </label>
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
                    Loại môi trường
                    <select
                      className="apple-input mt-2 w-full"
                      value={value.environment_type}
                      onChange={(event) =>
                        setValue((current) => ({
                          ...current,
                          environment_type: event.target.value,
                        }))
                      }
                    >
                      {environmentTypes.map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-label">
                    Hệ điều hành
                    <input
                      className="apple-input mt-2 w-full"
                      value={value.operating_system}
                      onChange={(event) =>
                        setValue((current) => ({
                          ...current,
                          operating_system: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label className="field-label">
                    Trình duyệt
                    <input
                      className="apple-input mt-2 w-full"
                      value={value.browser}
                      onChange={(event) =>
                        setValue((current) => ({ ...current, browser: event.target.value }))
                      }
                    />
                  </label>
                  <label className="field-label">
                    Phiên bản trình duyệt
                    <input
                      className="apple-input mt-2 w-full"
                      value={value.browser_version}
                      onChange={(event) =>
                        setValue((current) => ({ ...current, browser_version: event.target.value }))
                      }
                    />
                  </label>
                  <label className="field-label">
                    Thiết bị
                    <input
                      className="apple-input mt-2 w-full"
                      value={value.device}
                      onChange={(event) =>
                        setValue((current) => ({ ...current, device: event.target.value }))
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
                </div>
                {error && <p className="text-sm text-danger">{error}</p>}
              </ModalContent>
              <ModalFooter>
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
              </ModalFooter>
            </form>
          </Modal>
        </div>
      </Panel>
      {dialog}
    </>
  );
}
