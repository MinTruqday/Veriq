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
import { taskProgressPresentation } from "../lib/projectProgress.logic.mjs";
import {
  formatProjectDate,
  invalidProjectDateRange,
  minimumProjectEndDate,
  projectPlannedDurationDays,
} from "../lib/projectSchedule.logic.mjs";

function projectScheduleLabel(project) {
  const duration = projectPlannedDurationDays(project.planned_start_at, project.planned_end_at);
  const dates = [
    project.planned_start_at && `Bắt đầu dự kiến: ${formatProjectDate(project.planned_start_at)}`,
    project.planned_end_at && `Kết thúc dự kiến: ${formatProjectDate(project.planned_end_at)}`,
    duration && `Thời lượng dự kiến: ${duration} ngày lịch`,
  ].filter(Boolean);
  return dates.join(" · ");
}

export default function ProjectsPage() {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [invitationActionId, setInvitationActionId] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("active");
  const [invitationError, setInvitationError] = useState("");
  const [invitationActionError, setInvitationActionError] = useState("");
  const [form, setForm] = useState({
    key: "",
    name: "",
    description: "",
    project_type: "web",
    planning_method: "SCRUM",
    initial_qa_user_id: "",
    planned_start_at: "",
    planned_end_at: "",
  });
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createError, setCreateError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canCreateProject, setCanCreateProject] = useState(false);
  const [capabilityError, setCapabilityError] = useState("");
  const invitationActionInFlight = useRef(false);
  const requestSequence = useRef(0);
  const minimumPlannedEndAt = minimumProjectEndDate(form.planned_start_at);
  const plannedDateRangeInvalid = invalidProjectDateRange(
    form.planned_start_at,
    form.planned_end_at,
  );
  const openCreateModal = () => {
    setCreateError("");
    setCreating(true);
  };
  const load = useCallback(async (value = "", statusValue = "active") => {
    const requestId = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const [projectsResult, invitationsResult] = await Promise.allSettled([
        testingApi.listProjects(value, statusValue),
        testingApi.listInvitations(),
      ]);
      if (requestId !== requestSequence.current) return;
      if (projectsResult.status === "rejected") throw projectsResult.reason;
      setItems(projectsResult.value);
      if (invitationsResult.status === "fulfilled") {
        setInvitations(invitationsResult.value);
        setInvitationError("");
      } else if (invitationsResult.reason?.status === 403) {
        setInvitations([]);
        setInvitationError("");
      } else {
        setInvitations([]);
        setInvitationError(messageOf(invitationsResult.reason));
      }
    } catch (reason) {
      if (requestId !== requestSequence.current) return;
      setError(messageOf(reason));
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, []);
  const loadCapabilities = useCallback(async () => {
    setCapabilityError("");
    try {
      const capabilities = await testingApi.getProjectCapabilities();
      setCanCreateProject(capabilities?.can_create_project === true);
    } catch (reason) {
      setCanCreateProject(false);
      setCapabilityError(reason?.status === 403 ? "" : messageOf(reason));
    }
  }, []);
  const respondToInvitation = async (invitation, action) => {
    if (invitationActionInFlight.current) return;
    invitationActionInFlight.current = true;
    setInvitationActionId(invitation._id);
    setInvitationActionError("");
    try {
      if (action === "accept") await testingApi.acceptInvitation(invitation._id);
      else await testingApi.declineInvitation(invitation._id);
      await load(query, status);
    } catch (reason) {
      setInvitationActionError(messageOf(reason));
    } finally {
      invitationActionInFlight.current = false;
      setInvitationActionId("");
    }
  };
  useEffect(() => {
    void load("", status);
  }, [load, status]);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  const submit = async (event) => {
    event.preventDefault();
    if (saving) return;
    if (plannedDateRangeInvalid) {
      setCreateError("Ngày kết thúc phải sau ngày bắt đầu.");
      return;
    }
    setCreateError("");
    setSaving(true);
    try {
      await testingApi.createProject({
        ...form,
        key: form.key.trim().toUpperCase(),
        name: form.name.trim(),
        planned_start_at: form.planned_start_at
          ? new Date(`${form.planned_start_at}T00:00:00.000Z`).toISOString()
          : null,
        planned_end_at: form.planned_end_at
          ? new Date(`${form.planned_end_at}T00:00:00.000Z`).toISOString()
          : null,
      });
      setForm({
        key: "",
        name: "",
        description: "",
        project_type: "web",
        planning_method: "SCRUM",
        initial_qa_user_id: "",
        planned_start_at: "",
        planned_end_at: "",
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
        canCreateProject ? (
          <button type="button" className="apple-button" onClick={openCreateModal}>
            <Plus size={16} />
            Tạo dự án
          </button>
        ) : null
      }
    >
      {error && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <ErrorState message={error} />
          <button
            className="secondary-button"
            type="button"
            disabled={loading}
            onClick={() => void load(query, status)}
          >
            Thử tải lại danh sách
          </button>
        </div>
      )}
      {capabilityError && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <ErrorState message={`Không thể xác định quyền tạo dự án: ${capabilityError}`} />
          <button type="button" className="apple-button" onClick={() => void loadCapabilities()}>
            Thử lại
          </button>
        </div>
      )}
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
              type="text"
              autoComplete="username"
              required
              value={form.initial_qa_user_id}
              onChange={(event) => setForm({ ...form, initial_qa_user_id: event.target.value })}
              aria-describedby="initial-qa-help"
              placeholder="qa@congty.vn hoặc mã tài khoản QA"
            />
            <span className="mt-1 block text-xs leading-5 text-ink-muted" id="initial-qa-help">
              Có thể nhập email hoặc mã tài khoản. Nếu là chính bạn, tài khoản sẽ có cả vai trò BA
              và QA trong dự án.
            </span>
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
          <label className="field-label block min-w-0">
            Ngày bắt đầu dự kiến
            <input
              className="apple-input mt-2 w-full"
              type="date"
              value={form.planned_start_at}
              onChange={(event) => setForm({ ...form, planned_start_at: event.target.value })}
            />
          </label>
          <label className="field-label block min-w-0">
            Ngày kết thúc dự kiến
            <input
              className="apple-input mt-2 w-full"
              type="date"
              min={minimumPlannedEndAt}
              value={form.planned_end_at}
              aria-invalid={Boolean(plannedDateRangeInvalid)}
              aria-describedby="project-date-range-help"
              onChange={(event) => setForm({ ...form, planned_end_at: event.target.value })}
            />
            <span
              className={`mt-1 block text-xs ${
                plannedDateRangeInvalid ? "text-danger" : "text-ink-muted"
              }`}
              id="project-date-range-help"
              role={plannedDateRangeInvalid ? "alert" : undefined}
            >
              {plannedDateRangeInvalid
                ? "Ngày kết thúc phải sau ngày bắt đầu."
                : "Có thể để trống nếu chưa xác định thời hạn."}
            </span>
          </label>
          <div className="action-dialog-footer flex justify-end gap-3 md:col-span-2">
            <button
              className="secondary-button"
              type="button"
              disabled={saving}
              onClick={() => setCreating(false)}
            >
              Hủy
            </button>
            <button
              className="apple-button"
              type="submit"
              disabled={saving || Boolean(plannedDateRangeInvalid)}
            >
              {saving ? "Đang lưu" : "Lưu dự án"}
            </button>
          </div>
        </form>
      </Modal>
      {(invitations.length > 0 || invitationError || invitationActionError) && (
        <Panel title="Lời mời tham gia dự án">
          {invitationError ? (
            <div className="space-y-3 p-5">
              <ErrorState message={`Không thể tải lời mời: ${invitationError}`} />
              <button
                className="secondary-button"
                type="button"
                onClick={() => void load(query, status)}
              >
                Thử tải lại lời mời
              </button>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {invitationActionError && (
                <div className="p-5">
                  <ErrorState message={`Không thể xử lý lời mời: ${invitationActionError}`} />
                </div>
              )}
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
                      disabled={Boolean(invitationActionId)}
                      onClick={() => void respondToInvitation(invitation, "decline")}
                    >
                      {invitationActionId === invitation._id ? "Đang xử lý" : "Từ chối"}
                    </button>
                    <button
                      type="button"
                      className="apple-button"
                      disabled={Boolean(invitationActionId)}
                      onClick={() => void respondToInvitation(invitation, "accept")}
                    >
                      {invitationActionId === invitation._id ? "Đang xử lý" : "Chấp nhận"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Panel>
      )}
      <Panel
        title="Danh sách dự án"
        actions={
          <form
            className="flex w-full flex-col gap-2 sm:flex-row sm:items-center"
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
                className="apple-input h-10 w-full py-0 pl-10 sm:w-64"
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
              className="apple-input w-full sm:w-auto"
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
            {items.map((item) => {
              const taskProgress = taskProgressPresentation(item.task_summary);
              return (
                <article
                  key={item._id}
                  className="grid gap-4 p-5 transition hover:bg-surface-quiet xl:grid-cols-[120px_minmax(0,1fr)_minmax(180px,0.7fr)_140px_180px_auto] xl:items-center"
                >
                  <span className="font-mono text-[13px] font-semibold text-brand">{item.key}</span>
                  <Link href={`/du-an/${item._id}`} className="min-w-0">
                    <span className="flex min-w-0 flex-wrap items-center gap-2">
                      <strong className="break-words text-[14px]">{item.name}</strong>
                      <StatusPill value={item.planning_method || "SCRUM"} />
                    </span>
                    {item.description && (
                      <small className="line-clamp-1 text-ink-muted">{item.description}</small>
                    )}
                    {projectScheduleLabel(item) && (
                      <small className="mt-1 block text-ink-muted">
                        {projectScheduleLabel(item)}
                      </small>
                    )}
                  </Link>
                  <div className="space-y-2 text-[12px]">
                    {Number.isFinite(item.project_completion_percent) ? (
                      <div className="space-y-1">
                        <div className="flex justify-between gap-2">
                          <span>Project · QA đánh giá</span>
                          <strong>{item.project_completion_percent}%</strong>
                        </div>
                        <div
                          aria-label={`Project ${item.project_completion_percent}%`}
                          aria-valuemax={100}
                          aria-valuemin={0}
                          aria-valuenow={item.project_completion_percent}
                          className="h-1.5 overflow-hidden rounded-full bg-surface-quiet"
                          role="progressbar"
                        >
                          <div
                            className="h-full rounded-full bg-brand"
                            style={{ width: `${item.project_completion_percent}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-ink-muted">Project · Chưa có đánh giá của QA</span>
                    )}
                    {taskProgress.completionPercent == null ? (
                      <span className="text-ink-muted">Tasks · {taskProgress.label}</span>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex justify-between gap-2">
                          <span>Tasks · Tự tính</span>
                          <strong>{taskProgress.completionPercent}%</strong>
                        </div>
                        <div
                          aria-label={`Tasks ${taskProgress.completionPercent}%`}
                          aria-valuemax={100}
                          aria-valuemin={0}
                          aria-valuenow={taskProgress.completionPercent}
                          className="h-1.5 overflow-hidden rounded-full bg-surface-quiet"
                          role="progressbar"
                        >
                          <div
                            className="h-full rounded-full bg-sky-500"
                            style={{ width: `${taskProgress.completionPercent}%` }}
                          />
                        </div>
                      </div>
                    )}
                    <span className="text-ink-muted">
                      {taskProgress.total == null
                        ? "Chưa có thống kê số lượng công việc"
                        : `${taskProgress.total} công việc · ${taskProgress.blocked ?? 0} bị chặn`}
                    </span>
                  </div>
                  <div className="flex items-center xl:block">
                    <StatusPill value={String(item.status).toUpperCase()} />
                  </div>
                  <div className="text-[12px] text-ink-muted">
                    <span className="mr-2 font-semibold text-ink xl:hidden">Cập nhật</span>
                    {formatDate(item.updated_at)}
                  </div>
                  {item.status === "archived" &&
                    item.current_permissions?.includes("project.restore") && (
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={async () => {
                          await ask({
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
                            onConfirm: async (answer) => {
                              try {
                                await testingApi.restoreProject(item._id, {
                                  expected_revision: item.revision,
                                  reason: answer.reason,
                                });
                                await load(query, status);
                              } catch (reason) {
                                throw new Error(messageOf(reason));
                              }
                            },
                          });
                        }}
                      >
                        Khôi phục
                      </button>
                    )}
                </article>
              );
            })}
          </div>
        )}
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
