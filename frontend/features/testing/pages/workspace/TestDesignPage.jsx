"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Archive,
  Copy,
  FilePlus2,
  GitCompareArrows,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../components/DataTable";
import FilePicker from "../../components/FilePicker";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import TestCaseTemplatesPanel from "../../components/TestCaseTemplatesPanel";
import AutomationScriptsPanel from "../../components/AutomationScriptsPanel";
import AIRunPanel from "../../components/AIRunPanel";
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
import SearchField from "@/shared/components/ui/SearchField";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import {
  testCaseSubsectionItems,
  testDesignSectionItems,
} from "@/shared/components/layout/navigation";
import { testingApi } from "../../services/testing.service";
import { docText, formatDate as formatDateValue, messageOf, valueLabel } from "../../lib/testing";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import ApiArtifactsPanel from "./test-design/ApiArtifactsPanel";
import DataSetsPanel from "./test-design/DataSetsPanel";
import ScenariosPanel from "./test-design/ScenariosPanel";
import ManualTestGenerationPanel from "../../components/ManualTestGenerationPanel";
import TestCaseCreateForm from "./test-design/TestCaseCreateForm";
import RequirementCoverageSelector from "./test-design/RequirementCoverageSelector";
import TestSetEditorModal from "./test-design/TestSetEditorModal";
import TestCaseCompareWorkspace from "./test-design/TestCaseCompareWorkspace";
import StructuredValueEditor from "../../components/StructuredValueEditor";
import {
  isGroupApprovalComparisonCurrent,
  recordAiComparison,
  requiresAiComparison,
  unreviewedAiDrafts,
} from "./test-design/testCaseApproval.logic.mjs";
import TestCaseTransferPanel from "./test-design/TestCaseTransferPanel";
import { canUseAssignedDraft, testDesignAccess } from "./test-design/testDesignAccess.logic.mjs";
import {
  createDataSetForm,
  createScenarioForm,
  scenarioPayload,
  createTestCaseForm,
  testDataEntriesToObject,
  UNASSESSED_VALUE,
  buildTestCaseDraftChanges,
} from "./test-design/testDesign.model";

function draftConditionValues(draft, conditions, field, currentValue) {
  const requirementIds = new Set(draft?.requirement_version_ids || []);
  const criterionIds = new Set(draft?.acceptance_criterion_ids || []);
  const selectedConditionIds = new Set(draft?.test_condition_ids || []);
  const hasScope = requirementIds.size > 0 || criterionIds.size > 0;
  const values = conditions
    .filter((condition) => {
      if (selectedConditionIds.has(condition._id) || !hasScope) return true;
      return (condition.basis_refs || []).some((reference) => {
        const referenceId = reference.artifact_version_id || reference.artifact_id;
        return (
          (reference.artifact_type === "REQUIREMENT_VERSION" && requirementIds.has(referenceId)) ||
          (reference.artifact_type === "ACCEPTANCE_CRITERION" && criterionIds.has(referenceId))
        );
      });
    })
    .map((condition) => String(condition[field] || "").trim())
    .filter(Boolean);
  return [...new Set([...values, String(currentValue || "").trim()].filter(Boolean))];
}

