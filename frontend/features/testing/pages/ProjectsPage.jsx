"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CalendarDays, Grid2X2, List, Plus, RefreshCw, RotateCcw, Search } from "lucide-react";
import { Pagination } from "@/shared/components/ui/Pagination";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { isSupportedTimeZone } from "@/shared/lib/timeZone.mjs";
import { safeLocale } from "@/shared/lib/locale.mjs";
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
import { formatProjectDate } from "../lib/projectSchedule.logic.mjs";

function projectSchedule(project, locale) {
  const start = project.planned_start_at
    ? formatProjectDate(project.planned_start_at, locale)
    : null;
  const end = project.planned_end_at ? formatProjectDate(project.planned_end_at, locale) : null;
  if (start && end) return `${start} – ${end}`;
  if (start) return `Từ ${start}`;
  if (end) return `Đến ${end}`;
  return null;
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

function formatProjectUpdatedAt(value, configuredTimeZone, locale) {
  if (!value) return "Chưa có thông tin";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có thông tin";
  const timeZone = isSupportedTimeZone(configuredTimeZone) ? configuredTimeZone : undefined;
  const dateLabel = date.toLocaleDateString(safeLocale(locale), {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    ...(timeZone ? { timeZone } : {}),
  });
  const timeLabel = date.toLocaleTimeString(safeLocale(locale), {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    ...(timeZone ? { timeZone } : {}),
  });
  return `${dateLabel}, ${timeLabel}`;
}

export default function ProjectsPage() {
  const { ask, dialog } = useActionDialog();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [invitationActionId, setInvitationActionId] = useState("");
  const [query, setQuery] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");
  const [projectPage, setProjectPage] = useState(1);
  const [projectView, setProjectView] = useState("grid");
  const [status, setStatus] = useState("active");
  const [invitationError, setInvitationError] = useState("");
  const [invitationActionError, setInvitationActionError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canCreateProject, setCanCreateProject] = useState(false);
  const [capabilityError, setCapabilityError] = useState("");
  const invitationActionInFlight = useRef(false);
  const requestSequence = useRef(0);
  const filteredItems = items.filter((item) => projectIncludesDate(item, scheduleDate));
  const projectPageSize = 15;
  const projectPageCount = Math.max(1, Math.ceil(filteredItems.length / projectPageSize));
  const visibleProjects = filteredItems.slice(
    (Math.min(projectPage, projectPageCount) - 1) * projectPageSize,
    Math.min(projectPage, projectPageCount) * projectPageSize,
  );
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
    const timeout = window.setTimeout(() => void load(query, status), 250);
    return () => window.clearTimeout(timeout);
  }, [load, query, status]);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  return (
    <WorkspacePage
      title="Dự án"
      actions={
        canCreateProject ? (
          <Link href="/du-an/tao-moi" className="apple-button">
            <Plus size={16} />
            Tạo dự án
          </Link>
        ) : null
      }
    >
      {error && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <ErrorState message={error} />
          <button
            aria-label="Tải lại danh sách dự án"
            className="icon-button h-9 w-9"
            type="button"
            title="Tải lại danh sách"
            disabled={loading}
            onClick={() => void load(query, status)}
          >
            <RefreshCw aria-hidden="true" size={16} />
          </button>
        </div>
      )}
      {capabilityError && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <ErrorState message={`Không thể xác định quyền tạo dự án: ${capabilityError}`} />
          <button
            aria-label="Thử tải lại quyền tạo dự án"
            type="button"
            className="icon-button h-9 w-9"
            title="Thử lại"
            onClick={() => void loadCapabilities()}
          >
            <RefreshCw aria-hidden="true" size={16} />
          </button>
        </div>
      )}
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
                      Vai trò được mời{" "}
                      {(invitation.project_roles?.length
                        ? invitation.project_roles
                        : [invitation.project_role].filter(Boolean)
                      )
                        .map(valueLabel)
                        .join(", ")}
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
          className="grid min-w-0 grid-cols-1 gap-3 border-b border-border p-4 md:grid-cols-2 xl:grid-cols-[minmax(300px,1fr)_minmax(170px,220px)_minmax(170px,210px)_auto] xl:items-center"
          onSubmit={(event) => {
            event.preventDefault();
            setProjectPage(1);
            void load(query, status);
          }}
        >
          <div className="flex min-w-0 md:col-span-2 xl:col-span-1">
            <label className="relative block min-w-0 flex-1">
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
          </div>
          <select
            aria-label="Trạng thái dự án"
            className="apple-input h-10 w-full"
            value={status}
            onChange={(event) => {
              const nextStatus = event.target.value;
              setStatus(nextStatus);
              setProjectPage(1);
              void load(query, nextStatus);
            }}
          >
            <option value="active">Đang hoạt động</option>
            <option value="archived">Đã lưu trữ</option>
            <option value="all">Tất cả dự án</option>
          </select>
          <label className="block min-w-0">
            <span className="sr-only">Lịch dự án</span>
            <input
              aria-label="Lịch dự án"
              className="apple-input h-10 w-full"
              type="date"
              value={scheduleDate}
              onChange={(event) => {
                setScheduleDate(event.target.value);
                setProjectPage(1);
              }}
            />
          </label>
          <div aria-label="Chế độ hiển thị dự án" className="flex items-center gap-1" role="group">
            <button
              aria-label="Xem dạng lưới"
              aria-pressed={projectView === "grid"}
              className={`icon-button h-10 w-10 ${projectView === "grid" ? "bg-brand/10 text-brand" : ""}`}
              onClick={() => setProjectView("grid")}
              title="Dạng lưới"
              type="button"
            >
              <Grid2X2 aria-hidden="true" size={16} />
            </button>
            <button
              aria-label="Xem dạng danh sách"
              aria-pressed={projectView === "list"}
              className={`icon-button h-10 w-10 ${projectView === "list" ? "bg-brand/10 text-brand" : ""}`}
              onClick={() => setProjectView("list")}
              title="Dạng danh sách"
              type="button"
            >
              <List aria-hidden="true" size={16} />
            </button>
          </div>
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
          <div
            className={
              projectView === "grid"
                ? "grid gap-4 p-4 md:grid-cols-2 2xl:grid-cols-3"
                : "divide-y divide-border"
            }
          >
            {visibleProjects.map((item) => {
              const completionPercent = Number.isFinite(item.project_completion_percent)
                ? item.project_completion_percent
                : null;
              const schedule = projectSchedule(item, user?.locale);
              const activityDate = item.updated_at || item.created_at;
              const activityLabel = item.updated_at
                ? "Cập nhật"
                : item.created_at
                  ? "Tạo lúc"
                  : "Chưa có thông tin";
              return (
                <article
                  key={item._id}
                  className={`min-w-0 transition hover:bg-surface-quiet/50 ${projectView === "grid" ? "flex flex-col rounded-panel border border-border bg-surface p-4 hover:border-brand/40" : "grid gap-x-5 gap-y-3 p-4 sm:px-5 lg:grid-cols-[minmax(7rem,.7fr)_minmax(15rem,1.6fr)_minmax(10rem,1fr)_minmax(9rem,.9fr)_minmax(10rem,1fr)] lg:items-center"}`}
                  onClick={(event) => {
                    if (
                      projectView === "grid" &&
                      !event.target.closest("a, button, input, select, textarea")
                    ) {
                      window.location.assign(`/du-an/${item._id}`);
                    }
                  }}
                  onKeyDown={(event) => {
                    if (
                      projectView === "grid" &&
                      event.target === event.currentTarget &&
                      (event.key === "Enter" || event.key === " ")
                    ) {
                      event.preventDefault();
                      window.location.assign(`/du-an/${item._id}`);
                    }
                  }}
                  role={projectView === "grid" ? "link" : undefined}
                  tabIndex={projectView === "grid" ? 0 : undefined}
                >
                  <header className="flex min-w-0 items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span
                        aria-hidden="true"
                        className="mr-2 inline-flex size-8 items-center justify-center rounded-control bg-brand/10 text-xs font-semibold text-brand"
                      >
                        {(item.name || item.key || "D").slice(0, 2).toUpperCase()}
                      </span>
                      <span
                        className="inline-flex rounded-full bg-brand/10 px-2.5 py-1 font-mono text-[11px] font-semibold text-brand"
                        title={item.key}
                      >
                        {item.key}
                      </span>
                    </div>
                    <StatusPill
                      value={item.status ? valueLabel(item.status) : "Chưa có thông tin"}
                    />
                  </header>
                  <div className={`${projectView === "grid" ? "mt-3" : "lg:min-w-0"} min-w-0`}>
                    {projectView === "grid" ? (
                      <strong
                        className="line-clamp-2 break-words text-base font-semibold leading-6 [overflow-wrap:anywhere]"
                        title={item.name}
                      >
                        {item.name}
                      </strong>
                    ) : (
                      <Link href={`/du-an/${item._id}`} className="group block min-w-0">
                        <strong
                          className="line-clamp-2 break-words text-base font-semibold leading-6 [overflow-wrap:anywhere] group-hover:text-brand"
                          title={item.name}
                        >
                          {item.name}
                        </strong>
                      </Link>
                    )}
                    {item.description && (
                      <small className="mt-1 line-clamp-2 text-ink-muted">{item.description}</small>
                    )}
                    {item.project_type && (
                      <small className="mt-1 block text-[12px] text-ink-muted">
                        {valueLabel(item.project_type)}
                      </small>
                    )}
                    <small className="mt-2 block text-[12px] text-ink-muted"></small>
                  </div>
                  <div
                    className={`${projectView === "grid" ? "mt-4" : "lg:mt-0"} flex min-w-0 items-start gap-2 text-[12px] text-ink-muted`}
                  >
                    <CalendarDays
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-ink-muted"
                      size={15}
                    />
                    <span className="min-w-0 break-words font-medium">
                      {schedule || "Chưa có lịch"}
                    </span>
                  </div>
                  <div
                    className={`${projectView === "grid" ? "mt-4" : "lg:mt-0"} min-w-0 space-y-2 text-[12px]`}
                  >
                    {completionPercent == null ? (
                      <span className="text-ink-muted">Chưa có tiến độ</span>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex justify-between gap-2">
                          <span>Tiến độ dự án</span>
                          <strong>{completionPercent}%</strong>
                        </div>
                        <div
                          aria-label={`Tiến độ dự án ${completionPercent}%`}
                          aria-valuemax={100}
                          aria-valuemin={0}
                          aria-valuenow={completionPercent}
                          className="h-1.5 overflow-hidden rounded-full bg-surface-quiet"
                          role="progressbar"
                        >
                          <div
                            className="h-full rounded-full bg-brand"
                            style={{ width: `${completionPercent}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  <footer
                    className={`${projectView === "grid" ? "mt-4 border-t border-border pt-3" : "lg:mt-0"} flex min-w-0 items-end justify-between gap-3`}
                  >
                    <p
                      className="min-w-0 text-[11px] text-ink-muted"
                      title={`${activityLabel}${activityDate ? ` ${formatProjectUpdatedAt(activityDate, user?.timezone, user?.locale)}` : ""}`}
                    >
                      {activityDate
                        ? `${activityLabel} ${formatProjectUpdatedAt(activityDate, user?.timezone, user?.locale)}`
                        : activityLabel}
                    </p>
                    {item.status === "archived" &&
                      item.current_permissions?.includes("project.restore") && (
                        <button
                          type="button"
                          aria-label={`Khôi phục dự án ${item.name || item.key}`}
                          className="icon-button h-9 w-9"
                          title="Khôi phục dự án"
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
                          <RotateCcw aria-hidden="true" size={16} />
                        </button>
                      )}
                  </footer>
                </article>
              );
            })}
          </div>
        )}
        {!loading && filteredItems.length > projectPageSize && (
          <Pagination
            page={Math.min(projectPage, projectPageCount)}
            pageSize={projectPageSize}
            total={filteredItems.length}
            onChange={setProjectPage}
          />
        )}
        {!loading && items.length >= 200 && (
          <p className="border-t border-border px-4 py-3 text-xs text-ink-muted">
            Đang hiển thị tối đa 200 dự án. Dùng ô tìm kiếm để thu hẹp danh sách
          </p>
        )}
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
