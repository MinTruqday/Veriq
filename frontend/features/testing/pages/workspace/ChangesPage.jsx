"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ProposalDiffPanel from "../../components/ProposalDiffPanel";
import {
  DegradedBanner,
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { messageOf, valueLabel } from "../../lib/testing";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

export default function ChangesPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [sets, setSets] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [selectedProposalIds, setSelectedProposalIds] = useState([]);
  const [selected, setSelected] = useState(null);
  const [impact, setImpact] = useState(null);
  const [regression, setRegression] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [changeFacts, setChangeFacts] = useState([]);
  const [aiAction, setAiAction] = useState("");
  const [filters, setFilters] = useState({
    requirement_id: "",
    status: "",
    sort: "-created_at",
  });
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
      const [changeValues, proposalValues] = await Promise.all([
        can("changeset.read")
          ? testingApi.listChangeSets(project._id, filters)
          : Promise.resolve([]),
        can("proposal.read") ? testingApi.listProposals(project._id) : Promise.resolve([]),
      ]);
      setSets(Array.isArray(changeValues) ? changeValues : changeValues.items || []);
      setProposals(proposalValues);
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
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Phân tích thay đổi"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  const openChangeSet = async (item) => {
    try {
      const value = await testingApi.getChangeSet(item._id);
      setSelected(value);
      setChangeFacts(value.changes || []);
      setImpact(null);
      setRegression(null);
      if (can("impact.read") && ["ANALYZED", "REVIEWED"].includes(value.status)) {
        try {
          const result = await testingApi.getChangeSetImpact(item._id);
          setImpact(result);
          setOverrides({});
          if (result.status === "REVIEWED" && can("regression.read")) {
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
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const analyze = async () => {
    setAiAction("impact");
    try {
      const result = await testingApi.analyzeImpact(selected._id);
      setSelected(await testingApi.getChangeSet(selected._id));
      setImpact(result);
      setOverrides({});
      setRegression(
        result.status === "REVIEWED" && can("regression.read")
          ? await testingApi.getChangeSetRegression(selected._id)
          : null,
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  const decide = async (item, action) => {
    const fields = [
      {
        name: "note",
        label: action === "reject" ? "Lý do từ chối" : "Ghi chú rà soát",
        initialValue:
          action === "reject" ? "Không phù hợp với ý định kiểm thử" : "Đã rà soát bằng chứng",
        required: true,
        multiline: true,
        autoFocus: true,
      },
    ];
    if (action === "edit")
      fields.push({
        name: "patch",
        label: "Nội dung đề xuất sau chỉnh sửa dạng JSON",
        initialValue: JSON.stringify(item.patch, null, 2),
        required: true,
        multiline: true,
      });
    const answer = await ask({
      title: action === "reject" ? "Từ chối đề xuất bảo trì" : "Chấp nhận đề xuất bảo trì",
      description: `${item.test_case_key || item.test_case_id} tạo phiên bản mới khi được chấp nhận`,
      confirmLabel: action === "reject" ? "Từ chối" : "Chấp nhận",
      danger: action === "reject",
      fields,
    });
    if (!answer) return;
    try {
      if (action === "reject")
        await testingApi.rejectProposal(item._id, {
          expected_revision: item.revision,
          review_note: answer.note,
        });
      else {
        let patch = null;
        if (action === "edit") {
          try {
            patch = JSON.parse(answer.patch);
          } catch {
            setError("Nội dung chỉnh sửa phải là JSON hợp lệ");
            return;
          }
        }
        await testingApi.acceptProposal(
          item._id,
          {
            expected_revision: item.revision,
            review_note: answer.note,
            patch,
          },
          action === "edit",
        );
      }
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const reviewImpact = async () => {
    const answer = await ask({
      title: "Duyệt phân tích ảnh hưởng",
      description: `${impact.affected_test_cases?.length || 0} ca kiểm thử sẽ được chốt phân loại`,
      confirmLabel: "Duyệt phân tích",
      fields: [
        {
          name: "note",
          label: "Ghi chú duyệt",
          initialValue: "Đã kiểm tra bằng chứng và phân loại",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
    });
    if (!answer) return;
    setAiAction("review");
    try {
      const items = impact.affected_test_cases || [];
      const payload = items
        .filter((item) => overrides[item.test_case_version_id])
        .map((item) => ({
          test_case_version_id: item.test_case_version_id,
          classification: overrides[item.test_case_version_id],
          reason: "Người rà soát điều chỉnh từ giao diện",
        }));
      const reviewed = await testingApi.reviewImpact(impact._id, {
        expected_revision: impact.revision,
        overrides: payload,
        review_note: answer.note,
      });
      setImpact(reviewed);
      if (can("ai.create_proposal")) await testingApi.createProposals(reviewed._id);
      if (can("regression.generate") && can("ai.generate_regression") && can("regression.read")) {
        setRegression(await testingApi.regression(selected._id));
      }
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  const rerunImpact = async () => {
    const answer = await ask({
      title: "Chạy lại phân tích ảnh hưởng",
      description: `Lần phân tích ${impact.snapshot_number || 1} vẫn được giữ nguyên để đối chiếu`,
      confirmLabel: "Tạo lần phân tích mới",
      fields: [
        {
          name: "reason",
          label: "Lý do chạy lại",
          initialValue: "Dữ liệu truy vết hoặc chỉ mục tri thức đã thay đổi",
          required: true,
          multiline: true,
          autoFocus: true,
        },
        {
          name: "knowledge_index_version",
          label: "Phiên bản chỉ mục tri thức nếu có",
          initialValue: impact.knowledge_index_version || "",
        },
      ],
    });
    if (!answer) return;
    setAiAction("rerun");
    try {
      const result = await testingApi.rerunImpact(impact._id, {
        expected_revision: impact.revision,
        reason: answer.reason,
        knowledge_index_version: answer.knowledge_index_version || null,
        algorithm_version: "impact_pipeline",
      });
      setImpact(result);
      setOverrides({});
      setRegression(null);
      setSelected(await testingApi.getChangeSet(selected._id));
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  return (
    <WorkspacePage title="Phân tích thay đổi" actions={<ProjectCrumb projectId={project._id} />}>
      {error && <ErrorState message={error} />}
      {can("changeset.read") && (
        <Panel title="Bộ thay đổi">
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium text-ink">Bộ lọc</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <input
                aria-label="Lọc bộ thay đổi theo yêu cầu"
                className="apple-input"
                placeholder="Mã yêu cầu"
                value={filters.requirement_id}
                onChange={(event) => setFilters({ ...filters, requirement_id: event.target.value })}
              />
              <select
                aria-label="Lọc trạng thái bộ thay đổi"
                className="apple-input"
                value={filters.status}
                onChange={(event) => setFilters({ ...filters, status: event.target.value })}
              >
                <option value="">Mọi trạng thái</option>
                {["READY", "REVIEWED", "ANALYZED"].map((value) => (
                  <option value={value} key={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sắp xếp bộ thay đổi"
                className="apple-input"
                value={filters.sort}
                onChange={(event) => setFilters({ ...filters, sort: event.target.value })}
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
            empty="Chưa có bộ thay đổi"
            emptyActionHref={
              can("requirement.read")
                ? projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements)
                : undefined
            }
            emptyActionLabel="Mở danh sách yêu cầu"
            columns={[
              { key: "requirement_label", label: "Yêu cầu" },
              {
                key: "versions",
                label: "Phiên bản",
                render: (item) =>
                  item.from_version_label && item.to_version_label
                    ? `${item.from_version_label} đến ${item.to_version_label}`
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
        <div className="grid gap-5 xl:grid-cols-2">
          <Panel
            title="So sánh thay đổi"
            actions={
              selected.status === "READY" && can("changeset.review") ? (
                <button
                  className="apple-button"
                  type="button"
                  onClick={async () => {
                    try {
                      const value = await testingApi.reviewChangeSet(selected._id, {
                        expected_revision: selected.revision,
                        changes: changeFacts,
                        review_note: "Đã xác nhận chi tiết thay đổi trên giao diện",
                      });
                      setSelected(value);
                      setChangeFacts(value.changes);
                      await load();
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Xác nhận chi tiết thay đổi
                </button>
              ) : selected.status === "REVIEWED" &&
                can("impact.execute") &&
                can("ai.run_impact") ? (
                <button
                  aria-busy={aiAction === "impact"}
                  className="apple-button"
                  disabled={Boolean(aiAction)}
                  type="button"
                  onClick={analyze}
                >
                  {aiAction === "impact" ? "AI đang phân tích ảnh hưởng" : "Phân tích ảnh hưởng"}
                </button>
              ) : null
            }
          >
            <DataTable
              items={changeFacts.map((item, index) => ({ ...item, _id: index, factIndex: index }))}
              empty="Không phát hiện thay đổi ngữ nghĩa"
              columns={[
                {
                  key: "type",
                  label: "Loại",
                  render: (item) =>
                    selected.status === "READY" && can("changeset.review") ? (
                      <select
                        aria-label={`Loại thay đổi ${item.factIndex + 1}`}
                        className="apple-input min-w-48"
                        value={item.type}
                        onChange={(event) =>
                          setChangeFacts((values) =>
                            values.map((value, index) =>
                              index === item.factIndex
                                ? { ...value, type: event.target.value }
                                : value,
                            ),
                          )
                        }
                      >
                        {[
                          "TEXT_ONLY",
                          "MODIFIED_INPUT",
                          "MODIFIED_BOUNDARY",
                          "MODIFIED_PERMISSION",
                          "MODIFIED_ERROR",
                          "ADDED_BEHAVIOR",
                          "REMOVED_BEHAVIOR",
                        ].map((value) => (
                          <option key={value} value={value}>
                            {valueLabel(value)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      valueLabel(item.type)
                    ),
                },
                { key: "subject", label: "Đối tượng" },
                { key: "before", label: "Trước", render: (item) => JSON.stringify(item.before) },
                { key: "after", label: "Sau", render: (item) => JSON.stringify(item.after) },
                {
                  key: "wording_only",
                  label: "Chỉ đổi cách diễn đạt",
                  render: (item) => {
                    const wordingOnly = item.wording_only || item.type === "TEXT_ONLY";
                    return can("changeset.review") && selected.status === "READY" ? (
                      <input
                        aria-label={`Chỉ đổi cách diễn đạt ${item.factIndex + 1}`}
                        type="checkbox"
                        checked={wordingOnly}
                        onChange={(event) =>
                          setChangeFacts((values) =>
                            values.map((value, index) =>
                              index === item.factIndex
                                ? {
                                    ...value,
                                    wording_only: event.target.checked,
                                    type: event.target.checked ? "TEXT_ONLY" : value.type,
                                  }
                                : value,
                            ),
                          )
                        }
                      />
                    ) : wordingOnly ? (
                      "Có"
                    ) : (
                      "Không"
                    );
                  },
                },
              ]}
            />
          </Panel>
          {can("regression.read") && (
            <Panel title="Khuyến nghị kiểm thử hồi quy">
              <DataTable
                items={regression?.items || []}
                empty="Chưa có khuyến nghị"
                columns={[
                  { key: "test_case_key", label: "Ca kiểm thử" },
                  {
                    key: "level",
                    label: "Khuyến nghị",
                    render: (item) => <StatusPill value={item.level} />,
                  },
                  { key: "reasons", label: "Lý do", render: (item) => item.reasons?.join(", ") },
                ]}
              />
              {regression?.status === "PENDING_APPROVAL" && can("regression.approve") && (
                <div className="border-t border-border p-5">
                  <button
                    className="apple-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Phê duyệt phạm vi hồi quy",
                        description: "Các ca mức bắt buộc và nên chạy sẽ được đưa vào bộ kiểm thử",
                        confirmLabel: "Phê duyệt và tạo bộ",
                        fields: [
                          {
                            name: "note",
                            label: "Ghi chú phê duyệt",
                            initialValue: "Đã kiểm tra mức độ và bằng chứng",
                            required: true,
                            multiline: true,
                            autoFocus: true,
                          },
                        ],
                      });
                      if (!answer) return;
                      try {
                        const value = await testingApi.approveRegression(regression._id, {
                          expected_revision: regression.revision,
                          selected_test_case_version_ids: regression.items
                            .filter((item) => ["MUST_RUN", "SHOULD_RUN"].includes(item.level))
                            .map((item) => item.test_case_version_id),
                          review_note: answer.note,
                        });
                        setRegression(value.recommendation);
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Phê duyệt và tạo bộ kiểm thử
                  </button>
                </div>
              )}
            </Panel>
          )}
        </div>
      )}
      {impact && (
        <Panel
          title={`Phân tích ảnh hưởng lần ${impact.snapshot_number || 1}`}
          actions={
            <div className="flex flex-wrap gap-2">
              {impact.status === "REVIEW_READY" && can("impact.review") && (
                <button
                  aria-busy={aiAction === "review"}
                  className="apple-button"
                  disabled={Boolean(aiAction)}
                  type="button"
                  onClick={reviewImpact}
                >
                  {aiAction === "review" ? "Đang tạo đề xuất và bộ hồi quy" : "Duyệt phân tích"}
                </button>
              )}
              {["REVIEW_READY", "REVIEWED"].includes(impact.status) &&
                can("impact.execute") &&
                can("ai.run_impact") && (
                  <button
                    aria-busy={aiAction === "rerun"}
                    className="secondary-button"
                    disabled={Boolean(aiAction)}
                    type="button"
                    onClick={rerunImpact}
                  >
                    {aiAction === "rerun"
                      ? "AI đang chạy lại phân tích"
                      : "Chạy lại thành lần phân tích mới"}
                  </button>
                )}
            </div>
          }
        >
          <div className="p-5 pb-0">
            <DegradedBanner
              mode={impact.mode === "DEGRADED_AI" ? "DEGRADED_AI" : "NORMAL"}
              message="Mô hình AI không khả dụng nên hệ thống dùng ứng viên trực tiếp ngữ nghĩa và kỹ thuật có thể kiểm chứng"
            />
          </div>
          <DataTable
            items={impact.reviewed_affected_test_cases || impact.affected_test_cases || []}
            columns={[
              { key: "test_case_key", label: "Ca kiểm thử" },
              {
                key: "classification",
                label: "Phân loại",
                render: (item) =>
                  impact.status === "REVIEW_READY" && can("impact.override") ? (
                    <select
                      aria-label={`Phân loại ${item.test_case_key}`}
                      className="apple-input"
                      value={overrides[item.test_case_version_id] || item.classification}
                      onChange={(event) =>
                        setOverrides({
                          ...overrides,
                          [item.test_case_version_id]: event.target.value,
                        })
                      }
                    >
                      {["STILL_VALID", "POTENTIALLY_AFFECTED", "NEEDS_UPDATE", "OBSOLETE"].map(
                        (value) => (
                          <option key={value} value={value}>
                            {valueLabel(value)}
                          </option>
                        ),
                      )}
                    </select>
                  ) : (
                    <StatusPill value={item.classification} />
                  ),
              },
              { key: "confidence", label: "Mức tin cậy" },
              { key: "reasons", label: "Bằng chứng", render: (item) => item.reasons?.join(", ") },
            ]}
          />
        </Panel>
      )}
      {can("proposal.read") && (
        <Panel
          title="Đề xuất bảo trì chờ duyệt"
          actions={
            can("proposal.approve") && selectedProposalIds.length ? (
              <button
                className="apple-button"
                type="button"
                onClick={async () => {
                  const answer = await ask({
                    title: "Duyệt hàng loạt đề xuất an toàn",
                    description: `${selectedProposalIds.length} mục đã chọn sẽ vẫn được kiểm tra ngưỡng chính sách riêng lẻ`,
                    confirmLabel: "Duyệt các mục đạt chính sách",
                    fields: [
                      {
                        name: "note",
                        label: "Ghi chú duyệt",
                        required: true,
                        multiline: true,
                        autoFocus: true,
                      },
                    ],
                  });
                  if (!answer) return;
                  try {
                    await testingApi.bulkApproveProposals(project._id, {
                      proposal_ids: selectedProposalIds,
                      review_note: answer.note,
                      idempotency_key: crypto.randomUUID(),
                    });
                    setSelectedProposalIds([]);
                    await load();
                  } catch (reason) {
                    setError(messageOf(reason));
                  }
                }}
              >
                Duyệt hàng loạt theo chính sách
              </button>
            ) : null
          }
        >
          <DataTable
            items={proposals}
            selectedIds={can("proposal.approve") ? selectedProposalIds : undefined}
            onSelectionChange={can("proposal.approve") ? setSelectedProposalIds : undefined}
            selectionLabel="Chọn đề xuất"
            empty="Không có đề xuất chờ duyệt"
            columns={[
              { key: "test_case_key", label: "Ca kiểm thử" },
              { key: "proposal_type", label: "Loại đề xuất" },
              {
                key: "base_version",
                label: "Phiên bản gốc",
                render: (item) =>
                  item.base_version
                    ? `${item.test_case_key || "Ca kiểm thử"} phiên bản ${item.base_version.version}`
                    : "Đề xuất tạo mới",
              },
              {
                key: "patch",
                label: "Thay đổi đề xuất",
                render: (item) => <ProposalDiffPanel proposal={item} />,
              },
              { key: "reason", label: "Lý do" },
              {
                key: "confidence",
                label: "Mức tin cậy hỗ trợ",
                render: (item) => `${item.confidence ?? 0} điểm cần người duyệt`,
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "decision",
                label: "Quyết định của người duyệt",
                hideWhenEmpty: true,
                render: (item) =>
                  can("proposal.approve") || can("proposal.reject") || can("ai.create_proposal") ? (
                    <span className="flex flex-wrap gap-2">
                      {can("proposal.approve") && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => decide(item, "accept")}
                        >
                          Chấp nhận
                        </button>
                      )}
                      {can("proposal.approve") && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => decide(item, "edit")}
                        >
                          Sửa rồi nhận
                        </button>
                      )}
                      {can("proposal.reject") && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => decide(item, "reject")}
                        >
                          Từ chối
                        </button>
                      )}
                      {can("ai.create_proposal") && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={async () => {
                            const answer = await ask({
                              title: "Yêu cầu tạo lại đề xuất",
                              description:
                                item.test_case_key || item.target_artifact_id || item._id,
                              confirmLabel: "Tạo lại",
                              fields: [
                                {
                                  name: "instruction",
                                  label: "Hướng điều chỉnh",
                                  required: true,
                                  multiline: true,
                                  autoFocus: true,
                                },
                              ],
                            });
                            if (!answer) return;
                            try {
                              await testingApi.regenerateProposal(item._id, {
                                expected_revision: item.revision,
                                instruction: answer.instruction,
                              });
                              await load();
                            } catch (reason) {
                              setError(messageOf(reason));
                            }
                          }}
                        >
                          Tạo lại
                        </button>
                      )}
                    </span>
                  ) : null,
              },
            ]}
          />
        </Panel>
      )}
      {dialog}
    </WorkspacePage>
  );
}