export default function TestDesignPage({ project, workspaceView, section }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const currentUserId = project.current_membership?.user_id;
  const independentReviewRequired = Boolean(project?.settings?.require_independent_review);
  const canReviewDraft = (item) =>
    !independentReviewRequired ||
    (item.created_by !== currentUserId &&
      item.review_submitted_by !== currentUserId &&
      !(item.content_author_ids || []).includes(currentUserId));
  const { ask, dialog } = useActionDialog();
  const pathname = usePathname();
  const router = useRouter();
  const caseListPath = `/du-an/${project._id}/ca-kiem-thu`;
  const creatingCase = workspaceView === "cases" && section?.[0] === "tao-moi";
  const searchParams = useSearchParams();
  const linkedCaseId = searchParams.get("case") || "";
  const [requirements, setRequirements] = useState([]);
  const [testConditions, setTestConditions] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [dataSets, setDataSets] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [tests, setTests] = useState([]);
  const [suites, setSuites] = useState([]);
  const [suiteSearch, setSuiteSearch] = useState("");
  const [testSetDialog, setTestSetDialog] = useState(null);
  const [projectMembers, setProjectMembers] = useState([]);
  const [projectMembersUnavailable, setProjectMembersUnavailable] = useState(false);
  const [selectedTestIds, setSelectedTestIds] = useState([]);
  const [testPage, setTestPage] = useState(1);
  const [testPageSize, setTestPageSize] = useState(10);
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
  const [aiRuns, setAIRuns] = useState([]);
  const [aiRunsError, setAIRunsError] = useState("");
  const [aiRunsLoading, setAIRunsLoading] = useState(false);
  const handleAIRunsStateChange = useCallback(
    ({ runs, error: nextError, loading: nextLoading }) => {
      setAIRuns(runs);
      setAIRunsError(nextError);
      setAIRunsLoading(nextLoading);
    },
    [],
  );
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
  const [selectedTestRecord, setSelectedTestRecord] = useState(null);
  const [selectedCaseLoading, setSelectedCaseLoading] = useState(false);
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
  const [creatingScenario, setCreatingScenario] = useState(false);
  const [creatingDataSet, setCreatingDataSet] = useState(false);
  const [savingCreation, setSavingCreation] = useState(false);
  const creationInFlight = useRef(new Set());
  const testImportPanelRef = useRef(null);
  const can = (permission) => project.current_permissions?.includes(permission);
  const canDraft = (permission, draft) => canUseAssignedDraft(project, draft, permission);
  const assignedScenarios = scenarios.filter(
    (scenario) => scenario.owner_id === currentUserId && scenario.status !== "archived",
  );
  const canCreateUnassignedCase = can("testcase.create");
  const availableScenarios = canCreateUnassignedCase
    ? scenarios
    : assignedScenarios.filter((scenario) => canDraft("testscenario.update", scenario));
  const canCreateCase = canCreateUnassignedCase || availableScenarios.length > 0;
  const designSectionItems = useMemo(() => testDesignSectionItems(project._id), [project._id]);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const caseTabFromPath = pathname.split("/ca-kiem-thu/")[1]?.split("/")[0];
  const requestedCaseTab =
    {
      ai: "agent-runs",
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
  const showAIRuns = isCaseWorkspace && caseTab === "agent-runs";
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
      setCreatingScenario(false);
      setCreatingDataSet(false);
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
      setSuiteSearch("");
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
        apiArtifactValues,
        operationValues,
        memberResult,
      ] = await Promise.all([
        (showCases || showAIRuns || showScenarios || workspaceView === "test-data") &&
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
        (showScenarios || showCases) && permissions.includes("testscenario.read")
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
              page_size: testPageSize,
            })
          : Promise.resolve({ items: [], total: 0 }),
        (showCases || workspaceView === "test-sets") && permissions.includes("testsuite.read")
          ? testingApi.listSuites(project._id)
          : Promise.resolve([]),
        showApi && permissions.includes("apiartifact.read")
          ? testingApi.listApiArtifacts(project._id)
          : Promise.resolve([]),
        showApi && permissions.includes("apiartifact.read")
          ? testingApi.listApiOperations(project._id)
          : Promise.resolve([]),
        (showCases || showScenarios) && permissions.includes("project.members.read")
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
    access.canLoadTestCases,
    canReadTestData,
    initialDataLoaded,
    loadedProjectId,
    permissions,
    project._id,
    scenarioFilters,
    showAIRuns,
    showApi,
    showCases,
    showScenarios,
    testFilters,
    testPage,
    testPageSize,
    workspaceView,
  ]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!linkedCaseId || !showCases || !canReadTestCases) return;
    let active = true;
    setSelectedTestId(linkedCaseId);
    setSelectedTestRecord(null);
    setSelectedDraftId("");
    setComparisonDraftId("");
    setSelectedCaseLoading(true);
    setTestVersions([]);
    Promise.all([testingApi.getTestCase(linkedCaseId), testingApi.listTestVersions(linkedCaseId)])
      .then(([record, versions]) => {
        if (!active) return;
        if (record.project_id !== project._id) {
          setError("Ca kiểm thử không thuộc dự án đang mở.");
          return;
        }
        setSelectedTestRecord(record);
        setTestVersions(versions);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      })
      .finally(() => {
        if (active) setSelectedCaseLoading(false);
      });
    return () => {
      active = false;
    };
  }, [canReadTestCases, linkedCaseId, project._id, showCases]);
  const canReadAIRuns =
    permissions.includes("requirement.read") || permissions.includes("proposal.read");
  const selectedRequirementRecord = requirements.find(
    (item) => item.current_version_id === selectedRequirement,
  );
  const requirementLabels = Object.fromEntries(
    requirements
      .filter((item) => item.current_version_id)
      .map((item) => [
        item.current_version_id,
        `${item.requirement_key} · ${item.current_version?.title || "Yêu cầu"}`,
      ]),
  );
  const requirementAIRun = selectedRequirement
    ? aiRuns.find(
        (run) => run.trigger === "MANUAL" && run.target_artifact_ids?.includes(selectedRequirement),
      ) || null
    : null;
  const actionableDrafts = drafts.filter((item) => item.status !== "APPROVED");
  const editableDrafts = actionableDrafts.filter((item) => item.status !== "IN_REVIEW");
  const selectedDraft = actionableDrafts.find((item) => item._id === selectedDraftId) || null;
  const draftTestLevelOptions = [
    ...new Set([
      ...draftConditionValues(selectedDraft, testConditions, "test_level", draftEdit?.test_level),
    ]),
  ];
  const draftTestKindOptions = [
    ...new Set([
      ...draftConditionValues(selectedDraft, testConditions, "test_type", draftEdit?.test_kind),
    ]),
  ];
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
      durationMinutes: selectedDraft.duration_minutes || "",
      scenarioId: selectedDraft.scenario_id || "",
      requirementVersionIds: selectedDraft.requirement_version_ids || [],
      acceptanceCriterionIds: selectedDraft.acceptance_criterion_ids || [],
      coverageItemIds: selectedDraft.coverage_item_ids || [],
      bdd: selectedDraft.bdd
        ? {
            feature: selectedDraft.bdd.feature || "",
            scenario: selectedDraft.bdd.scenario || "",
            steps: (selectedDraft.bdd.steps || []).map((step) => ({
              id: step.id,
              keyword: step.keyword,
              text: step.text || "",
            })),
          }
        : null,
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
      alternateFlows: docText(selectedDraft.alternate_flows_doc),
      exceptionFlows: docText(selectedDraft.exception_flows_doc),
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
        scenario_id: form.scenarioId || null,
        type: form.type,
        priority: form.priority,
        risk: form.risk,
        duration_minutes: form.durationMinutes ? Number(form.durationMinutes) : null,
        test_level: form.testLevel || null,
        test_kind: form.testKind || null,
        owner_id:
          permissions.includes("project.members.read") && !projectMembersUnavailable
            ? form.ownerId || null
            : null,
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
        alternate_flows_doc: form.alternateFlows,
        exception_flows_doc: form.exceptionFlows,
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
        requirement_version_ids: form.requirementVersionIds,
        acceptance_criterion_ids: form.acceptanceCriterionIds,
        coverage_item_ids: form.coverageItemIds,
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
                ].filter((item) => item.text.trim()),
              }
            : null,
      });
      setForm(createTestCaseForm());
      router.replace(caseListPath);
    });
  const createScenario = (event) =>
    submitCreation(event, async () => {
      await testingApi.createScenario(project._id, {
        ...scenarioPayload(scenarioForm),
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
        generation_source: dataSetForm.generationSource || "USER",
        source_requirement_version_ids: dataSetForm.sourceRequirementVersionIds || [],
      });
      setDataSetForm(createDataSetForm());
      setCreatingDataSet(false);
    });
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
      setError(
        "Cần đối chiếu bản gốc và đề xuất AI ở lần cập nhật hiện tại trước khi duyệt ca này.",
      );
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
          const blockedDraftId = reason?.details?.draft_id || reason?.draft_id;
          const blockedDraft = selected.find((draft) => draft._id === blockedDraftId);
          const findings = (reason?.details?.findings || [])
            .filter((finding) => finding.severity === "error")
            .slice(0, 3)
            .map((finding) => finding.message || finding.suggestion)
            .filter(Boolean);
          const details = [messageOf(reason), ...findings].filter(Boolean).join(" ");
          throw new Error(
            blockedDraft
              ? `${blockedDraft.test_case_key || blockedDraft.title}: ${details}`
              : details,
          );
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
        ...(action === "changes"
          ? [
              {
                name: "reasonCode",
                label: "Lý do cần chỉnh sửa",
                options: [
                  { value: "INCOMPLETE", label: "Thiếu nội dung" },
                  { value: "INCORRECT", label: "Thông tin chưa đúng" },
                  { value: "DUPLICATE", label: "Trùng lặp" },
                  { value: "UNSUPPORTED_BY_SOURCE", label: "Nguồn chưa đủ căn cứ" },
                  { value: "OUT_OF_SCOPE", label: "Ngoài phạm vi" },
                  { value: "OTHER", label: "Lý do khác" },
                ],
                required: true,
              },
            ]
          : []),
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
          const payload = {
            expected_revision: draft.revision,
            review_note: answer.note,
            ...(action === "changes" ? { review_reason_code: answer.reasonCode } : {}),
          };
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
      !canUseAssignedDraft(project, selectedDraft, "testcase.update")
    )
      return undefined;
    const sequence = draftSequence.current;
    const timer = window.setTimeout(() => {
      void persistDraft(draftEdit, sequence);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [draftDirty, draftEdit, persistDraft, project, selectedDraft, comparisonDraftId]);
  const visibleSuites = useMemo(() => {
    const query = suiteSearch.trim().toLocaleLowerCase();
    if (!query) return suites;
    return suites.filter((item) =>
      [item.name, valueLabel(item.suite_type)]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase()
        .includes(query),
    );
  }, [suiteSearch, suites]);
  const pageTitle = linkedCaseId
    ? "Chi tiết ca kiểm thử"
    : workspaceView === "" || workspaceView === "cases"
      ? {
          cases: "Ca kiểm thử",
          "agent-runs": "Hoạt động AI",
          scenarios: "Kịch bản kiểm thử",
          templates: "Mẫu ca kiểm thử",
          automation: "Mã kiểm thử tự động",
          api: "Tích hợp API",
          import: "Nhập và xuất ca kiểm thử",
        }[caseTab]
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
            <button
              aria-label="Tải lại dữ liệu thiết kế kiểm thử"
              className="icon-button h-9 w-9"
              title="Tải lại"
              type="button"
              onClick={() => void load()}
            >
              <RefreshCw aria-hidden="true" size={16} />
            </button>
          </div>
        )}
      </WorkspacePage>
    );
  }
  if (creatingCase) {
    return (
      <WorkspacePage title="Tạo ca kiểm thử">
        {error && <ErrorState message={error} />}
        {canCreateCase ? (
          <Panel title="Thông tin ca kiểm thử">
            <TestCaseCreateForm
              onClose={() => router.push(caseListPath)}
              saving={savingCreation}
              form={form}
              setForm={setForm}
              dataSets={dataSets}
              testConditions={testConditions}
              requirements={requirements}
              scenarios={availableScenarios}
              scenarioRequired={!canCreateUnassignedCase}
              members={projectMembers}
              canReadMembers={permissions.includes("project.members.read")}
              membersUnavailable={projectMembersUnavailable}
              onRetryMembers={() => load()}
              onSubmit={create}
            />
          </Panel>
        ) : (
          <ErrorState message="Bạn không có quyền tạo ca kiểm thử trong dự án này." />
        )}
      </WorkspacePage>
    );
  }
  return (
    <WorkspacePage
      title={pageTitle}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          {linkedCaseId ? (
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => router.push(caseListPath)}
              >
                Quay lại danh sách
              </button>
              {can("testcase.version.create") && selectedTestRecord?.current_version && (
                <button
                  className="apple-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: `Tạo phiên bản mới cho ${selectedTestRecord.test_case_key}`,
                      description:
                        "Phiên bản hiện tại được giữ nguyên. Bản mới sẽ được gửi rà soát và phê duyệt.",
                      confirmLabel: "Tạo bản nháp",
                      fields: [
                        {
                          name: "change_reason",
                          label: "Lý do thay đổi",
                          required: true,
                          multiline: true,
                          autoFocus: true,
                        },
                      ],
                    });
                    if (!answer) return;
                    try {
                      const draft = await testingApi.createTestCaseVersionDraft(
                        selectedTestRecord._id,
                        {
                          expected_current_version_id: selectedTestRecord.current_version_id,
                          change_reason: answer.change_reason,
                        },
                      );
                      await load();
                      setSelectedDraftId(draft._id);
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Tạo phiên bản mới
                </button>
              )}
            </>
          ) : (
            <ProjectCrumb projectId={project._id} />
          )}
          {!linkedCaseId && showCases && canCreateCase && (
            <button
              className="apple-button"
              type="button"
              onClick={() => router.push(`${caseListPath}/tao-moi`)}
            >
              Tạo ca kiểm thử
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {linkedCaseId && selectedCaseLoading && <LoadingState label="Đang tải ca kiểm thử" />}
      {!linkedCaseId && (
        <div className="lg:hidden">
          <WorkspaceSectionNav
            current={
              {
                cases: "test-cases",
                "test-data": "test-data",
                "test-sets": "test-sets",
              }[workspaceView] || "test-cases"
            }
            items={designSectionItems}
            permissions={permissions}
          />
        </div>
      )}
      {!linkedCaseId && isCaseWorkspace && (
        <div className="lg:hidden">
          <WorkspaceSectionNav
            current={caseTab === "agent-runs" ? "ai" : caseTab}
            compact
            permissions={permissions}
            items={testCaseSubsectionItems(project._id).filter((item) => item.id !== "cases")}
          />
        </div>
      )}
      {linkedCaseId && selectedTestRecord && (
        <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(18rem,1fr)]">
          <div className="grid min-w-0 content-start gap-5">
            <Panel title="Thông tin chung">
              <dl className="grid min-w-0 gap-x-6 gap-y-4 p-5 sm:grid-cols-2 xl:grid-cols-4">
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Mã ca kiểm thử</dt>
                  <dd className="mt-1 break-words text-sm font-medium">
                    {selectedTestRecord.test_case_key}
                  </dd>
                </div>
                <div className="min-w-0 sm:col-span-2">
                  <dt className="text-xs text-ink-muted">Tên ca kiểm thử</dt>
                  <dd className="mt-1 break-words text-sm font-medium">
                    {selectedTestRecord.current_version?.title || selectedTestRecord.title}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Loại</dt>
                  <dd className="mt-1 text-sm">
                    {valueLabel(
                      selectedTestRecord.current_version?.type || selectedTestRecord.type,
                    )}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Ưu tiên</dt>
                  <dd className="mt-1 text-sm">
                    {valueLabel(
                      selectedTestRecord.current_version?.priority || selectedTestRecord.priority,
                    )}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Rủi ro</dt>
                  <dd className="mt-1 text-sm">
                    {valueLabel(
                      selectedTestRecord.current_version?.risk || selectedTestRecord.risk,
                    )}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Trạng thái</dt>
                  <dd className="mt-1">
                    <StatusPill value={selectedTestRecord.status} />
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Phiên bản</dt>
                  <dd className="mt-1 text-sm">
                    {selectedTestRecord.current_version?.version
                      ? `v${selectedTestRecord.current_version.version}`
                      : "Chưa có phiên bản"}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Ước lượng</dt>
                  <dd className="mt-1 text-sm">
                    {selectedTestRecord.current_version?.duration_minutes
                      ? `${selectedTestRecord.current_version.duration_minutes} phút`
                      : "Chưa có dữ liệu"}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="text-xs text-ink-muted">Người phụ trách</dt>
                  <dd className="mt-1 break-words text-sm">
                    {projectMembers.find(
                      (member) => member.user_id === selectedTestRecord.current_version?.owner_id,
                    )?.user_label || "Chưa phân công"}
                  </dd>
                </div>
              </dl>
              {selectedTestRecord.current_version?.objective_doc && (
                <div className="border-t border-border px-5 py-4">
                  <h3 className="text-sm font-medium">Mô tả ca kiểm thử</h3>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink-muted">
                    {docText(selectedTestRecord.current_version.objective_doc) || "Chưa có mô tả"}
                  </p>
                </div>
              )}
            </Panel>
            <Panel title="Tiền điều kiện và hậu điều kiện">
              <div className="grid gap-4 p-5 md:grid-cols-2">
                {[
                  ["Tiền điều kiện", selectedTestRecord.current_version?.preconditions_doc],
                  ["Hậu điều kiện", selectedTestRecord.current_version?.postconditions_doc],
                ].map(([label, content]) => (
                  <section className="min-w-0 rounded-control border border-border p-4" key={label}>
                    <h3 className="text-sm font-medium">{label}</h3>
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink-muted">
                      {docText(content) || "Chưa có nội dung"}
                    </p>
                  </section>
                ))}
              </div>
            </Panel>
            <Panel title="Các bước kiểm thử">
              {selectedTestRecord.current_version?.steps?.length ? (
                <DataTable
                  items={selectedTestRecord.current_version.steps.map((step, index) => ({
                    ...step,
                    _id: step._id || String(index),
                    step_number: step.step_number || step.number || index + 1,
                  }))}
                  columns={[
                    { key: "step_number", label: "STT", minWidth: 64 },
                    {
                      key: "action",
                      label: "Thao tác",
                      minWidth: 220,
                      render: (step) => docText(step.action_doc || step.action),
                    },
                    {
                      key: "data",
                      label: "Dữ liệu",
                      minWidth: 180,
                      render: (step) => docText(step.test_data || step.data),
                    },
                    {
                      key: "expected",
                      label: "Kết quả mong đợi",
                      minWidth: 240,
                      render: (step) => docText(step.expected_result_doc || step.expected),
                    },
                  ]}
                />
              ) : (
                <p className="p-5 text-sm text-ink-muted">Chưa có bước kiểm thử</p>
              )}
            </Panel>
            {[
              ["Luồng thay thế", selectedTestRecord.current_version?.alternate_flows_doc],
              ["Luồng ngoại lệ", selectedTestRecord.current_version?.exception_flows_doc],
            ].some(([, content]) => content) && (
              <Panel title="Luồng thay thế và ngoại lệ">
                <div className="grid gap-4 p-5 md:grid-cols-2">
                  {[
                    ["Luồng thay thế", selectedTestRecord.current_version?.alternate_flows_doc],
                    ["Luồng ngoại lệ", selectedTestRecord.current_version?.exception_flows_doc],
                  ].map(
                    ([label, content]) =>
                      content && (
                        <section
                          className="min-w-0 rounded-control border border-border p-4"
                          key={label}
                        >
                          <h3 className="text-sm font-medium">{label}</h3>
                          <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink-muted">
                            {docText(content)}
                          </p>
                        </section>
                      ),
                  )}
                </div>
              </Panel>
            )}
          </div>
          <Panel title="Thông tin bổ sung và liên kết">
            <dl className="divide-y divide-border px-5">
              {[
                [
                  "Yêu cầu",
                  (selectedTestRecord.current_version?.requirement_version_ids || [])
                    .map((id) => {
                      const item = requirements.find(
                        (requirement) => requirement.current_version_id === id,
                      );
                      return item
                        ? `${item.requirement_key} · ${item.current_version?.title || item.title || "Yêu cầu"}`
                        : id;
                    })
                    .join("\n"),
                ],
                [
                  "Kịch bản kiểm thử",
                  scenarios.find(
                    (item) => item._id === selectedTestRecord.current_version?.scenario_id,
                  )?.title || selectedTestRecord.current_version?.scenario_id,
                ],
                ["Kỹ thuật", selectedTestRecord.current_version?.techniques],
                ["Thẻ", selectedTestRecord.current_version?.tags],
                [
                  "Dữ liệu kiểm thử",
                  Object.entries(selectedTestRecord.current_version?.test_data || {})
                    .map(([key, value]) => `${key}: ${docText(value) || String(value)}`)
                    .join("\n"),
                ],
              ].map(([label, content]) => (
                <div className="py-3" key={label}>
                  <dt className="text-xs text-ink-muted">{label}</dt>
                  <dd className="mt-1 whitespace-pre-wrap break-words text-sm">
                    {Array.isArray(content)
                      ? content.map(valueLabel).join(" · ") || "Chưa liên kết"
                      : docText(content) || "Chưa liên kết"}
                  </dd>
                </div>
              ))}
            </dl>
          </Panel>
        </div>
      )}
      {showAIRuns && canReadAIRuns && (
        <div id="agent-run-details">
          <AIRunPanel
            project={project}
            showPanelHeading={false}
            onRunsStateChange={handleAIRunsStateChange}
            targetArtifactIds={selectedRequirement ? [selectedRequirement] : []}
            targetArtifactLabels={requirementLabels}
            contextContent={
              permissions.includes("requirement.read") ? (
                <section
                  aria-label="Phạm vi yêu cầu cho hoạt động AI"
                  className="grid gap-3 rounded-control border border-border bg-surface p-4"
                >
                  <label className="grid min-w-0 gap-2 text-sm font-medium text-ink">
                    Yêu cầu làm phạm vi cho lượt AI mới (tùy chọn)
                    <select
                      aria-label="Yêu cầu làm phạm vi cho lượt AI mới"
                      className="apple-input w-full min-w-0"
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
                  {selectedRequirement && (
                    <div className="grid min-w-0 gap-3 rounded-control border border-border bg-surface-raised/40 p-4 text-sm">
                      <div>
                        <p className="text-xs font-medium text-ink-muted">
                          Phạm vi cho lượt AI mới
                        </p>
                        <p className="mt-1 break-words font-semibold text-ink">
                          {selectedRequirementRecord?.requirement_key} ·{" "}
                          {selectedRequirementRecord?.current_version?.title || "Yêu cầu"}
                        </p>
                      </div>
                      {aiRunsLoading ? (
                        <p className="border-t border-border pt-3 text-ink-muted">
                          Đang tải hoạt động liên quan…
                        </p>
                      ) : aiRunsError ? (
                        <p className="border-t border-border pt-3 text-danger" role="status">
                          {aiRunsError}
                        </p>
                      ) : requirementAIRun ? (
                        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
                          <span className="text-ink-muted">
                            Lượt do người dùng bắt đầu gần nhất ·{" "}
                            {formatDate(requirementAIRun.created_at)}
                          </span>
                          <StatusPill value={requirementAIRun.status} />
                        </div>
                      ) : (
                        <p className="border-t border-border pt-3 text-ink-muted">
                          Khi bấm “Bắt đầu xử lý bằng AI”, lượt mới sẽ dùng phiên bản yêu cầu này
                          làm phạm vi tham chiếu.
                        </p>
                      )}
                    </div>
                  )}
                </section>
              ) : null
            }
          />
        </div>
      )}
      {showTemplates && can("testcase.template.read") && (
        <TestCaseTemplatesPanel project={project} />
      )}
      {showAutomation && <AutomationScriptsPanel project={project} />}
      {((showScenarios && can("ai.generate_scenario") && can("testscenario.create")) ||
        (showCases && !linkedCaseId && can("ai.generate_testcase") && can("testcase.create"))) && (
        <ManualTestGenerationPanel
          key={`${project._id}:${showScenarios ? "scenarios" : "cases"}`}
          projectId={project._id}
          requirements={requirements}
          mode={showScenarios ? "scenarios" : "cases"}
          onSaved={load}
        />
      )}
      {showCases && !linkedCaseId && (
        <div className="flex flex-col gap-5">
          {actionableDrafts.length > 0 && (
            <Panel className="order-last" title="Ca kiểm thử chưa phê duyệt">
              <div className="space-y-4 p-4 sm:p-5">
                {can("testcase.approve") &&
                  actionableDrafts.some(
                    (item) => item.status === "IN_REVIEW" && canReviewDraft(item),
                  ) && (
                    <div className="space-y-3">
                      <p className="text-sm text-ink-muted">
                        Chọn các ca cần duyệt. Chỉ ca hợp lệ mới được công bố.
                      </p>
                      <DataTable
                        onSelect={(item) => setSelectedDraftId(item._id)}
                        items={actionableDrafts.filter(
                          (item) => item.status === "IN_REVIEW" && canReviewDraft(item),
                        )}
                        selectedIds={selectedApprovalDraftIds}
                        onSelectionChange={setSelectedApprovalDraftIds}
                        selectionLabel="Chọn ca chờ duyệt"
                        columns={[
                          { key: "test_case_key", label: "Mã", minWidth: 120 },
                          {
                            key: "title",
                            label: "Tên",
                            minWidth: 280,
                            render: (item) => (
                              <span
                                className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                                title={item.title || ""}
                              >
                                {item.title}
                              </span>
                            ),
                            mobileRender: (item) => item.title,
                          },
                          {
                            key: "origin",
                            label: "Nguồn",
                            minWidth: 120,
                            render: (item) => (
                              <ContentOriginBadge origin={item.origin || "manual"} />
                            ),
                          },
                          {
                            key: "revision",
                            label: "Lần cập nhật",
                            width: 112,
                            minWidth: 112,
                          },
                          {
                            key: "comparison",
                            label: "Đối chiếu",
                            width: 160,
                            minWidth: 160,
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
                                  aria-label={
                                    reviewed
                                      ? `Đối chiếu lại ca kiểm thử ${item.test_case_key || item.title}`
                                      : `Đối chiếu gốc và AI cho ca kiểm thử ${item.test_case_key || item.title}`
                                  }
                                  title={reviewed ? "Đối chiếu lại" : "Đối chiếu bản gốc và AI"}
                                  className="icon-button h-9 w-9"
                                  onClick={() => setComparisonDraftId(item._id)}
                                >
                                  <GitCompareArrows aria-hidden="true" size={16} />
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
                          Mỗi ca do AI đề xuất phải được mở đối chiếu ở lần cập nhật hiện tại trước
                          khi đưa vào nhóm duyệt.
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
                {editableDrafts.length > 0 && (
                  <DataTable
                    onSelect={(item) => setSelectedDraftId(item._id)}
                    items={editableDrafts}
                    columns={[
                      { key: "test_case_key", label: "Mã", minWidth: 120 },
                      {
                        key: "title",
                        label: "Tên",
                        minWidth: 320,
                        render: (item) => (
                          <span
                            className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                            title={item.title || ""}
                          >
                            {item.title}
                          </span>
                        ),
                        mobileRender: (item) => item.title,
                      },
                      {
                        key: "type",
                        label: "Loại",
                        minWidth: 128,
                        render: (item) => valueLabel(item.type),
                      },
                      {
                        key: "status",
                        label: "Trạng thái",
                        minWidth: 136,
                        render: (item) => <StatusPill value={item.status} />,
                      },
                      {
                        key: "action",
                        label: "Thao tác",
                        minWidth: 88,
                        hideWhenEmpty: true,
                        render: (item) => {
                          const hasActions =
                            (item.status === "DRAFT" &&
                              (canDraft("testcase.submit_review", item) ||
                                canDraft("testcase.update", item))) ||
                            (item.status === "IN_REVIEW" && can("testcase.review")) ||
                            (item.status === "IN_REVIEW" &&
                              canReviewDraft(item) &&
                              can("testcase.approve"));
                          if (!hasActions) return null;
                          return (
                            <details
                              className="relative"
                              onClick={(event) => event.stopPropagation()}
                            >
                              <summary
                                className="icon-button flex h-9 w-9 cursor-pointer list-none items-center justify-center [&::-webkit-details-marker]:hidden"
                                aria-label={`Thao tác ca kiểm thử ${item.test_case_key}`}
                                title="Thao tác"
                              >
                                <MoreHorizontal size={18} aria-hidden="true" />
                              </summary>
                              <div className="absolute right-0 top-10 z-50 w-56 rounded-control border border-border bg-surface p-1 shadow-panel">
                                <span className="flex flex-col gap-1">
                                  {item.status === "DRAFT" &&
                                    canDraft("testcase.submit_review", item) && (
                                      <button
                                        className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                        type="button"
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          void reviewDraft(item, "submit");
                                        }}
                                      >
                                        Gửi rà soát
                                      </button>
                                    )}
                                  {item.status === "DRAFT" && canDraft("testcase.update", item) && (
                                    <button
                                      className="w-full rounded-control px-3 py-2 text-left text-sm text-danger hover:bg-danger/10"
                                      type="button"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        event.currentTarget
                                          .closest("details")
                                          ?.removeAttribute("open");
                                        void ask({
                                          title: "Xóa bản nháp ca kiểm thử",
                                          description: `${item.test_case_key} chưa được gửi rà soát và sẽ bị xóa khỏi dự án.`,
                                          confirmLabel: "Xóa bản nháp",
                                          danger: true,
                                          onConfirm: async () => {
                                            try {
                                              await testingApi.deleteTestDraft(item._id);
                                              if (selectedDraftId === item._id) {
                                                setSelectedDraftId("");
                                              }
                                              await load();
                                            } catch (reason) {
                                              throw new Error(messageOf(reason));
                                            }
                                          },
                                        });
                                      }}
                                    >
                                      Xóa bản nháp
                                    </button>
                                  )}
                                  {item.status === "IN_REVIEW" && can("testcase.review") && (
                                    <button
                                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                      type="button"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        void reviewDraft(item, "changes");
                                      }}
                                    >
                                      Yêu cầu sửa
                                    </button>
                                  )}
                                  {item.status === "IN_REVIEW" &&
                                    canReviewDraft(item) &&
                                    can("testcase.approve") && (
                                      <button
                                        className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                        type="button"
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          if (
                                            unreviewedAiDrafts(
                                              [item],
                                              comparedApprovalDraftRevisions,
                                            ).length
                                          ) {
                                            setError("");
                                            setComparisonDraftId(item._id);
                                          } else {
                                            void freeze(item);
                                          }
                                        }}
                                      >
                                        {unreviewedAiDrafts([item], comparedApprovalDraftRevisions)
                                          .length
                                          ? "Đối chiếu trước khi duyệt"
                                          : "Phê duyệt"}
                                      </button>
                                    )}
                                </span>
                              </div>
                            </details>
                          );
                        },
                      },
                    ]}
                  />
                )}
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
            <div className="grid min-w-0 gap-3 border-b border-border px-4 py-3 md:grid-cols-2 xl:grid-cols-5">
              <SearchField
                ariaLabel="Tìm ca kiểm thử"
                className="min-w-0 xl:col-span-2"
                onChange={(event) => {
                  setTestFilters({ ...testFilters, q: event.target.value });
                  setTestPage(1);
                }}
                placeholder="Tìm theo mã hoặc tên ca"
                value={testFilters.q}
              />
              <select
                aria-label="Lọc loại ca kiểm thử"
                className="apple-input min-w-0"
                value={testFilters.test_type}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, test_type: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="">Mọi loại</option>
                {[
                  ...new Set([
                    ...tests.map((item) => item.current_version?.type || item.type).filter(Boolean),
                  ]),
                ].map((type) => (
                  <option value={type} key={type}>
                    {valueLabel(type)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Lọc ưu tiên ca kiểm thử"
                className="apple-input min-w-0"
                value={testFilters.priority}
                onChange={(event) => {
                  setTestFilters({ ...testFilters, priority: event.target.value });
                  setTestPage(1);
                }}
              >
                <option value="">Mọi ưu tiên</option>
                {[
                  ...new Set([
                    ...tests
                      .map((item) => item.current_version?.priority || item.priority)
                      .filter(Boolean),
                  ]),
                ].map((priority) => (
                  <option value={priority} key={priority}>
                    {valueLabel(priority)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Lọc trạng thái ca kiểm thử"
                className="apple-input min-w-0"
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
              {permissions.includes("project.members.read") && (
                <select
                  aria-label="Lọc người phụ trách ca kiểm thử"
                  className="apple-input min-w-0"
                  value={testFilters.owner}
                  onChange={(event) => {
                    setTestFilters({ ...testFilters, owner: event.target.value });
                    setTestPage(1);
                  }}
                >
                  <option value="">Mọi người phụ trách</option>
                  {projectMembers.map((member) => (
                    <option value={member.user_id} key={member.user_id}>
                      {member.user_label || member.user?.full_name || "Thành viên dự án"}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <details className="border-b border-border px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium">Bộ lọc khác</summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
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
                  aria-label="Lọc trạng thái tự động hóa ca kiểm thử"
                  className="apple-input"
                  value={testFilters.automation_status}
                  onChange={(event) => {
                    setTestFilters({ ...testFilters, automation_status: event.target.value });
                    setTestPage(1);
                  }}
                >
                  <option value="">Mọi trạng thái tự động hóa</option>
                  {[
                    ["MANUAL", "Thủ công"],
                    ["AUTOMATED", "Đã tự động hóa"],
                    ["CANDIDATE", "Có thể tự động hóa"],
                    ["NOT_AUTOMATABLE", "Không phù hợp tự động hóa"],
                  ].map(([status, label]) => (
                    <option value={status} key={status}>
                      {label}
                    </option>
                  ))}
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
              onSelect={(item) =>
                router.push(`${caseListPath}?case=${encodeURIComponent(item._id)}`)
              }
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
                { key: "test_case_key", label: "Mã", minWidth: 88 },
                {
                  key: "title",
                  label: "Tên",
                  minWidth: 225,
                  render: (item) => (
                    <span
                      className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                      title={item.current_version?.title || ""}
                    >
                      {item.current_version?.title}
                    </span>
                  ),
                  mobileRender: (item) => item.current_version?.title,
                },
                {
                  key: "type",
                  label: "Loại",
                  minWidth: 105,
                  render: (item) => valueLabel(item.current_version?.type || item.type),
                },
                {
                  key: "priority",
                  label: "Ưu tiên",
                  minWidth: 85,
                  render: (item) =>
                    valueLabel(item.current_version?.priority || item.priority || "UNASSESSED"),
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  minWidth: 110,
                  render: (item) => <StatusPill value={item.status} />,
                },
                {
                  key: "owner",
                  label: "Người phụ trách",
                  minWidth: 130,
                  render: (item) => {
                    const ownerId = item.current_version?.owner_id || item.owner_id;
                    return (
                      projectMembers.find((member) => member.user_id === ownerId)?.user_label ||
                      "Chưa phân công"
                    );
                  },
                },
                {
                  key: "updated_at",
                  label: "Cập nhật",
                  minWidth: 132,
                  render: (item) => formatDate(item.updated_at),
                },
                {
                  key: "lifecycle",
                  label: "Thao tác",
                  minWidth: 88,
                  hideWhenEmpty: true,
                  render: (item) => {
                    const hasActions =
                      can("testcase.version.create") ||
                      can("testcase.clone") ||
                      (item.status !== "OBSOLETE" && can("testcase.bulk.archive")) ||
                      (item.status === "OBSOLETE" && can("testcase.restore"));
                    if (!hasActions) return null;
                    return (
                      <details className="relative" onClick={(event) => event.stopPropagation()}>
                        <summary
                          className="icon-button flex h-9 w-9 cursor-pointer list-none items-center justify-center [&::-webkit-details-marker]:hidden"
                          aria-label={`Thao tác ca kiểm thử ${item.test_case_key}`}
                          title="Thao tác"
                        >
                          <MoreHorizontal size={18} aria-hidden="true" />
                        </summary>
                        <div className="absolute right-0 top-10 z-50 w-56 rounded-control border border-border bg-surface p-1 shadow-panel">
                          <span className="flex flex-col gap-1">
                            {can("testcase.version.create") && item.current_version && (
                              <button
                                aria-label="Tạo phiên bản mới"
                                className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                type="button"
                                title="Tạo phiên bản mới"
                                onClick={async (event) => {
                                  event.stopPropagation();
                                  const answer = await ask({
                                    title: `Tạo phiên bản mới cho ${item.test_case_key}`,
                                    description:
                                      "Phiên bản hiện tại được giữ nguyên. Bản mới sẽ được gửi rà soát và phê duyệt.",
                                    confirmLabel: "Tạo bản nháp",
                                    fields: [
                                      {
                                        name: "change_reason",
                                        label: "Lý do thay đổi",
                                        required: true,
                                        multiline: true,
                                        autoFocus: true,
                                      },
                                    ],
                                  });
                                  if (!answer) return;
                                  try {
                                    const draft = await testingApi.createTestCaseVersionDraft(
                                      item._id,
                                      {
                                        expected_current_version_id: item.current_version_id,
                                        change_reason: answer.change_reason,
                                      },
                                    );
                                    setSelectedTestId(item._id);
                                    setSelectedTestIds([]);
                                    await Promise.all([
                                      load(),
                                      testingApi.listTestVersions(item._id).then(setTestVersions),
                                    ]);
                                    setSelectedDraftId(draft._id);
                                  } catch (reasonValue) {
                                    setError(messageOf(reasonValue));
                                  }
                                }}
                              >
                                <FilePlus2 size={17} aria-hidden="true" />
                                Tạo phiên bản mới
                              </button>
                            )}
                            {can("testcase.clone") && (
                              <button
                                aria-label="Nhân bản ca kiểm thử"
                                className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                type="button"
                                title="Nhân bản ca kiểm thử"
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
                                <Copy size={16} aria-hidden="true" />
                                Nhân bản ca kiểm thử
                              </button>
                            )}
                            {item.status !== "OBSOLETE" && can("testcase.bulk.archive") ? (
                              <button
                                aria-label="Đánh dấu ca kiểm thử không còn hiệu lực"
                                className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm text-danger hover:bg-danger-soft"
                                type="button"
                                title="Đánh dấu không còn hiệu lực"
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
                                <Archive size={16} aria-hidden="true" />
                                Đánh dấu không còn hiệu lực
                              </button>
                            ) : item.status === "OBSOLETE" && can("testcase.restore") ? (
                              <button
                                aria-label="Khôi phục ca kiểm thử"
                                className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                type="button"
                                title="Khôi phục ca kiểm thử"
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
                                <RotateCcw size={16} aria-hidden="true" />
                                Khôi phục ca kiểm thử
                              </button>
                            ) : item.status === "OBSOLETE" ? (
                              <span className="text-[11px] text-ink-muted">Đã lưu lịch sử</span>
                            ) : null}
                          </span>
                        </div>
                      </details>
                    );
                  },
                },
              ]}
            />
            <Pagination
              value={testPageInfo}
              pageSize={testPageSize}
              onChange={setTestPage}
              pageSizeOptions={[10, 20, 40]}
              onPageSizeChange={(size) => {
                setTestPageSize(size);
                setTestPage(1);
              }}
            />
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
              {
                key: "version",
                label: "Phiên bản",
                align: "center",
                render: (item) => `v${item.version}`,
              },
              {
                key: "title",
                label: "Tên",
                render: (item) => (
                  <span
                    className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                    title={item.title || ""}
                  >
                    {item.title}
                  </span>
                ),
                mobileRender: (item) => item.title,
              },
              { key: "change_reason", label: "Lý do thay đổi" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
            ]}
          />
          {testVersions
            .filter((version) => version.evidence_quotes?.length)
            .map((version) => (
              <details
                className="border-t border-border p-4 text-sm"
                key={`evidence-${version._id}`}
              >
                <summary className="cursor-pointer font-medium">
                  Căn cứ nguồn của phiên bản v{version.version}
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
            title={`${canDraft("testcase.update", selectedDraft) && selectedDraft.status === "DRAFT" ? "Biên tập" : "Chi tiết"} ${selectedDraft.test_case_key}`}
          >
            <div className="border-b border-border px-5 py-3">
              <ContentOriginBadge origin={selectedDraft.origin || "manual"} />
            </div>
            {!!selectedDraft.evidence_quotes?.length && (
              <div className="space-y-2 border-b border-border p-5 text-sm">
                <p className="font-medium">Căn cứ nguồn của ca kiểm thử</p>
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
                  Ca này đã được chỉnh sửa sau khi AI tạo. Dẫn chứng ban đầu không còn xác nhận nội
                  dung hiện tại; hãy rà soát lại căn cứ trước khi duyệt.
                </p>
              )}
            {canDraft("testcase.update", selectedDraft) && selectedDraft.status === "DRAFT" ? (
              <div className="test-design-form grid gap-4 p-5 lg:grid-cols-2">
                <label className="field-label lg:col-span-2">
                  Tên ca kiểm thử
                  <input
                    className="apple-input mt-2"
                    value={draftEdit.title}
                    onChange={(event) => changeDraftEdit({ title: event.target.value })}
                  />
                </label>
                <div className="grid gap-3 lg:col-span-2 sm:grid-cols-3">
                  <label className="field-label">
                    Loại ca kiểm thử
                    <input
                      aria-label="Loại bản nháp ca kiểm thử"
                      className="apple-input mt-2"
                      required
                      maxLength={100}
                      value={draftEdit.type ? valueLabel(draftEdit.type) : ""}
                      onChange={(event) => changeDraftEdit({ type: event.target.value })}
                      placeholder="Ví dụ: Chức năng, hồi quy"
                    />
                  </label>
                  <label className="field-label">
                    Mức ưu tiên
                    <input
                      aria-label="Ưu tiên bản nháp ca kiểm thử"
                      className="apple-input mt-2"
                      maxLength={100}
                      placeholder="Theo quy ước dự án"
                      value={draftEdit.priority ? valueLabel(draftEdit.priority) : ""}
                      onChange={(event) => changeDraftEdit({ priority: event.target.value })}
                    />
                  </label>
                  <label className="field-label">
                    Mức rủi ro
                    <input
                      aria-label="Rủi ro bản nháp ca kiểm thử"
                      className="apple-input mt-2"
                      maxLength={100}
                      placeholder="Theo quy ước dự án"
                      value={draftEdit.risk ? valueLabel(draftEdit.risk) : ""}
                      onChange={(event) => changeDraftEdit({ risk: event.target.value })}
                    />
                  </label>
                  <label className="field-label">
                    Ước lượng (phút)
                    <input
                      aria-label="Ước lượng thời gian thực hiện bản nháp (phút)"
                      className="apple-input mt-2"
                      type="number"
                      min="1"
                      max="10080"
                      step="1"
                      value={draftEdit.durationMinutes}
                      onChange={(event) => changeDraftEdit({ durationMinutes: event.target.value })}
                    />
                  </label>
                </div>
                <div className="grid gap-3 lg:col-span-2 sm:grid-cols-3">
                  <label className="field-label">
                    Cấp kiểm thử
                    <select
                      aria-label="Cấp kiểm thử bản nháp"
                      className="apple-input mt-2"
                      value={draftEdit.test_level}
                      onChange={(event) => changeDraftEdit({ test_level: event.target.value })}
                      disabled={!draftTestLevelOptions.length}
                    >
                      <option value="">Chọn cấp kiểm thử</option>
                      {draftTestLevelOptions.map((value) => (
                        <option key={value} value={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                    {!draftTestLevelOptions.length && (
                      <span className="mt-1 block font-normal">
                        Chưa có giá trị từ điều kiện kiểm thử đã duyệt liên quan.
                      </span>
                    )}
                  </label>
                  <label className="field-label">
                    Loại kiểm thử
                    <select
                      aria-label="Loại kiểm thử bản nháp"
                      className="apple-input mt-2"
                      value={draftEdit.test_kind}
                      onChange={(event) => changeDraftEdit({ test_kind: event.target.value })}
                      disabled={!draftTestKindOptions.length}
                    >
                      <option value="">Chọn loại kiểm thử</option>
                      {draftTestKindOptions.map((value) => (
                        <option key={value} value={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                    {!draftTestKindOptions.length && (
                      <span className="mt-1 block font-normal">
                        Chưa có giá trị từ điều kiện kiểm thử đã duyệt liên quan.
                      </span>
                    )}
                  </label>
                </div>
                <div className="grid gap-4 lg:col-span-2">
                  <label className="field-label">
                    Kịch bản liên kết
                    <select
                      className="apple-input mt-2"
                      aria-label="Kịch bản liên kết"
                      value={draftEdit.scenarioId}
                      onChange={(event) => changeDraftEdit({ scenarioId: event.target.value })}
                    >
                      <option value="">Chưa liên kết kịch bản</option>
                      {scenarios.map((scenario) => (
                        <option key={scenario._id} value={scenario._id}>
                          {scenario.scenario_key || scenario._id} · {scenario.title || "Kịch bản"}
                        </option>
                      ))}
                      {draftEdit.scenarioId &&
                        !scenarios.some((scenario) => scenario._id === draftEdit.scenarioId) && (
                          <option value={draftEdit.scenarioId}>Kịch bản đã liên kết</option>
                        )}
                    </select>
                  </label>
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
                  <RequirementCoverageSelector
                    requirements={requirements}
                    requirementVersionIds={draftEdit.requirementVersionIds}
                    value={draftEdit.coverageItemIds || []}
                    onChange={(coverageItemIds) => changeDraftEdit({ coverageItemIds })}
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
                    {selectedDraft.status === "DRAFT" &&
                      canDraft("testcase.update", selectedDraft) && (
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
                        canDraft("testcase.update", selectedDraft) &&
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
                {[
                  ["alternateFlows", "Luồng thay thế"],
                  ["exceptionFlows", "Luồng ngoại lệ"],
                ].map(([field, label]) => (
                  <label className="field-label" key={field}>
                    {label}
                    <textarea
                      className="apple-input mt-2 min-h-24"
                      value={draftEdit[field]}
                      onChange={(event) => changeDraftEdit({ [field]: event.target.value })}
                    />
                  </label>
                ))}
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
                              {member.project_roles?.length
                                ? ` · ${member.project_roles.map(valueLabel).join(", ")}`
                                : member.project_role
                                  ? ` · ${valueLabel(member.project_role)}`
                                  : ""}
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
                  <p className="mt-2 text-sm text-ink-muted">
                    Người phụ trách gắn với bản Test Case; người thực chạy được phân công riêng theo
                    từng Test Run.
                  </p>
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
                {selectedDraft.status === "DRAFT" && canDraft("testcase.update", selectedDraft) && (
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
                  ["Luồng thay thế", draftEdit.alternateFlows],
                  ["Luồng ngoại lệ", draftEdit.exceptionFlows],
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
                    Kết quả kiểm tra này áp dụng cho bản trước. Nội dung hiện tại chưa có kết quả rà
                    soát mới.
                  </p>
                )}
                {testLint.artifact_revision && (
                  <p className="px-5 pt-3 text-sm text-ink-muted">
                    Kết quả kiểm tra cho lần cập nhật {testLint.artifact_revision}
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
          canEdit={canDraft(
            "testcase.update",
            actionableDrafts.find((item) => item._id === comparisonDraftId),
          )}
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
          requirements={requirements}
          members={projectMembers}
          canReview={can("testscenario.review")}
          canEdit={(scenario) => canDraft("testscenario.update", scenario)}
          canAssignOwner={can("project.members.read")}
          canReadTestConditions={permissions.includes("testcondition.read")}
          ask={ask}
          reload={load}
          onError={setError}
        />
      )}
      {workspaceView === "test-data" && (
        <DataSetsPanel
          projectId={project._id}
          requirements={requirements}
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
      {workspaceView === "test-sets" && access.canReadTestSets && (
        <Panel title="Danh sách bộ kiểm thử">
          <div className="flex flex-wrap items-center gap-2 px-4 pt-4 pb-4 sm:px-5">
            <SearchField
              ariaLabel="Tìm bộ kiểm thử"
              className="min-w-64 flex-1"
              onChange={(event) => setSuiteSearch(event.target.value)}
              placeholder="Tìm theo tên hoặc loại bộ"
              value={suiteSearch}
            />
            <span className="px-2 text-[12px] text-ink-muted">{visibleSuites.length} bộ</span>
            {can("testsuite.create") && (
              <button className="apple-button" type="button" onClick={createTestSet}>
                Tạo bộ kiểm thử
              </button>
            )}
          </div>
          <DataTable
            items={visibleSuites}
            empty={suites.length ? "Không tìm thấy bộ kiểm thử phù hợp" : "Chưa có bộ kiểm thử"}
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
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Cập nhật bộ kiểm thử ${item.name}`}
                        title="Cập nhật bộ kiểm thử"
                        onClick={() => updateTestSet(item)}
                      >
                        <Pencil aria-hidden="true" size={16} />
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("testsuite.archive") && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Lưu trữ bộ kiểm thử ${item.name}`}
                        title="Lưu trữ bộ kiểm thử"
                        onClick={() => archiveTestSet(item)}
                      >
                        <Archive aria-hidden="true" size={16} />
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
