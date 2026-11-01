"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  InitialLoadState,
  Metric,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

export default function TraceabilityPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [matrix, setMatrix] = useState({ trace_links: [], requirements: [], test_cases: [] });
  const [coverage, setCoverage] = useState({});
  const [snapshots, setSnapshots] = useState([]);
  const [linkForm, setLinkForm] = useState({ source_id: "", target_id: "" });
  const [error, setError] = useState("");
  const [linkError, setLinkError] = useState("");
  const [creating, setCreating] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = useCallback((permission) => permissions.includes(permission), [permissions]);
  const load = useCallback(async () => {
    if (!can("trace.read")) {
      setInitialLoading(false);
      return;
    }
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      const [traceValue, coverageValue, snapshotValues] = await Promise.all([
        testingApi.traceability(project._id),
        can("coverage.read") ? testingApi.coverage(project._id) : Promise.resolve({}),
        can("coverage.read") ? testingApi.listCoverageSnapshots(project._id) : Promise.resolve([]),
      ]);
      setMatrix(traceValue);
      setCoverage(coverageValue);
      setSnapshots(snapshotValues);
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [can, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  if (!can("trace.read")) return null;
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Truy vết"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  const decision = async (item, accept) => {
    try {
      await (accept ? testingApi.confirmTrace(item._id) : testingApi.rejectTrace(item._id));
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <WorkspacePage
      title="Truy vết"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          {can("report.export") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                testingApi
                  .exportTraceability(project._id)
                  .catch((reason) => setError(messageOf(reason)))
              }
            >
              Xuất CSV
            </button>
          )}
          {can("trace.recover") && (
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                try {
                  await testingApi.recoverTrace(project._id);
                  await load();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Tìm liên kết bị thiếu
            </button>
          )}
          {can("coverage.snapshot.create") && (
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                await ask({
                  title: "Lưu mốc độ phủ",
                  description:
                    "Lưu lại các chỉ số hiện tại để đối chiếu với bản phát hành sau này.",
                  confirmLabel: "Lưu mốc độ phủ",
                  fields: [
                    {
                      name: "label",
                      label: "Tên mốc độ phủ",
                      initialValue: "Độ phủ hiện tại",
                      required: true,
                      autoFocus: true,
                    },
                  ],
                  onConfirm: async (answer) => {
                    try {
                      await testingApi.createCoverageSnapshot(project._id, {
                        label: answer.label,
                        idempotency_key: crypto.randomUUID(),
                      });
                      await load();
                    } catch (reason) {
                      throw new Error(messageOf(reason));
                    }
                  },
                });
              }}
            >
              Lưu mốc độ phủ
            </button>
          )}
          {can("trace.create") && (
            <button
              className="apple-button"
              type="button"
              onClick={() => {
                setLinkError("");
                setCreating(true);
              }}
            >
              Tạo liên kết
            </button>
          )}
          <ProjectCrumb projectId={project._id} />
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {can("coverage.read") && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-5">
          <Metric
            label="Yêu cầu có liên kết kiểm thử"
            value={`${coverage.requirement_coverage || 0}%`}
          />
          <Metric
            label="Tiêu chí chấp nhận có liên kết kiểm thử"
            value={`${coverage.acceptance_criterion_coverage || 0}%`}
          />
          <Metric label="Liên kết còn hiệu lực" value={`${coverage.fresh_coverage || 0}%`} />
          <Metric label="Ca kiểm thử đã chạy" value={`${coverage.execution_coverage || 0}%`} />
          <Metric label="Ca kiểm thử chưa liên kết" value={coverage.unlinked_tests?.length || 0} />
        </div>
      )}
      {can("trace.create") && (
        <Modal
          isOpen={creating}
          onClose={() => setCreating(false)}
          ariaLabel="Tạo liên kết yêu cầu và ca kiểm thử"
          className="max-w-2xl"
        >
          <ModalHeader>
            <ModalTitle>Tạo liên kết yêu cầu và ca kiểm thử</ModalTitle>
          </ModalHeader>
          {linkError && (
            <div className="px-5 pt-4 text-sm text-danger" role="alert">
              {linkError}
            </div>
          )}
          <form
            className="grid min-w-0 gap-3 p-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await testingApi.createTrace({
                  project_id: project._id,
                  source_type: "requirement_version",
                  source_id: linkForm.source_id,
                  target_type: "test_case_version",
                  target_id: linkForm.target_id,
                  link_type: "verifies",
                  confidence: 1,
                  origin: "manual",
                  evidence: [],
                });
                setLinkForm({ source_id: "", target_id: "" });
                setCreating(false);
                setLinkError("");
                await load();
              } catch (reason) {
                setLinkError(messageOf(reason));
              }
            }}
          >
            <select
              aria-label="Phiên bản yêu cầu nguồn"
              className="apple-input min-w-0 w-full"
              required
              value={linkForm.source_id}
              onChange={(event) => setLinkForm({ ...linkForm, source_id: event.target.value })}
            >
              <option value="">Chọn phiên bản yêu cầu</option>
              {(matrix.requirement_versions || []).map((item) => (
                <option key={item._id} value={item._id}>
                  {item.requirement_key} v{item.version} {item.title}
                </option>
              ))}
            </select>
            <select
              aria-label="Phiên bản ca kiểm thử đích"
              className="apple-input min-w-0 w-full"
              required
              value={linkForm.target_id}
              onChange={(event) => setLinkForm({ ...linkForm, target_id: event.target.value })}
            >
              <option value="">Chọn phiên bản ca kiểm thử</option>
              {(matrix.test_case_versions || []).map((item) => (
                <option key={item._id} value={item._id}>
                  {item.test_case_key} v{item.version} {item.title}
                </option>
              ))}
            </select>
            <div className="flex justify-end gap-3 md:col-span-3">
              <button className="secondary-button" type="button" onClick={() => setCreating(false)}>
                Hủy
              </button>
              <button className="apple-button" type="submit">
                Tạo liên kết
              </button>
            </div>
          </form>
        </Modal>
      )}
      <Panel title="Liên kết yêu cầu và ca kiểm thử">
        <DataTable
          items={matrix.trace_links || []}
          empty="Chưa có liên kết giữa yêu cầu và ca kiểm thử"
          columns={[
            {
              key: "source_id",
              label: "Yêu cầu",
              minWidth: 200,
              render: (item) => {
                const sourceEvidence = item.evidence?.find(
                  (evidence) => evidence.artifact_version_id === item.source_id,
                );
                return (
                  <div className="space-y-1">
                    <span className="font-medium">
                      {item.source_label || "Yêu cầu không còn khả dụng"}
                    </span>
                    <p className="text-xs text-ink-muted">{valueLabel(item.source_type)}</p>
                    {sourceEvidence?.text && (
                      <p
                        className="line-clamp-2 text-xs leading-5 text-ink-muted"
                        title={sourceEvidence.text}
                      >
                        {sourceEvidence.text}
                      </p>
                    )}
                  </div>
                );
              },
            },
            {
              key: "target_id",
              label: "Ca kiểm thử",
              minWidth: 200,
              render: (item) => (
                <span className="font-medium">
                  {item.target_label || "Ca kiểm thử không còn khả dụng"}
                </span>
              ),
            },
            {
              key: "confidence",
              label: "Độ phù hợp",
              minWidth: 120,
              render: (item) => (
                <div className="space-y-1">
                  <span className="font-medium">
                    {typeof item.confidence === "number"
                      ? `${Math.round(item.confidence * 100)}%`
                      : "Chưa đánh giá"}
                  </span>
                  {item.obsolete && <p className="text-xs text-danger">Cần rà soát lại</p>}
                </div>
              ),
            },
            {
              key: "latest_execution",
              label: "Kết quả gần nhất",
              minWidth: 150,
              render: (item) => {
                const result = coverage.latest_execution?.[item.target_id];
                const defectCount = (matrix.defects || []).filter(
                  (defect) => defect.linked_test_case_version_id === item.target_id,
                ).length;
                return (
                  <div className="space-y-1">
                    {result ? <StatusPill value={result.status} /> : "Chưa chạy"}
                    <p className="text-xs text-ink-muted">
                      {defectCount ? `${defectCount} lỗi đang mở` : "Không có lỗi đang mở"}
                    </p>
                  </div>
                );
              },
            },
            {
              key: "status",
              label: "Trạng thái",
              minWidth: 120,
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "decision",
              label: "Thao tác",
              minWidth: 190,
              hideWhenEmpty: true,
              render: (item) =>
                item.status === "SUGGESTED" && (can("trace.confirm") || can("trace.review")) ? (
                  <span className="flex flex-nowrap gap-2">
                    {can("trace.confirm") && (
                      <button
                        aria-label="Xác nhận liên kết truy vết"
                        title="Xác nhận liên kết"
                        className="icon-button h-9 w-9"
                        type="button"
                        onClick={() => decision(item, true)}
                      >
                        <Check aria-hidden="true" size={16} />
                      </button>
                    )}
                    {can("trace.review") && (
                      <button
                        aria-label="Từ chối liên kết truy vết"
                        title="Từ chối liên kết"
                        className="icon-button h-9 w-9"
                        type="button"
                        onClick={() => decision(item, false)}
                      >
                        <X aria-hidden="true" size={16} />
                      </button>
                    )}
                  </span>
                ) : item.status === "CONFIRMED" && can("trace.revoke") ? (
                  <button
                    aria-label="Thu hồi liên kết truy vết"
                    title="Thu hồi liên kết"
                    className="icon-button h-9 w-9"
                    type="button"
                    onClick={async () => {
                      try {
                        await testingApi.revokeTrace(item._id);
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    <RotateCcw aria-hidden="true" size={16} />
                  </button>
                ) : (
                  ""
                ),
            },
          ]}
        />
      </Panel>
      {can("coverage.read") && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Yêu cầu chưa liên kết ca kiểm thử">
            <DataTable
              items={coverage.uncovered_requirements || []}
              empty="Tất cả yêu cầu hiện hành đã có liên kết xác nhận"
              columns={[
                { key: "requirement_key", label: "Mã" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
              ]}
            />
          </Panel>
          <Panel title="Ca kiểm thử chưa liên kết">
            <DataTable
              items={coverage.unlinked_tests || []}
              empty="Tất cả ca kiểm thử hiện hành đã được liên kết"
              columns={[
                { key: "test_case_key", label: "Mã" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
              ]}
            />
          </Panel>
        </div>
      )}
      {can("coverage.read") && (
        <Panel title="Lịch sử mốc độ phủ">
          <DataTable
            items={snapshots}
            empty="Chưa lưu mốc độ phủ nào"
            columns={[
              { key: "label", label: "Tên" },
              {
                key: "requirement_coverage",
                label: "Yêu cầu",
                render: (item) => `${item.metrics?.requirement_coverage || 0}%`,
              },
              {
                key: "fresh_coverage",
                label: "Còn hiệu lực",
                render: (item) => `${item.metrics?.fresh_coverage || 0}%`,
              },
              {
                key: "execution_coverage",
                label: "Thực thi",
                render: (item) => `${item.metrics?.execution_coverage || 0}%`,
              },
              {
                key: "created_at",
                label: "Thời điểm",
                render: (item) => formatDate(item.created_at),
              },
            ]}
          />
        </Panel>
      )}
      {dialog}
    </WorkspacePage>
  );
}
