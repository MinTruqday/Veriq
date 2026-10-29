"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ErrorState,
  LoadingState,
  Panel,
  EmptyState,
} from "../../../components/WorkspacePrimitives";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

const toDraft = (field) => ({
  label: field.label || "",
  required: Boolean(field.required),
  status: field.status || "ACTIVE",
});

export default function TestCaseCustomFieldManager({ projectId, onUpdated }) {
  const [fields, setFields] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await testingApi.listManagedTestCaseCustomFields(projectId);
      const items = Array.isArray(result) ? result : [];
      setFields(items);
      setDrafts(Object.fromEntries(items.map((field) => [field._id, toDraft(field)])));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async (field) => {
    const draft = drafts[field._id];
    if (!draft || draft.label.trim().length < 2) {
      setError("Tên trường phải có ít nhất 2 ký tự.");
      return;
    }
    setSavingId(field._id);
    setError("");
    setNotice("");
    try {
      const updated = await testingApi.updateTestCaseCustomField(projectId, field._id, {
        expected_revision: field.revision || 1,
        label: draft.label.trim(),
        required: draft.required,
        status: draft.status,
      });
      setFields((current) => current.map((item) => (item._id === field._id ? updated : item)));
      setDrafts((current) => ({ ...current, [field._id]: toDraft(updated) }));
      setNotice(`Đã lưu trường “${updated.label}”.`);
      await onUpdated?.(updated);
    } catch (reason) {
      setError(messageOf(reason));
      if (reason?.status === 409) await load();
    } finally {
      setSavingId("");
    }
  };

  return (
    <Panel
      title="Trường mở rộng của ca kiểm thử"
      description="Đổi nhãn, kiểu nhập hoặc trạng thái; giá trị đã lưu vẫn được giữ nguyên."
      actions={
        <button
          className="secondary-button"
          type="button"
          onClick={() => void load()}
          disabled={loading}
        >
          Tải lại
        </button>
      }
    >
      {error && <ErrorState message={error} />}
      {notice && (
        <p className="px-5 pt-4 text-sm text-brand" role="status">
          {notice}
        </p>
      )}
      {loading ? (
        <div className="p-5">
          <LoadingState />
        </div>
      ) : fields.length === 0 ? (
        <EmptyState>Chưa có trường mở rộng trong dự án.</EmptyState>
      ) : (
        <div className="divide-y divide-border">
          {fields.map((field) => {
            const draft = drafts[field._id] || toDraft(field);
            return (
              <div
                className="grid min-w-0 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] lg:items-end"
                key={field._id}
              >
                <div className="min-w-0 text-sm">
                  <p className="break-words font-semibold text-ink">{field.label}</p>
                  <p className="mt-1 text-ink-muted">
                    {{
                      string: "Văn bản",
                      text: "Văn bản",
                      number: "Số",
                      boolean: "Có hoặc không",
                      choice: "Danh sách lựa chọn",
                      date: "Ngày",
                    }[field.value_type] || "Trường tùy chỉnh"}
                    {field.value_type === "choice" && field.choices?.length
                      ? ` · ${field.choices.join(", ")}`
                      : ""}
                  </p>
                  {field.status === "INACTIVE" && (
                    <p className="mt-1 text-xs text-ink-faint">
                      Đã ngừng dùng · dữ liệu cũ được giữ
                    </p>
                  )}
                </div>
                <div className="grid min-w-0 gap-3 sm:grid-cols-2">
                  <label className="field-label min-w-0">
                    Tên hiển thị
                    <input
                      className="apple-input mt-2"
                      maxLength={200}
                      minLength={2}
                      value={draft.label}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [field._id]: { ...draft, label: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label className="field-label min-w-0">
                    Bắt buộc khi duyệt
                    <select
                      className="apple-input mt-2"
                      value={String(draft.required)}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [field._id]: { ...draft, required: event.target.value === "true" },
                        }))
                      }
                    >
                      <option value="false">Không</option>
                      <option value="true">Có</option>
                    </select>
                  </label>
                  <label className="field-label min-w-0 sm:col-span-2">
                    Trạng thái sử dụng
                    <select
                      className="apple-input mt-2"
                      value={draft.status}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [field._id]: { ...draft, status: event.target.value },
                        }))
                      }
                    >
                      <option value="ACTIVE">Đang dùng</option>
                      <option value="INACTIVE">Ngừng dùng</option>
                    </select>
                  </label>
                </div>
                <button
                  className="apple-button w-fit"
                  type="button"
                  disabled={savingId === field._id}
                  onClick={() => void save(field)}
                >
                  {savingId === field._id ? "Đang lưu" : "Lưu thay đổi"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
