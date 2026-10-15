"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../components/DataTable";
import FormalReviewPanel from "../../components/FormalReviewPanel";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import TestCaseTemplatesPanel from "../../components/TestCaseTemplatesPanel";
import SpecializedDesignPanel from "../../components/SpecializedDesignPanel";
import AutomationScriptsPanel from "../../components/AutomationScriptsPanel";
import CollaborationPanel from "../../components/CollaborationPanel";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { testingApi } from "../../services/testing.service";
import { docText, messageOf, textDoc, valueLabel } from "../../lib/testing";
import DocumentEditor from "../../editor/DocumentEditor";
import ApiArtifactsPanel from "./test-design/ApiArtifactsPanel";
import DataSetsPanel from "./test-design/DataSetsPanel";
import ScenariosPanel from "./test-design/ScenariosPanel";
import TestCaseCreateModal from "./test-design/TestCaseCreateModal";
import TestCaseTransferPanel from "./test-design/TestCaseTransferPanel";
import TestAdequacyPanel from "./design/TestAdequacyPanel";
import TestRepositoryPanel from "./test-design/TestRepositoryPanel";
import {
  createDataSetForm,
  createScenarioForm,
  createTestCaseForm,
  AI_TEST_GENERATION_CATEGORIES,
  TEST_CASE_TYPES,
  TEST_LEVELS,
  TEST_SCENARIO_CATEGORIES,
  buildTestCaseDraftChanges,
} from "./test-design/testDesign.model";

const relevantGeneratedMatches = (item, selectedIndexes) =>
  (item.similar_cases || []).filter(
    (match) =>
      !match.id.startsWith("preview:") ||
      selectedIndexes.includes(Number(match.id.slice("preview:".length))),
  );

function ChallengeProvenance({ challenges }) {
  return (
    <div className="space-y-3 text-sm">
      {challenges.map((challenge) => (
        <div className="rounded-control border border-border p-3" key={challenge.technique}>
          <p>Kỹ thuật {valueLabel(challenge.technique)}</p>
          <p>Hành vi sai giả định {challenge.hypothetical_fault}</p>
          <p>Đầu vào phân biệt {challenge.distinguishing_input}</p>
          <p>Kết quả cần đối chiếu {challenge.expected_result}</p>
          <p>Đoạn nguồn {challenge.source_quote}</p>
          <p>Ca được đối chiếu {challenge.existing_case_refs.join("  ")}</p>
        </div>
      ))}
      <p className="text-ink-muted">Đây là giả thuyết thiết kế chưa chứng minh lỗi thực tế</p>
    </div>
  );
}

