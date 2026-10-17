"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Search } from "lucide-react";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Panel,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../components/WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../lib/testing";

export default function ProjectsPage() {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("active");
  const [form, setForm] = useState({
    key: "",
    name: "",
    description: "",
    project_type: "web",
    planning_method: "SCRUM",
    initial_qa_user_id: "",
  });
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createError, setCreateError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestSequence = useRef(0);
  const openCreateModal = () => {
    setCreateError("");
    setCreating(true);
  };
  const load = useCallback(async (value = "", statusValue = "active") => {
    const requestId = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const [projects, pendingInvitations] = await Promise.all([
        testingApi.listProjects(value, statusValue),
        testingApi.listInvitations(),
      ]);
      if (requestId !== requestSequence.current) return;
      setItems(projects);
      setInvitations(pendingInvitations);
    } catch (reason) {
      if (requestId !== requestSequence.current) return;
      setError(messageOf(reason));
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load("", status);
  }, [load, status]);
  const submit = async (event) => {
    event.preventDefault();
    if (saving) return;
    setCreateError("");
    setSaving(true);
    try {
      await testingApi.createProject({
        ...form,
        key: form.key.trim().toUpperCase(),
        name: form.name.trim(),
      });
      setForm({
        key: "",
        name: "",
        description: "",
        project_type: "web",
        planning_method: "SCRUM",
        initial_qa_user_id: "",
      });
      setCreating(false);
      setQuery("");
      setStatus("active");
      await load("", "active");
    } catch (reason) {
      setCreateError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };
  return (
    <WorkspacePage
      title="Dự án"
      actions={
        <button type="button" className="apple-button" onClick={openCreateModal}>
          <Plus size={16} />
          Tạo dự án
        </button>
      }
    >
      {error && <ErrorState message={error} />}
      <Modal
        isOpen={creating}
        onClose={() => {
          if (!saving) setCreating(false);
        }}
        ariaLabel="Tạo dự án"
        className="max-w-xl max-h-[90dvh] overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>Tạo dự án</ModalTitle>
        </ModalHeader>
        <form onSubmit={submit} className="grid gap-5 p-5 md:grid-cols-2">
          {createError && (
            <div className="md:col-span-2">
              <ErrorState message={createError} />
            </div>
          )}
          <label className="field-label block min-w-0">
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
          <label className="field-label block min-w-0">
            Tài khoản QA đầu tiên
            <input
              className="apple-input mt-2 w-full"
              type="email"
              required
              value={form.initial_qa_user_id}
              onChange={(event) => setForm({ ...form, initial_qa_user_id: event.target.value })}
              placeholder="qa@congty.vn hoặc mã tài khoản QA"
            />
          </label>
          <label className="field-label block min-w-0">
            Tên dự án
            <input
              className="apple-input mt-2 w-full"
              required
              minLength={2}
              maxLength={200}
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Tên dự án"
            />
          </label>
          <label className="field-label block min-w-0">
            Loại dự án
            <select
              className="apple-input mt-2 w-full"
              value={form.project_type}
              onChange={(event) => setForm({ ...form, project_type: event.target.value })}
            >
              <option value="web">Ứng dụng web</option>
              <option value="mobile">Ứng dụng di động</option>
              <option value="api">API</option>
              <option value="desktop">Ứng dụng máy tính</option>
              <option value="embedded">Thiết bị nhúng</option>
              <option value="other">Khác</option>
            </select>
          </label>
          <label className="field-label block min-w-0">
            Phương thức làm việc
            <select
              className="apple-input mt-2 w-full"
              value={form.planning_method}
              onChange={(event) => setForm({ ...form, planning_method: event.target.value })}
            >
              <option value="SCRUM">Scrum</option>
              <option value="KANBAN">Kanban</option>
            </select>
          </label>
          <label className="field-label block min-w-0 md:col-span-2">
            Mô tả
            <textarea
              className="apple-input mt-2 min-h-24 w-full resize-y"
              maxLength={5000}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          <div className="flex justify-end gap-3 md:col-span-2">
            <button
              className="secondary-button"
              type="button"
              disabled={saving}
              onClick={() => setCreating(false)}
            >
              Hủy
            </button>
            <button className="apple-button" type="submit" disabled={saving}>
              {saving ? "Đang lưu" : "Lưu dự án"}
            </button>
          </div>
        </form>
      </Modal>
      {invitations.length > 0 && (
        <Panel
          title="Lời mời tham gia dự án"
          description="Chấp nhận lời mời để dự án xuất hiện trong danh sách của bạn"
        >
          <div className="divide-y divide-border">
            {invitations.map((invitation) => (
              <article
                key={invitation._id}
                className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between"
              >
                <div className="min-w-0">
                  <span className="font-mono text-[12px] font-semibold text-brand">
                    {invitation.project?.key}
                  </span>
                  <strong className="mt-1 block text-[14px]">{invitation.project?.name}</strong>
                  <small className="text-ink-muted">
                    Vai trò được mời {valueLabel(invitation.project_role)}
                  </small>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={async () => {
                      try {
                        await testingApi.declineInvitation(invitation._id);
                        await load(query, status);
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Từ chối
                  </button>
                  <button
                    type="button"
                    className="apple-button"
                    onClick={async () => {
                      try {
                        await testingApi.acceptInvitation(invitation._id);
                        await load(query, status);
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Chấp nhận
                  </button>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      )}
      <Panel
        title="Danh sách dự án"
        actions={
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              void load(query, status);
            }}
          >
            <div className="relative flex items-center">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-3 z-10 text-ink-faint"
                size={16}
              />
              <input
                aria-label="Tìm dự án"
                className="apple-input h-10 w-64 py-0 pl-10"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") return;
                  event.preventDefault();
                  void load(event.currentTarget.value, status);
                }}
                placeholder="Tìm mã hoặc tên"
              />
            </div>
            <button className="secondary-button h-10" type="submit">
              Tìm
            </button>
            <select
              aria-label="Trạng thái dự án"
              className="apple-input"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="active">Đang hoạt động</option>
              <option value="archived">Đã lưu trữ</option>
              <option value="all">Tất cả</option>
            </select>
          </form>
        }
      >
        {loading ? (
          <div className="p-5">
            <LoadingState />
          </div>
        ) : items.length === 0 ? (
          <EmptyState>
            {query.trim()
              ? "Không tìm thấy dự án phù hợp"
              : status === "archived"
                ? "Chưa có dự án đã lưu trữ"
                : "Chưa có dự án"}
          </EmptyState>
        ) : (
          <div className="divide-y divide-border">
            {items.map((item) => (
              <article
                key={item._id}
                className="grid gap-4 p-5 transition hover:bg-surface-quiet md:grid-cols-[120px_minmax(0,1fr)_minmax(180px,0.7fr)_140px_180px_auto] md:items-center"
              >
                <span className="font-mono text-[13px] font-semibold text-brand">{item.key}</span>
                <Link href={`/du-an/${item._id}`} className="min-w-0">
                  <strong className="block text-[14px]">{item.name}</strong>
                  {item.description && (
                    <small className="line-clamp-1 text-ink-muted">{item.description}</small>
                  )}
                </Link>
                <div className="space-y-2 text-[12px]">
                  <div className="flex justify-between gap-2">
                    <span>Tiến độ dự án {item.project_completion_percent ?? 0}%</span>
                    <span>
                      {item.task_summary?.completion_percent === null
                        ? "Chưa có công việc"
                        : `Tiến độ công việc ${item.task_summary?.completion_percent ?? 0}%`}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface-quiet">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${item.project_completion_percent ?? 0}%` }}
                    />
                  </div>
                  <span className="text-ink-muted">
                    {item.task_summary?.total ?? 0} công việc · {item.task_summary?.blocked ?? 0} bị
                    chặn
                  </span>
                </div>
                <div className="flex items-center md:block">
                  <StatusPill value={String(item.status).toUpperCase()} />
                </div>
                <div className="text-[12px] text-ink-muted">
                  <span className="mr-2 font-semibold text-ink md:hidden">Cập nhật</span>
                  {formatDate(item.updated_at)}
                </div>
                {item.status === "archived" &&
                  item.current_permissions?.includes("project.restore") && (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={async () => {
                        const answer = await ask({
                          title: "Khôi phục dự án",
                          description: `${item.key} sẽ hoạt động trở lại và tiếp tục nhận thay đổi`,
                          confirmLabel: "Khôi phục",
                          fields: [
                            {
                              name: "reason",
                              label: "Lý do khôi phục",
                              initialValue: "Tiếp tục thực hiện dự án",
                              required: true,
                            },
                          ],
                        });
                        if (!answer) return;
                        try {
                          await testingApi.restoreProject(item._id, {
                            expected_revision: item.revision,
                            reason: answer.reason,
                          });
                          await load(query, status);
                        } catch (reason) {
                          setError(messageOf(reason));
                        }
                      }}
                    >
                      Khôi phục
                    </button>
                  )}
              </article>
            ))}
          </div>
        )}
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
