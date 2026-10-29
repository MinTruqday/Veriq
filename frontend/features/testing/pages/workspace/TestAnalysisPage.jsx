"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import TestConditionEditor from "../../components/TestConditionEditor";
import TestConditionTable from "../../components/TestConditionTable";
import {
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  StatusPill,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import { docText, messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";

const findingTypeLabels = {
  AMBIGUITY: "Nội dung chưa rõ",
  OMISSION: "Thiếu nội dung",
  INCONSISTENCY: "Nội dung không nhất quán",
  CONTRADICTION: "Nội dung mâu thuẫn",
  UNTESTABLE: "Chưa thể kiểm thử",
  MISSING_ACCEPTANCE_CRITERIA: "Thiếu tiêu chí chấp nhận",
  MISSING_ERROR_BEHAVIOR: "Thiếu cách xử lý lỗi",
  MISSING_PERMISSION_RULE: "Thiếu quy tắc phân quyền",
  MISSING_BOUNDARY: "Thiếu giá trị biên",
  MISSING_NON_FUNCTIONAL_CRITERIA: "Thiếu tiêu chí phi chức năng",
};

const techniqueLabels = {
  EQUIVALENCE_PARTITIONING: "Phân vùng tương đương",
  equivalence_partitioning: "Phân vùng tương đương",
  BOUNDARY_VALUE: "Giá trị biên",
  boundary_value: "Giá trị biên",
  DECISION_TABLE: "Bảng quyết định",
  decision_table: "Bảng quyết định",
  STATE_TRANSITION: "Chuyển trạng thái",
  state_transition: "Chuyển trạng thái",
  ERROR_GUESSING: "Dự đoán lỗi",
  error_guessing: "Dự đoán lỗi",
};

const findingTypeLabel = (value) => findingTypeLabels[value] || valueLabel(value);
const techniqueLabel = (value) => techniqueLabels[value] || valueLabel(value);
const severityLabel = (value) => (value === "CRITICAL" ? "Nghiêm trọng" : valueLabel(value));

export default function TestAnalysisPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [conditions, setConditions] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [members, setMembers] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [findings, setFindings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("conditions");
  const [editing, setEditing] = useState(false);
  const [aiResults, setAiResults] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
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
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      let memberLoadError = "";
      const [
        conditionResult,
        requirementValues,
        coverageValue,
        findingValues,
        aiResultValues,
        memberValues,
      ] = await Promise.all([
        testingApi.listTestConditions(project._id, { q: query, status, page_size: 200 }),
        can("requirement.read")
          ? testingApi.listRequirements(project._id, { status: "BASELINED", page_size: 500 })
          : Promise.resolve([]),
        can("testcondition.read")
          ? testingApi.getTestConditionCoverage(project._id)
          : Promise.resolve(null),
        can("testanalysis.read")
          ? testingApi.listTestAnalysisFindings(project._id)
          : Promise.resolve({ items: [] }),
        can("testanalysis.read")
          ? testingApi.listTestAnalysisAiResults(project._id)
          : Promise.resolve([]),
        can("testanalysis.finding.assign") && can("project.members.read")
          ? testingApi.listMembers(project._id).catch((reason) => {
              memberLoadError = `Không tải được danh sách thành viên để phân công: ${messageOf(reason)}`;
              return [];
            })
          : Promise.resolve([]),
      ]);
      setConditions(conditionResult.items || []);
      setRequirements(requirementValues);
      setCoverage(coverageValue);
      setFindings(findingValues.items || []);
      setAiResults(aiResultValues || []);
      setMembers(memberValues || []);
      setError(memberLoadError);
      setSelected(
        (current) => conditionResult.items?.find((item) => item._id === current?._id) || current,
      );
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [can, project._id, query, status]);
  useEffect(() => {
    void load();
  }, [load]);
  const tabs = [
    ...(can("testcondition.read") ? [{ id: "conditions", label: "Điều kiện kiểm thử" }] : []),
    ...(can("testanalysis.read") ? [{ id: "ai", label: "Đề xuất AI" }] : []),
    ...(can("testanalysis.read") ? [{ id: "findings", label: "Phát hiện" }] : []),
    ...(can("testcondition.read") ? [{ id: "traceability", label: "Truy vết" }] : []),
  ];
  const visibleTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : tabs[0]?.id;
  const aiCandidateItems = aiResults.flatMap((result) =>
    (result.candidates || []).map((candidate) => ({
      ...candidate,
      ai_result_id: result._id,
      source_event_id: result.source_event_id,
      requirement_version_id: result.requirement_version_id,
      created_at: result.created_at,
    })),
  );
  useEffect(() => {
    if (!can("testanalysis.read") || visibleTab !== "ai") return undefined;
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || pending) return;
      pending = true;
      try {
        const values = await testingApi.listTestAnalysisAiResults(project._id);
        if (active) setAiResults(values || []);
      } catch (reason) {
        if (active) setError(messageOf(reason));
      } finally {
        pending = false;
      }
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [can, project._id, visibleTab]);
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Phân tích kiểm thử"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  const transition = async (title, confirmLabel, action) => {
    await ask({
      title,
      confirmLabel,
      fields: [{ name: "note", label: "Ghi chú", required: true, multiline: true }],
      onConfirm: async (answer) => {
        try {
          await action(selected._id, { expected_revision: selected.revision, note: answer.note });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  return (
    <WorkspacePage
      title="Phân tích kiểm thử"
      actions={
        <>
          <ProjectCrumb projectId={project._id} />
          {can("testcondition.create") && (
            <button
              className="apple-button"
              type="button"
              onClick={() => {
                setSelected(null);
                setEditing(true);
              }}
            >
              Tạo điều kiện kiểm thử
            </button>
          )}
        </>
      }
    >
      {dialog}
      {error && <ErrorState message={error} />}
      {tabs.length > 1 && (
        <SegmentedTabs
          label="Khu vực phân tích kiểm thử"
          value={visibleTab}
          onChange={setActiveTab}
          tabs={tabs}
        />
      )}
      {can("testcondition.read") && (
        <div className="space-y-5" hidden={visibleTab !== "conditions"}>
          <Panel title="Điều kiện kiểm thử">
            <form
              className="grid gap-3 p-5 sm:grid-cols-[1fr_220px_auto]"
              onSubmit={(event) => {
                event.preventDefault();
                void load();
              }}
            >
              <input
                className="apple-input"
                aria-label="Tìm điều kiện kiểm thử"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm mã điều kiện hoặc hạng mục độ phủ"
              />
              <select
                className="apple-input"
                aria-label="Lọc trạng thái điều kiện"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">Tất cả trạng thái</option>
                {["DRAFT", "IN_REVIEW", "APPROVED", "ARCHIVED"].map((item) => (
                  <option key={item} value={item}>
                    {valueLabel(item)}
                  </option>
                ))}
              </select>
              <button className="secondary-button" type="submit">
                Lọc
              </button>
            </form>
            <TestConditionTable items={conditions} onSelect={setSelected} />
          </Panel>
        </div>
      )}
      {can("testanalysis.read") && (
        <div className="space-y-5" hidden={visibleTab !== "ai"}>
          <Panel title="Điều kiện do AI đề xuất">
            <div className="space-y-4 p-5">
              <div className="rounded-control border border-violet-300 bg-violet-50/60 p-3">
                <ContentOriginBadge origin="ai_generated" />
              </div>
              <p className="text-sm text-ink-muted">
                Đề xuất được tạo khi phiên bản yêu cầu được đặt làm phiên bản chuẩn. Mỗi đề xuất có
                dẫn chứng nguồn để bạn xem trước khi dùng làm bản nháp.
              </p>
              <DataTable
                items={aiCandidateItems}
                empty="Chưa có ứng viên từ các yêu cầu đã được đặt làm phiên bản chuẩn"
                columns={[
                  { key: "title", label: "Ứng viên" },
                  {
                    key: "category",
                    label: "Nhóm",
                    render: (item) => valueLabel(item.category),
                  },
                  { key: "coverage_item", label: "Điểm cần kiểm thử" },
                  {
                    key: "evidence_quotes",
                    label: "Dẫn chứng nguồn",
                    render: (item) => (
                      <div className="max-w-md space-y-1 whitespace-normal text-xs">
                        {(item.evidence_quotes || []).map((citation, index) => (
                          <p key={`${citation.evidence_ref}-${index}`}>
                            <span className="font-medium">{citation.evidence_ref}:</span> “
                            {citation.quote}”
                          </p>
                        ))}
                      </div>
                    ),
                  },
                  {
                    key: "requirement_version_id",
                    label: "Yêu cầu nguồn",
                    render: (item) => {
                      const requirement = requirements.find(
                        (value) => value.current_version_id === item.requirement_version_id,
                      );
                      return requirement
                        ? `${requirement.requirement_key} · v${requirement.current_version?.version} · ${requirement.current_version?.title || "Không có tiêu đề"}`
                        : "Yêu cầu phiên bản hiện không có trong danh sách";
                    },
                  },
                  {
                    key: "risk",
                    label: "Rủi ro",
                    render: (item) => (
                      <span className="status-badge">{severityLabel(item.risk)}</span>
                    ),
                  },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: () => <span className="status-badge">Đề xuất</span>,
                  },
                  ...(can("testcondition.create")
                    ? [
                        {
                          key: "actions",
                          label: "Thao tác",
                          hideWhenEmpty: true,
                          render: (item) => (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => {
                                setSelected({
                                  ...item,
                                  basis_refs: item.basis_refs || [],
                                  origin: "AI_CANDIDATE_CONFIRMED",
                                });
                                setEditing(true);
                              }}
                            >
                              Dùng làm bản nháp
                            </button>
                          ),
                        },
                      ]
                    : []),
                ]}
              />
            </div>
          </Panel>
        </div>
      )}
      {selected?._id && (
        <div className="space-y-5" hidden={visibleTab !== "conditions"}>
          <Panel
            title={`${selected.condition_key} ${selected.title}`}
            actions={
              <div className="flex flex-wrap gap-2">
                {can("testcondition.update") && selected.status === "DRAFT" && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => setEditing(true)}
                  >
                    Chỉnh sửa
                  </button>
                )}
                {can("testcondition.review") && selected.status === "DRAFT" && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      transition(
                        "Gửi điều kiện để rà soát",
                        "Gửi rà soát",
                        testingApi.submitTestCondition,
                      )
                    }
                  >
                    Gửi rà soát
                  </button>
                )}
                {can("testcondition.review") && selected.status === "IN_REVIEW" && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      transition(
                        "Ghi nhận rà soát điều kiện kiểm thử",
                        "Ghi nhận",
                        testingApi.reviewTestCondition,
                      )
                    }
                  >
                    Ghi nhận rà soát
                  </button>
                )}
                {can("testcondition.approve") && selected.status === "IN_REVIEW" && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={() =>
                      transition(
                        "Phê duyệt điều kiện kiểm thử",
                        "Phê duyệt",
                        testingApi.approveTestCondition,
                      )
                    }
                  >
                    Phê duyệt
                  </button>
                )}
                {can("testcondition.archive") &&
                  ["DRAFT", "APPROVED"].includes(selected.status) && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        transition(
                          "Lưu trữ điều kiện kiểm thử",
                          "Lưu trữ",
                          testingApi.archiveTestCondition,
                        )
                      }
                    >
                      Lưu trữ
                    </button>
                  )}
              </div>
            }
          >
            <div className="grid min-w-0 gap-4 p-5 md:grid-cols-3">
              <div>
                <p className="field-label">Mô tả</p>
                <p className="mt-2 whitespace-pre-wrap text-sm">
                  {docText(selected.description_doc)}
                </p>
              </div>
              <div>
                <p className="field-label">Nhóm điều kiện</p>
                <p className="mt-2 text-sm">
                  {selected.category ? valueLabel(selected.category) : "Chưa phân loại"}
                </p>
              </div>
              <div>
                <p className="field-label">Cơ sở kiểm thử</p>
                <p className="mt-2 text-sm">
                  {selected.basis_refs?.length
                    ? selected.basis_refs
                        .map((item) => {
                          const referenceId = item.artifact_version_id || item.artifact_id;
                          const requirement = requirements.find(
                            (value) => value.current_version_id === referenceId,
                          );
                          return requirement
                            ? `${requirement.requirement_key} · v${requirement.current_version?.version}`
                            : item.label || item.source_label || "Nguồn liên kết khác";
                        })
                        .join(" · ")
                    : "Chưa có căn cứ liên kết"}
                </p>
              </div>
              <div>
                <p className="field-label">Kỹ thuật</p>
                <p className="mt-2 text-sm">
                  {selected.technique_candidates?.length
                    ? selected.technique_candidates.map(techniqueLabel).join(" · ")
                    : "Chưa xác định"}
                </p>
              </div>
            </div>
            <DataTable
              items={selected.analysis_findings || []}
              empty="Không có phát hiện về khả năng kiểm thử"
              columns={[
                {
                  key: "finding_type",
                  label: "Loại phát hiện",
                  render: (item) => findingTypeLabel(item.finding_type),
                },
                {
                  key: "severity",
                  label: "Mức độ",
                  render: (item) => (
                    <span className="status-badge">{severityLabel(item.severity)}</span>
                  ),
                },
                { key: "description", label: "Mô tả" },
                { key: "suggestion", label: "Đề xuất" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                ...(can("testanalysis.resolve_finding")
                  ? [
                      {
                        key: "actions",
                        label: "Thao tác",
                        render: (finding) =>
                          finding.status === "OPEN" ? (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={async () => {
                                await ask({
                                  title: "Giải quyết phát hiện",
                                  confirmLabel: "Ghi nhận",
                                  fields: [
                                    {
                                      name: "status",
                                      label: "Kết quả",
                                      options: [
                                        { value: "RESOLVED", label: "Đã giải quyết" },
                                        { value: "ACCEPTED_RISK", label: "Chấp nhận rủi ro" },
                                      ],
                                    },
                                    {
                                      name: "resolution_ref",
                                      label: "Tham chiếu xử lý",
                                      required: true,
                                    },
                                    {
                                      name: "note",
                                      label: "Ghi chú",
                                      required: true,
                                      multiline: true,
                                    },
                                  ],
                                  onConfirm: async (answer) => {
                                    try {
                                      await testingApi.resolveTestAnalysisFinding(
                                        selected._id,
                                        finding.finding_id,
                                        {
                                          expected_revision: selected.revision,
                                          ...answer,
                                        },
                                      );
                                      await load();
                                    } catch (reason) {
                                      throw new Error(messageOf(reason));
                                    }
                                  },
                                });
                              }}
                            >
                              Giải quyết
                            </button>
                          ) : null,
                      },
                    ]
                  : []),
              ]}
            />
          </Panel>
        </div>
      )}
      {can("testanalysis.read") && (
        <div className="space-y-5" hidden={visibleTab !== "findings"}>
          <Panel title="Phát hiện kiểm thử đã được ghi nhận">
            <DataTable
              items={findings}
              empty="Chưa có phát hiện được ghi nhận"
              columns={[
                { key: "title", label: "Phát hiện" },
                {
                  key: "category",
                  label: "Loại phát hiện",
                  render: (item) => findingTypeLabel(item.category || item.finding_type),
                },
                {
                  key: "severity",
                  label: "Mức độ",
                  render: (item) => <StatusPill value={severityLabel(item.severity)} />,
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                {
                  key: "owner_id",
                  label: "Người phụ trách",
                  render: (item) =>
                    members.find((member) => member.user_id === item.owner_id)?.user_label ||
                    members.find((member) => member.user_id === item.owner_id)?.user?.email ||
                    (item.owner_id ? "Thành viên đã phân công" : "Chưa phân công"),
                },
                {
                  key: "actions",
                  label: "Thao tác",
                  hideWhenEmpty: true,
                  render: (item) => (
                    <span className="flex flex-wrap gap-2">
                      {can("testanalysis.finding.assign") &&
                        ["OPEN", "IN_PROGRESS"].includes(item.status) && (
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={async () => {
                              await ask({
                                title: "Phân công phát hiện",
                                confirmLabel: "Phân công",
                                fields: [
                                  members.length > 0
                                    ? {
                                        name: "owner_id",
                                        label: "Người phụ trách",
                                        required: true,
                                        initialValue: item.owner_id || "",
                                        options: members.map((member) => ({
                                          value: member.user_id,
                                          label:
                                            member.user_label ||
                                            member.user?.email ||
                                            member.user_id,
                                        })),
                                      }
                                    : {
                                        name: "owner_id",
                                        label: "Mã thành viên",
                                        required: true,
                                      },
                                ],
                                onConfirm: async (answer) => {
                                  try {
                                    await testingApi.assignTestAnalysisFinding(item._id, {
                                      expected_revision: item.revision,
                                      owner_id: answer.owner_id,
                                    });
                                    await load();
                                  } catch (reason) {
                                    throw new Error(messageOf(reason));
                                  }
                                },
                              });
                            }}
                          >
                            Phân công
                          </button>
                        )}
                      {can("testanalysis.resolve_finding") &&
                        ["OPEN", "IN_PROGRESS"].includes(item.status) && (
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={async () => {
                              await ask({
                                title: "Giải quyết phát hiện",
                                confirmLabel: "Giải quyết",
                                fields: [
                                  {
                                    name: "resolution",
                                    label: "Cách giải quyết",
                                    required: true,
                                    multiline: true,
                                  },
                                  { name: "resolution_ref", label: "Tham chiếu" },
                                ],
                                onConfirm: async (answer) => {
                                  try {
                                    await testingApi.resolveStandaloneTestAnalysisFinding(
                                      item._id,
                                      {
                                        expected_revision: item.revision,
                                        ...answer,
                                      },
                                    );
                                    await load();
                                  } catch (reason) {
                                    throw new Error(messageOf(reason));
                                  }
                                },
                              });
                            }}
                          >
                            Giải quyết
                          </button>
                        )}
                      {can("testanalysis.verify_finding") && item.status === "RESOLVED" && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={async () => {
                            await ask({
                              title: "Xác minh phát hiện",
                              confirmLabel: "Xác minh",
                              fields: [
                                {
                                  name: "resolution",
                                  label: "Kết quả xác minh",
                                  required: true,
                                  multiline: true,
                                },
                                { name: "resolution_ref", label: "Tham chiếu" },
                              ],
                              onConfirm: async (answer) => {
                                try {
                                  await testingApi.verifyTestAnalysisFinding(item._id, {
                                    expected_revision: item.revision,
                                    ...answer,
                                  });
                                  await load();
                                } catch (reason) {
                                  throw new Error(messageOf(reason));
                                }
                              },
                            });
                          }}
                        >
                          Xác minh
                        </button>
                      )}
                    </span>
                  ),
                },
              ]}
            />
          </Panel>
        </div>
      )}
      {can("testcondition.read") && (
        <div className="space-y-5" hidden={visibleTab !== "traceability"}>
          <Panel title="Liên kết yêu cầu, điều kiện và ca kiểm thử">
            <DataTable
              items={coverage?.items || []}
              empty="Chưa có điều kiện để tính độ phủ"
              columns={[
                { key: "condition_key", label: "Điều kiện" },
                {
                  key: "basis_refs",
                  label: "Yêu cầu hoặc cơ sở",
                  render: (item) =>
                    item.basis_refs
                      .map((ref) => {
                        const referenceId = ref.artifact_version_id || ref.artifact_id;
                        const requirement = requirements.find(
                          (value) => value.current_version_id === referenceId,
                        );
                        return requirement
                          ? `${requirement.requirement_key} · v${requirement.current_version?.version}`
                          : ref.label || ref.source_label || "Nguồn liên kết khác";
                      })
                      .join(" · "),
                },
                {
                  key: "scenario_ids",
                  label: "Kịch bản",
                  render: (item) => item.scenario_ids.length,
                },
                {
                  key: "test_case_version_ids",
                  label: "Ca kiểm thử",
                  render: (item) => item.test_case_version_ids.length,
                },
                {
                  key: "uncovered",
                  label: "Độ phủ",
                  render: (item) => <StatusPill value={item.uncovered ? "UNCOVERED" : "COVERED"} />,
                },
              ]}
            />
          </Panel>
        </div>
      )}
      <Modal
        isOpen={editing}
        onClose={() => setEditing(false)}
        ariaLabel="Chỉnh sửa điều kiện kiểm thử"
        className="max-h-[94dvh] max-w-5xl overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>
            {selected?._id ? "Chỉnh sửa điều kiện kiểm thử" : "Tạo điều kiện kiểm thử"}
          </ModalTitle>
        </ModalHeader>
        <TestConditionEditor
          initialValue={
            selected
              ? {
                  ...selected,
                  description: docText(selected.description_doc) || selected.description || "",
                }
              : null
          }
          requirements={requirements}
          onCancel={() => setEditing(false)}
          onSave={async (payload) => {
            const value = selected?._id
              ? await testingApi.updateTestCondition(selected._id, {
                  ...payload,
                  expected_revision: selected.revision,
                })
              : await testingApi.createTestCondition(project._id, payload);
            setSelected(value);
            setEditing(false);
            await load();
          }}
        />
      </Modal>
    </WorkspacePage>
  );
}
