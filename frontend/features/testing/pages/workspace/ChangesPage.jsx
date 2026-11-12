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

const IMPACT_LIMITATION_LABELS = {
  NO_CONFIRMED_TRACE_LINKS_FOUND: "Chưa tìm thấy liên kết truy vết đã xác nhận.",
  STALE_TRACE_LINKS_REQUIRE_REVIEW: "Có liên kết truy vết cũ cần được rà soát.",
  SCOPE_TRUNCATED_ACCEPTANCE_CRITERIA: "Số tiêu chí vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TRACE_LINKS: "Số liên kết truy vết vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_SCENARIOS: "Số kịch bản vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_CASES: "Số Test Case vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_CASE_VERSIONS: "Số phiên bản Test Case vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_CASE_VERSION_IDS: "Số phiên bản Test Case liên quan vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_PLANS: "Số Test Plan vượt giới hạn xử lý.",
  SCOPE_TRUNCATED_TEST_RUNS: "Số Test Run vượt giới hạn xử lý.",
};

function impactLimitationMessage(limitation) {
  if (IMPACT_LIMITATION_LABELS[limitation]) return IMPACT_LIMITATION_LABELS[limitation];
  return valueLabel(limitation);
}

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
      if (reason?.code === "IMPACT_SOURCE_CHANGED") {
        setImpact((current) => (current ? { ...current, source_stale: true } : current));
      }
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
      if (reason?.code === "IMPACT_SOURCE_CHANGED") {
        setImpact((current) => (current ? { ...current, source_stale: true } : current));
      }
      setError(messageOf(reason));
    } finally {
      setActionBusy(false);
    }
  };

  const rerunSelectedImpact = async () => {
    if (!impact || !impact.source_stale || !can("impact.execute") || !can("ai.run_impact")) {
      return;
    }
    setActionBusy(true);
    setError("");
    try {
      await testingApi.rerunImpact(impact._id, {
        expected_revision: impact.revision,
        reason: "Nguồn hoặc liên kết truy vết đã thay đổi sau lần phân tích.",
      });
      setImpact(await testingApi.getChangeSetImpact(selected._id));
      setRegression(null);
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
        <div
          className={`mx-auto grid w-full min-w-0 max-w-7xl gap-5 lg:items-start ${sets.length || selected ? "lg:grid-cols-2" : "lg:grid-cols-1"}`}
        >
          <div className="min-w-0 lg:sticky lg:top-4">
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
                    align: "center",
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
          </div>
          <div className="min-w-0 space-y-5">
            {selected && (
              <div className="min-w-0 space-y-5">
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
                  {(selected.changes || []).length ? (
                    <div className="divide-y divide-border">
                      {selected.changes.map((item, index) => (
                        <article className="min-w-0 px-4 py-4" key={`${item.subject}-${index}`}>
                          <div className="flex min-w-0 flex-wrap items-center gap-2">
                            <h3 className="min-w-0 break-words text-sm font-semibold text-ink">
                              {item.subject || "Nội dung thay đổi"}
                            </h3>
                            <StatusPill value={item.type} />
                            {(item.wording_only || item.type === "TEXT_ONLY") && (
                              <span className="text-xs text-ink-muted">Chỉ đổi cách diễn đạt</span>
                            )}
                          </div>
                          <dl className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">
                            <div className="min-w-0">
                              <dt className="mb-1 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
                                Trước
                              </dt>
                              <dd className="min-w-0 break-words rounded-control bg-surface-quiet/60 px-3 py-2 text-[13px] leading-5 text-ink">
                                <StructuredValueView value={item.before} />
                              </dd>
                            </div>
                            <div className="min-w-0">
                              <dt className="mb-1 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
                                Sau
                              </dt>
                              <dd className="min-w-0 break-words rounded-control bg-brand/5 px-3 py-2 text-[13px] leading-5 text-ink">
                                <StructuredValueView value={item.after} />
                              </dd>
                            </div>
                          </dl>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="px-4 py-5 text-sm text-ink-muted" role="status">
                      Không phát hiện khác biệt nội dung
                    </p>
                  )}
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
                        {
                          key: "reasons",
                          label: "Căn cứ",
                          render: (item) => item.reasons?.join("; "),
                        },
                      ]}
                    />
                  </Panel>
                )}
              </div>
            )}

            {!selected && sets.length > 0 && (
              <Panel title="Chi tiết thay đổi">
                <p className="px-4 py-5 text-sm text-ink-muted" role="status">
                  Chọn một thay đổi trong danh sách để xem nội dung và tác động kiểm thử.
                </p>
              </Panel>
            )}

            {impact && (
              <Panel
                title={`Kết quả phân tích ảnh hưởng lần ${impact.snapshot_number || 1}`}
                actions={
                  impact.source_stale && can("impact.execute") && can("ai.run_impact") ? (
                    <button
                      className="primary-button"
                      disabled={actionBusy}
                      onClick={rerunSelectedImpact}
                      type="button"
                    >
                      {actionBusy ? "Đang phân tích…" : "Chạy lại phân tích"}
                    </button>
                  ) : impact.status === "REVIEW_READY" &&
                    can("impact.close") &&
                    can("impact.review") ? (
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
                {impact.source_stale && (
                  <div
                    className="border-b border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"
                    role="alert"
                  >
                    Nguồn hoặc liên kết truy vết đã đổi sau lần phân tích. Không thể duyệt kết quả
                    cũ; hãy chạy lại phân tích.
                  </div>
                )}
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
                    {
                      key: "reasons",
                      label: "Bằng chứng",
                      render: (item) => item.reasons?.join("; "),
                    },
                  ]}
                />
                {impact.impact_limitations?.length > 0 && (
                  <div
                    className="border-t border-border px-4 py-3 text-sm text-ink-muted"
                    role="status"
                  >
                    {impact.scope_complete === false && (
                      <p className="mb-2 font-medium text-ink">
                        Phân tích chỉ bao phủ một phần dữ liệu. Chưa thể kết luận rằng danh sách ảnh
                        hưởng đã đầy đủ.
                      </p>
                    )}
                    <ul className="list-disc space-y-1 pl-5">
                      {impact.impact_limitations.map((limitation) => (
                        <li key={limitation}>{impactLimitationMessage(limitation)}</li>
                      ))}
                    </ul>
                    {impact.scope_complete === false && (
                      <p className="mt-2">
                        Hãy chia nhỏ phạm vi thay đổi rồi chạy phân tích cho từng phần.
                      </p>
                    )}
                  </div>
                )}
                <div className="grid min-w-0 gap-4 border-t border-border p-4">
                  <section aria-label="Kịch bản kiểm thử bị ảnh hưởng">
                    <h3 className="mb-2 text-sm font-semibold text-ink">Kịch bản cần rà soát</h3>
                    <DataTable
                      items={impact.affected_test_scenarios || []}
                      empty="Không tìm thấy kịch bản liên kết trực tiếp với phiên bản yêu cầu này"
                      columns={[
                        { key: "name", label: "Kịch bản" },
                        {
                          key: "status",
                          label: "Trạng thái",
                          render: (item) => <StatusPill value={item.status} />,
                        },
                        {
                          key: "related_test_case_version_ids",
                          label: "Ca liên quan",
                          render: (item) => item.related_test_case_version_ids?.length || 0,
                        },
                        {
                          key: "reasons",
                          label: "Căn cứ",
                          render: (item) => item.reasons?.map(valueLabel).join("; "),
                        },
                      ]}
                    />
                  </section>
                  <section aria-label="Kế hoạch kiểm thử bị ảnh hưởng">
                    <h3 className="mb-2 text-sm font-semibold text-ink">Kế hoạch cần xem lại</h3>
                    <DataTable
                      items={impact.affected_test_plans || []}
                      empty="Không tìm thấy kế hoạch có chứa phiên bản yêu cầu hoặc ca bị ảnh hưởng"
                      columns={[
                        { key: "name", label: "Kế hoạch" },
                        {
                          key: "status",
                          label: "Trạng thái",
                          render: (item) => <StatusPill value={item.status} />,
                        },
                        {
                          key: "related_test_case_version_ids",
                          label: "Ca liên quan",
                          render: (item) => item.related_test_case_version_ids?.length || 0,
                        },
                        {
                          key: "reasons",
                          label: "Căn cứ",
                          render: (item) => item.reasons?.map(valueLabel).join("; "),
                        },
                      ]}
                    />
                  </section>
                  <section aria-label="Lượt chạy kiểm thử có phạm vi liên quan">
                    <h3 className="mb-2 text-sm font-semibold text-ink">
                      Lượt chạy có phạm vi liên quan
                    </h3>
                    <p className="mb-2 text-xs text-ink-muted">
                      Đây là bản ghi lịch sử. Phân tích không sửa kết quả hoặc phạm vi của lượt chạy
                      đã tạo.
                    </p>
                    <DataTable
                      items={impact.affected_test_runs || []}
                      empty="Không tìm thấy lượt chạy có snapshot liên quan đến thay đổi này"
                      columns={[
                        { key: "name", label: "Lượt chạy" },
                        {
                          key: "execution_status",
                          label: "Trạng thái",
                          render: (item) => <StatusPill value={item.execution_status} />,
                        },
                        {
                          key: "test_plan_id",
                          label: "Có kế hoạch",
                          render: (item) => (item.test_plan_id ? "Có" : "Không"),
                        },
                        {
                          key: "related_test_case_version_ids",
                          label: "Ca liên quan",
                          render: (item) => item.related_test_case_version_ids?.length || 0,
                        },
                        {
                          key: "reasons",
                          label: "Căn cứ",
                          render: (item) => item.reasons?.map(valueLabel).join("; "),
                        },
                      ]}
                    />
                  </section>
                </div>
              </Panel>
            )}
          </div>
        </div>
      )}
      {(can("automation.read") || can("proposal.read")) && (
        <Panel className="mt-5" title="Nhật ký AI">
          <div className="flex flex-wrap items-center justify-between gap-3 p-4">
            <p className="text-sm text-ink-muted">
              Xem các lượt AI đã chạy trong dự án, kể cả những lượt chưa gắn với thay đổi yêu cầu.
            </p>
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
