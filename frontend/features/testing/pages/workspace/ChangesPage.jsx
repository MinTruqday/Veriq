"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import DataTable from "../../components/DataTable";
import {
  DegradedBanner,
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  StatusPill,
  WorkspacePage,
} from "../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../lib/testing";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";
import { testingApi } from "../../services/testing.service";
import { StructuredValueView } from "../../components/StructuredValueEditor";

export default function ChangesPage({ project }) {
  const [sets, setSets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [impact, setImpact] = useState(null);
  const [regression, setRegression] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [filters, setFilters] = useState({ requirement_id: "", status: "", sort: "-created_at" });
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const can = useCallback(
    (permission) => project.current_permissions?.includes(permission),
    [project.current_permissions],
  );

  const load = useCallback(async () => {
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      if (!can("changeset.read")) {
        setSets([]);
      } else {
        const result = await testingApi.listChangeSets(project._id, filters);
        setSets(Array.isArray(result) ? result : result.items || []);
      }
      setError("");
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [can, filters, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  const openChangeSet = async (item, { clearError = true } = {}) => {
    try {
      const detail = await testingApi.getChangeSet(item._id);
      setSelected(detail);
      setImpact(null);
      setRegression(null);
      if (can("impact.read") && ["ANALYZED", "REVIEWED"].includes(detail.status)) {
        try {
          const analysis = await testingApi.getChangeSetImpact(item._id);
          setImpact(analysis);
          if (analysis.status === "REVIEWED" && can("regression.read")) {
            try {
              setRegression(await testingApi.getChangeSetRegression(item._id));
            } catch (reason) {
              if (reason.status !== 404) throw reason;
            }
          }
        } catch (reason) {
          if (reason.status !== 404) throw reason;
        }
      }
      if (clearError) setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const reviewSelectedChangeSet = async () => {
    if (!selected || selected.status !== "READY" || !can("changeset.review")) return;
    setActionBusy(true);
    setError("");
    try {
      const updated = await testingApi.reviewChangeSet(selected._id, {
        expected_revision: selected.revision,
        changes: selected.changes || [],
        review_note: "",
      });
      const reviewed = { ...selected, ...updated };
      setSelected(reviewed);
      await load();
      await openChangeSet(reviewed, { clearError: false });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setActionBusy(false);
    }
  };

  const analyzeSelectedImpact = async () => {
    if (
      !selected ||
      !["REVIEWED", "ANALYZED"].includes(selected.status) ||
      !can("impact.execute") ||
      !can("ai.run_impact")
    ) {
      return;
    }
    setActionBusy(true);
    setError("");
    try {
      await testingApi.analyzeImpact(selected._id);
      setImpact(await testingApi.getChangeSetImpact(selected._id));
      setRegression(null);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setActionBusy(false);
    }
  };

  const reviewSelectedImpact = async () => {
    if (
      !impact ||
      impact.status !== "REVIEW_READY" ||
      !can("impact.close") ||
      !can("impact.review")
    ) {
      return;
    }
    setActionBusy(true);
    setError("");
    try {
      const updated = await testingApi.reviewImpact(impact._id, {
        expected_revision: impact.revision,
        overrides: [],
        review_note: "",
      });
      setImpact(await testingApi.getImpact(updated._id));
      if (can("regression.read")) {
        try {
          setRegression(await testingApi.getChangeSetRegression(selected._id));
        } catch (reason) {
          if (reason.status !== 404) throw reason;
        }
      }
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setActionBusy(false);
    }
  };

  if (initialLoading || initialLoadFailed) {
    return (
      <InitialLoadState
        title="Phân tích thay đổi"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  }

  return (
    <WorkspacePage title="Phân tích thay đổi" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      {can("changeset.read") && (
        <Panel title="Lịch sử thay đổi yêu cầu">
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium text-ink">
              Lọc và sắp xếp
            </summary>
            <div className="mt-3 grid min-w-0 gap-3 md:grid-cols-3">
              <input
                aria-label="Lọc thay đổi theo yêu cầu"
                className="apple-input min-w-0 w-full"
                placeholder="Mã yêu cầu"
                value={filters.requirement_id}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, requirement_id: event.target.value }))
                }
              />
              <select
                aria-label="Lọc trạng thái thay đổi"
                className="apple-input min-w-0 w-full"
                value={filters.status}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, status: event.target.value }))
                }
              >
                <option value="">Mọi trạng thái</option>
                {["READY", "REVIEWED", "ANALYZED"].map((value) => (
                  <option value={value} key={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sắp xếp thay đổi"
                className="apple-input min-w-0 w-full"
                value={filters.sort}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, sort: event.target.value }))
                }
              >
                <option value="-created_at">Mới nhất</option>
                <option value="created_at">Cũ nhất</option>
                <option value="requirement_id">Theo yêu cầu</option>
              </select>
            </div>
          </details>
          <DataTable
            onSelect={openChangeSet}
            items={sets}
            empty="Chưa có thay đổi yêu cầu được ghi nhận"
            emptyActionHref={
              can("requirement.read")
                ? projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements)
                : undefined
            }
            emptyActionLabel="Mở yêu cầu"
            columns={[
              { key: "requirement_label", label: "Yêu cầu" },
              {
                key: "versions",
                label: "Phiên bản",
                render: (item) =>
                  item.from_version_label && item.to_version_label
                    ? `${item.from_version_label} → ${item.to_version_label}`
                    : "Chưa xác định",
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              { key: "summary", label: "Tóm tắt" },
            ]}
          />
        </Panel>
      )}

      {selected && (
        <div className="grid min-w-0 gap-5 2xl:grid-cols-2">
          <Panel
            title="Nội dung thay đổi"
            actions={
              <>
                {selected.status === "READY" && can("changeset.review") && (
                  <button
                    className="primary-button"
                    disabled={actionBusy || !(selected.changes || []).length}
                    onClick={reviewSelectedChangeSet}
                    type="button"
                  >
                    {actionBusy ? "Đang lưu…" : "Duyệt thay đổi"}
                  </button>
                )}
                {["REVIEWED", "ANALYZED"].includes(selected.status) &&
                  !impact &&
                  can("impact.execute") &&
                  can("ai.run_impact") && (
                    <button
                      className="primary-button"
                      disabled={actionBusy}
                      onClick={analyzeSelectedImpact}
                      type="button"
                    >
                      {actionBusy ? "Đang phân tích…" : "Phân tích ảnh hưởng"}
                    </button>
                  )}
              </>
            }
          >
            <DataTable
              items={selected.changes || []}
              empty="Không phát hiện khác biệt nội dung"
              columns={[
                { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
                { key: "subject", label: "Trường thay đổi" },
                {
                  key: "before",
                  label: "Trước",
                  render: (item) => <StructuredValueView value={item.before} />,
                },
                {
                  key: "after",
                  label: "Sau",
                  render: (item) => <StructuredValueView value={item.after} />,
                },
                {
                  key: "wording_only",
                  label: "Chỉ đổi cách diễn đạt",
                  render: (item) =>
                    item.wording_only || item.type === "TEXT_ONLY" ? "Có" : "Không",
                },
              ]}
            />
          </Panel>

          {!impact && ["READY", "REVIEWED"].includes(selected.status) && (
            <Panel title="Ảnh hưởng đến kiểm thử">
              <p className="p-4 text-sm text-ink-muted" role="status">
                {selected.status === "READY"
                  ? "Cần duyệt nội dung thay đổi trước khi phân tích ảnh hưởng."
                  : can("impact.execute") && can("ai.run_impact")
                    ? "Chưa có kết quả phân tích ảnh hưởng cho thay đổi này."
                    : "Bạn không có quyền chạy phân tích ảnh hưởng."}
              </p>
            </Panel>
          )}

          {can("regression.read") && (
            <Panel title="Tác động đến kiểm thử hồi quy">
              <DataTable
                items={regression?.items || []}
                empty="Chưa có kết quả phân tích hồi quy cho thay đổi này"
                columns={[
                  { key: "test_case_key", label: "Ca kiểm thử" },
                  {
                    key: "level",
                    label: "Mức ảnh hưởng",
                    render: (item) => <StatusPill value={item.level} />,
                  },
                  { key: "reasons", label: "Căn cứ", render: (item) => item.reasons?.join("; ") },
                ]}
              />
            </Panel>
          )}
        </div>
      )}

      {impact && (
        <Panel
          title={`Kết quả phân tích ảnh hưởng lần ${impact.snapshot_number || 1}`}
          actions={
            impact.status === "REVIEW_READY" && can("impact.close") && can("impact.review") ? (
              <button
                className="primary-button"
                disabled={actionBusy}
                onClick={reviewSelectedImpact}
                type="button"
              >
                {actionBusy ? "Đang lưu…" : "Xác nhận đã rà soát"}
              </button>
            ) : null
          }
        >
          <div className="border-b border-border px-4 py-3 text-sm text-ink-muted">
            Trạng thái: <StatusPill value={impact.status} />
          </div>
          {impact.mode === "DEGRADED_AI" && (
            <div className="p-4 pb-0">
              <DegradedBanner
                mode="DEGRADED_AI"
                message="Kết quả AI chưa đầy đủ. Chỉ dùng kết quả và căn cứ đã ghi nhận; xem hoạt động AI để biết nguyên nhân."
              />
            </div>
          )}
          <DataTable
            items={impact.reviewed_affected_test_cases || impact.affected_test_cases || []}
            empty="Không có ca kiểm thử nào được xác định là bị ảnh hưởng"
            columns={[
              { key: "test_case_key", label: "Ca kiểm thử" },
              {
                key: "classification",
                label: "Phân loại",
                render: (item) => <StatusPill value={item.classification} />,
              },
              { key: "confidence", label: "Mức tin cậy" },
              { key: "reasons", label: "Bằng chứng", render: (item) => item.reasons?.join("; ") },
            ]}
          />
        </Panel>
      )}

      {(can("automation.read") || can("proposal.read")) && (
        <Panel title="Nhật ký AI">
          <div className="p-4">
            <Link
              className="secondary-button"
              href={projectRoute(project._id, PROJECT_SECTION_SLUGS.aiReview)}
            >
              Mở nhật ký AI
            </Link>
          </div>
        </Panel>
      )}
    </WorkspacePage>
  );
}
