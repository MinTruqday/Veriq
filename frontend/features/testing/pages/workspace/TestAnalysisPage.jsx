"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BadgeCheck, Check, FilePlus2, Pencil, UserRoundPlus } from "lucide-react";
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
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";
import SearchField from "@/shared/components/ui/SearchField";

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
const severityLabel = (value) => valueLabel(value);

export default function TestAnalysisPage({ project }) {
  const router = useRouter();
  const { ask, dialog } = useActionDialog();
  const [conditions, setConditions] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [members, setMembers] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [findings, setFindings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("conditions");
  const [editing, setEditing] = useState(false);
  const [aiResults, setAiResults] = useState([]);
  const [selectedRequirementVersions, setSelectedRequirementVersions] = useState([]);
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiGenerationError, setAiGenerationError] = useState("");
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
        strategyValues,
      ] = await Promise.all([
        can("testcondition.read")
          ? testingApi.listTestConditions(project._id, { q: query, status, page_size: 200 })
          : Promise.resolve({ items: [] }),
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
        can("teststrategy.read")
          ? testingApi
              .listTestStrategies(project._id, { status: "APPROVED", page_size: 200 })
              .catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] }),
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
      setStrategies(strategyValues.items || []);
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
      requirement_version_id:
        result.requirement_version_id ||
        candidate.basis_refs?.find((item) => item.artifact_type === "REQUIREMENT_VERSION")
          ?.artifact_version_id ||
        candidate.basis_refs?.find((item) => item.artifact_type === "REQUIREMENT_VERSION")
          ?.artifact_id,
      created_at: result.created_at,
    })),
  );
  const generateAiConditions = async () => {
    const selectedRequirements = requirements.filter(
      (item) =>
        item.current_version_id && selectedRequirementVersions.includes(item.current_version_id),
    );
    if (!selectedRequirements.length || aiGenerating) return;
    setAiGenerating(true);
    setAiGenerationError("");
    try {
      const result = await testingApi.runTestAnalysisAI(project._id, {
        basis_refs: selectedRequirements.map((item) => ({
          artifact_type: "REQUIREMENT_VERSION",
          artifact_id: item._id,
          artifact_version_id: item.current_version_id,
          relationship: "DERIVED_FROM",
        })),
        instruction: aiInstruction.trim(),
        idempotency_key: `manual-test-condition:${crypto.randomUUID()}`,
      });
      setAiResults((current) => [result, ...current.filter((item) => item._id !== result._id)]);
    } catch (reason) {
      setAiGenerationError(messageOf(reason));
    } finally {
      setAiGenerating(false);
    }
  };
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
        <div
          className="grid min-w-0 gap-5 lg:grid-cols-[minmax(17rem,0.78fr)_minmax(0,1.65fr)] lg:items-start"
          hidden={visibleTab !== "conditions"}
          style={{ display: visibleTab === "conditions" ? "grid" : "none" }}
        >
          <Panel title="Điều kiện kiểm thử">
            <form
              className="grid gap-3 p-5"
              onSubmit={(event) => {
                event.preventDefault();
                void load();
              }}
            >
              <SearchField
                ariaLabel="Tìm điều kiện kiểm thử"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm mã hoặc hạng mục độ phủ"
                value={query}
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
            <TestConditionTable
              items={conditions}
              selectedId={selected?._id}
              onSelect={setSelected}
            />
          </Panel>
          {selected?._id ? (
            <div className="min-w-0" hidden={visibleTab !== "conditions"}>
              <Panel
                title={
                  <span className="block min-w-0">
                    <span className="block text-[11px] font-medium tracking-wide text-ink-muted">
                      {selected.condition_key}
                    </span>
                    <span className="mt-0.5 block break-words">{selected.title}</span>
                  </span>
                }
                actions={
                  <div className="flex flex-wrap gap-2">
                    {can("testcondition.update") && selected.status === "DRAFT" && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Chỉnh sửa điều kiện ${selected.condition_key}`}
                        title="Chỉnh sửa điều kiện"
                        onClick={() => setEditing(true)}
                      >
                        <Pencil aria-hidden="true" size={16} />
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
                <div className="grid min-w-0 gap-4 p-5 sm:grid-cols-2">
                  <div>
                    <p className="field-label">Mô tả</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm">
                      {docText(selected.description_doc) || selected.description || "Chưa có mô tả"}
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
                  <div>
                    <p className="field-label">Nguồn nội dung</p>
                    <div className="mt-2">
                      <ContentOriginBadge origin={selected.origin || "manual"} />
                    </div>
                  </div>
                  <div>
                    <p className="field-label">Rủi ro</p>
                    <div className="mt-2">
                      <StatusPill value={severityLabel(selected.risk)} />
                    </div>
                  </div>
                  <div>
                    <p className="field-label">Ưu tiên</p>
                    <div className="mt-2">
                      <StatusPill value={selected.priority} />
                    </div>
                  </div>
                  <div>
                    <p className="field-label">Khả năng kiểm thử</p>
                    <div className="mt-2">
                      <StatusPill value={selected.testability_status} />
                    </div>
                  </div>
                  <div>
                    <p className="field-label">Trạng thái</p>
                    <div className="mt-2">
                      <StatusPill value={selected.status} />
                    </div>
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
                      render: (item) => <StatusPill value={severityLabel(item.severity)} />,
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
                                  aria-label={`Giải quyết phát hiện ${finding.finding_id}`}
                                  className="icon-button h-9 w-9"
                                  title="Giải quyết phát hiện"
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
                                  <Check aria-hidden="true" size={16} />
                                </button>
                              ) : null,
                          },
                        ]
                      : []),
                  ]}
                />
              </Panel>
            </div>
          ) : (
            <Panel title="Chi tiết điều kiện">
              <p className="px-4 py-5 text-sm text-ink-muted" role="status">
                Chọn một điều kiện để xem căn cứ, kết quả phân tích và thao tác rà soát.
              </p>
            </Panel>
          )}
        </div>
      )}
      {can("testanalysis.read") && (
        <div className="space-y-5" hidden={visibleTab !== "ai"}>
          <Panel title="Điều kiện do AI đề xuất">
            <div className="space-y-4 p-5">
              <ContentOriginBadge origin="ai_generated" />
              <p className="text-sm text-ink-muted">
                Chọn yêu cầu đã duyệt làm căn cứ rồi bấm tạo đề xuất. Kết quả chỉ là bản xem trước;
                mỗi đề xuất có dẫn chứng để bạn kiểm tra trước khi dùng làm bản nháp.
              </p>
              {can("testanalysis.run_ai") && (
                <div className="space-y-3 border-t border-border pt-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-medium">Yêu cầu nguồn</h3>
                    <div className="flex gap-2">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() =>
                          setSelectedRequirementVersions(
                            requirements.map((item) => item.current_version_id).filter(Boolean),
                          )
                        }
                      >
                        Chọn tất cả
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setSelectedRequirementVersions([])}
                      >
                        Bỏ chọn
                      </button>
                    </div>
                  </div>
                  {requirements.length ? (
                    <div className="grid gap-2 md:grid-cols-2">
                      {requirements
                        .filter((item) => item.current_version_id)
                        .map((item) => {
                          const checked = selectedRequirementVersions.includes(
                            item.current_version_id,
                          );
                          return (
                            <label
                              className="flex min-w-0 cursor-pointer items-start gap-2 border-b border-border py-2"
                              key={item.current_version_id}
                            >
                              <input
                                checked={checked}
                                className="mt-1"
                                onChange={(event) =>
                                  setSelectedRequirementVersions((current) =>
                                    event.target.checked
                                      ? [...new Set([...current, item.current_version_id])]
                                      : current.filter((id) => id !== item.current_version_id),
                                  )
                                }
                                type="checkbox"
                              />
                              <span className="min-w-0 text-sm">
                                <span className="block font-medium">{item.requirement_key}</span>
                                <span className="block break-words text-ink-muted">
                                  {item.current_version?.title || "Yêu cầu đã duyệt"}
                                </span>
                              </span>
                            </label>
                          );
                        })}
                    </div>
                  ) : (
                    <p className="text-sm text-ink-muted">
                      Chưa có yêu cầu đã duyệt để làm căn cứ.
                    </p>
                  )}
                  <label className="block space-y-1 text-sm">
                    <span>Hướng dẫn thêm (không bắt buộc)</span>
                    <textarea
                      className="apple-input min-h-20 w-full"
                      maxLength={5000}
                      onChange={(event) => setAiInstruction(event.target.value)}
                      value={aiInstruction}
                    />
                  </label>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      className="apple-button"
                      disabled={aiGenerating || selectedRequirementVersions.length === 0}
                      onClick={() => void generateAiConditions()}
                      type="button"
                    >
                      {aiGenerating ? "Đang tạo đề xuất…" : "Tạo đề xuất AI"}
                    </button>
                    <span className="text-sm text-ink-muted">
                      Đã chọn {selectedRequirementVersions.length} yêu cầu
                    </span>
                  </div>
                  {aiGenerationError && <ErrorState message={aiGenerationError} />}
                </div>
              )}
              <DataTable
                items={aiCandidateItems}
                empty="Chưa có ứng viên từ các yêu cầu đã được đặt làm phiên bản chuẩn"
                columns={[
                  {
                    key: "candidate",
                    label: "Ứng viên",
                    minWidth: 180,
                    render: (item) => (
                      <div className="min-w-0">
                        <p className="font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-ink-muted">{valueLabel(item.category)}</p>
                      </div>
                    ),
                  },
                  {
                    key: "coverage_item",
                    label: "Điểm cần kiểm thử",
                    minWidth: 170,
                  },
                  {
                    key: "source",
                    label: "Nguồn và căn cứ",
                    minWidth: 260,
                    render: (item) => {
                      const requirement = requirements.find(
                        (value) => value.current_version_id === item.requirement_version_id,
                      );
                      const citations = item.evidence_quotes || [];
                      const [firstCitation, ...additionalCitations] = citations;
                      return (
                        <div className="min-w-0 space-y-2 whitespace-normal text-xs">
                          {requirement ? (
                            <p className="min-w-0">
                              <strong className="font-semibold">
                                {requirement.requirement_key} · v
                                {requirement.current_version?.version}
                              </strong>
                              <span
                                className="mt-0.5 line-clamp-2 text-ink-muted"
                                title={requirement.current_version?.title || undefined}
                              >
                                {requirement.current_version?.title || "Yêu cầu nguồn"}
                              </span>
                            </p>
                          ) : (
                            <p className="text-ink-muted">
                              Yêu cầu phiên bản hiện không có trong danh sách
                            </p>
                          )}
                          {firstCitation && (
                            <p className="line-clamp-3 break-words border-l-2 border-violet-300 pl-2">
                              <span className="font-medium">{firstCitation.evidence_ref}:</span> “
                              {firstCitation.quote}”
                            </p>
                          )}
                          {additionalCitations.length > 0 && (
                            <details>
                              <summary className="w-fit cursor-pointer font-medium text-ink-muted">
                                Xem thêm {additionalCitations.length} dẫn chứng
                              </summary>
                              <div className="mt-2 space-y-2">
                                {additionalCitations.map((citation, index) => (
                                  <p
                                    className="break-words border-l-2 border-violet-300 pl-2"
                                    key={`${citation.evidence_ref}-${index + 1}`}
                                  >
                                    <span className="font-medium">{citation.evidence_ref}:</span> “
                                    {citation.quote}”
                                  </p>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                      );
                    },
                  },
                  {
                    key: "risk",
                    label: "Rủi ro",
                    minWidth: 112,
                    render: (item) => <StatusPill value={severityLabel(item.risk)} />,
                  },
                  ...(can("testcondition.create")
                    ? [
                        {
                          key: "actions",
                          label: "Thao tác",
                          minWidth: 72,
                          hideWhenEmpty: true,
                          render: (item) => (
                            <button
                              aria-label={`Dùng điều kiện ${item.condition_key} làm bản nháp`}
                              title="Dùng làm bản nháp"
                              className="icon-button h-9 w-9"
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
                              <FilePlus2 aria-hidden="true" size={16} />
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
                    <span className="flex items-center gap-1">
                      {can("testanalysis.finding.assign") &&
                        ["OPEN", "IN_PROGRESS"].includes(item.status) && (
                          <button
                            aria-label={`Phân công phát hiện ${item.finding_id}`}
                            className="icon-button h-9 w-9"
                            title="Phân công phát hiện"
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
                            <UserRoundPlus aria-hidden="true" size={16} />
                          </button>
                        )}
                      {can("testanalysis.resolve_finding") &&
                        ["OPEN", "IN_PROGRESS"].includes(item.status) && (
                          <button
                            aria-label={`Giải quyết phát hiện ${item.finding_id}`}
                            className="icon-button h-9 w-9"
                            title="Giải quyết phát hiện"
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
                            <Check aria-hidden="true" size={16} />
                          </button>
                        )}
                      {can("testanalysis.verify_finding") && item.status === "RESOLVED" && (
                        <button
                          aria-label={`Xác minh phát hiện ${item.finding_id}`}
                          className="icon-button h-9 w-9"
                          title="Xác minh phát hiện"
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
                          <BadgeCheck aria-hidden="true" size={16} />
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
            {coverage?.scope_complete === false && (
              <div
                className="mx-5 mt-5 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                role="status"
              >
                Chưa thể xác định toàn bộ độ phủ vì danh sách vượt giới hạn xử lý. Các mục chưa tìm
                thấy liên kết được giữ ở trạng thái chưa xác định.
                {coverage.truncated_sources?.length > 0 && (
                  <span className="mt-1 block">
                    Cần thu hẹp phạm vi: {coverage.truncated_sources.join(", ")}.
                  </span>
                )}
              </div>
            )}
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
                  render: (item) => {
                    const linkedCases = item.test_cases || [];
                    if (!linkedCases.length) return item.test_case_version_ids.length;
                    return (
                      <div className="space-y-1">
                        {linkedCases.map((testCase) => (
                          <a
                            className="block break-words font-medium text-brand underline-offset-2 hover:underline"
                            href={`${projectRoute(project._id, PROJECT_SECTION_SLUGS.testCases)}?case=${encodeURIComponent(testCase.id)}`}
                            key={testCase.version_id}
                            onClick={(event) => {
                              event.preventDefault();
                              router.push(
                                `${projectRoute(project._id, PROJECT_SECTION_SLUGS.testCases)}?case=${encodeURIComponent(testCase.id)}`,
                              );
                            }}
                          >
                            {testCase.key} · {testCase.title}
                            {testCase.version ? ` · v${testCase.version}` : ""}
                          </a>
                        ))}
                      </div>
                    );
                  },
                },
                {
                  key: "uncovered",
                  label: "Độ phủ",
                  render: (item) => (
                    <StatusPill
                      value={
                        item.coverage_status === "UNKNOWN"
                          ? "Chưa xác định"
                          : item.coverage_status === "UNCOVERED"
                            ? "Chưa có ca kiểm thử"
                            : "Đã liên kết ca kiểm thử"
                      }
                    />
                  ),
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
          strategies={strategies}
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
