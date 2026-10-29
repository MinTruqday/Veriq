"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../components/DataTable";
import FilePicker from "../../components/FilePicker";
import FormalReviewPanel from "../../components/FormalReviewPanel";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import TestCaseTemplatesPanel from "../../components/TestCaseTemplatesPanel";
import SpecializedDesignPanel from "../../components/SpecializedDesignPanel";
import AutomationScriptsPanel from "../../components/AutomationScriptsPanel";
import AgentRunPanel from "../../components/AgentRunPanel";
import CollaborationPanel from "../../components/CollaborationPanel";
import {
  ErrorState,
  LoadingState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  WorkspaceSectionNav,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import {
  testCaseSubsectionItems,
  testDesignSectionItems,
} from "@/shared/components/layout/navigation";
import { testingApi } from "../../services/testing.service";
import { docText, messageOf, valueLabel } from "../../lib/testing";
import DocumentEditor from "../../editor/DocumentEditor";
import ApiArtifactsPanel from "./test-design/ApiArtifactsPanel";
import DataSetsPanel from "./test-design/DataSetsPanel";
import ScenariosPanel from "./test-design/ScenariosPanel";
import TestCaseCreateModal from "./test-design/TestCaseCreateModal";
import TestCaseOwnerRecommendation from "./test-design/TestCaseOwnerRecommendation";
import TestSetEditorModal from "./test-design/TestSetEditorModal";
import TestCaseCustomValues from "./test-design/TestCaseCustomValues";
import TestCaseCustomFieldManager from "./test-design/TestCaseCustomFieldManager";
import TestCaseCompareWorkspace from "./test-design/TestCaseCompareWorkspace";
import StructuredValueEditor from "../../components/StructuredValueEditor";
import {
  isGroupApprovalComparisonCurrent,
  recordAiComparison,
  requiresAiComparison,
  unreviewedAiDrafts,
} from "./test-design/testCaseApproval.logic.mjs";
import TestCaseTransferPanel from "./test-design/TestCaseTransferPanel";
import { testDesignAccess } from "./test-design/testDesignAccess.logic.mjs";
import TestAdequacyPanel from "./design/TestAdequacyPanel";
import TestRepositoryPanel from "./test-design/TestRepositoryPanel";
import {
  createDataSetForm,
  createScenarioForm,
  createTestCaseForm,
  testDataEntriesToObject,
  TEST_CASE_TYPES,
  TEST_CASE_ASSESSMENT_LEVELS,
  TEST_SCENARIO_CATEGORIES,
  buildTestCaseDraftChanges,
} from "./test-design/testDesign.model";

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

export default function TestDesignPage({ project, workspaceView }) {
  const { ask, dialog } = useActionDialog();
  const pathname = usePathname();
  const [requirements, setRequirements] = useState([]);
  const [testConditions, setTestConditions] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [dataSets, setDataSets] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [tests, setTests] = useState([]);
  const [suites, setSuites] = useState([]);
  const [testSetDialog, setTestSetDialog] = useState(null);
  const [repositoryNodes, setRepositoryNodes] = useState([]);
  const [testCaseCustomFields, setTestCaseCustomFields] = useState([]);
  const [projectMembers, setProjectMembers] = useState([]);
  const [projectMembersUnavailable, setProjectMembersUnavailable] = useState(false);
  const [customFieldManagerOpen, setCustomFieldManagerOpen] = useState(false);
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
  const [automationRuns, setAutomationRuns] = useState([]);
  const [automationRunsError, setAutomationRunsError] = useState("");
  const [automationRunsLoading, setAutomationRunsLoading] = useState(false);
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
  const [selectedApprovalDraftIds, setSelectedApprovalDraftIds] = useState([]);
  const [comparedApprovalDraftRevisions, setComparedApprovalDraftRevisions] = useState({});
  const [approvingDraftGroup, setApprovingDraftGroup] = useState(false);
  const pendingGroupRequest = useRef(null);
  const [comparisonDraftId, setComparisonDraftId] = useState("");
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
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const loadSequence = useRef(0);
  const currentProjectId = useRef(project._id);
  currentProjectId.current = project._id;
  const [creatingTest, setCreatingTest] = useState(false);
  const [creatingScenario, setCreatingScenario] = useState(false);
  const [creatingDataSet, setCreatingDataSet] = useState(false);
  const [savingCreation, setSavingCreation] = useState(false);
  const creationInFlight = useRef(new Set());
  const testImportPanelRef = useRef(null);
  const can = (permission) => project.current_permissions?.includes(permission);
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const canManageTestCaseFields = can("project.update") && memberRoles.includes("QA");
  const designSectionItems = useMemo(() => testDesignSectionItems(project._id), [project._id]);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const caseTabFromPath = pathname.split("/ca-kiem-thu/")[1]?.split("/")[0];
  const requestedCaseTab =
    {
      ai: "agent-runs",
      "do-day-du": "adequacy",
      "kich-ban": "scenarios",
      mau: "templates",
      "tu-dong-hoa": "automation",
      api: "api",
      "nhap-xuat": "import",
    }[caseTabFromPath] || "cases";
  const caseTab = requestedCaseTab;
  const access = testDesignAccess({ workspaceView, caseTab, permissions });
  const isCaseWorkspace = workspaceView === "" || workspaceView === "cases";
  const showCases = access.showCases;
  const showAdequacy = isCaseWorkspace && caseTab === "adequacy";
  const showAgentRuns = isCaseWorkspace && caseTab === "agent-runs";
  const showScenarios = isCaseWorkspace && caseTab === "scenarios";
  const showTemplates = isCaseWorkspace && caseTab === "templates";
  const showAutomation = isCaseWorkspace && caseTab === "automation";
  const showApi = isCaseWorkspace && caseTab === "api";
  const showImport = access.showImport;
  const canReadTestCases = access.canReadTestCases;
  const canReadTestData = project.current_permissions?.includes("testdata.read");
  const load = useCallback(async () => {
    const requestProjectId = project._id;
    if (requestProjectId !== currentProjectId.current) return false;
    const requestSequence = ++loadSequence.current;
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      pendingGroupRequest.current = null;
      setTestImport(null);
      setTestSetDialog(null);
      setCreatingTest(false);
      setCreatingScenario(false);
      setCreatingDataSet(false);
      setCustomFieldManagerOpen(false);
      setSavingCreation(false);
      setForm(createTestCaseForm());
      setScenarioForm(createScenarioForm());
      setDataSetForm(createDataSetForm());
      setApiImport({ filename: "openapi.json", format: "openapi", content: "" });
      setRequirements([]);
      setTestConditions([]);
      setScenarios([]);
      setDataSets([]);
      setDrafts([]);
      setTests([]);
      setSuites([]);
      setRepositoryNodes([]);
      setReusableSteps([]);
      setTestCaseCustomFields([]);
      setProjectMembers([]);
      setProjectMembersUnavailable(false);
      setApiArtifacts([]);
      setOperations([]);
      setApiCompareFrom("");
      setApiCompareTo("");
      setApiDifference(null);
      setTestPageInfo(null);
      setSelectedTestIds([]);
      setSelectedRequirement("");
      setSelectedDraftId("");
      setSelectedApprovalDraftIds([]);
      setComparedApprovalDraftRevisions({});
      setComparisonDraftId("");
      setSelectedTestId("");
      setTestVersions([]);
      setDraftEdit(null);
      setDraftDirty(false);
      setTestLint(null);
      setTestPage(1);
      setError("");
    }
    if (!initialDataLoaded.current) {
      setInitialLoading(true);
      setInitialLoadFailed(false);
    }
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
        customFieldValues,
        apiArtifactValues,
        operationValues,
        memberResult,
      ] = await Promise.all([
        (showCases || showAgentRuns || showScenarios || showAdequacy) &&
        permissions.includes("requirement.read")
          ? testingApi.listRequirements(project._id, {
              page_size: 500,
              status: "BASELINED",
              include_acceptance_criteria: true,
            })
          : Promise.resolve([]),
        (showCases || showScenarios) && permissions.includes("testcondition.read")
          ? testingApi.listTestConditions(project._id, { status: "APPROVED", page_size: 200 })
          : Promise.resolve({ items: [] }),
        showScenarios && permissions.includes("testscenario.read")
          ? testingApi.listScenarios(project._id, scenarioFilters)
          : Promise.resolve([]),
        (showCases || workspaceView === "test-data") && canReadTestData
          ? testingApi.listDataSets(project._id)
          : Promise.resolve([]),
        access.canLoadDrafts ? testingApi.listTestDrafts(project._id) : Promise.resolve([]),
        access.canLoadTestCases
          ? testingApi.listTestCasePage(project._id, {
              ...testFilters,
              page: testPage,
              page_size: 50,
            })
          : Promise.resolve({ items: [], total: 0 }),
        (showCases || workspaceView === "test-sets") && permissions.includes("testsuite.read")
          ? testingApi.listSuites(project._id)
          : Promise.resolve([]),
        access.canLoadRepository ? testingApi.listTestRepository(project._id) : Promise.resolve([]),
        access.canLoadRepository
          ? testingApi.listReusableTestSteps(project._id)
          : Promise.resolve([]),
        showCases && permissions.includes("testcase.read")
          ? testingApi.listTestCaseCustomFields(project._id)
          : Promise.resolve([]),
        showApi && permissions.includes("apiartifact.read")
          ? testingApi.listApiArtifacts(project._id)
          : Promise.resolve([]),
        showApi && permissions.includes("apiartifact.read")
          ? testingApi.listApiOperations(project._id)
          : Promise.resolve([]),
        showCases && permissions.includes("project.members.read")
          ? testingApi
              .listMembers(project._id)
              .then((items) => ({ items: items || [], unavailable: false }))
              .catch(() => ({ items: [], unavailable: true }))
          : Promise.resolve({ items: [], unavailable: false }),
      ]);
      if (
        requestSequence !== loadSequence.current ||
        requestProjectId !== currentProjectId.current
      ) {
        return false;
      }
      setRequirements(requirementValues);
      setTestConditions(testConditionValues.items || []);
      setScenarios(scenarioValues);
      setDataSets(dataSetValues);
      setDrafts(draftValues);
      setSelectedApprovalDraftIds((current) => {
        const eligible = new Set(
          draftValues.filter((draft) => draft.status === "IN_REVIEW").map((draft) => draft._id),
        );
        return current.filter((id) => eligible.has(id));
      });
      setTests(testValues.items);
      setTestPageInfo(testValues);
      setSuites(suiteValues);
      setRepositoryNodes(repositoryValues);
      setReusableSteps(reusableStepValues);
      setTestCaseCustomFields(customFieldValues);
      setProjectMembers((memberResult.items || []).filter((item) => item.status === "ACTIVE"));
      setProjectMembersUnavailable(memberResult.unavailable);
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
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
      return true;
    } catch (reason) {
      if (
        requestSequence !== loadSequence.current ||
        requestProjectId !== currentProjectId.current
      ) {
        return false;
      }
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
      setError(messageOf(reason));
      return false;
    } finally {
      if (
        requestSequence === loadSequence.current &&
        requestProjectId === currentProjectId.current
      ) {
        setInitialLoading(false);
      }
    }
  }, [
    access.canLoadDrafts,
    access.canLoadRepository,
    access.canLoadTestCases,
    canReadTestData,
    initialDataLoaded,
    loadedProjectId,
    permissions,
    project._id,
    scenarioFilters,
    showAdequacy,
    showAgentRuns,
    showApi,
    showCases,
    showScenarios,
    testFilters,
    testPage,
    workspaceView,
  ]);
  useEffect(() => {
    void load();
  }, [load]);
  const canReadAutomationRuns =
    permissions.includes("automation.read") || permissions.includes("proposal.read");
  useEffect(() => {
    if (!showAgentRuns || !canReadAutomationRuns) {
      setAutomationRuns([]);
      setAutomationRunsError("");
      setAutomationRunsLoading(false);
      return undefined;
    }
    let active = true;
    let pending = false;
    const refresh = async () => {
      if (pending) return;
      pending = true;
      setAutomationRunsLoading(true);
      try {
        const values = await testingApi.listAutomationRuns(project._id);
        if (active) {
          setAutomationRuns(values || []);
          setAutomationRunsError("");
        }
      } catch (reason) {
        if (active) setAutomationRunsError(messageOf(reason));
      } finally {
        pending = false;
        if (active) setAutomationRunsLoading(false);
      }
    };
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [canReadAutomationRuns, project._id, showAgentRuns]);
  const selectedRequirementRecord = requirements.find(
    (item) => item.current_version_id === selectedRequirement,
  );
  const selectedRequirementVersion = selectedRequirementRecord?.current_version;
  const requirementEventId =
    selectedRequirement && Number.isInteger(selectedRequirementVersion?.revision)
      ? `requirement-version:${selectedRequirement}:${selectedRequirementVersion.revision}:${selectedRequirementVersion.status || "DRAFT"}`
      : "";
  const requirementAutomationRun = requirementEventId
    ? automationRuns.find(
        (run) =>
          run.trigger === "REQUIREMENT_CHANGED" &&
          run.source_event_id === requirementEventId &&
          run.evidence?.some(
            (item) =>
              item.artifact_type === "requirement_version" &&
              item.artifact_version_id === selectedRequirement &&
              item.artifact_revision === selectedRequirementVersion?.revision,
          ),
      ) || null
    : null;
  const actionableDrafts = drafts.filter((item) => item.status !== "APPROVED");
  const selectedDraft = actionableDrafts.find((item) => item._id === selectedDraftId) || null;
  const lintDraftId = selectedDraft?._id;
  const lintDraftRevision = selectedDraft?.revision;
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
      test_level: selectedDraft.test_level || "",
      test_kind: selectedDraft.test_kind || "",
      expected_impact: selectedDraft.expected_impact || "unassessed",
      assessment_reason: selectedDraft.assessment_reason || "",
      requirementVersionIds: selectedDraft.requirement_version_ids || [],
      acceptanceCriterionIds: selectedDraft.acceptance_criterion_ids || [],
      repositoryNodeId: selectedDraft.repository_node_id || "",
      bdd: selectedDraft.bdd
        ? {
            feature: selectedDraft.bdd.feature || "",
            scenario: selectedDraft.bdd.scenario || "",
            steps: (selectedDraft.bdd.steps || []).map((step) => ({
              id: step.id,
              keyword: step.keyword,
              text: step.text || "",
              ...(step.reusable_step_version_id
                ? { reusable_step_version_id: step.reusable_step_version_id }
                : {}),
            })),
          }
        : null,
      requiredSkills: (selectedDraft.required_skills || []).join(", "),
      objective: docText(selectedDraft.objective_doc),
      preconditions: docText(selectedDraft.preconditions_doc),
      steps: (selectedDraft.steps || []).map((step) => ({
        id: step.id,
        action: docText(step.action_doc),
        data: step.test_data || {},
        expected: docText(step.expected_doc),
      })),
      testData: selectedDraft.test_data || {},
      expected: docText(selectedDraft.expected_result_doc),
      postconditions: docText(selectedDraft.postconditions_doc),
      techniques: (selectedDraft.techniques || []).join(", "),
      tags: (selectedDraft.tags || []).join(", "),
      ownerId: selectedDraft.owner_id || "",
      automationStatus: selectedDraft.automation_status || "manual",
      attachments: selectedDraft.attachments || [],
      dataSetVersionIds: selectedDraft.data_set_version_ids || [],
      testConditionIds: selectedDraft.test_condition_ids || [],
      customValues: selectedDraft.custom_values || {},
    });
    setDraftDirty(false);
    setDraftSaveState("saved");
  }, [selectedDraft]);
  useEffect(() => {
    if (!lintDraftId || !permissions.includes("testcase.read")) {
      setTestLint(null);
      return undefined;
    }
    let active = true;
    testingApi.getLatestTestDraftLint(lintDraftId).then(
      (result) => {
        if (active) setTestLint(result || null);
      },
      (reason) => {
        if (active && reason?.status !== 404) setError(messageOf(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [lintDraftId, lintDraftRevision, permissions]);
  const changeDraftEdit = (next) => {
    draftSequence.current += 1;
    setDraftEdit((value) => (typeof next === "function" ? next(value) : { ...value, ...next }));
    setDraftDirty(true);
    setDraftSaveState("pending");
  };
  const submitCreation = async (event, createArtifact) => {
    event.preventDefault();
    const requestProjectId = project._id;
    if (
      requestProjectId !== currentProjectId.current ||
      creationInFlight.current.has(requestProjectId)
    ) {
      return;
    }
    creationInFlight.current.add(requestProjectId);
    setSavingCreation(true);
    try {
      await createArtifact();
      if (requestProjectId !== currentProjectId.current) return;
      await load();
    } catch (reason) {
      if (requestProjectId !== currentProjectId.current) return;
      setError(messageOf(reason));
    } finally {
      creationInFlight.current.delete(requestProjectId);
      if (requestProjectId === currentProjectId.current) setSavingCreation(false);
    }
  };
  const create = (event) =>
    submitCreation(event, async () => {
      await testingApi.createTestDraft(project._id, {
        title: form.title,
        type: form.type,
        priority: form.priority,
        risk: form.risk,
        test_level: form.testLevel || null,
        test_kind: form.testKind || null,
        expected_impact: form.expectedImpact,
        assessment_reason: form.assessmentReason,
        required_skills: form.requiredSkills
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        owner_id:
          permissions.includes("project.members.read") && !projectMembersUnavailable
            ? form.ownerId || null
            : null,
        custom_values: form.customValues || {},
        objective_doc: form.objective,
        preconditions_doc: form.preconditions,
        steps:
          form.testStyle === "BDD"
            ? []
            : form.steps.map((step, index) => ({
                id: step.id,
                order: index + 1,
                action_doc: step.action,
                test_data: testDataEntriesToObject(step.data),
                expected_doc: step.expected,
              })),
        test_data: testDataEntriesToObject(form.testData),
        expected_result_doc: form.expectedResult,
        postconditions_doc: form.postconditions,
        tags: form.tags
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        techniques: form.techniques
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        automation_status: form.automationStatus,
        attachments: [],
        data_set_version_ids: form.dataSetVersionIds,
        test_condition_ids: form.testConditionIds,
        repository_node_id: form.repositoryNodeId || null,
        requirement_version_ids: form.requirementVersionIds,
        acceptance_criterion_ids: form.acceptanceCriterionIds,
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
    });
  const createScenario = (event) =>
    submitCreation(event, async () => {
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
    });
  const createDataSet = (event) =>
    submitCreation(event, async () => {
      await testingApi.createDataSet(project._id, {
        name: dataSetForm.name,
        variables: dataSetForm.variables || {},
        secret_refs: dataSetForm.secretRefs || {},
      });
      setDataSetForm(createDataSetForm());
      setCreatingDataSet(false);
    });
  const configureTestCaseField = async () => {
    await ask({
      title: "Thêm trường mở rộng cho ca kiểm thử",
      description: "Trường được lưu có kiểu dữ liệu và áp dụng cho các ca trong dự án này.",
      confirmLabel: "Tạo trường",
      fields: [
        { name: "key", label: "Mã trường (chữ thường, số, gạch dưới)", required: true },
        { name: "label", label: "Tên hiển thị", required: true },
        {
          name: "value_type",
          label: "Kiểu dữ liệu",
          options: [
            { value: "text", label: "Văn bản" },
            { value: "number", label: "Số" },
            { value: "boolean", label: "Có / Không" },
            { value: "date", label: "Ngày" },
            { value: "choice", label: "Danh sách lựa chọn" },
          ],
        },
        {
          name: "required",
          label: "Bắt buộc khi QA duyệt",
          options: [
            { value: "false", label: "Không" },
            { value: "true", label: "Có" },
          ],
        },
        {
          name: "choices",
          label: "Các lựa chọn (mỗi dòng một giá trị, chỉ dùng cho kiểu danh sách)",
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const choices = (answer.choices || "")
            .split("\n")
            .map((value) => value.trim())
            .filter(Boolean);
          await testingApi.createTestCaseCustomField(project._id, {
            key: answer.key.trim(),
            label: answer.label.trim(),
            value_type: answer.value_type,
            required: answer.required === "true",
            choices,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const createTestSet = async () => {
    setTestSetDialog({ mode: "create", suite: null });
  };
  const updateTestSet = async (suite) => {
    setTestSetDialog({ mode: "edit", suite });
  };
  const saveTestSet = async ({ name, suiteType, versionIds }) => {
    if (testSetDialog?.mode === "edit" && testSetDialog.suite) {
      const suite = testSetDialog.suite;
      await testingApi.updateSuite(suite._id, {
        expected_revision: suite.revision,
        name: name.trim(),
        suite_type: suiteType,
        test_case_version_ids: versionIds,
      });
    } else {
      await testingApi.createSuite({
        project_id: project._id,
        name: name.trim(),
        suite_type: suiteType,
        test_case_version_ids: versionIds,
      });
    }
    setTestSetDialog(null);
    await load();
  };
  const archiveTestSet = async (suite) => {
    await ask({
      title: "Lưu trữ bộ kiểm thử",
      description: suite.name,
      confirmLabel: "Lưu trữ",
      danger: true,
      fields: [{ name: "reason", label: "Lý do", required: true, multiline: true }],
      onConfirm: async (answer) => {
        try {
          await testingApi.archiveSuite(suite._id, {
            expected_revision: suite.revision,
            reason: answer.reason.trim(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const freeze = async (draft) => {
    if (unreviewedAiDrafts([draft], comparedApprovalDraftRevisions).length) {
      setError("Cần đối chiếu bản gốc và đề xuất AI ở revision hiện tại trước khi duyệt ca này.");
      setComparisonDraftId(draft._id);
      return;
    }
    await ask({
      title: "Phê duyệt ca kiểm thử",
      description: `${draft.test_case_key} sẽ trở thành phiên bản bất biến và được dùng trong lần chạy`,
      confirmLabel: "Phê duyệt",
      onConfirm: async () => {
        try {
          await testingApi.freezeTestDraft(
            draft._id,
            draft.revision,
            "Phê duyệt sau rà soát của con người",
          );
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const approveDraftGroup = async () => {
    const selected = actionableDrafts.filter(
      (draft) => selectedApprovalDraftIds.includes(draft._id) && draft.status === "IN_REVIEW",
    );
    if (!selected.length || selected.length !== selectedApprovalDraftIds.length) {
      setError("Chọn các ca đang ở trạng thái chờ duyệt; nhóm không được tự bỏ qua ca khác.");
      return;
    }
    const selectionSummary = selected
      .slice(0, 6)
      .map((draft) => `${draft.test_case_key} · ${draft.title}`)
      .join("\n");
    const omittedCount = selected.length - Math.min(selected.length, 6);
    const unreviewed = unreviewedAiDrafts(selected, comparedApprovalDraftRevisions);
    if (unreviewed.length) {
      setError(
        `Mở và đối chiếu bản gốc với đề xuất AI cho ${unreviewed.length} ca được đánh dấu trước khi duyệt nhóm.`,
      );
      return;
    }
    await ask({
      title: `Duyệt nhóm ${selected.length} ca kiểm thử`,
      description: [
        "Các ca được duyệt cùng một giao dịch. Nếu một ca không hợp lệ hoặc phiên bản đã đổi, toàn bộ nhóm sẽ rollback.",
        selectionSummary,
        omittedCount ? `Còn ${omittedCount} ca khác trong nhóm.` : "",
      ]
        .filter(Boolean)
        .join("\n"),
      confirmLabel: "Đối chiếu và duyệt nhóm",
      fields: [
        {
          name: "note",
          label: "Ghi chú duyệt",
          required: true,
          minLength: 2,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        setApprovingDraftGroup(true);
        try {
          if (project._id !== currentProjectId.current) return;
          const selectionKey = selected
            .map((draft) => `${draft._id}:${draft.revision}`)
            .sort()
            .join("|");
          if (
            !pendingGroupRequest.current ||
            pendingGroupRequest.current.selectionKey !== selectionKey ||
            pendingGroupRequest.current.reviewNote !== answer.note.trim()
          ) {
            const comparisons = await Promise.all(
              selected.map(async (draft) => ({
                draft,
                comparison: await testingApi.compareTestDraft(draft._id),
              })),
            );
            if (project._id !== currentProjectId.current) return;
            const changedComparison = comparisons.find(
              ({ draft, comparison }) =>
                !isGroupApprovalComparisonCurrent(
                  draft,
                  comparison,
                  comparedApprovalDraftRevisions,
                ),
            );
            if (changedComparison) {
              pendingGroupRequest.current = null;
              setComparedApprovalDraftRevisions((current) => {
                const next = { ...current };
                for (const item of comparisons) delete next[item.draft._id];
                return next;
              });
              await load();
              throw new Error(
                "Có ca đã đổi phiên bản hoặc nguồn sau lần đối chiếu. Nhóm chưa được duyệt; hãy mở lại từng ca để xem bản mới nhất.",
              );
            }
            const items = comparisons.map(({ draft, comparison }) => ({
              draft_id: draft._id,
              expected_revision: comparison.draft.revision,
              comparison_token: comparison.comparison_token,
            }));
            pendingGroupRequest.current = {
              selectionKey,
              reviewNote: answer.note.trim(),
              payload: {
                items,
                operation_id: crypto.randomUUID(),
                review_note: answer.note.trim(),
              },
            };
          }
          const response = await testingApi.acceptTestDraftGroup(
            project._id,
            pendingGroupRequest.current.payload,
          );
          if (project._id !== currentProjectId.current) return;
          const approvedDraftIds = [...(response?.draft_ids || [])].sort();
          const requestedDraftIds = selected.map((draft) => draft._id).sort();
          const publishedVersionIds = response?.version_ids || [];
          if (
            response?.count !== requestedDraftIds.length ||
            typeof response?.batch_id !== "string" ||
            !response.batch_id ||
            approvedDraftIds.length !== requestedDraftIds.length ||
            approvedDraftIds.some((draftId, index) => draftId !== requestedDraftIds[index]) ||
            publishedVersionIds.length !== requestedDraftIds.length ||
            new Set(publishedVersionIds).size !== publishedVersionIds.length ||
            publishedVersionIds.some((versionId) => typeof versionId !== "string" || !versionId)
          ) {
            pendingGroupRequest.current = null;
            await load();
            throw new Error(
              "Phản hồi duyệt nhóm không khớp danh sách đã chọn. Đã tải lại dữ liệu; hãy kiểm tra trạng thái từng ca trước khi thao tác tiếp.",
            );
          }
          pendingGroupRequest.current = null;
          const approvedDraftIdSet = new Set(approvedDraftIds);
          setDrafts((current) => current.filter((draft) => !approvedDraftIdSet.has(draft._id)));
          setSelectedApprovalDraftIds([]);
          const refreshed = await load();
          if (!refreshed) {
            setError(
              `Nhóm ${response.count} ca đã được duyệt và lưu nguyên tử, nhưng chưa tải lại được danh sách. Hãy tải lại trang; không gửi lại thao tác duyệt.`,
            );
            return;
          }
          if (response.derived_pending_version_ids?.length) {
            setError(
              `Đã duyệt ${response.count} ca trong giao dịch; ${response.derived_pending_version_ids.length} phiên bản đang chờ đồng bộ truy vết hoặc tìm kiếm.`,
            );
          }
        } catch (reason) {
          if (reason?.status >= 400 && reason.status < 500) pendingGroupRequest.current = null;
          throw new Error(messageOf(reason));
        } finally {
          setApprovingDraftGroup(false);
        }
      },
    });
  };
  const reviewDraft = async (draft, action) => {
    await ask({
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
      onConfirm: async (answer) => {
        try {
          const payload = { expected_revision: draft.revision, review_note: answer.note };
          if (action === "submit") {
            await testingApi.submitTestCaseReview(project._id, draft._id, payload);
          } else {
            await testingApi.requestTestCaseChanges(project._id, draft._id, payload);
          }
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const persistDraft = useCallback(
    async (snapshot, sequence) => {
      const requestProjectId = project._id;
      const requestDraftId = selectedDraft._id;
      const requestKey = `${requestProjectId}:${requestDraftId}`;
      if (
        requestProjectId !== currentProjectId.current ||
        draftSavesInFlight.current.has(requestKey)
      ) {
        return;
      }
      draftSavesInFlight.current.add(requestKey);
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
          requestProjectId,
          requestDraftId,
          {
            base_revision: selectedDraft.revision,
            operation_id: crypto.randomUUID(),
            changes,
          },
        );
        if (requestProjectId !== currentProjectId.current) return;
        setDrafts((values) =>
          values.map((item) =>
            item._id === result._id && item.revision <= result.revision ? result : item,
          ),
        );
        if (draftSequence.current === sequence) {
          setDraftDirty(false);
          setDraftSaveState("saved");
        } else {
          setDraftSaveState("pending");
        }
      } catch (reason) {
        if (requestProjectId !== currentProjectId.current) return;
        setDraftSaveState("error");
        setError(messageOf(reason));
      } finally {
        draftSavesInFlight.current.delete(requestKey);
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
      comparisonDraftId ||
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
  }, [
    draftDirty,
    draftEdit,
    persistDraft,
    project.current_permissions,
    selectedDraft?.status,
    comparisonDraftId,
  ]);
  const pageTitle =
    workspaceView === "repository"
      ? "Kho kiểm thử"
      : workspaceView === "" || workspaceView === "cases"
        ? {
            cases: "Ca kiểm thử",
            adequacy: "Hồ sơ đảm bảo",
            "agent-runs": "Lượt chạy AI",
            scenarios: "Kịch bản kiểm thử",
            templates: "Mẫu ca kiểm thử",
            automation: "Mã kiểm thử tự động",
            api: "Tích hợp API",
            import: "Nhập và xuất ca kiểm thử",
          }[caseTab]
        : workspaceView === "reusable-steps"
          ? "Bước dùng lại"
          : workspaceView === "test-data"
            ? "Dữ liệu kiểm thử"
            : workspaceView === "test-sets"
              ? "Bộ kiểm thử"
              : "Thiết kế kiểm thử";
  if (initialLoading || initialLoadFailed) {
    return (
      <WorkspacePage title={pageTitle} actions={<ProjectCrumb projectId={project._id} />}>
        {initialLoading ? (
          <LoadingState />
        ) : (
          <div className="space-y-3">
            <ErrorState message={error || "Không thể tải dữ liệu thiết kế kiểm thử"} />
            <button className="secondary-button" type="button" onClick={() => void load()}>
              Tải lại
            </button>
          </div>
        )}
      </WorkspacePage>
    );
  }
  return (
    <WorkspacePage
      title={pageTitle}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {showCases && can("testcase.create") && (
            <button className="apple-button" type="button" onClick={() => setCreatingTest(true)}>
              Tạo ca kiểm thử
            </button>
          )}
          {showCases && canManageTestCaseFields && (
            <>
              <button className="secondary-button" type="button" onClick={configureTestCaseField}>
                Thêm trường cho ca
              </button>
              <button
                className="secondary-button"
                type="button"
                aria-expanded={customFieldManagerOpen}
                onClick={() => setCustomFieldManagerOpen((open) => !open)}
              >
                {customFieldManagerOpen ? "Đóng quản lý trường" : "Quản lý trường"}
              </button>
            </>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      <div className="lg:hidden">
        <WorkspaceSectionNav
          current={
            {
              repository: "test-repository",
              cases: "test-cases",
              "reusable-steps": "reusable-steps",
              "test-data": "test-data",
              "test-sets": "test-sets",
            }[workspaceView] || "test-cases"
          }
          items={designSectionItems}
          permissions={permissions}
        />
      </div>
      {isCaseWorkspace && (
        <WorkspaceSectionNav
          current={caseTab === "agent-runs" ? "ai" : caseTab}
          compact
          permissions={permissions}
          items={testCaseSubsectionItems(project._id).filter((item) => item.id !== "cases")}
        />
      )}
      {showCases && canManageTestCaseFields && customFieldManagerOpen && (
        <TestCaseCustomFieldManager
          projectId={project._id}
          onUpdated={(updatedField) =>
            setTestCaseCustomFields((current) =>
              updatedField.status === "ACTIVE"
                ? current.some((field) => field._id === updatedField._id)
                  ? current.map((field) => (field._id === updatedField._id ? updatedField : field))
                  : [...current, updatedField]
                : current.filter((field) => field._id !== updatedField._id),
            )
          }
        />
      )}
      {showAdequacy && selectedRequirement && (
        <TestAdequacyPanel
          requirementVersionId={selectedRequirement}
          canDecide={memberRoles.includes("QA") && can("testcase.read")}
          canCreateClarification={memberRoles.includes("QA") && can("requirement.review")}
          canApprove={memberRoles.includes("QA") && can("testcase.review")}
          canSubmit={can("testcase.submit_review")}
        />
      )}
      {showAgentRuns && permissions.includes("requirement.read") && canReadAutomationRuns && (
        <Panel title="Tự động hóa khi yêu cầu thay đổi">
          <div className="grid gap-4 p-5">
            <p className="text-sm text-ink-muted">
              Kết quả được ghép theo mã sự kiện, phiên bản và revision chính xác; màn hình không suy
              đoán theo tên yêu cầu.
            </p>
            <label className="field-label block max-w-2xl">
              Yêu cầu đã duyệt
              <select
                aria-label="Yêu cầu cần xem trạng thái tự động hóa"
                className="apple-input mt-2 w-full min-w-0"
                value={selectedRequirement}
                onChange={(event) => setSelectedRequirement(event.target.value)}
              >
                <option value="">Chọn yêu cầu</option>
                {requirements.map((item) => (
                  <option key={item._id} value={item.current_version_id}>
                    {item.requirement_key} · {item.current_version?.title}
                  </option>
                ))}
              </select>
            </label>
            {automationRunsLoading && <LoadingState />}
            {automationRunsError && <ErrorState message={automationRunsError} />}
            {!automationRunsLoading &&
              !automationRunsError &&
              selectedRequirement &&
              (requirementAutomationRun ? (
                <div className="grid gap-2 rounded-control border border-border p-4 text-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusPill value={requirementAutomationRun.status} />
                    <details className="text-xs text-ink-muted">
                      <summary className="cursor-pointer">Thông tin hỗ trợ</summary>
                      <p className="mt-1 break-all">
                        Mã lượt chạy: {requirementAutomationRun.automation_run_id}
                      </p>
                      <p className="break-all">
                        Mã sự kiện: {requirementAutomationRun.source_event_id}
                      </p>
                    </details>
                  </div>
                  {requirementAutomationRun.error_code && (
                    <p>Lượt chạy có lỗi: {valueLabel(requirementAutomationRun.error_code)}</p>
                  )}
                  <p className="whitespace-pre-wrap break-words">
                    {requirementAutomationRun.result?.summary ||
                      requirementAutomationRun.result?.proposal?.summary ||
                      "Chưa có phần tóm tắt kết quả trong lượt chạy."}
                  </p>
                  <a className="text-accent underline" href="#automation-run-details">
                    Đến lịch sử lượt chạy
                  </a>
                </div>
              ) : (
                <p className="text-sm text-ink-muted">
                  Chưa tìm thấy lượt chạy khớp chính xác trong danh sách gần đây. Điều này không
                  khẳng định sự kiện đã thất bại.
                </p>
              ))}
            {!automationRunsLoading && !automationRunsError && !selectedRequirement && (
              <p className="text-sm text-ink-muted">Chọn yêu cầu để tra lượt chạy tương ứng.</p>
            )}
          </div>
        </Panel>
      )}
      {showAgentRuns && canReadAutomationRuns && (
        <div id="automation-run-details">
          <AgentRunPanel project={project} showDefinitions={false} />
        </div>
      )}
      {showTemplates && can("testcase.template.read") && (
        <TestCaseTemplatesPanel project={project} />
      )}
      {showScenarios && <SpecializedDesignPanel project={project} />}
      {showAutomation && <AutomationScriptsPanel project={project} />}
      {showCases && (
        <div className="grid gap-5">
          {actionableDrafts.length > 0 && (
            <Panel title="Ca kiểm thử chưa phê duyệt">
              <div className="space-y-4 p-4 sm:p-5">
                {can("testcase.approve") &&
                  actionableDrafts.some((item) => item.status === "IN_REVIEW") && (
                    <div className="space-y-3">
                      <p className="text-sm text-ink-muted">
                        Chọn ca đang chờ duyệt. Nhóm chỉ được công bố toàn bộ khi mọi nguồn, phiên
                        bản và kiểm tra đều hợp lệ.
                      </p>
                      <DataTable
                        items={actionableDrafts.filter((item) => item.status === "IN_REVIEW")}
                        selectedIds={selectedApprovalDraftIds}
                        onSelectionChange={setSelectedApprovalDraftIds}
                        selectionLabel="Chọn ca chờ duyệt"
                        columns={[
                          { key: "test_case_key", label: "Mã" },
                          { key: "title", label: "Tên" },
                          {
                            key: "origin",
                            label: "Nguồn",
                            render: (item) => (
                              <ContentOriginBadge origin={item.origin || "manual"} />
                            ),
                          },
                          { key: "revision", label: "Lần sửa" },
                          {
                            key: "comparison",
                            label: "Đối chiếu",
                            minWidth: 180,
                            render: (item) => {
                              const requiresComparison = requiresAiComparison(item);
                              if (!requiresComparison) return "Không áp dụng";
                              const reviewed = !unreviewedAiDrafts(
                                [item],
                                comparedApprovalDraftRevisions,
                              ).length;
                              return (
                                <button
                                  type="button"
                                  className="secondary-button"
                                  onClick={() => setComparisonDraftId(item._id)}
                                >
                                  {reviewed ? "Đối chiếu lại" : "Đối chiếu gốc và AI"}
                                </button>
                              );
                            },
                          },
                        ]}
                      />
                      {selectedApprovalDraftIds.some((id) => {
                        const draft = actionableDrafts.find((item) => item._id === id);
                        return (
                          draft &&
                          unreviewedAiDrafts([draft], comparedApprovalDraftRevisions).length > 0
                        );
                      }) && (
                        <p role="status" className="text-sm text-amber-800">
                          Mỗi ca do AI đề xuất phải được mở đối chiếu ở revision hiện tại trước khi
                          đưa vào nhóm duyệt.
                        </p>
                      )}
                      <button
                        type="button"
                        className="apple-button"
                        disabled={!selectedApprovalDraftIds.length || approvingDraftGroup}
                        onClick={approveDraftGroup}
                      >
                        {approvingDraftGroup
                          ? "Đang đối chiếu và duyệt…"
                          : `Duyệt nhóm${selectedApprovalDraftIds.length ? ` (${selectedApprovalDraftIds.length})` : ""}`}
                      </button>
                    </div>
                  )}
                <DataTable
                  onSelect={(item) => setSelectedDraftId(item._id)}
                  items={actionableDrafts}
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
                      hideWhenEmpty: true,
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
                                if (
                                  unreviewedAiDrafts([item], comparedApprovalDraftRevisions).length
                                ) {
                                  setError("");
                                  setComparisonDraftId(item._id);
                                } else {
                                  void freeze(item);
                                }
                              }}
                            >
                              {unreviewedAiDrafts([item], comparedApprovalDraftRevisions).length
                                ? "Đối chiếu trước khi duyệt"
                                : "Phê duyệt"}
                            </button>
                          )}
                        </span>
                      ),
                    },
                  ]}
                />
              </div>
            </Panel>
          )}
          <Panel
            title="Danh sách ca kiểm thử"
            actions={
              <div className="flex flex-wrap gap-2">
                {selectedTestIds.length > 0 && can("testcase.bulk.update") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      await ask({
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
                        onConfirm: async (answer) => {
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
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
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
                      await ask({
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
                            options: suites.map((item) => ({
                              value: item._id,
                              label: item.name,
                            })),
                          },
                        ],
                        onConfirm: async (answer) => {
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
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
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
                      await ask({
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
                        onConfirm: async (answer) => {
                          try {
                            await testingApi.bulkMarkReviewRequired(project._id, {
                              test_case_ids: selectedTestIds,
                              reason: answer.reason,
                              idempotency_key: crypto.randomUUID(),
                            });
                            setSelectedTestIds([]);
                            await load();
                          } catch (reason) {
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
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
                      await ask({
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
                        onConfirm: async (answer) => {
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
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
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
              activeRowId={selectedTestId}
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
      )}
      {showCases && selectedTestId && (
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
      {showCases &&
        selectedTestId &&
        testVersions[0] &&
        project.current_permissions?.includes("reviewsession.read") && (
          <FormalReviewPanel
            project={project}
            artifactType="TEST_CASE"
            artifactId={selectedTestId}
            artifactVersionId={testVersions[0]._id}
            reviewType="TEST_CASE_REVIEW"
            readOnly
          />
        )}
      {showCases && selectedDraft && draftEdit && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="secondary-button"
              disabled={draftDirty || draftSaveState === "saving"}
              onClick={() => setComparisonDraftId(selectedDraft._id)}
            >
              So sánh / ghép bản gốc và AI
            </button>
            {draftDirty && (
              <p className="text-sm text-ink-muted">Lưu phần đang biên tập trước khi mở so sánh.</p>
            )}
          </div>
          <Panel
            title={`${can("testcase.update") && selectedDraft.status === "DRAFT" ? "Biên tập" : "Chi tiết"} ${selectedDraft.test_case_key}`}
          >
            <div className="border-b border-border px-5 py-3">
              <ContentOriginBadge origin={selectedDraft.origin || "manual"} />
            </div>
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
            {can("testcase.update") && selectedDraft.status === "DRAFT" ? (
              <div className="grid gap-4 p-5 lg:grid-cols-2">
                <label className="field-label lg:col-span-2">
                  Tên ca kiểm thử
                  <input
                    className="apple-input mt-2"
                    value={draftEdit.title}
                    onChange={(event) => changeDraftEdit({ title: event.target.value })}
                  />
                </label>
                <label className="field-label lg:col-span-2">
                  Kỹ năng cần có để thực hiện ca (phân cách bằng dấu phẩy)
                  <input
                    className="apple-input mt-2"
                    value={draftEdit.requiredSkills}
                    onChange={(event) => changeDraftEdit({ requiredSkills: event.target.value })}
                    placeholder="Ví dụ: kiểm thử API, bảo mật"
                  />
                </label>
                <div className="grid gap-3 lg:col-span-2 sm:grid-cols-3">
                  <select
                    aria-label="Loại bản nháp ca kiểm thử"
                    className="apple-input"
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
                    value={draftEdit.priority}
                    onChange={(event) => changeDraftEdit({ priority: event.target.value })}
                  >
                    {TEST_CASE_ASSESSMENT_LEVELS.map((value) => (
                      <option key={value} value={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Rủi ro bản nháp ca kiểm thử"
                    className="apple-input"
                    value={draftEdit.risk}
                    onChange={(event) => changeDraftEdit({ risk: event.target.value })}
                  >
                    {TEST_CASE_ASSESSMENT_LEVELS.map((value) => (
                      <option key={value} value={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-3 lg:col-span-2 sm:grid-cols-3">
                  <label className="field-label">
                    Cấp kiểm thử
                    <select
                      aria-label="Cấp kiểm thử bản nháp"
                      className="apple-input mt-2"
                      value={draftEdit.test_level}
                      onChange={(event) => changeDraftEdit({ test_level: event.target.value })}
                    >
                      <option value="">Chưa phân loại</option>
                      {["UNIT", "INTEGRATION", "SYSTEM", "ACCEPTANCE"].map((value) => (
                        <option value={value} key={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-label">
                    Loại kiểm thử
                    <select
                      aria-label="Loại kiểm thử bản nháp"
                      className="apple-input mt-2"
                      value={draftEdit.test_kind}
                      onChange={(event) => changeDraftEdit({ test_kind: event.target.value })}
                    >
                      <option value="">Chưa phân loại</option>
                      {[
                        "functional",
                        "performance",
                        "security",
                        "usability",
                        "compatibility",
                        "reliability",
                        "accessibility",
                      ].map((value) => (
                        <option value={value} key={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-label">
                    Ảnh hưởng dự kiến
                    <select
                      aria-label="Ảnh hưởng dự kiến bản nháp"
                      className="apple-input mt-2"
                      value={draftEdit.expected_impact}
                      onChange={(event) => changeDraftEdit({ expected_impact: event.target.value })}
                    >
                      {["unassessed", "low", "medium", "high", "critical"].map((value) => (
                        <option value={value} key={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="field-label lg:col-span-2">
                  Lý do đánh giá ảnh hưởng
                  <textarea
                    className="apple-input mt-2 min-h-20"
                    maxLength={2000}
                    value={draftEdit.assessment_reason}
                    onChange={(event) => changeDraftEdit({ assessment_reason: event.target.value })}
                  />
                </label>
                <div className="grid gap-4 lg:col-span-2">
                  <MultiSelect
                    label="Phiên bản yêu cầu liên quan"
                    searchPlaceholder="Tìm yêu cầu"
                    options={[
                      ...requirements.map((item) => ({
                        value: item.current_version_id,
                        label: `${item.requirement_key} · ${item.current_version?.title || "Không có tiêu đề"}`,
                      })),
                      ...draftEdit.requirementVersionIds
                        .filter(
                          (id) => !requirements.some((item) => item.current_version_id === id),
                        )
                        .map((id) => ({
                          value: id,
                          label: "Phiên bản yêu cầu đã liên kết",
                          description: "Phiên bản này không còn trong danh sách hiện tại.",
                        })),
                    ]}
                    value={draftEdit.requirementVersionIds}
                    onChange={(requirementVersionIds) => {
                      const allowed = new Set(
                        requirements
                          .filter((item) => requirementVersionIds.includes(item.current_version_id))
                          .flatMap((item) =>
                            (item.current_version?.acceptance_criteria || []).map(
                              (criterion) => criterion._id,
                            ),
                          ),
                      );
                      changeDraftEdit({
                        requirementVersionIds,
                        acceptanceCriterionIds: draftEdit.acceptanceCriterionIds.filter((id) =>
                          allowed.has(id),
                        ),
                      });
                    }}
                  />
                  <MultiSelect
                    label="Tiêu chí chấp nhận liên kết"
                    searchPlaceholder="Tìm tiêu chí chấp nhận"
                    emptyMessage="Yêu cầu đã chọn chưa có tiêu chí chấp nhận khả dụng"
                    options={[
                      ...requirements
                        .filter((item) =>
                          draftEdit.requirementVersionIds.includes(item.current_version_id),
                        )
                        .flatMap((item) =>
                          (item.current_version?.acceptance_criteria || []).map((criterion) => ({
                            value: criterion._id,
                            label: `${item.requirement_key} · ${criterion.key || "Tiêu chí"}`,
                            description: criterion.plain_text || docText(criterion.content_doc),
                          })),
                        ),
                      ...draftEdit.acceptanceCriterionIds
                        .filter(
                          (id) =>
                            !requirements.some((item) =>
                              (item.current_version?.acceptance_criteria || []).some(
                                (criterion) => criterion._id === id,
                              ),
                            ),
                        )
                        .map((id) => ({
                          value: id,
                          label: "Tiêu chí chấp nhận đã liên kết",
                          description: "Tiêu chí này không còn trong phiên bản yêu cầu hiện tại.",
                        })),
                    ]}
                    value={draftEdit.acceptanceCriterionIds}
                    onChange={(acceptanceCriterionIds) =>
                      changeDraftEdit({ acceptanceCriterionIds })
                    }
                  />
                </div>
                {draftEdit.bdd && (
                  <section
                    className="space-y-3 rounded-control border border-border p-4 lg:col-span-2"
                    aria-label="Kịch bản BDD"
                  >
                    <h3 className="font-semibold">Kịch bản BDD</h3>
                    <label className="field-label">
                      Tính năng
                      <input
                        className="apple-input mt-2"
                        value={draftEdit.bdd.feature}
                        onChange={(event) =>
                          changeDraftEdit({
                            bdd: { ...draftEdit.bdd, feature: event.target.value },
                          })
                        }
                      />
                    </label>
                    <label className="field-label">
                      Kịch bản
                      <input
                        className="apple-input mt-2"
                        value={draftEdit.bdd.scenario}
                        onChange={(event) =>
                          changeDraftEdit({
                            bdd: { ...draftEdit.bdd, scenario: event.target.value },
                          })
                        }
                      />
                    </label>
                    {draftEdit.bdd.steps.map((step, index) => (
                      <label className="field-label" key={step.id || index}>
                        {valueLabel(step.keyword)}
                        <textarea
                          className="apple-input mt-2 min-h-16"
                          value={step.text}
                          onChange={(event) =>
                            changeDraftEdit({
                              bdd: {
                                ...draftEdit.bdd,
                                steps: draftEdit.bdd.steps.map((item, stepIndex) =>
                                  stepIndex === index
                                    ? { ...item, text: event.target.value }
                                    : item,
                                ),
                              },
                            })
                          }
                        />
                      </label>
                    ))}
                  </section>
                )}
                <label className="field-label lg:col-span-2">
                  Mục tiêu kiểm thử
                  <textarea
                    className="apple-input mt-2 min-h-20"
                    value={draftEdit.objective}
                    onChange={(event) => changeDraftEdit({ objective: event.target.value })}
                  />
                </label>
                <label className="field-label">
                  Điều kiện trước
                  <textarea
                    className="apple-input mt-2 min-h-24"
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
                              { id: crypto.randomUUID(), action: "", data: {}, expected: "" },
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
                          value={step.expected}
                          onChange={(event) => {
                            const steps = [...draftEdit.steps];
                            steps[index] = { ...step, expected: event.target.value };
                            changeDraftEdit({ steps });
                          }}
                        />
                      </label>
                      <div className="min-w-0 space-y-2 lg:col-span-2">
                        <p className="field-label">Dữ liệu của bước</p>
                        <StructuredValueEditor
                          label={`Dữ liệu bước ${index + 1}`}
                          value={step.data || {}}
                          fixedType="object"
                          onChange={(data) => {
                            const steps = [...draftEdit.steps];
                            steps[index] = { ...step, data };
                            changeDraftEdit({ steps });
                          }}
                        />
                      </div>
                      {selectedDraft.status === "DRAFT" &&
                        can("testcase.update") &&
                        draftEdit.steps.length > 1 && (
                          <button
                            className="secondary-button w-fit"
                            type="button"
                            onClick={() =>
                              changeDraftEdit({
                                steps: draftEdit.steps.filter(
                                  (_, stepIndex) => stepIndex !== index,
                                ),
                              })
                            }
                          >
                            Xóa bước
                          </button>
                        )}
                    </fieldset>
                  ))}
                </div>
                <div className="min-w-0 space-y-2">
                  <p className="field-label">Dữ liệu dùng chung</p>
                  <StructuredValueEditor
                    label="Dữ liệu dùng chung"
                    value={draftEdit.testData || {}}
                    fixedType="object"
                    onChange={(testData) => changeDraftEdit({ testData })}
                  />
                </div>
                <MultiSelect
                  label="Phiên bản bộ dữ liệu tham số"
                  options={dataSets.map((item) => ({
                    value: item.current_version_id,
                    label: `${item.name} v${item.current_version?.version}`,
                  }))}
                  searchPlaceholder="Tìm bộ dữ liệu"
                  value={draftEdit.dataSetVersionIds}
                  onChange={(dataSetVersionIds) => changeDraftEdit({ dataSetVersionIds })}
                />
                <label className="field-label">
                  Thư mục kho ca kiểm thử
                  <select
                    className="apple-input mt-2"
                    aria-label="Thư mục kho ca kiểm thử của bản nháp"
                    value={draftEdit.repositoryNodeId || ""}
                    onChange={(event) => changeDraftEdit({ repositoryNodeId: event.target.value })}
                  >
                    <option value="">
                      {selectedDraft.repository_node_id
                        ? "Giữ nguyên thư mục hiện tại"
                        : "Thư mục gốc (hiện tại)"}
                    </option>
                    {repositoryNodes.map((node) => (
                      <option key={node._id} value={node._id}>
                        {node.name}
                      </option>
                    ))}
                  </select>
                  <span className="mt-1 block text-sm text-ink-muted">
                    Chọn thư mục để phân loại bản nháp; để trống giữ nguyên vị trí hiện tại.
                  </span>
                </label>
                <MultiSelect
                  label="Điều kiện kiểm thử đã phê duyệt"
                  options={testConditions.map((item) => ({
                    value: item._id,
                    label: `${item.condition_key} ${item.title}`,
                  }))}
                  searchPlaceholder="Tìm điều kiện kiểm thử"
                  value={draftEdit.testConditionIds}
                  onChange={(testConditionIds) => changeDraftEdit({ testConditionIds })}
                />
                <label className="field-label">
                  Kết quả mong đợi tổng thể
                  <textarea
                    className="apple-input mt-2 min-h-28"
                    value={draftEdit.expected}
                    onChange={(event) => changeDraftEdit({ expected: event.target.value })}
                  />
                </label>
                <label className="field-label lg:col-span-2">
                  Điều kiện sau
                  <textarea
                    className="apple-input mt-2 min-h-24"
                    value={draftEdit.postconditions}
                    onChange={(event) => changeDraftEdit({ postconditions: event.target.value })}
                  />
                </label>
                <label className="field-label">
                  Kỹ thuật kiểm thử phân tách bằng dấu phẩy
                  <input
                    className="apple-input mt-2"
                    value={draftEdit.techniques}
                    onChange={(event) => changeDraftEdit({ techniques: event.target.value })}
                  />
                </label>
                <label className="field-label">
                  Nhãn phân tách bằng dấu phẩy
                  <input
                    className="apple-input mt-2"
                    value={draftEdit.tags}
                    onChange={(event) => changeDraftEdit({ tags: event.target.value })}
                  />
                </label>
                <label className="field-label">
                  Trạng thái tự động hóa
                  <select
                    className="apple-input mt-2"
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
                <div>
                  <label className="field-label">
                    Người phụ trách ca kiểm thử
                    {permissions.includes("project.members.read") ? (
                      <>
                        <select
                          aria-label="Người phụ trách ca kiểm thử"
                          className="apple-input mt-2"
                          value={draftEdit.ownerId}
                          disabled={projectMembersUnavailable}
                          onChange={(event) => changeDraftEdit({ ownerId: event.target.value })}
                        >
                          <option value="">Chưa phân công</option>
                          {draftEdit.ownerId &&
                            !projectMembers.some(
                              (member) => member.user_id === draftEdit.ownerId,
                            ) && (
                              <option value={draftEdit.ownerId}>
                                Người phụ trách hiện tại không còn hoạt động trong dự án
                              </option>
                            )}
                          {projectMembers.map((member) => (
                            <option key={member.user_id} value={member.user_id}>
                              {member.user_label ||
                                member.user?.full_name ||
                                member.user?.email ||
                                member.user_id}
                              {member.project_role ? ` · ${valueLabel(member.project_role)}` : ""}
                            </option>
                          ))}
                        </select>
                        {projectMembersUnavailable && (
                          <span role="status" className="text-sm text-amber-800">
                            Không tải được thành viên dự án; người phụ trách hiện tại được giữ
                            nguyên.
                          </span>
                        )}
                      </>
                    ) : (
                      <p className="mt-2 text-sm text-ink-muted">
                        {draftEdit.ownerId || "Chưa phân công"}
                      </p>
                    )}
                  </label>
                  {permissions.includes("project.members.read") && (
                    <TestCaseOwnerRecommendation
                      projectId={project._id}
                      draftId={selectedDraft._id}
                      requiredSkills={draftEdit.requiredSkills}
                      onSelect={(candidate) => changeDraftEdit({ ownerId: candidate.user_id })}
                    />
                  )}
                  <p className="mt-2 text-sm text-ink-muted">
                    Người phụ trách gắn với bản Test Case; người thực chạy được phân công riêng theo
                    từng Test Run.
                  </p>
                </div>
                <div className="lg:col-span-2">
                  <TestCaseCustomValues
                    fields={testCaseCustomFields}
                    values={draftEdit.customValues || {}}
                    onChange={(customValues) => changeDraftEdit({ customValues })}
                  />
                </div>
                <div className="min-w-0">
                  <FilePicker
                    label="Tệp đính kèm"
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
                </div>
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
                          : draftSaveState === "error"
                            ? "Tự động lưu thất bại"
                            : "Đã tự động lưu"}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <dl className="grid gap-4 p-5 sm:grid-cols-2">
                {[
                  ["Loại ca", valueLabel(draftEdit.type)],
                  ["Mức ưu tiên", valueLabel(draftEdit.priority)],
                  ["Rủi ro", valueLabel(draftEdit.risk)],
                  ["Mục tiêu", draftEdit.objective],
                  ["Điều kiện trước", draftEdit.preconditions],
                  ["Kết quả mong đợi", draftEdit.expected],
                  ["Điều kiện sau", draftEdit.postconditions],
                  ["Kỹ thuật kiểm thử", draftEdit.techniques],
                  ["Nhãn", draftEdit.tags],
                  [
                    "Người phụ trách",
                    projectMembers.find((member) => member.user_id === draftEdit.ownerId)
                      ?.user_label || draftEdit.ownerId,
                  ],
                ].map(([label, value]) => (
                  <div className="min-w-0 space-y-1" key={label}>
                    <dt className="text-xs font-semibold text-ink-muted">{label}</dt>
                    <dd className="break-words text-sm text-ink">{value || "Chưa có thông tin"}</dd>
                  </div>
                ))}
                {testCaseCustomFields.map((field) => (
                  <div className="min-w-0 space-y-1" key={field._id}>
                    <dt className="text-xs font-semibold text-ink-muted">{field.label}</dt>
                    <dd className="break-words text-sm text-ink">
                      {String(draftEdit.customValues?.[field.key] ?? "Chưa có thông tin")}
                    </dd>
                  </div>
                ))}
                <div className="space-y-2 sm:col-span-2">
                  <dt className="text-xs font-semibold text-ink-muted">Các bước kiểm thử</dt>
                  {(draftEdit.steps || []).map((step, index) => (
                    <div
                      className="grid gap-2 rounded-control border border-border p-3 sm:grid-cols-2"
                      key={step.id || index}
                    >
                      <p className="break-words text-sm">
                        <span className="font-semibold">Bước {index + 1}</span>
                        <br />
                        {step.action || "Chưa có thao tác"}
                      </p>
                      <p className="break-words text-sm">
                        <span className="font-semibold">Kết quả mong đợi</span>
                        <br />
                        {step.expected || "Chưa có kết quả mong đợi"}
                      </p>
                    </div>
                  ))}
                </div>
                {(draftEdit.attachments || []).length > 0 && (
                  <div className="space-y-1 sm:col-span-2">
                    <dt className="text-xs font-semibold text-ink-muted">Tệp đính kèm</dt>
                    {draftEdit.attachments.map((attachment) => (
                      <dd className="break-all text-sm text-ink" key={attachment.url}>
                        {attachment.filename}
                      </dd>
                    ))}
                  </div>
                )}
              </dl>
            )}
            {testLint && (
              <div className="border-t border-border">
                {(testLint.is_stale || draftDirty) && (
                  <p className="px-5 pt-4 text-sm text-warning" role="status">
                    Kết quả tự động thuộc revision trước; thay đổi hiện tại chưa có kết quả rà soát
                    mới.
                  </p>
                )}
                {testLint.artifact_revision && (
                  <p className="px-5 pt-3 text-sm text-ink-muted">
                    Kết quả tự động cho revision {testLint.artifact_revision}
                  </p>
                )}
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
            permissions={permissions}
            currentUserId={project.current_membership?.user_id}
          />
          <CollaborationPanel
            project={project}
            artifactType="test_case"
            artifactId={selectedDraft._id}
            onResolved={load}
          />
        </>
      )}
      {comparisonDraftId && (
        <TestCaseCompareWorkspace
          key={`${comparisonDraftId}:${project.current_membership?.user_id || "unknown"}`}
          draftId={comparisonDraftId}
          recoveryIdentity={project.current_membership?.user_id}
          projectId={project._id}
          canEdit={can("testcase.update")}
          canReadMembers={can("project.members.read")}
          canManageAttachments={can("attachment.manage")}
          onClose={() => setComparisonDraftId("")}
          onCompared={(draft, { current: comparisonIsCurrent }) =>
            setComparedApprovalDraftRevisions((previous) =>
              recordAiComparison(previous, draft, comparisonIsCurrent),
            )
          }
          onSaved={(draft) => {
            loadedDraft.current = "";
            setDrafts((values) => values.map((item) => (item._id === draft._id ? draft : item)));
            setTestLint(null);
          }}
        />
      )}
      {showCases && can("testcase.create") && (
        <TestCaseCreateModal
          projectId={project._id}
          isOpen={creatingTest}
          onClose={() => {
            if (!savingCreation) setCreatingTest(false);
          }}
          saving={savingCreation}
          form={form}
          setForm={setForm}
          dataSets={dataSets}
          testConditions={testConditions}
          repositoryNodes={repositoryNodes}
          reusableSteps={reusableSteps}
          customFields={testCaseCustomFields}
          requirements={requirements}
          members={projectMembers}
          canReadMembers={permissions.includes("project.members.read")}
          membersUnavailable={projectMembersUnavailable}
          onSubmit={create}
        />
      )}
      {testSetDialog && (
        <TestSetEditorModal
          key={`${project._id}:${testSetDialog.suite?._id || testSetDialog.mode}`}
          projectId={project._id}
          mode={testSetDialog.mode}
          suite={testSetDialog.suite}
          onClose={() => setTestSetDialog(null)}
          onSubmit={saveTestSet}
        />
      )}
      {showScenarios && (
        <div className="grid gap-5 xl:grid-cols-2">
          <ScenariosPanel
            can={can}
            scenarios={scenarios}
            filters={scenarioFilters}
            setFilters={setScenarioFilters}
            isCreating={creatingScenario}
            setCreating={setCreatingScenario}
            saving={savingCreation}
            form={scenarioForm}
            setForm={setScenarioForm}
            testConditions={testConditions}
            onSubmit={createScenario}
            ask={ask}
            reload={load}
            onError={setError}
          />
        </div>
      )}
      {workspaceView === "test-data" && (
        <DataSetsPanel
          projectId={project._id}
          can={can}
          canRead={canReadTestData}
          items={dataSets}
          isCreating={creatingDataSet}
          setCreating={setCreatingDataSet}
          saving={savingCreation}
          form={dataSetForm}
          setForm={setDataSetForm}
          onSubmit={createDataSet}
          ask={ask}
          reload={load}
          onError={setError}
        />
      )}
      {access.canRenderRepository && (
        <TestRepositoryPanel
          project={project}
          can={can}
          ask={ask}
          onError={setError}
          focus={workspaceView}
        />
      )}
      {workspaceView === "test-sets" && access.canReadTestSets && (
        <Panel
          title="Danh sách bộ kiểm thử"
          actions={
            can("testsuite.create") ? (
              <button className="apple-button" type="button" onClick={createTestSet}>
                Tạo bộ kiểm thử
              </button>
            ) : null
          }
        >
          <DataTable
            items={suites}
            empty="Chưa có bộ kiểm thử"
            columns={[
              { key: "name", label: "Tên" },
              {
                key: "suite_type",
                label: "Loại",
                render: (item) => valueLabel(item.suite_type),
              },
              {
                key: "test_case_version_ids",
                label: "Số ca",
                render: (item) => item.test_case_version_ids?.length || 0,
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "actions",
                label: "Thao tác",
                hideWhenEmpty: true,
                render: (item) => (
                  <span className="flex flex-wrap gap-2">
                    {can("testsuite.update") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => updateTestSet(item)}
                      >
                        Cập nhật
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("testsuite.archive") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => archiveTestSet(item)}
                      >
                        Lưu trữ
                      </button>
                    )}
                  </span>
                ),
              },
            ]}
          />
        </Panel>
      )}
      {showApi && (
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
      )}
      {access.canRenderImport && (showImport || (showApi && testImport)) && (
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
      )}
      {dialog}
    </WorkspacePage>
  );
}
