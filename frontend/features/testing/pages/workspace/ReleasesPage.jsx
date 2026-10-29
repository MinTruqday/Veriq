"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Plus, RefreshCw } from "lucide-react";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf } from "../../lib/testing";

export default function ReleasesPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [releases, setReleases] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
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
          <DataTable
            items={releases}
            empty="Chưa có bản phát hành"
            columns={[
              { key: "key", label: "Mã" },
              { key: "name", label: "Tên" },
              { key: "version", label: "Phiên bản" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "planned_end_at",
                label: "Kết thúc dự kiến",
                render: (item) =>
                  item.planned_end_at ? formatDate(item.planned_end_at) : "Chưa đặt",
              },
              ...(can("release.manage") || can("release.close")
                ? [
                    {
                      key: "actions",
                      label: "Thao tác",
                      hideWhenEmpty: true,
                      render: (item) => {
                        if (item.status === "PLANNED" && can("release.manage"))
                          return (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => transition(item, "activate")}
                            >
                              Kích hoạt
                            </button>
                          );
                        if (item.status !== "ACTIVE" || !can("release.close")) return null;
                        const current = readiness[item._id];
                        const stale =
                          current?.data &&
                          (current.data.revision !== item.revision ||
                            (item.gate_revision !== undefined &&
                              current.data.gate_revision !== item.gate_revision));
                        const blockers = current?.data?.blockers || [];
                        const allowed = Boolean(current?.data?.can_close) && !stale;
                        return (
                          <div className="min-w-64 space-y-2">
                            {!can("release.read") ? (
                              <p className="text-xs text-ink-muted">
                                Cần quyền xem bản phát hành để kiểm tra điều kiện đóng.
                              </p>
                            ) : current?.error ? (
                              <div className="space-y-1">
                                <p className="text-xs text-danger">
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
                              <p className="text-xs text-ink-muted">
                                Đang kiểm tra điều kiện đóng…
                              </p>
                            ) : stale ? (
                              <div className="space-y-1">
                                <p className="text-xs text-danger">
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
                              <div className="space-y-2">
                                <p
                                  className={`flex items-center gap-1 text-xs ${allowed ? "text-brand" : "text-danger"}`}
                                >
                                  {allowed ? (
                                    <CheckCircle2 size={14} />
                                  ) : (
                                    <AlertTriangle size={14} />
                                  )}
                                  {allowed
                                    ? `Đủ điều kiện đóng · ${current.data.checks?.length || 0} điều kiện đã kiểm tra`
                                    : `Chưa đủ điều kiện (${blockers.length} mục)`}
                                </p>
                                {!allowed && blockers.length > 0 && (
                                  <ul className="list-disc space-y-1 pl-4 text-xs text-ink-muted">
                                    {blockers.map((check, index) => (
                                      <li key={`${check.gate}-${check.code}-${index}`}>
                                        {readinessGateLabel(check.gate)}:{" "}
                                        {readinessCodeLabel(check.code)}
                                      </li>
                                    ))}
                                  </ul>
                                )}
                                {current.data.checks?.length > 0 && (
                                  <details className="text-xs text-ink-muted">
                                    <summary className="cursor-pointer py-1">
                                      Xem toàn bộ điều kiện
                                    </summary>
                                    <ul className="mt-1 space-y-1 pl-1">
                                      {current.data.checks.map((check, index) => (
                                        <li
                                          className="flex items-start gap-1.5"
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
                                  </details>
                                )}
                              </div>
                            )}
                            <button
                              className="secondary-button"
                              type="button"
                              disabled={!allowed}
                              onClick={() => transition(item, "close")}
                            >
                              Đóng phát hành
                            </button>
                          </div>
                        );
                      },
                    },
                  ]
                : []),
            ]}
          />
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
