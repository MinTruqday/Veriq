"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CalendarDays, Plus, Search } from "lucide-react";
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
import { messageOf, valueLabel } from "../lib/testing";
import { taskProgressPresentation } from "../lib/projectProgress.logic.mjs";
import {
  formatProjectDate,
  invalidProjectDateRange,
  minimumProjectEndDate,
} from "../lib/projectSchedule.logic.mjs";

function projectSchedule(project) {
  const start = project.planned_start_at ? formatProjectDate(project.planned_start_at) : null;
  const end = project.planned_end_at ? formatProjectDate(project.planned_end_at) : null;
  if (start && end) return `${start} – ${end}`;
  if (start) return `Từ ${start}`;
  if (end) return `Đến ${end}`;
  return "Chưa có lịch";
}

function projectIncludesDate(project, day) {
  if (!day) return true;
  if (!project.planned_start_at && !project.planned_end_at) return false;
  const [year, month, date] = day.split("-").map(Number);
  const selectedDayStart = Date.UTC(year, month - 1, date);
  const selectedDayEnd = selectedDayStart + 24 * 60 * 60 * 1000 - 1;
  const start = project.planned_start_at ? Date.parse(project.planned_start_at) : null;
  const end = project.planned_end_at ? Date.parse(project.planned_end_at) : null;
  return (start == null || start <= selectedDayEnd) && (end == null || end >= selectedDayStart);
}

function formatProjectUpdatedAt(value) {
  if (!value) return "Chưa có thông tin";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có thông tin";
  const dateLabel = date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "Asia/Ho_Chi_Minh",
  });
  const timeLabel = date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Asia/Ho_Chi_Minh",
  });
  return `${dateLabel}, ${timeLabel}`;
}

export default function ProjectsPage() {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [invitationActionId, setInvitationActionId] = useState("");
  const [query, setQuery] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");
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
  const filteredItems = items.filter((item) => projectIncludesDate(item, scheduleDate));
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
        testingApi.listProjects(value, statusValue, 200),
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
    void load("", "active");
  }, [load]);
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
      <Panel title="Danh sách dự án">
        <form
          className="grid min-w-0 gap-3 border-b border-border p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end xl:grid-cols-[minmax(260px,1fr)_auto_minmax(170px,220px)_minmax(170px,210px)] xl:items-center"
          onSubmit={(event) => {
            event.preventDefault();
            void load(query, status);
          }}
        >
          <label className="relative block min-w-0">
            <span className="sr-only">Tìm dự án</span>
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 text-ink-faint"
              size={16}
            />
            <input
              aria-label="Tìm dự án"
              className="apple-input h-10 w-full py-0 pl-10"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm theo mã hoặc tên dự án"
            />
          </label>
          <button className="secondary-button h-10" type="submit">
            Tìm
          </button>
          <select
            aria-label="Trạng thái dự án"
            className="apple-input h-10 w-full"
            value={status}
            onChange={(event) => {
              const nextStatus = event.target.value;
              setStatus(nextStatus);
              void load(query, nextStatus);
            }}
          >
            <option value="active">Đang hoạt động</option>
            <option value="archived">Đã lưu trữ</option>
            <option value="all">Tất cả dự án</option>
          </select>
          <label className="field-label min-w-0">
            Có lịch trong ngày
            <input
              aria-label="Lịch dự án"
              className="apple-input mt-2 h-10 w-full"
              type="date"
              value={scheduleDate}
              onChange={(event) => setScheduleDate(event.target.value)}
            />
          </label>
        </form>
        {loading ? (
          <div className="p-5">
            <LoadingState />
          </div>
        ) : filteredItems.length === 0 ? (
          <EmptyState>
            {scheduleDate
              ? "Không có dự án theo ngày đã chọn"
              : query.trim()
                ? "Không tìm thấy dự án phù hợp"
                : status === "archived"
                  ? "Chưa có dự án đã lưu trữ"
                  : "Chưa có dự án"}
          </EmptyState>
        ) : (
          <div className="divide-y divide-border">
            {filteredItems.map((item) => {
              const taskProgress = taskProgressPresentation(item.task_summary);
              const schedule = projectSchedule(item);
              const activityDate = item.updated_at || item.created_at;
              const activityLabel = item.updated_at
                ? "Cập nhật"
                : item.created_at
                  ? "Tạo lúc"
                  : "Chưa có thông tin";
              return (
                <article
                  key={item._id}
                  className="grid min-w-0 gap-5 p-5 transition hover:bg-surface-quiet lg:grid-cols-2 lg:items-center xl:grid-cols-[minmax(220px,1.2fr)_minmax(205px,1fr)_minmax(190px,1fr)_minmax(180px,0.9fr)]"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="shrink-0 font-mono text-[13px] font-semibold text-brand">
                      {item.key}
                    </span>
                    <Link href={`/du-an/${item._id}`} className="min-w-0">
                      <strong className="block break-words text-[14px]">{item.name}</strong>
                      {item.description && (
                        <small className="mt-1 line-clamp-2 block text-ink-muted">
                          {item.description}
                        </small>
                      )}
                    </Link>
                  </div>
                  <div className="flex min-w-0 items-start gap-2 text-[12px]">
                    <CalendarDays
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-ink-muted"
                      size={15}
                    />
                    <span className="min-w-0 break-words font-medium">{schedule}</span>
                  </div>
                  <div className="min-w-0 space-y-2 text-[12px]">
                    {taskProgress.completionPercent == null ? (
                      <span className="text-ink-muted">{taskProgress.label}</span>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex justify-between gap-2">
                          <span>Tiến độ công việc</span>
                          <strong>{taskProgress.completionPercent}%</strong>
                        </div>
                        <div
                          aria-label={`Tiến độ công việc ${taskProgress.completionPercent}%`}
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
                    {taskProgress.applicableTotal > 0 && (
                      <span className="block text-ink-muted">
                        {taskProgress.applicableTotal} công việc · {taskProgress.completed ?? 0}{" "}
                        hoàn thành
                        {taskProgress.blocked > 0 ? ` · ${taskProgress.blocked} bị chặn` : ""}
                      </span>
                    )}
                  </div>
                  <div className="flex min-w-0 flex-col items-start gap-1.5 lg:items-end">
                    <StatusPill value={String(item.status).toUpperCase()} />
                    <p
                      className="text-[11px] text-ink-muted lg:text-right"
                      title={`${activityLabel}${activityDate ? ` ${formatProjectUpdatedAt(activityDate)}` : ""}`}
                    >
                      {activityDate
                        ? `${activityLabel} ${formatProjectUpdatedAt(activityDate)}`
                        : activityLabel}
                    </p>
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
                  </div>
                </article>
              );
            })}
          </div>
        )}
        {!loading && items.length >= 200 && (
          <p className="border-t border-border px-4 py-3 text-xs text-ink-muted">
            Đang hiển thị tối đa 200 dự án. Dùng ô tìm kiếm để thu hẹp danh sách.
          </p>
        )}
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
