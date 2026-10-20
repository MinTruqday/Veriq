"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import TestBasisPanel from "../../components/TestBasisPanel";
import TestConditionEditor from "../../components/TestConditionEditor";
import TestConditionTable from "../../components/TestConditionTable";
import TestabilityFindingsPanel from "../../components/TestabilityFindingsPanel";
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

export default function TestAnalysisPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [conditions, setConditions] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [findings, setFindings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("conditions");
  const [editing, setEditing] = useState(false);
  const [basisRefs, setBasisRefs] = useState([]);
  const [aiResult, setAiResult] = useState(null);
  const [aiRunning, setAiRunning] = useState(false);
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
      const [conditionResult, requirementValues, coverageValue, findingValues] = await Promise.all([
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
      ]);
      setConditions(conditionResult.items || []);
      setRequirements(requirementValues);
      setCoverage(coverageValue);
      setFindings(findingValues.items || []);
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
    const answer = await ask({
      title,
      confirmLabel,
      fields: [{ name: "note", label: "Ghi chú", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      await action(selected._id, { expected_revision: selected.revision, note: answer.note });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const tabs = [
    ...(can("testcondition.read") ? [{ id: "conditions", label: "Điều kiện kiểm thử" }] : []),
    ...(can("testanalysis.run_ai") ? [{ id: "ai", label: "Đề xuất AI" }] : []),
    ...(can("testanalysis.read") ? [{ id: "findings", label: "Phát hiện" }] : []),
    ...(can("testcondition.read") ? [{ id: "traceability", label: "Truy vết" }] : []),
  ];
  const visibleTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : tabs[0]?.id;
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
      {can("testanalysis.run_ai") && (
        <div className="space-y-5" hidden={visibleTab !== "ai"}>
          <Panel title="Đề xuất điều kiện bằng AI">
            <div className="space-y-4 p-5">
              <TestBasisPanel
                refs={basisRefs}
                onChange={setBasisRefs}
                requirements={requirements}
              />
              <button
                className="secondary-button"
                type="button"
                disabled={!basisRefs.length || aiRunning}
                onClick={async () => {
                  try {
                    setAiRunning(true);
                    setError("");
                    setAiResult(
                      await testingApi.runTestAnalysisAi(project._id, {
                        basis_refs: basisRefs,
                        instruction:
                          "Phân tích đầy đủ hành vi dương âm biên trạng thái quyền tích hợp dữ liệu lỗi và phi chức năng",
                        idempotency_key: crypto.randomUUID(),
                      }),
                    );
                  } catch (reason) {
                    setError(messageOf(reason));
                  } finally {
                    setAiRunning(false);
                  }
                }}
              >
                {aiRunning ? "AI đang tạo điều kiện" : "Tạo ứng viên điều kiện"}
              </button>
              {aiResult?.degraded_mode && (
                <p className="text-sm text-warning">AI chưa sẵn sàng để tạo điều kiện kiểm thử</p>
              )}
              <DataTable
                items={aiResult?.candidates || []}
                empty="Chưa có ứng viên"
                columns={[
                  { key: "title", label: "Ứng viên" },
                  {
                    key: "category",
                    label: "Nhóm",
                    render: (item) => valueLabel(item.category),
                  },
                  { key: "coverage_item", label: "Hạng mục độ phủ" },
                  {
                    key: "risk",
                    label: "Rủi ro",
                    render: (item) => <StatusPill value={item.risk} />,
                  },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: () => <StatusPill value="CANDIDATE" />,
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
                                  basis_refs: item.basis_refs || basisRefs,
                                  origin: "AI_CANDIDATE_CONFIRMED",
                                  ai_result_id: aiResult._id,
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
            <div className="grid gap-4 p-5 md:grid-cols-3">
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
                  {selected.basis_refs
                    ?.map((item) => item.artifact_version_id || item.artifact_id)
                    .join(" · ")}
                </p>
              </div>
              <div>
                <p className="field-label">Kỹ thuật</p>
                <p className="mt-2 text-sm">
                  {selected.technique_candidates?.join(" · ") || "Chưa xác định"}
                </p>
              </div>
            </div>
            <TestabilityFindingsPanel
              condition={selected}
              canResolve={can("testanalysis.resolve_finding")}
              onResolve={async (finding) => {
                const answer = await ask({
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
                    { name: "resolution_ref", label: "Tham chiếu xử lý", required: true },
                    { name: "note", label: "Ghi chú", required: true, multiline: true },
                  ],
                });
                if (!answer) return;
                try {
                  await testingApi.resolveTestAnalysisFinding(selected._id, finding.finding_id, {
                    expected_revision: selected.revision,
                    ...answer,
                  });
                  await load();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
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
                { key: "category", label: "Phân loại" },
                {
                  key: "severity",
                  label: "Mức độ",
                  render: (item) => <StatusPill value={item.severity} />,
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                { key: "owner_id", label: "Người phụ trách" },
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
                              const answer = await ask({
                                title: "Phân công phát hiện",
                                confirmLabel: "Phân công",
                                fields: [
                                  { name: "owner_id", label: "Mã thành viên", required: true },
                                ],
                              });
                              if (!answer) return;
                              try {
                                await testingApi.assignTestAnalysisFinding(item._id, {
                                  expected_revision: item.revision,
                                  owner_id: answer.owner_id,
                                });
                                await load();
                              } catch (reason) {
                                setError(messageOf(reason));
                              }
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
                              const answer = await ask({
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
                              });
                              if (!answer) return;
                              try {
                                await testingApi.resolveStandaloneTestAnalysisFinding(item._id, {
                                  expected_revision: item.revision,
                                  ...answer,
                                });
                                await load();
                              } catch (reason) {
                                setError(messageOf(reason));
                              }
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
                            const answer = await ask({
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
                            });
                            if (!answer) return;
                            try {
                              await testingApi.verifyTestAnalysisFinding(item._id, {
                                expected_revision: item.revision,
                                ...answer,
                              });
                              await load();
                            } catch (reason) {
                              setError(messageOf(reason));
                            }
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
                      .map((ref) => ref.artifact_version_id || ref.artifact_id)
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
        ariaLabel="Biên tập điều kiện kiểm thử"
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