export default function TestDesignPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [requirements, setRequirements] = useState([]);
  const [testConditions, setTestConditions] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [dataSets, setDataSets] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [tests, setTests] = useState([]);
  const [suites, setSuites] = useState([]);
  const [repositoryNodes, setRepositoryNodes] = useState([]);
  const [reusableSteps, setReusableSteps] = useState([]);
  const [selectedTestIds, setSelectedTestIds] = useState([]);
  const [testPage, setTestPage] = useState(1);
  const [testPageInfo, setTestPageInfo] = useState(null);
  const [testFilters, setTestFilters] = useState({
    q: "",
    status: "",
    priority: "",
    stale_status: "",
    automation_status: "",
    sort: "-updated_at",
  });
  const [scenarioFilters, setScenarioFilters] = useState({
    q: "",
    category: "",
    risk: "",
    status: "",
    sort: "-updated_at",
  });
  const [duplicates, setDuplicates] = useState([]);
  const [operations, setOperations] = useState([]);
  const [apiArtifacts, setApiArtifacts] = useState([]);
  const [apiCompareFrom, setApiCompareFrom] = useState("");
  const [apiCompareTo, setApiCompareTo] = useState("");
  const [apiDifference, setApiDifference] = useState(null);
  const [testImport, setTestImport] = useState(null);
  const [apiImport, setApiImport] = useState({
    filename: "openapi.json",
    format: "openapi",
    content: "",
  });
  const [selectedRequirement, setSelectedRequirement] = useState("");
  const [selectedDraftId, setSelectedDraftId] = useState("");
  const [selectedTestId, setSelectedTestId] = useState("");
  const [testVersions, setTestVersions] = useState([]);
  const [draftEdit, setDraftEdit] = useState(null);
  const [draftDirty, setDraftDirty] = useState(false);
  const [draftSaveState, setDraftSaveState] = useState("saved");
  const draftSequence = useRef(0);
  const draftSavesInFlight = useRef(new Set());
  const loadedDraft = useRef("");
  const [testLint, setTestLint] = useState(null);
  const [scenarioForm, setScenarioForm] = useState(createScenarioForm);
  const [dataSetForm, setDataSetForm] = useState(createDataSetForm);
  const [form, setForm] = useState(createTestCaseForm);
  const [error, setError] = useState("");
  const [creatingTest, setCreatingTest] = useState(false);
  const [creatingScenario, setCreatingScenario] = useState(false);
  const [creatingDataSet, setCreatingDataSet] = useState(false);
  const [aiAction, setAiAction] = useState("");
  const [selectedTechniques, setSelectedTechniques] = useState([]);
  const [maximumCases, setMaximumCases] = useState(5);
  const [techniqueAdvice, setTechniqueAdvice] = useState(null);
  const [approvedChallenges, setApprovedChallenges] = useState([]);
  const [generationPreview, setGenerationPreview] = useState(null);
  const testImportPanelRef = useRef(null);
  const [selectedGenerated, setSelectedGenerated] = useState([]);
  const [generatedReasons, setGeneratedReasons] = useState({});
  const [generatedVersionResolutions, setGeneratedVersionResolutions] = useState({});
  useEffect(() => {
    setTechniqueAdvice(null);
    setApprovedChallenges([]);
    setGenerationPreview(null);
    setSelectedGenerated([]);
    setGeneratedReasons({});
    setGeneratedVersionResolutions({});
    setSelectedTechniques([]);
  }, [selectedRequirement]);
  useEffect(() => {
    setGenerationPreview(null);
    setSelectedGenerated([]);
    setGeneratedReasons({});
    setGeneratedVersionResolutions({});
    setApprovedChallenges((current) =>
      current.filter((technique) => selectedTechniques.includes(technique)),
    );
  }, [selectedTechniques, maximumCases]);
  const can = (permission) => project.current_permissions?.includes(permission);
  const canReadTestData = project.current_permissions?.includes("testdata.read");
  const load = useCallback(async () => {
    try {
      const [
        requirementValues,
        testConditionValues,
        scenarioValues,
        dataSetValues,
        draftValues,
        testValues,
        suiteValues,
        repositoryValues,
        reusableStepValues,
        apiArtifactValues,
        operationValues,
      ] = await Promise.all([
        testingApi.listRequirements(project._id, { page_size: 500, status: "BASELINED" }),
        testingApi.listTestConditions(project._id, { status: "APPROVED", page_size: 200 }),
        testingApi.listScenarios(project._id, scenarioFilters),
        canReadTestData ? testingApi.listDataSets(project._id) : Promise.resolve([]),
        testingApi.listTestDrafts(project._id),
        testingApi.listTestCasePage(project._id, {
          ...testFilters,
          page: testPage,
          page_size: 50,
        }),
        testingApi.listSuites(project._id),
        testingApi.listTestRepository(project._id),
        testingApi.listReusableTestSteps(project._id),
        testingApi.listApiArtifacts(project._id),
        testingApi.listApiOperations(project._id),
      ]);
      setRequirements(requirementValues);
      setTestConditions(testConditionValues.items || []);
      setScenarios(scenarioValues);
      setDataSets(dataSetValues);
      setDrafts(draftValues);
      setTests(testValues.items);
      setTestPageInfo(testValues);
      setSuites(suiteValues);
      setRepositoryNodes(repositoryValues);
      setReusableSteps(reusableStepValues);
      setApiArtifacts(apiArtifactValues);
      const confirmedArtifacts = apiArtifactValues.filter((item) => item.status === "CONFIRMED");
      setApiCompareFrom((current) =>
        confirmedArtifacts.some((item) => item._id === current)
          ? current
          : confirmedArtifacts[1]?._id || "",
      );
      setApiCompareTo((current) =>
        confirmedArtifacts.some((item) => item._id === current)
          ? current
          : confirmedArtifacts[0]?._id || "",
      );
      setOperations(operationValues);
      setSelectedRequirement((current) =>
        requirementValues.some((item) => item.current_version_id === current)
          ? current
          : requirementValues[0]?.current_version_id || "",
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canReadTestData, project._id, scenarioFilters, testFilters, testPage]);
  useEffect(() => {
    void load();
  }, [load]);
  const selectedDraft = drafts.find((item) => item._id === selectedDraftId) || null;
  useEffect(() => {
    if (!selectedDraft) {
      loadedDraft.current = "";
      setDraftEdit(null);
      setTestLint(null);
      return;
    }
    if (loadedDraft.current === selectedDraft._id) return;
    loadedDraft.current = selectedDraft._id;
    setTestLint(null);
    setDraftEdit({
      title: selectedDraft.title,
      type: selectedDraft.type,
      priority: selectedDraft.priority,
      risk: selectedDraft.risk,
      objective: docText(selectedDraft.objective_doc),
      preconditions: docText(selectedDraft.preconditions_doc),
      steps: (selectedDraft.steps || []).map((step) => ({
        id: step.id,
        action: docText(step.action_doc),
        data: JSON.stringify(step.test_data || {}, null, 2),
        expected: docText(step.expected_doc),
      })),
      testData: JSON.stringify(selectedDraft.test_data || {}, null, 2),
      expected: docText(selectedDraft.expected_result_doc),
      postconditions: docText(selectedDraft.postconditions_doc),
      techniques: (selectedDraft.techniques || []).join(", "),
      tags: (selectedDraft.tags || []).join(", "),
      ownerId: selectedDraft.owner_id || "",
      automationStatus: selectedDraft.automation_status || "manual",
      attachments: selectedDraft.attachments || [],
      dataSetVersionIds: selectedDraft.data_set_version_ids || [],
      testConditionIds: selectedDraft.test_condition_ids || [],
    });
    setDraftDirty(false);
    setDraftSaveState("saved");
  }, [selectedDraft]);
  const changeDraftEdit = (next) => {
    draftSequence.current += 1;
    setDraftEdit((value) => (typeof next === "function" ? next(value) : { ...value, ...next }));
    setDraftDirty(true);
    setDraftSaveState("pending");
  };
  const create = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createTestDraft(project._id, {
        title: form.title,
        type: form.type,
        priority: form.priority,
        risk: form.risk,
        objective_doc: textDoc(form.title),
        preconditions_doc: textDoc(""),
        steps: [
          {
            id: crypto.randomUUID(),
            order: 1,
            action_doc: form.action,
            test_data: {},
            expected_doc: form.expected,
          },
        ],
        test_data: {},
        expected_result_doc: form.expected,
        postconditions_doc: textDoc(""),
        tags: [],
        techniques: [],
        automation_status: "manual",
        attachments: [],
        data_set_version_ids: form.dataSetVersionIds,
        test_condition_ids: form.testConditionIds,
        repository_node_id: form.repositoryNodeId || null,
        requirement_version_ids: selectedRequirement ? [selectedRequirement] : [],
        acceptance_criterion_ids: [],
        origin: "manual",
        source_evidence: [],
        bdd:
          form.testStyle === "BDD"
            ? {
                feature: form.feature,
                scenario: form.scenario || form.title,
                steps: [
                  { keyword: "Given", text: form.given },
                  { keyword: "When", text: form.when },
                  { keyword: "Then", text: form.then },
                  ...form.reusableStepVersionIds.flatMap((versionId) => {
                    const reusableStep = reusableSteps.find(
                      (item) => item.current_version_id === versionId,
                    );
                    if (!reusableStep) return [];
                    return [
                      {
                        keyword: "And",
                        text: docText(reusableStep.action_doc),
                        reusable_step_version_id: versionId,
                      },
                    ];
                  }),
                ].filter((item) => item.text.trim()),
              }
            : null,
      });
      setForm(createTestCaseForm());
      setCreatingTest(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createScenario = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createScenario(project._id, {
        title: scenarioForm.title,
        objective: scenarioForm.objective,
        category: scenarioForm.category,
        risk: "medium",
        priority: "medium",
        requirement_version_ids: selectedRequirement ? [selectedRequirement] : [],
        acceptance_criterion_ids: [],
        test_condition_ids: scenarioForm.testConditionIds,
        status: "draft",
        origin: "manual",
      });
      setScenarioForm(createScenarioForm());
      setCreatingScenario(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createDataSet = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createDataSet(project._id, {
        name: dataSetForm.name,
        variables: JSON.parse(dataSetForm.variables || "{}"),
        secret_refs: JSON.parse(dataSetForm.secretRefs || "{}"),
      });
      setDataSetForm(createDataSetForm());
      setCreatingDataSet(false);
      await load();
    } catch (reason) {
      setError(
        reason instanceof SyntaxError ? "Bộ dữ liệu phải là JSON hợp lệ" : messageOf(reason),
      );
    }
  };
  const generate = async () => {
    if (!selectedRequirement) return setError("Cần chọn yêu cầu trước khi tạo ca kiểm thử");
    if (!selectedTechniques.length) return setError("Chọn ít nhất một kỹ thuật thiết kế kiểm thử");
    if (!Number.isInteger(maximumCases) || maximumCases < 1 || maximumCases > 100) {
      return setError("Số ca tối đa phải là số nguyên từ 1 đến 100");
    }
    setError("");
    setGenerationPreview(null);
    setSelectedGenerated([]);
    setGeneratedReasons({});
    setGeneratedVersionResolutions({});
    setAiAction("testcase");
    try {
      const result = await testingApi.generateTestCases(selectedRequirement, {
        categories: [],
        techniques: selectedTechniques,
        challenge_suite_signature: approvedChallenges.length
          ? techniqueAdvice?.suite_signature
          : null,
        challenge_hypotheses: (techniqueAdvice?.items || [])
          .filter(
            (item) =>
              selectedTechniques.includes(item.technique) &&
              approvedChallenges.includes(item.technique) &&
              item.challenge,
          )
          .map((item) => ({
            technique: item.technique,
            source_ref: item.challenge.source_ref,
            source_quote: item.challenge.source_quote,
            hypothetical_fault: item.challenge.hypothetical_fault,
            distinguishing_input: item.challenge.distinguishing_input,
            expected_result: item.challenge.expected_result,
            existing_case_refs: item.challenge.existing_case_refs,
          })),
        max_cases: maximumCases,
        preview_only: true,
        instruction:
          "Generate test cases in Vietnamese with verifiable inputs and results using only the selected design techniques",
      });
      setGenerationPreview(result);
      setSelectedGenerated(
        result.items.reduce(
          (selected, item, index) =>
            relevantGeneratedMatches(item, selected).length ? selected : [...selected, index],
          [],
        ),
      );
      setGeneratedReasons({});
      setGeneratedVersionResolutions({});
    } catch (reason) {
      const missing = reason.details?.unapplied_techniques;
      const unaddressed = reason.details?.unaddressed_challenges;
      const unsupported = reason.details?.unsupported_claims;
      const limitations = reason.details?.warnings;
      setError(
        Array.isArray(missing) && missing.length
          ? `${messageOf(reason)}  Thiếu bằng chứng cho ${missing.map(valueLabel).join("  ")}${Array.isArray(limitations) && limitations.length ? `  ${limitations.slice(0, 3).join("  ")}` : ""}`
          : Array.isArray(unaddressed) && unaddressed.length
            ? `${messageOf(reason)}  Chưa xử lý ${unaddressed.map(valueLabel).join("  ")}`
            : Array.isArray(unsupported) && unsupported.length
              ? `${messageOf(reason)}  Cần kiểm tra nội dung ${unsupported.slice(0, 3).join("  ")}`
              : messageOf(reason),
      );
    } finally {
      setAiAction("");
    }
  };
  const recommendTechniques = async () => {
    if (!selectedRequirement) return setError("Cần chọn yêu cầu trước khi nhận gợi ý");
    setError("");
    setAiAction("technique");
    try {
      const result = await testingApi.recommendTestTechniques(selectedRequirement, {
        instruction:
          "Recommend suitable test design techniques in Vietnamese and provide evidence plus expected coverage against existing cases",
      });
      setTechniqueAdvice(result);
      setApprovedChallenges([]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  const saveGenerated = async () => {
    if (!selectedGenerated.length || !generationPreview) return;
    if (
      selectedGenerated.some(
        (index) =>
          relevantGeneratedMatches(generationPreview.items[index], selectedGenerated).length &&
          !generatedVersionResolutions[index]?.target_version_id &&
          (generatedReasons[index] || "").trim().length < 2,
      )
    ) {
      setError("Cần ghi lý do tạo riêng cho từng ca gần giống");
      return;
    }
    if (
      selectedGenerated.some(
        (index) =>
          generatedVersionResolutions[index]?.target_version_id &&
          (generatedVersionResolutions[index]?.reason || "").trim().length < 2,
      )
    ) {
      setError("Cần ghi lý do tạo phiên bản mới cho từng ca được cập nhật");
      return;
    }
    setAiAction("saving-generated");
    try {
      await testingApi.createGeneratedTestDrafts(
        project._id,
        [...selectedGenerated]
          .sort((left, right) => left - right)
          .map((index) => ({
            ...generationPreview.items[index].draft,
            duplicate_reason: generatedVersionResolutions[index]?.target_version_id
              ? null
              : generatedReasons[index]?.trim() || null,
            target_version_id: generatedVersionResolutions[index]?.target_version_id || null,
            version_reason: generatedVersionResolutions[index]?.target_version_id
              ? generatedVersionResolutions[index]?.reason?.trim()
              : null,
          })),
      );
      setGenerationPreview(null);
      setSelectedGenerated([]);
      setGeneratedVersionResolutions({});
      await load();
    } catch (reason) {
      const failedIndex = [...selectedGenerated].sort((left, right) => left - right)[
        reason.details?.index
      ];
      if (reason.code === "TEST_CASE_DUPLICATE_REVIEW_REQUIRED" && failedIndex !== undefined) {
        setGenerationPreview((current) => ({
          ...current,
          items: current.items.map((item, index) =>
            index === failedIndex
              ? { ...item, similar_cases: reason.details?.matches || [] }
              : item,
          ),
        }));
      }
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  const freeze = async (draft) => {
    const answer = await ask({
      title: "Phê duyệt ca kiểm thử",
      description: `${draft.test_case_key} sẽ trở thành phiên bản bất biến và được dùng trong lần chạy`,
      confirmLabel: "Phê duyệt",
    });
    if (!answer) return;
    try {
      await testingApi.freezeTestDraft(
        draft._id,
        draft.revision,
        "Phê duyệt sau rà soát của con người",
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const reviewDraft = async (draft, action) => {
    const answer = await ask({
      title: action === "changes" ? "Yêu cầu chỉnh sửa ca kiểm thử" : "Gửi ca kiểm thử để rà soát",
      description: draft.test_case_key,
      confirmLabel: action === "changes" ? "Yêu cầu chỉnh sửa" : "Gửi rà soát",
      fields: [
        {
          name: "note",
          label: action === "changes" ? "Nội dung cần chỉnh sửa" : "Ghi chú rà soát",
          initialValue:
            action === "changes" ? "Cần cập nhật theo nhận xét" : "Đã rà soát các bước và dữ liệu",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
    });
    if (!answer) return;
    try {
      const payload = { expected_revision: draft.revision, review_note: answer.note };
      if (action === "submit") {
        await testingApi.submitTestCaseReview(project._id, draft._id, payload);
      } else {
        await testingApi.requestTestCaseChanges(project._id, draft._id, payload);
      }
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const persistDraft = useCallback(
    async (snapshot, sequence) => {
      if (draftSavesInFlight.current.has(selectedDraft._id)) return;
      draftSavesInFlight.current.add(selectedDraft._id);
      try {
        const changes = buildTestCaseDraftChanges(snapshot, selectedDraft);
        if (!Object.keys(changes).length) {
          if (draftSequence.current === sequence) {
            setDraftDirty(false);
            setDraftSaveState("saved");
          }
          return;
        }
        setDraftSaveState("saving");
        const result = await testingApi.applyTestCaseCollaborationOperation(
          project._id,
          selectedDraft._id,
          {
            base_revision: selectedDraft.revision,
            operation_id: crypto.randomUUID(),
            changes,
          },
        );
        setDrafts((values) => values.map((item) => (item._id === result._id ? result : item)));
        if (draftSequence.current === sequence) {
          setDraftDirty(false);
          setDraftSaveState("saved");
        } else {
          setDraftSaveState("pending");
        }
      } catch (reason) {
        setDraftSaveState(reason instanceof SyntaxError ? "invalid" : "error");
        setError(
          reason instanceof SyntaxError
            ? "Dữ liệu kiểm thử phải là JSON hợp lệ"
            : messageOf(reason),
        );
      } finally {
        draftSavesInFlight.current.delete(selectedDraft._id);
      }
    },
    [project._id, selectedDraft],
  );
  const saveDraft = async () => {
    await persistDraft(draftEdit, draftSequence.current);
  };
  useEffect(() => {
    if (
      !draftDirty ||
      selectedDraft?.status !== "DRAFT" ||
      !draftEdit ||
      !project.current_permissions?.includes("testcase.update")
    )
      return undefined;
    const sequence = draftSequence.current;
    const timer = window.setTimeout(() => {
      void persistDraft(draftEdit, sequence);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [draftDirty, draftEdit, persistDraft, project.current_permissions, selectedDraft?.status]);
  const criterionCoverage = generationPreview?.criterion_coverage;
  const selectedCriterionIds = new Set([
    ...(criterionCoverage?.linked_criterion_ids || []),
    ...selectedGenerated.flatMap(
      (index) => generationPreview?.items[index]?.draft.acceptance_criterion_ids || [],
    ),
  ]);
  const remainingCriterionIds = (criterionCoverage?.criterion_ids || []).filter(
    (id) => !selectedCriterionIds.has(id),
  );
  const criterionLabel = (id) => {
    const criterion = generationPreview?.evidence?.find((item) => item._id === id);
    return criterion?.key || criterion?.plain_text || id;
  };
  const criterionIdsLostWithout = (excludedIndex) => {
    const retained = new Set([
      ...(criterionCoverage?.linked_criterion_ids || []),
      ...selectedGenerated
        .filter((index) => index !== excludedIndex)
        .flatMap((index) => generationPreview?.items[index]?.draft.acceptance_criterion_ids || []),
    ]);
    return (generationPreview?.items[excludedIndex]?.draft.acceptance_criterion_ids || []).filter(
      (id) => !retained.has(id),
    );
  };
  return (
    <WorkspacePage
      title="Thiết kế kiểm thử"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {can("testcase.create") && (
            <button className="apple-button" type="button" onClick={() => setCreatingTest(true)}>
              Tạo ca kiểm thử
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {selectedRequirement && (
        <TestAdequacyPanel
          requirementVersionId={selectedRequirement}
          canReview={project.current_membership?.project_role === "QA"}
        />
      )}
      {(can("ai.generate_testcase") ||
        can("ai.generate_scenario") ||
        can("testcase.duplicate_check")) && (
        <Panel title="Hỗ trợ thiết kế kiểm thử">
          <div className="flex flex-wrap gap-3 p-5">
            <select
              aria-label="Yêu cầu nguồn"
              className="apple-input min-w-72"
              value={selectedRequirement}
              disabled={Boolean(aiAction)}
              onChange={(event) => {
                setSelectedRequirement(event.target.value);
                setSelectedTechniques([]);
                setTechniqueAdvice(null);
                setApprovedChallenges([]);
                setGenerationPreview(null);
                setSelectedGenerated([]);
                setGeneratedReasons({});
                setGeneratedVersionResolutions({});
                setError("");
              }}
            >
              <option value="">Chọn yêu cầu</option>
              {requirements.map((item) => (
                <option key={item._id} value={item.current_version_id}>
                  {item.requirement_key} {item.current_version?.title}
                </option>
              ))}
            </select>
            {can("ai.generate_testcase") && (
              <button
                className="secondary-button"
                type="button"
                disabled={Boolean(aiAction) || !selectedRequirement}
                aria-busy={aiAction === "technique"}
                onClick={recommendTechniques}
              >
                {aiAction === "technique" ? "AI đang đánh giá kỹ thuật" : "AI gợi ý kỹ thuật"}
              </button>
            )}
            {can("ai.generate_testcase") && can("testcase.create") && (
              <button
                aria-busy={aiAction === "testcase"}
                className="apple-button"
                disabled={Boolean(aiAction) || !selectedRequirement || !selectedTechniques.length}
                type="button"
                onClick={generate}
              >
                {aiAction === "testcase" ? "AI đang tạo bản xem trước" : "Xem trước ca kiểm thử"}
              </button>
            )}
            {can("ai.generate_scenario") && can("testscenario.create") && (
              <button
                className="secondary-button"
                aria-busy={aiAction === "scenario"}
                disabled={Boolean(aiAction)}
                type="button"
                onClick={async () => {
                  if (!selectedRequirement) return;
                  setAiAction("scenario");
                  try {
                    await testingApi.generateScenarios(selectedRequirement, {
                      categories: AI_TEST_GENERATION_CATEGORIES,
                      count_per_category: 1,
                    });
                    await load();
                  } catch (reason) {
                    setError(messageOf(reason));
                  } finally {
                    setAiAction("");
                  }
                }}
              >
                {aiAction === "scenario" ? "AI đang tạo kịch bản" : "Tạo kịch bản"}
              </button>
            )}
            {can("testcase.duplicate_check") && can("ai.run_duplicate_check") && (
              <button
                className="secondary-button"
                aria-busy={aiAction === "duplicates"}
                disabled={Boolean(aiAction)}
                type="button"
                onClick={async () => {
                  setAiAction("duplicates");
                  try {
                    setDuplicates(await testingApi.findDuplicates(project._id));
                  } catch (reason) {
                    setError(messageOf(reason));
                  } finally {
                    setAiAction("");
                  }
                }}
              >
                {aiAction === "duplicates"
                  ? "Đang tìm ca kiểm thử trùng lặp"
                  : "Tìm ca kiểm thử trùng lặp"}
              </button>
            )}
          </div>
          {can("ai.generate_testcase") && (
            <div className="space-y-4 border-t border-border p-5">
              <fieldset>
                <legend className="mb-2 font-medium">Kỹ thuật thiết kế kiểm thử</legend>
                <div className="flex flex-wrap gap-4">
                  {[
                    ["equivalence_partitioning", "Phân vùng tương đương"],
                    ["boundary_value", "Giá trị biên"],
                    ["decision_table", "Bảng quyết định"],
                    ["state_transition", "Chuyển trạng thái"],
                    ["error_guessing", "Dự đoán lỗi"],
                  ].map(([value, label]) => (
                    <label className="flex items-center gap-2 text-sm" key={value}>
                      <input
                        type="checkbox"
                        checked={selectedTechniques.includes(value)}
                        disabled={Boolean(aiAction)}
                        onChange={(event) =>
                          setSelectedTechniques((current) =>
                            event.target.checked
                              ? [...current, value]
                              : current.filter((item) => item !== value),
                          )
                        }
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>
              <label className="field-label block max-w-48">
                Số ca tối đa
                <input
                  className="apple-input mt-2"
                  type="number"
                  min="1"
                  max="100"
                  value={maximumCases}
                  disabled={Boolean(aiAction)}
                  onChange={(event) => setMaximumCases(Number(event.target.value))}
                />
              </label>
              {techniqueAdvice?.items.some(
                (item) =>
                  selectedTechniques.includes(item.technique) &&
                  approvedChallenges.includes(item.technique) &&
                  item.challenge,
              ) && (
                <p className="text-sm text-ink-muted">
                  Khi tạo ca AI sẽ thử xử lý giả thuyết lỗi đã chọn Giả thuyết không thay thế tài
                  liệu nguồn
                </p>
              )}
              {techniqueAdvice && (
                <div className="space-y-3">
                  {techniqueAdvice.items.some((item) => item.suitability === "recommended") ? (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={Boolean(aiAction)}
                      onClick={() =>
                        setSelectedTechniques(
                          techniqueAdvice.items
                            .filter((item) => item.suitability === "recommended")
                            .map((item) => item.technique),
                        )
                      }
                    >
                      Chọn các kỹ thuật AI khuyến nghị
                    </button>
                  ) : (
                    <p className="text-sm text-ink-muted">
                      AI chưa có kỹ thuật khuyến nghị từ bằng chứng hiện có Bạn có thể tự chọn kỹ
                      thuật được đánh dấu Có thể dùng sau khi xem phần còn thiếu
                    </p>
                  )}
                  {!!techniqueAdvice.warnings?.length && (
                    <div className="text-sm text-ink-muted">
                      {techniqueAdvice.warnings.map((warning, index) => (
                        <p key={index}>{warning}</p>
                      ))}
                    </div>
                  )}
                  {techniqueAdvice.items.map((item) => (
                    <div
                      className="rounded-control border border-border p-3 text-sm"
                      key={item.technique}
                    >
                      <p className="font-medium">
                        {valueLabel(item.technique)} {valueLabel(item.suitability)}
                      </p>
                      <p>{item.rationale}</p>
                      {!!item.expected_coverage?.length && (
                        <p>Phần bao phủ dự kiến {item.expected_coverage.join("  ")}</p>
                      )}
                      {!!item.existing_coverage_refs?.length && (
                        <p>Ca đã bao phủ {item.existing_coverage_refs.join("  ")}</p>
                      )}
                      {!!item.incremental_coverage?.length && (
                        <p>Phần có thể bổ sung {item.incremental_coverage.join("  ")}</p>
                      )}
                      {!!item.missing_information?.length && (
                        <p>Còn thiếu {item.missing_information.join("  ")}</p>
                      )}
                      {item.challenge && (
                        <div className="mt-3 space-y-1 border-t border-border pt-3">
                          <p className="font-medium">Giả thuyết lỗi có thể lọt qua bộ ca hiện có</p>
                          <p>Hành vi sai giả định {item.challenge.hypothetical_fault}</p>
                          <p>Đầu vào phân biệt {item.challenge.distinguishing_input}</p>
                          <p>
                            Kết quả AI đề xuất cần QA đối chiếu nguồn{" "}
                            {item.challenge.expected_result}
                          </p>
                          <p>Đoạn nguồn {item.challenge.source_quote}</p>
                          {!!item.challenge.existing_case_refs?.length && (
                            <details className="rounded-control border border-border p-3">
                              <summary className="cursor-pointer font-medium">
                                Đối chiếu {item.challenge.existing_case_refs.length} ca hiện có
                              </summary>
                              <div className="mt-2 space-y-3">
                                {item.challenge.existing_case_refs.map((reference) => {
                                  const citedCase = techniqueAdvice.evidence?.find(
                                    (evidence) =>
                                      evidence.artifact_type === "existing_test_case" &&
                                      evidence.artifact_version_id === reference,
                                  );
                                  return (
                                    <div className="border-t border-border pt-2" key={reference}>
                                      <p className="font-medium">{reference}</p>
                                      <p className="whitespace-pre-wrap break-words">
                                        {citedCase?.text || "Không còn nội dung ca để đối chiếu"}
                                      </p>
                                    </div>
                                  );
                                })}
                              </div>
                            </details>
                          )}
                          <p className="text-ink-muted">
                            Đây là giả thuyết cần QA xác nhận Chưa phải lỗi đã được chứng minh
                          </p>
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={approvedChallenges.includes(item.technique)}
                              disabled={
                                Boolean(aiAction) || !selectedTechniques.includes(item.technique)
                              }
                              onChange={(event) =>
                                setApprovedChallenges((current) =>
                                  event.target.checked
                                    ? [...current, item.technique]
                                    : current.filter((technique) => technique !== item.technique),
                                )
                              }
                            />
                            Tập trung vào giả thuyết này khi tạo ca kiểm thử
                          </label>
                          {!selectedTechniques.includes(item.technique) && (
                            <p className="text-ink-muted">
                              Chọn kỹ thuật này trước khi xác nhận giả thuyết
                            </p>
                          )}
                        </div>
                      )}
                      <p className="text-ink-muted">Dẫn chứng {item.evidence_refs.join("  ")}</p>
                    </div>
                  ))}
                </div>
              )}
              {generationPreview && (
                <div className="space-y-3 border-t border-border pt-4">
                  <p className="font-medium">Bản xem trước chưa được lưu</p>
                  {!!generationPreview.grounding_findings?.length && (
                    <div className="rounded-control border border-warning bg-warning/10 p-3 text-sm">
                      <p className="font-medium">Cần đối chiếu dẫn chứng trước khi lưu</p>
                      {generationPreview.grounding_findings.map((finding) => (
                        <p key={finding.case_index}>
                          Ca {finding.case_index + 1} cần QA xem lại{" "}
                          {finding.unsupported_claims.join("  ")}
                        </p>
                      ))}
                    </div>
                  )}
                  {!!generationPreview.challenge_hypotheses?.length && (
                    <div className="rounded-control border border-border p-3 text-sm">
                      {generationPreview.challenge_hypotheses.map((challenge) => (
                        <div key={challenge.technique}>
                          <p className="font-medium">Giả thuyết QA đã chọn để thử</p>
                          <p>Đầu vào phân biệt {challenge.distinguishing_input}</p>
                          <p>
                            Kết quả AI đề xuất cần QA đối chiếu nguồn {challenge.expected_result}
                          </p>
                          <p className="text-ink-muted">
                            AI được yêu cầu tập trung vào giả thuyết này QA vẫn cần xác nhận ca bên
                            dưới thực sự phân biệt được hành vi sai
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                  {criterionCoverage && (
                    <div className="rounded-control border border-border p-3 text-sm">
                      {criterionCoverage.criterion_ids.length ? (
                        <>
                          <p>
                            Tiêu chí có ca đang hiệu lực{" "}
                            {criterionCoverage.linked_criterion_ids.length}/
                            {criterionCoverage.criterion_ids.length}
                          </p>
                          <p>
                            Nếu lưu bản nháp đã chọn sẽ có liên kết {selectedCriterionIds.size}/
                            {criterionCoverage.criterion_ids.length}
                          </p>
                          {!!remainingCriterionIds.length && (
                            <p>
                              Còn chưa có ca liên kết{" "}
                              {remainingCriterionIds.map(criterionLabel).join("  ")}
                            </p>
                          )}
                          <p className="text-ink-muted">
                            Liên kết của bản nháp chưa phải ca đang hiệu lực Chất lượng kiểm thử vẫn
                            cần được rà soát
                          </p>
                        </>
                      ) : (
                        <p>Yêu cầu chưa có tiêu chí chấp nhận để đối chiếu liên kết ca kiểm thử</p>
                      )}
                    </div>
                  )}
                  {generationPreview.items.map((item, index) => (
                    <div
                      className="flex gap-3 rounded-control border border-border p-3 text-sm"
                      key={index}
                    >
                      <input
                        type="checkbox"
                        aria-label={`Lưu ca kiểm thử ${item.draft.title}`}
                        checked={selectedGenerated.includes(index)}
                        onChange={(event) =>
                          setSelectedGenerated((current) =>
                            event.target.checked
                              ? [...current, index]
                              : current.filter((value) => value !== index),
                          )
                        }
                      />
                      <span>
                        <span className="block font-medium">{item.draft.title}</span>
                        <span className="block">
                          Kỹ thuật {item.draft.techniques.map(valueLabel).join("  ")}
                        </span>
                        {docText(item.draft.preconditions_doc) && (
                          <span className="block">
                            Điều kiện {docText(item.draft.preconditions_doc)}
                          </span>
                        )}
                        {(item.draft.steps || []).map((step) => (
                          <span className="block" key={step.id}>
                            Bước {step.order} {docText(step.action_doc)} Kết quả{" "}
                            {docText(step.expected_doc)}
                          </span>
                        ))}
                        <span className="block">
                          Kết quả cuối {docText(item.draft.expected_result_doc)}
                        </span>
                        <span className="block">
                          Mục cần kiểm chứng {item.coverage_obligations.join("  ")}
                        </span>
                        {!!item.challenge_techniques?.length && (
                          <span className="block">
                            AI cho rằng ca này nhắm tới giả thuyết thuộc kỹ thuật{" "}
                            {item.challenge_techniques.map(valueLabel).join("  ")}
                          </span>
                        )}
                        {!!item.new_criterion_ids?.length && (
                          <span className="block">
                            Tiêu chí chưa có ca liên kết{" "}
                            {item.new_criterion_ids.map(criterionLabel).join("  ")}
                          </span>
                        )}
                        {selectedGenerated.includes(index) &&
                          !!criterionIdsLostWithout(index).length && (
                            <span className="block">
                              Nếu bỏ ca này sẽ thiếu liên kết cho{" "}
                              {criterionIdsLostWithout(index).map(criterionLabel).join("  ")}
                            </span>
                          )}
                        <span className="block">Dẫn chứng {item.evidence_refs.join("  ")}</span>
                        {!!item.evidence_quotes?.length && (
                          <span className="block">
                            Trích dẫn {item.evidence_quotes.map((quote) => quote.quote).join("  ")}
                          </span>
                        )}
                        {!!relevantGeneratedMatches(item, selectedGenerated).length && (
                          <span className="block text-ink-muted">
                            Ca hiện có gần giống{" "}
                            {relevantGeneratedMatches(item, selectedGenerated)
                              .map((caseItem) =>
                                caseItem.id.startsWith("preview:")
                                  ? `Ca ${Number(caseItem.id.slice(8)) + 1} trong bản xem trước`
                                  : caseItem.title || caseItem.id,
                              )
                              .join("  ")}
                          </span>
                        )}
                        {!!relevantGeneratedMatches(item, selectedGenerated).length &&
                          selectedGenerated.includes(index) && (
                            <span className="mt-2 block space-y-2">
                              <select
                                className="apple-input"
                                aria-label={`Cách xử lý ca do AI tạo ${index + 1}`}
                                value={generatedVersionResolutions[index]?.target_version_id || ""}
                                onChange={(event) =>
                                  setGeneratedVersionResolutions((current) => ({
                                    ...current,
                                    [index]: {
                                      target_version_id: event.target.value,
                                      reason: current[index]?.reason || "",
                                    },
                                  }))
                                }
                              >
                                <option value="">Tạo ca riêng</option>
                                {relevantGeneratedMatches(item, selectedGenerated)
                                  .filter((match) => match.target_version_id)
                                  .map((match) => (
                                    <option key={match.id} value={match.target_version_id}>
                                      Tạo phiên bản mới của {match.title || match.id}
                                    </option>
                                  ))}
                              </select>
                              <input
                                className="apple-input"
                                aria-label={`Lý do xử lý ca do AI tạo ${index + 1}`}
                                value={
                                  generatedVersionResolutions[index]?.target_version_id
                                    ? generatedVersionResolutions[index]?.reason || ""
                                    : generatedReasons[index] || ""
                                }
                                onChange={(event) =>
                                  generatedVersionResolutions[index]?.target_version_id
                                    ? setGeneratedVersionResolutions((current) => ({
                                        ...current,
                                        [index]: { ...current[index], reason: event.target.value },
                                      }))
                                    : setGeneratedReasons((current) => ({
                                        ...current,
                                        [index]: event.target.value,
                                      }))
                                }
                              />
                            </span>
                          )}
                      </span>
                    </div>
                  ))}
                  <button
                    className="apple-button"
                    type="button"
                    disabled={
                      !selectedGenerated.length ||
                      Boolean(aiAction) ||
                      selectedGenerated.some(
                        (index) =>
                          relevantGeneratedMatches(
                            generationPreview.items[index],
                            selectedGenerated,
                          ).length &&
                          (generatedVersionResolutions[index]?.target_version_id
                            ? (generatedVersionResolutions[index]?.reason || "").trim().length < 2
                            : (generatedReasons[index] || "").trim().length < 2),
                      )
                    }
                    aria-busy={aiAction === "saving-generated"}
                    onClick={saveGenerated}
                  >
                    {aiAction === "saving-generated"
                      ? "Đang lưu ca đã chọn"
                      : "Lưu ca kiểm thử đã chọn"}
                  </button>
                </div>
              )}
            </div>
          )}
        </Panel>
      )}
      {can("testcase.template.read") && <TestCaseTemplatesPanel project={project} />}
      <SpecializedDesignPanel project={project} requirements={requirements} />
      <AutomationScriptsPanel project={project} tests={tests} />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Bản nháp ca kiểm thử">
          <DataTable
            onSelect={(item) => setSelectedDraftId(item._id)}
            items={drafts}
            empty="Chưa có bản nháp"
            columns={[
              { key: "test_case_key", label: "Mã" },
              { key: "title", label: "Tên" },
              { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "action",
                label: "Duyệt",
                render: (item) => (
                  <span className="flex flex-wrap gap-2">
                    {item.status === "DRAFT" && can("testcase.submit_review") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void reviewDraft(item, "submit");
                        }}
                      >
                        Gửi rà soát
                      </button>
                    )}
                    {item.status === "IN_REVIEW" && can("testcase.review") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void reviewDraft(item, "changes");
                        }}
                      >
                        Yêu cầu sửa
                      </button>
                    )}
                    {item.status === "IN_REVIEW" && can("testcase.approve") && (
                      <button
                        className="apple-button"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void freeze(item);
                        }}
                      >
                        Phê duyệt
                      </button>
                    )}
                  </span>
                ),
              },
            ]}
          />
        </Panel>
        <Panel
          title="Phiên bản ca kiểm thử"
          actions={
            <div className="flex flex-wrap gap-2">
              {selectedTestIds.length > 0 && can("testcase.bulk.update") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Cập nhật nhãn ca kiểm thử",
                      description: `${selectedTestIds.length} ca kiểm thử đã chọn`,
                      confirmLabel: "Cập nhật",
                      fields: [
                        {
                          name: "add",
                          label: "Nhãn cần thêm phân cách bằng dấu phẩy",
                          autoFocus: true,
                        },
                        { name: "remove", label: "Nhãn cần gỡ phân cách bằng dấu phẩy" },
                      ],
                    });
                    if (!answer) return;
                    const splitTags = (value) =>
                      value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean);
                    try {
                      await testingApi.bulkTags(project._id, {
                        artifact_type: "test_case",
                        ids: selectedTestIds,
                        add_tags: splitTags(answer.add),
                        remove_tags: splitTags(answer.remove),
                        idempotency_key: crypto.randomUUID(),
                      });
                      setSelectedTestIds([]);
                      await load();
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Cập nhật nhãn
                </button>
              )}
              {selectedTestIds.length > 0 && can("testcase.bulk.update") && (
                <button
                  className="secondary-button"
                  disabled={!suites.length}
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Thêm vào bộ kiểm thử",
                      description: `${selectedTestIds.length} ca kiểm thử đã chọn`,
                      confirmLabel: "Thêm vào bộ",
                      fields: [
                        {
                          name: "suiteId",
                          label: "Bộ kiểm thử",
                          required: true,
                          autoFocus: true,
                          initialValue: suites[0]?._id || "",
                          options: suites.map((item) => ({ value: item._id, label: item.name })),
                        },
                      ],
                    });
                    if (!answer) return;
                    const suite = suites.find((item) => item._id === answer.suiteId);
                    try {
                      await testingApi.bulkAddToSuite(project._id, {
                        suite_id: answer.suiteId,
                        test_case_ids: selectedTestIds,
                        expected_revision: suite?.revision || 1,
                        idempotency_key: crypto.randomUUID(),
                      });
                      setSelectedTestIds([]);
                      await load();
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Thêm vào bộ
                </button>
              )}
              {selectedTestIds.length > 0 && can("testcase.bulk.update") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Đánh dấu cần rà soát",
                      description: `${selectedTestIds.length} ca kiểm thử đã chọn`,
                      confirmLabel: "Đánh dấu",
                      fields: [
                        {
                          name: "reason",
                          label: "Lý do",
                          required: true,
                          multiline: true,
                          autoFocus: true,
                        },
                      ],
                    });
                    if (!answer) return;
                    try {
                      await testingApi.bulkMarkReviewRequired(project._id, {
                        test_case_ids: selectedTestIds,
                        reason: answer.reason,
                        idempotency_key: crypto.randomUUID(),
                      });
                      setSelectedTestIds([]);
                      await load();
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Cần rà soát
                </button>
              )}
              {selectedTestIds.length > 0 && can("testcase.bulk.archive") && (
                <button
                  className="danger-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Lưu trữ ca kiểm thử",
                      description:
                        "Các ca đang nằm trong lần chạy chưa kết thúc sẽ bị từ chối riêng lẻ",
                      confirmLabel: "Lưu trữ",
                      danger: true,
                      fields: [
                        {
                          name: "reason",
                          label: "Lý do",
                          required: true,
                          multiline: true,
                          autoFocus: true,
                        },
                      ],
                    });
                    if (!answer) return;
                    try {
                      await testingApi.bulkArchive(project._id, {
                        artifact_type: "test_case",
                        ids: selectedTestIds,
                        reason: answer.reason,
                        idempotency_key: crypto.randomUUID(),
                      });
                      setSelectedTestIds([]);
                      await load();
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Lưu trữ
                </button>
              )}
            </div>
          }
        >
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium">
              Tìm kiếm bộ lọc và sắp xếp
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
              <input
                aria-label="Tìm ca kiểm thử"
                className="apple-input xl:col-span-2"
                placeholder="Tìm theo mã hoặc tên"
                value={testFilters.q}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, q: event.target.value });
                  setTestPage(1);
                }}
              />
              <select
                aria-label="Lọc trạng thái ca kiểm thử"
                className="apple-input"
                value={testFilters.status}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, status: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="">Mọi trạng thái</option>
                <option value="ACTIVE">Đang hoạt động</option>
                <option value="NEEDS_UPDATE">Cần cập nhật</option>
                <option value="OBSOLETE">Không còn hiệu lực</option>
              </select>
              <select
                aria-label="Lọc ưu tiên ca kiểm thử"
                className="apple-input"
                value={testFilters.priority}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, priority: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="">Mọi ưu tiên</option>
                <option value="critical">Nghiêm trọng</option>
                <option value="high">Cao</option>
                <option value="medium">Trung bình</option>
                <option value="low">Thấp</option>
              </select>
              <select
                aria-label="Lọc độ mới ca kiểm thử"
                className="apple-input"
                value={testFilters.stale_status}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, stale_status: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="">Mọi độ mới</option>
                <option value="FRESH">Còn phù hợp</option>
                <option value="STALE">Đã lỗi thời</option>
              </select>
              <select
                aria-label="Sắp xếp ca kiểm thử"
                className="apple-input"
                value={testFilters.sort}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, sort: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="-updated_at">Mới cập nhật</option>
                <option value="updated_at">Cũ cập nhật</option>
                <option value="test_case_key">Mã tăng dần</option>
                <option value="title">Tên tăng dần</option>
              </select>
            </div>
          </details>
          <DataTable
            onSelect={async (item) => {
              setSelectedTestId(item._id);
              try {
                setTestVersions(await testingApi.listTestVersions(item._id));
              } catch (reason) {
                setError(messageOf(reason));
              }
            }}
            items={tests}
            selectedIds={
              can("testcase.bulk.update") || can("testcase.bulk.archive")
                ? selectedTestIds
                : undefined
            }
            onSelectionChange={
              can("testcase.bulk.update") || can("testcase.bulk.archive")
                ? setSelectedTestIds
                : undefined
            }
            selectionLabel="Chọn ca kiểm thử"
            empty="Chưa có ca kiểm thử được phê duyệt"
            columns={[
              { key: "test_case_key", label: "Mã" },
              { key: "title", label: "Tên", render: (item) => item.current_version?.title },
              {
                key: "version",
                label: "Phiên bản",
                render: (item) => `v${item.current_version?.version}`,
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "lifecycle",
                label: "Vòng đời",
                render: (item) => (
                  <span className="flex flex-wrap gap-2">
                    {can("testcase.clone") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async (event) => {
                          event.stopPropagation();
                          try {
                            await testingApi.cloneTestCase(item._id, {
                              expected_current_version_id: item.current_version_id,
                              title: `${item.current_version?.title || item.test_case_key} bản sao`,
                            });
                            await load();
                          } catch (reasonValue) {
                            setError(messageOf(reasonValue));
                          }
                        }}
                      >
                        Nhân bản
                      </button>
                    )}
                    {item.status !== "OBSOLETE" && can("testcase.bulk.archive") ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async (event) => {
                          event.stopPropagation();
                          const answer = await ask({
                            title: "Đánh dấu ca kiểm thử không còn hiệu lực",
                            description: `${item.test_case_key} vẫn được giữ trong lịch sử phiên bản`,
                            confirmLabel: "Đánh dấu",
                            danger: true,
                            fields: [
                              {
                                name: "reason",
                                label: "Lý do",
                                initialValue: "Hành vi kiểm thử không còn thuộc phạm vi",
                                required: true,
                                multiline: true,
                                autoFocus: true,
                              },
                            ],
                          });
                          if (!answer) return;
                          try {
                            await testingApi.obsoleteTestCase(item._id, {
                              expected_current_version_id: item.current_version_id,
                              reason: answer.reason,
                            });
                            await load();
                            if (selectedTestId === item._id) {
                              setTestVersions(await testingApi.listTestVersions(item._id));
                            }
                          } catch (reasonValue) {
                            setError(messageOf(reasonValue));
                          }
                        }}
                      >
                        Đánh dấu không còn hiệu lực
                      </button>
                    ) : item.status === "OBSOLETE" && can("testcase.restore") ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async (event) => {
                          event.stopPropagation();
                          const answer = await ask({
                            title: "Khôi phục ca kiểm thử",
                            description: `${item.test_case_key} sẽ trở lại trạng thái hoạt động`,
                            confirmLabel: "Khôi phục",
                            fields: [
                              {
                                name: "reason",
                                label: "Lý do",
                                required: true,
                                multiline: true,
                                autoFocus: true,
                              },
                            ],
                          });
                          if (!answer) return;
                          try {
                            await testingApi.restoreTestCase(item._id, {
                              expected_current_version_id: item.current_version_id,
                              reason: answer.reason,
                            });
                            await load();
                          } catch (reasonValue) {
                            setError(messageOf(reasonValue));
                          }
                        }}
                      >
                        Khôi phục
                      </button>
                    ) : item.status === "OBSOLETE" ? (
                      <span className="text-[11px] text-ink-muted">Đã lưu lịch sử</span>
                    ) : null}
                  </span>
                ),
              },
            ]}
          />
          <Pagination value={testPageInfo} onChange={setTestPage} />
        </Panel>
      </div>
      {selectedTestId && (
        <Panel title="Lịch sử phiên bản ca kiểm thử">
          <DataTable
            items={testVersions}
            empty="Chưa có phiên bản"
            columns={[
              { key: "test_case_key", label: "Mã" },
              { key: "version", label: "Phiên bản", render: (item) => `v${item.version}` },
              { key: "title", label: "Tên" },
              { key: "change_reason", label: "Lý do thay đổi" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
            ]}
          />
          {testVersions
            .filter((version) => version.challenge_hypotheses?.length)
            .map((version) => (
              <details className="border-t border-border p-4 text-sm" key={version._id}>
                <summary className="cursor-pointer font-medium">
                  Giả thuyết thiết kế của phiên bản v{version.version}
                </summary>
                <div className="mt-3">
                  <ChallengeProvenance challenges={version.challenge_hypotheses} />
                </div>
              </details>
            ))}
          {testVersions
            .filter((version) => version.evidence_quotes?.length)
            .map((version) => (
              <details
                className="border-t border-border p-4 text-sm"
                key={`evidence-${version._id}`}
              >
                <summary className="cursor-pointer font-medium">
                  Trích dẫn nguồn của phiên bản v{version.version}
                </summary>
                <div className="mt-3 space-y-2">
                  {version.evidence_quotes.map((item, index) => (
                    <p key={`${item.evidence_ref}-${index}`}>
                      {item.evidence_ref} {item.quote}
                    </p>
                  ))}
                </div>
              </details>
            ))}
        </Panel>
      )}
      {selectedTestId &&
        testVersions[0] &&
        project.current_permissions?.includes("reviewsession.read") && (
          <FormalReviewPanel
            project={project}
            artifactType="TEST_CASE"
            artifactId={selectedTestId}
            artifactVersionId={testVersions[0]._id}
            reviewType="TEST_CASE_REVIEW"
          />
        )}
      {selectedDraft && draftEdit && (
        <>
          <Panel
            title={`Biên tập ${selectedDraft.test_case_key}`}
            actions={
              can("testcase.lint") && can("ai.run_lint") ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    try {
                      setTestLint(await testingApi.lintTestDraft(selectedDraft._id));
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Kiểm tra chất lượng
                </button>
              ) : null
            }
          >
            {!!selectedDraft.challenge_hypotheses?.length && (
              <div className="space-y-2 border-b border-border p-5 text-sm">
                <p className="font-medium">Giả thuyết dùng để thiết kế ca này</p>
                <ChallengeProvenance challenges={selectedDraft.challenge_hypotheses} />
              </div>
            )}
            {!!selectedDraft.evidence_quotes?.length && (
              <div className="space-y-2 border-b border-border p-5 text-sm">
                <p className="font-medium">Trích dẫn nguồn khi AI tạo ca</p>
                {selectedDraft.evidence_quotes.map((item, index) => (
                  <p key={`${item.evidence_ref}-${index}`}>
                    {item.evidence_ref} {item.quote}
                  </p>
                ))}
              </div>
            )}
            {selectedDraft.origin === "ai_generated" &&
              !!selectedDraft.source_evidence?.length &&
              !selectedDraft.evidence_refs?.length && (
                <p className="border-b border-border p-5 text-sm text-ink-muted">
                  Ca đã được chỉnh sửa sau khi AI tạo Dẫn chứng AI ban đầu không còn dùng để xác
                  nhận nội dung hiện tại Cần rà soát lại trước khi duyệt
                </p>
              )}
            <div className="grid gap-4 p-5 lg:grid-cols-2">
              <label className="field-label lg:col-span-2">
                Tên ca kiểm thử
                <input
                  className="apple-input mt-2"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.title}
                  onChange={(event) => changeDraftEdit({ title: event.target.value })}
                />
              </label>
              <div className="grid gap-3 lg:col-span-2 sm:grid-cols-3">
                <select
                  aria-label="Loại bản nháp ca kiểm thử"
                  className="apple-input"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.type}
                  onChange={(event) => changeDraftEdit({ type: event.target.value })}
                >
                  {TEST_CASE_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Ưu tiên bản nháp ca kiểm thử"
                  className="apple-input"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.priority}
                  onChange={(event) => changeDraftEdit({ priority: event.target.value })}
                >
                  {TEST_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Rủi ro bản nháp ca kiểm thử"
                  className="apple-input"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.risk}
                  onChange={(event) => changeDraftEdit({ risk: event.target.value })}
                >
                  {TEST_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </div>
              <label className="field-label lg:col-span-2">
                Mục tiêu kiểm thử
                <textarea
                  className="apple-input mt-2 min-h-20"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.objective}
                  onChange={(event) => changeDraftEdit({ objective: event.target.value })}
                />
              </label>
              <label className="field-label">
                Điều kiện trước
                <textarea
                  className="apple-input mt-2 min-h-24"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.preconditions}
                  onChange={(event) => changeDraftEdit({ preconditions: event.target.value })}
                />
              </label>
              <div className="space-y-4 lg:col-span-2">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="field-label">Các bước kiểm thử</p>
                  {selectedDraft.status === "DRAFT" && can("testcase.update") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        changeDraftEdit({
                          steps: [
                            ...draftEdit.steps,
                            { id: crypto.randomUUID(), action: "", data: "{}", expected: "" },
                          ],
                        })
                      }
                    >
                      Thêm bước
                    </button>
                  )}
                </div>
                {draftEdit.steps.map((step, index) => (
                  <fieldset
                    className="grid gap-3 rounded-xl border border-border p-4 lg:grid-cols-2"
                    key={step.id}
                  >
                    <legend className="px-2 text-[12px] font-semibold">Bước {index + 1}</legend>
                    <label className="field-label">
                      Thao tác
                      <textarea
                        className="apple-input mt-2 min-h-24"
                        disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                        value={step.action}
                        onChange={(event) => {
                          const steps = [...draftEdit.steps];
                          steps[index] = { ...step, action: event.target.value };
                          changeDraftEdit({ steps });
                        }}
                      />
                    </label>
                    <label className="field-label">
                      Kết quả mong đợi
                      <textarea
                        className="apple-input mt-2 min-h-24"
                        disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                        value={step.expected}
                        onChange={(event) => {
                          const steps = [...draftEdit.steps];
                          steps[index] = { ...step, expected: event.target.value };
                          changeDraftEdit({ steps });
                        }}
                      />
                    </label>
                    <label className="field-label lg:col-span-2">
                      Dữ liệu dạng JSON
                      <textarea
                        className="apple-input mt-2 min-h-24 font-mono"
                        disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                        value={step.data}
                        onChange={(event) => {
                          const steps = [...draftEdit.steps];
                          steps[index] = { ...step, data: event.target.value };
                          changeDraftEdit({ steps });
                        }}
                      />
                    </label>
                    {selectedDraft.status === "DRAFT" &&
                      can("testcase.update") &&
                      draftEdit.steps.length > 1 && (
                        <button
                          className="secondary-button w-fit"
                          type="button"
                          onClick={() =>
                            changeDraftEdit({
                              steps: draftEdit.steps.filter((_, stepIndex) => stepIndex !== index),
                            })
                          }
                        >
                          Xóa bước
                        </button>
                      )}
                  </fieldset>
                ))}
              </div>
              <label className="field-label">
                Dữ liệu dùng chung dạng JSON
                <textarea
                  className="apple-input mt-2 min-h-28 font-mono"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.testData}
                  onChange={(event) => changeDraftEdit({ testData: event.target.value })}
                />
              </label>
              <label className="field-label">
                Phiên bản bộ dữ liệu tham số
                <select
                  aria-label="Phiên bản bộ dữ liệu của bản nháp"
                  className="apple-input mt-2 min-h-28"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  multiple
                  value={draftEdit.dataSetVersionIds}
                  onChange={(event) =>
                    changeDraftEdit({
                      dataSetVersionIds: Array.from(
                        event.target.selectedOptions,
                        (option) => option.value,
                      ),
                    })
                  }
                >
                  {dataSets.map((item) => (
                    <option key={item.current_version_id} value={item.current_version_id}>
                      {item.name} v{item.current_version?.version}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Điều kiện kiểm thử đã phê duyệt
                <select
                  aria-label="Điều kiện kiểm thử của bản nháp"
                  className="apple-input mt-2 min-h-28"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  multiple
                  value={draftEdit.testConditionIds}
                  onChange={(event) =>
                    changeDraftEdit({
                      testConditionIds: Array.from(
                        event.target.selectedOptions,
                        (option) => option.value,
                      ),
                    })
                  }
                >
                  {testConditions.map((item) => (
                    <option key={item._id} value={item._id}>
                      {item.condition_key} {item.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Kết quả mong đợi tổng thể
                <textarea
                  className="apple-input mt-2 min-h-28"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.expected}
                  onChange={(event) => changeDraftEdit({ expected: event.target.value })}
                />
              </label>
              <label className="field-label lg:col-span-2">
                Điều kiện sau
                <textarea
                  className="apple-input mt-2 min-h-24"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.postconditions}
                  onChange={(event) => changeDraftEdit({ postconditions: event.target.value })}
                />
              </label>
              <label className="field-label">
                Kỹ thuật kiểm thử phân tách bằng dấu phẩy
                <input
                  className="apple-input mt-2"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.techniques}
                  onChange={(event) => changeDraftEdit({ techniques: event.target.value })}
                />
              </label>
              <label className="field-label">
                Nhãn phân tách bằng dấu phẩy
                <input
                  className="apple-input mt-2"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.tags}
                  onChange={(event) => changeDraftEdit({ tags: event.target.value })}
                />
              </label>
              <label className="field-label">
                Trạng thái tự động hóa
                <select
                  className="apple-input mt-2"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.automationStatus}
                  onChange={(event) => changeDraftEdit({ automationStatus: event.target.value })}
                >
                  {["manual", "candidate", "automated"].map((value) => (
                    <option value={value} key={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Mã người phụ trách
                <input
                  className="apple-input mt-2"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  value={draftEdit.ownerId}
                  onChange={(event) => changeDraftEdit({ ownerId: event.target.value })}
                />
              </label>
              <label className="field-label">
                Tệp đính kèm
                <input
                  className="apple-input mt-2"
                  type="file"
                  disabled={selectedDraft.status !== "DRAFT" || !can("testcase.update")}
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    if (!file) return;
                    try {
                      const uploaded = await uploadAssetAPI(file);
                      changeDraftEdit({
                        attachments: [...draftEdit.attachments, uploaded.data],
                      });
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                />
                {draftEdit.attachments.map((attachment) => (
                  <span
                    className="mt-2 block break-all text-[11px] text-ink-muted"
                    key={attachment.url}
                  >
                    {attachment.filename}
                  </span>
                ))}
              </label>
              {selectedDraft.status === "DRAFT" && can("testcase.update") && (
                <div className="flex flex-wrap items-center gap-3 lg:col-span-2">
                  <button
                    className="secondary-button w-fit"
                    type="button"
                    disabled={draftSaveState === "saving"}
                    onClick={saveDraft}
                  >
                    Lưu bản nháp
                  </button>
                  <span className="text-[12px] text-ink-muted" aria-live="polite">
                    {draftSaveState === "saving"
                      ? "Đang tự động lưu"
                      : draftSaveState === "pending"
                        ? "Có thay đổi chưa lưu"
                        : draftSaveState === "invalid"
                          ? "JSON chưa hợp lệ nên chưa tự động lưu"
                          : draftSaveState === "error"
                            ? "Tự động lưu thất bại"
                            : "Đã tự động lưu"}
                  </span>
                </div>
              )}
            </div>
            {testLint && (
              <div className="border-t border-border">
                <DataTable
                  items={testLint.findings}
                  empty="Không có vấn đề chất lượng"
                  columns={[
                    { key: "severity", label: "Mức độ" },
                    { key: "code", label: "Mã" },
                    { key: "message", label: "Nội dung" },
                  ]}
                />
              </div>
            )}
          </Panel>
          <ReviewCommentsPanel
            projectId={project._id}
            artifactType="test_case_draft"
            artifactId={selectedDraft._id}
          />
          <CollaborationPanel
            project={project}
            artifactType="test_case"
            artifactId={selectedDraft._id}
            onResolved={load}
          />
        </>
      )}
      <div className="grid gap-5 xl:grid-cols-2">
        {can("testcase.create") && (
          <TestCaseCreateModal
            isOpen={creatingTest}
            onClose={() => setCreatingTest(false)}
            form={form}
            setForm={setForm}
            dataSets={dataSets}
            testConditions={testConditions}
            repositoryNodes={repositoryNodes}
            reusableSteps={reusableSteps}
            onSubmit={create}
          />
        )}
        <ScenariosPanel
          can={can}
          scenarios={scenarios}
          filters={scenarioFilters}
          setFilters={setScenarioFilters}
          isCreating={creatingScenario}
          setCreating={setCreatingScenario}
          form={scenarioForm}
          setForm={setScenarioForm}
          testConditions={testConditions}
          onSubmit={createScenario}
          ask={ask}
          reload={load}
          onError={setError}
        />
      </div>
      <DataSetsPanel
        can={can}
        canRead={canReadTestData}
        items={dataSets}
        isCreating={creatingDataSet}
        setCreating={setCreatingDataSet}
        form={dataSetForm}
        setForm={setDataSetForm}
        onSubmit={createDataSet}
        ask={ask}
        reload={load}
        onError={setError}
      />
      <TestRepositoryPanel project={project} can={can} onError={setError} />
      {duplicates.length > 0 && (
        <Panel title="Các ca kiểm thử có khả năng trùng">
          <DataTable
            items={duplicates.map((item, index) => ({ ...item, _id: index }))}
            columns={[
              {
                key: "left",
                label: "Ca kiểm thử bên trái",
                render: (item) => item.left.test_case_key,
              },
              {
                key: "right",
                label: "Ca kiểm thử bên phải",
                render: (item) => item.right.test_case_key,
              },
              { key: "similarity", label: "Độ tương đồng" },
              { key: "reasons", label: "Bằng chứng", render: (item) => item.reasons.join(", ") },
            ]}
          />
        </Panel>
      )}
      <ApiArtifactsPanel
        projectId={project._id}
        can={can}
        ask={ask}
        apiImport={apiImport}
        setApiImport={setApiImport}
        artifacts={apiArtifacts}
        operations={operations}
        compareFrom={apiCompareFrom}
        setCompareFrom={setApiCompareFrom}
        compareTo={apiCompareTo}
        setCompareTo={setApiCompareTo}
        difference={apiDifference}
        setDifference={setApiDifference}
        onTestImportPreview={(preview) => {
          setTestImport(preview);
          requestAnimationFrame(() => {
            testImportPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
          });
        }}
        reload={load}
        onError={setError}
      />
      <div ref={testImportPanelRef}>
        <TestCaseTransferPanel
          projectId={project._id}
          can={can}
          preview={testImport}
          setPreview={setTestImport}
          reload={load}
          onError={setError}
        />
      </div>
      {dialog}
    </WorkspacePage>
  );
}
