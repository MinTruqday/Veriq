"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Plus, RefreshCw } from "lucide-react";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatCalendarDate, messageOf } from "../../lib/testing";

export default function ReleasesPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [releases, setReleases] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [expandedReleaseId, setExpandedReleaseId] = useState(null);
  const loadSequence = useRef(0);
  const can = useCallback(
    (permission) => project.current_permissions?.includes(permission),
    [project.current_permissions],
  );
  const load = useCallback(
    async ({ showLoading = true } = {}) => {
      const sequence = ++loadSequence.current;
      if (!can("release.read")) {
        if (sequence === loadSequence.current) setLoading(false);
        return;
      }
      if (showLoading) setLoading(true);
      try {
        const values = await testingApi.listReleases(project._id);
        if (sequence !== loadSequence.current) return;
        setReleases(values);
        setError("");
        const active = values.filter((item) => item.status === "ACTIVE");
        if (can("release.read")) {
          setReadiness(Object.fromEntries(active.map((item) => [item._id, { loading: true }])));
          const results = await Promise.all(
            active.map(async (release) => {
              try {
                return [
                  release._id,
                  { data: await testingApi.getReleaseCloseReadiness(release._id) },
                ];
              } catch (reason) {
                return [release._id, { error: messageOf(reason) }];
              }
            }),
          );
          if (sequence !== loadSequence.current) return;
          setReadiness(Object.fromEntries(results));
        } else setReadiness({});
      } catch (reason) {
        if (sequence === loadSequence.current) setError(messageOf(reason));
      } finally {
        if (showLoading && sequence === loadSequence.current) setLoading(false);
      }
    },
    [can, project._id],
  );
  useEffect(() => {
    void load();
  }, [load]);
  const createRelease = async () => {
    await ask({
      title: "Tạo bản phát hành",
      confirmLabel: "Tạo bản phát hành",
      fields: [
        { name: "key", label: "Mã", required: true },
        { name: "name", label: "Tên", required: true },
        { name: "version", label: "Phiên bản", required: true },
        { name: "planned_start_at", label: "Bắt đầu dự kiến", type: "date" },
        { name: "planned_end_at", label: "Kết thúc dự kiến", type: "date" },
        { name: "notes", label: "Ghi chú", multiline: true },
      ],
      onConfirm: async (value) => {
        await testingApi.createRelease(project._id, {
          ...value,
          key: value.key.trim(),
          name: value.name.trim(),
          version: value.version.trim(),
          planned_start_at: value.planned_start_at || null,
          planned_end_at: value.planned_end_at || null,
          notes: value.notes.trim(),
        });
        await load({ showLoading: false });
      },
    });
  };
  const transition = async (release, action) => {
    await ask({
      title: action === "activate" ? "Kích hoạt bản phát hành" : "Đóng bản phát hành",
      confirmLabel: action === "activate" ? "Kích hoạt" : "Đóng bản phát hành",
      fields: [{ name: "reason", label: "Lý do", multiline: true, required: true }],
      onConfirm: async (value) => {
        const payload = { expected_revision: release.revision, reason: value.reason.trim() };
        if (action === "activate") await testingApi.activateRelease(release._id, payload);
        else {
          const current = await testingApi.getReleaseCloseReadiness(release._id);
          if (
            current.release_id !== release._id ||
            current.project_id !== project._id ||
            current.revision !== release.revision ||
            (release.gate_revision !== undefined && current.gate_revision !== release.gate_revision)
          ) {
            await load({ showLoading: false });
            throw new Error(
              "Điều kiện phát hành vừa thay đổi. Đã tải lại trạng thái; vui lòng kiểm tra và thử đóng lại.",
            );
          }
          if (!current.can_close) {
            await load({ showLoading: false });
            throw new Error(readinessBlockerMessage(current));
          }
          try {
            await testingApi.closeRelease(release._id, payload);
          } catch (reason) {
            await load({ showLoading: false });
            throw reason;
          }
        }
        await load({ showLoading: false });
      },
    });
  };
  if (!can("release.read")) return null;
  if (loading)
    return (
      <WorkspacePage title="Bản phát hành">
        <LoadingState />
      </WorkspacePage>
    );
  return (
    <WorkspacePage
      title="Bản phát hành"
      actions={
        can("release.create") ? (
          <button className="apple-button" type="button" onClick={createRelease}>
            <Plus size={16} />
            Tạo bản phát hành
          </button>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      {error && releases.length === 0 ? (
        <Panel title="Danh sách bản phát hành">
          <div className="space-y-3 p-5">
            <p className="text-sm text-ink-muted">Chưa thể xác định danh sách bản phát hành</p>
            <button className="secondary-button" type="button" onClick={() => void load()}>
              Tải lại
            </button>
          </div>
        </Panel>
      ) : (
        <Panel title="Danh sách bản phát hành">
          {releases.length === 0 ? (
            <EmptyState
              onAction={can("release.create") ? createRelease : undefined}
              actionLabel="Tạo bản phát hành"
            >
              Chưa có bản phát hành
            </EmptyState>
          ) : (
            <div className="divide-y divide-border">
              {releases.map((item) => {
                const current = readiness[item._id];
                const stale =
                  current?.data &&
                  (current.data.revision !== item.revision ||
                    (item.gate_revision !== undefined &&
                      current.data.gate_revision !== item.gate_revision));
                const blockers = current?.data?.blockers || [];
                const allowed = Boolean(current?.data?.can_close) && !stale;
                const expanded = expandedReleaseId === item._id;
                const canActivate = item.status === "PLANNED" && can("release.manage");
                const canClose = item.status === "ACTIVE" && can("release.close");
                return (
                  <article className="min-w-0 px-4 py-4 sm:px-5" key={item._id}>
                    <div className="grid min-w-0 gap-x-6 gap-y-3 2xl:grid-cols-[minmax(0,1fr)_minmax(15rem,0.55fr)_auto] 2xl:items-start">
                      <div className="min-w-0">
                        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                          <h3 className="min-w-0 break-words text-[15px] font-semibold text-ink">
                            {item.name}
                          </h3>
                          <StatusPill value={item.status} />
                        </div>
                        <p className="mt-1 break-words text-[13px] text-ink-muted">
                          <span className="font-medium text-ink">{item.key}</span>
                          <span className="mx-2 text-border-strong">·</span>Phiên bản {item.version}
                        </p>
                        {item.notes && (
                          <p className="mt-2 max-w-3xl break-words text-[13px] leading-5 text-ink-muted">
                            {item.notes}
                          </p>
                        )}
                      </div>
                      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
                        <div>
                          <dt className="text-ink-muted">Bắt đầu</dt>
                          <dd className="mt-0.5 font-medium text-ink">
                            {item.planned_start_at
                              ? formatCalendarDate(item.planned_start_at)
                              : "Chưa đặt"}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-ink-muted">Kết thúc</dt>
                          <dd className="mt-0.5 font-medium text-ink">
                            {item.planned_end_at
                              ? formatCalendarDate(item.planned_end_at)
                              : "Chưa đặt"}
                          </dd>
                        </div>
                        {item.status === "ACTIVE" && can("release.read") && (
                          <div className="col-span-2 min-w-0">
                            {current?.error ? (
                              <p className="break-words text-danger">
                                Chưa tải được điều kiện đóng: {current.error}
                              </p>
                            ) : current?.loading || !current?.data ? (
                              <p className="text-ink-muted">Đang kiểm tra điều kiện đóng…</p>
                            ) : stale ? (
                              <p className="text-danger">
                                Điều kiện đã thay đổi; cần kiểm tra lại.
                              </p>
                            ) : (
                              <p
                                className={`flex items-start gap-1.5 ${allowed ? "text-brand" : "text-danger"}`}
                              >
                                {allowed ? (
                                  <CheckCircle2 className="mt-0.5 shrink-0" size={14} />
                                ) : (
                                  <AlertTriangle className="mt-0.5 shrink-0" size={14} />
                                )}
                                <span>
                                  {allowed
                                    ? `Đủ điều kiện đóng · ${current.data.checks?.length || 0} điều kiện đã kiểm tra`
                                    : `Chưa đủ điều kiện · ${blockers.length} mục cần xử lý`}
                                </span>
                              </p>
                            )}
                          </div>
                        )}
                      </dl>
                      {(canActivate ||
                        canClose ||
                        (item.status === "ACTIVE" && can("release.read"))) && (
                        <div className="flex flex-wrap items-center gap-2 2xl:justify-end">
                          {canActivate && (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => transition(item, "activate")}
                            >
                              Kích hoạt
                            </button>
                          )}
                          {canClose && (
                            <button
                              className="secondary-button"
                              type="button"
                              disabled={!allowed}
                              onClick={() => transition(item, "close")}
                            >
                              Đóng phát hành
                            </button>
                          )}
                          {item.status === "ACTIVE" && can("release.read") && (
                            <button
                              aria-expanded={expanded}
                              className="text-button"
                              type="button"
                              onClick={() => setExpandedReleaseId(expanded ? null : item._id)}
                            >
                              {expanded ? "Thu gọn điều kiện" : "Xem điều kiện"}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                    {expanded && item.status === "ACTIVE" && (
                      <div className="mt-4 border-t border-border pt-3">
                        {current?.error ? (
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm text-danger">
                              Không tải được điều kiện đóng: {current.error}
                            </p>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => void load()}
                            >
                              <RefreshCw size={14} /> Tải lại kiểm tra
                            </button>
                          </div>
                        ) : current?.loading || !current?.data ? (
                          <p className="text-sm text-ink-muted">Đang kiểm tra điều kiện đóng…</p>
                        ) : stale ? (
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm text-danger">
                              Điều kiện phát hành đã thay đổi; hãy kiểm tra lại trước khi đóng.
                            </p>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => void load()}
                            >
                              <RefreshCw size={14} /> Cập nhật điều kiện
                            </button>
                          </div>
                        ) : (
                          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
                            <div>
                              <h4 className="text-[13px] font-semibold">Mục cần xử lý</h4>
                              {blockers.length ? (
                                <ul className="mt-2 space-y-2 text-[13px] text-ink-muted">
                                  {blockers.map((check, index) => (
                                    <li key={`${check.gate}-${check.code}-${index}`}>
                                      {readinessGateLabel(check.gate)}:{" "}
                                      {readinessCodeLabel(check.code)}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="mt-2 text-[13px] text-brand">
                                  Không còn mục chặn phát hành.
                                </p>
                              )}
                            </div>
                            <div>
                              <h4 className="text-[13px] font-semibold">
                                Toàn bộ điều kiện ({current.data.checks?.length || 0})
                              </h4>
                              <ul className="mt-2 grid gap-x-5 gap-y-2 sm:grid-cols-2">
                                {(current.data.checks || []).map((check, index) => (
                                  <li
                                    className="flex min-w-0 items-start gap-1.5 text-[12px] text-ink-muted"
                                    key={`${check.gate}-${check.code}-${index}`}
                                  >
                                    {check.status === "PASS" ? (
                                      <CheckCircle2
                                        className="mt-0.5 shrink-0 text-brand"
                                        size={13}
                                      />
                                    ) : (
                                      <AlertTriangle
                                        className="mt-0.5 shrink-0 text-danger"
                                        size={13}
                                      />
                                    )}
                                    <span>
                                      {readinessGateLabel(check.gate)}:{" "}
                                      {readinessCodeLabel(check.code)}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </Panel>
      )}
      {dialog}
    </WorkspacePage>
  );
}

function readinessBlockerMessage(readiness) {
  const blockers = readiness?.blockers || [];
  if (!blockers.length)
    return "Chưa thể xác nhận điều kiện đóng phát hành. Vui lòng tải lại và thử lại.";
  return `Chưa thể đóng phát hành: ${blockers
    .map((item) => `${readinessGateLabel(item.gate)} — ${readinessCodeLabel(item.code)}`)
    .join("; ")}`;
}

function readinessGateLabel(gate) {
  return (
    {
      RELEASE_STATE: "Trạng thái phát hành",
      GATE_REVISION: "Điều kiện phát hành",
      COMPLETION_REPORT: "Báo cáo hoàn tất",
      BLOCKING_DEFECTS: "Lỗi chặn phát hành",
      REQUIREMENT_ASSURANCE: "Hồ sơ đảm bảo yêu cầu",
    }[gate] || "Điều kiện phát hành"
  );
}

function readinessCodeLabel(code) {
  return (
    {
      RELEASE_ACTIVE: "Phát hành đang hoạt động",
      RELEASE_STATE_INVALID: "Trạng thái hiện tại không cho phép đóng",
      RELEASE_GATE_REVISION_VALID: "Điều kiện đóng còn hiệu lực",
      RELEASE_GATE_REVISION_INVALID: "Điều kiện đóng đã thay đổi; cần kiểm tra lại",
      RELEASE_COMPLETION_REPORT_VALID: "Báo cáo hoàn tất hợp lệ",
      OPEN_BLOCKING_DEFECTS: "Còn lỗi mức chặn đang mở",
      NO_OPEN_BLOCKING_DEFECTS: "Không còn lỗi mức chặn đang mở",
      RELEASE_REQUIREMENT_ASSURANCE_VALID: "Hồ sơ đảm bảo hợp lệ",
      RELEASE_COMPLETION_GATE_FAILED: "Chưa đạt điều kiện báo cáo hoàn tất",
      RELEASE_TEST_PLAN_SCOPE_REQUIRED: "Cần chọn phạm vi kế hoạch kiểm thử",
      RELEASE_TEST_PLAN_SNAPSHOT_INVALID: "Phạm vi kế hoạch kiểm thử không còn hiệu lực",
      RELEASE_REQUIREMENT_SCOPE_REQUIRED: "Cần có yêu cầu trong phạm vi phát hành",
      RELEASE_REQUIREMENT_ASSURANCE_GATE_FAILED: "Hồ sơ đảm bảo chưa đạt",
    }[code] || "Điều kiện này chưa đạt hoặc cần được kiểm tra lại"
  );
}
