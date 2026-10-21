"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ProposalDiffPanel from "../../components/ProposalDiffPanel";
import {
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
} from "../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";

function EvidenceList({ items }) {
  if (!items?.length) return <span className="text-ink-muted">Chưa có bằng chứng</span>;

  return (
    <ul className="grid min-w-56 max-w-md gap-2">
      {items.map((evidence, index) => (
        <li
          className="min-w-0 rounded-control bg-surface-quiet p-3"
          key={`${evidence.artifact_id || evidence.artifact_type}-${index}`}
        >
          <p className="break-words text-xs font-semibold text-ink">
            {[valueLabel(evidence.artifact_type), evidence.artifact_id].filter(Boolean).join(" · ")}
          </p>
          {evidence.artifact_version_id && (
            <p className="mt-1 break-all text-[11px] text-ink-muted">
              Phiên bản: {evidence.artifact_version_id}
            </p>
          )}
          {evidence.text && (
            <p className="mt-2 whitespace-pre-wrap break-words text-xs leading-5 text-ink-muted">
              {evidence.text}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function ReviewQueuePage({ project }) {
  const [items, setItems] = useState([]);
  const [filters, setFilters] = useState({
    status: "",
    proposal_type: "",
    target_artifact_id: "",
    sort: "-created_at",
  });
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);

  const load = useCallback(async () => {
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      setItems(await testingApi.listProposals(project._id, filters));
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [filters, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (initialLoading || initialLoadFailed) {
    return (
      <InitialLoadState
        title="Đề xuất AI"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  }

  return (
    <WorkspacePage title="Đề xuất AI" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      <Panel title="Danh sách đề xuất">
        <details className="border-b border-border p-4">
          <summary className="cursor-pointer text-sm font-medium text-ink">Bộ lọc</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <select
              aria-label="Lọc trạng thái đề xuất"
              className="apple-input"
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({ ...current, status: event.target.value }))
              }
            >
              <option value="">Mọi trạng thái</option>
              {["PENDING", "APPROVED", "REJECTED", "APPLY_PARTIAL", "EXPIRED"].map((value) => (
                <option value={value} key={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
            <select
              aria-label="Lọc loại đề xuất"
              className="apple-input"
              value={filters.proposal_type}
              onChange={(event) =>
                setFilters((current) => ({ ...current, proposal_type: event.target.value }))
              }
            >
              <option value="">Mọi loại</option>
              {["UPDATE_TEST_CASE", "CREATE_TEST_CASE", "OBSOLETE_TEST_CASE"].map((value) => (
                <option value={value} key={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
            <input
              aria-label="Lọc đối tượng đề xuất"
              className="apple-input"
              placeholder="Mã đối tượng"
              value={filters.target_artifact_id}
              onChange={(event) =>
                setFilters((current) => ({ ...current, target_artifact_id: event.target.value }))
              }
            />
            <select
              aria-label="Sắp xếp đề xuất"
              className="apple-input"
              value={filters.sort}
              onChange={(event) =>
                setFilters((current) => ({ ...current, sort: event.target.value }))
              }
            >
              <option value="-created_at">Mới nhất</option>
              <option value="created_at">Cũ nhất</option>
              <option value="-confidence">Mức hỗ trợ cao</option>
            </select>
          </div>
        </details>
        <DataTable
          items={items}
          empty="Không có đề xuất phù hợp"
          columns={[
            { key: "proposal_type", label: "Loại" },
            { key: "test_case_key", label: "Đối tượng" },
            {
              key: "base_version",
              label: "Phiên bản gốc",
              render: (item) =>
                item.base_version
                  ? `${item.test_case_key || "Ca kiểm thử"} phiên bản ${item.base_version.version}`
                  : "Đề xuất tạo mới",
            },
            {
              key: "impact_analysis",
              label: "Phân tích thay đổi",
              render: (item) =>
                item.impact_analysis
                  ? `Lần phân tích ${item.impact_analysis.snapshot_number || 1}`
                  : "Không có",
            },
            {
              key: "confidence",
              label: "Mức hỗ trợ",
              render: (item) => `${item.confidence ?? 0} điểm`,
            },
            { key: "reason", label: "Căn cứ" },
            {
              key: "evidence",
              label: "Bằng chứng",
              render: (item) => <EvidenceList items={item.evidence} />,
            },
            {
              key: "diff",
              label: "Thay đổi đề xuất",
              render: (item) => <ProposalDiffPanel proposal={item} />,
            },
            { key: "model_version", label: "Mô hình" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
          ]}
        />
      </Panel>
    </WorkspacePage>
  );
}
