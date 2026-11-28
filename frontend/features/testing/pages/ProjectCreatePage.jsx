"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { ErrorState, WorkspacePage } from "../components/WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import { invalidProjectDateRange, minimumProjectEndDate } from "../lib/projectSchedule.logic.mjs";

const initialForm = {
  key: "",
  name: "",
  description: "",
  project_type: "",
  planned_start_at: "",
  planned_end_at: "",
};

export default function ProjectCreatePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [canCreate, setCanCreate] = useState(false);
  const [checking, setChecking] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const invalidRange = invalidProjectDateRange(form.planned_start_at, form.planned_end_at);

  useEffect(() => {
    let active = true;
    testingApi
      .getProjectCapabilities()
      .then((capabilities) => {
        if (active) setCanCreate(capabilities?.can_create_project === true);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    if (saving || invalidRange || !canCreate) return;
    setSaving(true);
    setError("");
    try {
      await testingApi.createProject({
        ...form,
        key: form.key.trim().toUpperCase(),
        name: form.name.trim(),
        locale: user?.locale || "vi",
        timezone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        planned_start_at: form.planned_start_at
          ? new Date(`${form.planned_start_at}T00:00:00.000Z`).toISOString()
          : null,
        planned_end_at: form.planned_end_at
          ? new Date(`${form.planned_end_at}T00:00:00.000Z`).toISOString()
          : null,
      });
      router.replace("/du-an");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };

  return (
    <WorkspacePage
      title="Tạo dự án"
      actions={
        <button type="button" className="secondary-button" onClick={() => router.push("/du-an")}>
          <ArrowLeft size={16} /> Quay lại dự án
        </button>
      }
    >
      {error && (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      )}
      {checking ? (
        <p className="text-sm text-ink-muted">Đang kiểm tra quyền tạo dự án</p>
      ) : !canCreate ? (
        <ErrorState message="Bạn không có quyền tạo dự án" />
      ) : (
        <form
          onSubmit={submit}
          className="max-w-3xl space-y-6 rounded-panel border border-border bg-surface p-5 sm:p-6"
        >
          <section className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-ink">Thông tin cơ bản</h2>
              <p className="mt-1 text-xs text-ink-muted">Nhập mã, tên và loại dự án</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-label">
                Mã dự án
                <input
                  className="apple-input mt-2 w-full"
                  required
                  minLength={2}
                  maxLength={30}
                  pattern="[A-Za-z][A-Za-z0-9_\-]+"
                  value={form.key}
                  onChange={(event) => setForm({ ...form, key: event.target.value })}
                  placeholder="THANHTOAN"
                />
              </label>
              <label className="field-label">
                Tên dự án
                <input
                  className="apple-input mt-2 w-full"
                  required
                  minLength={2}
                  maxLength={200}
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </label>
              <label className="field-label">
                Loại dự án
                <input
                  className="apple-input mt-2 w-full"
                  required
                  minLength={1}
                  maxLength={100}
                  value={form.project_type}
                  onChange={(event) => setForm({ ...form, project_type: event.target.value })}
                />
              </label>
              <label className="field-label md:col-span-2">
                Mô tả
                <textarea
                  className="apple-input mt-2 min-h-24 w-full resize-y"
                  maxLength={5000}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </label>
            </div>
          </section>
          <section className="space-y-4 border-t border-border pt-5">
            <div>
              <h2 className="text-sm font-semibold text-ink">Thời gian dự kiến</h2>
              <p className="mt-1 text-xs text-ink-muted">Có thể để trống khi lịch chưa xác định</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-label">
                Ngày bắt đầu dự kiến
                <input
                  className="apple-input mt-2 w-full"
                  type="date"
                  value={form.planned_start_at}
                  onChange={(event) => setForm({ ...form, planned_start_at: event.target.value })}
                />
              </label>
              <label className="field-label">
                Ngày kết thúc dự kiến
                <input
                  className="apple-input mt-2 w-full"
                  type="date"
                  min={minimumProjectEndDate(form.planned_start_at)}
                  value={form.planned_end_at}
                  aria-invalid={Boolean(invalidRange)}
                  onChange={(event) => setForm({ ...form, planned_end_at: event.target.value })}
                />
                {invalidRange && (
                  <span className="mt-1 block text-xs text-danger" role="alert">
                    Ngày kết thúc phải sau ngày bắt đầu
                  </span>
                )}
              </label>
            </div>
          </section>
          <div className="flex justify-end gap-3 border-t border-border pt-5">
            <button
              className="secondary-button"
              type="button"
              disabled={saving}
              onClick={() => router.push("/du-an")}
            >
              Hủy
            </button>
            <button
              className="apple-button"
              type="submit"
              disabled={saving || Boolean(invalidRange)}
            >
              {saving ? "Đang lưu" : "Tạo dự án"}
            </button>
          </div>
        </form>
      )}
    </WorkspacePage>
  );
}
