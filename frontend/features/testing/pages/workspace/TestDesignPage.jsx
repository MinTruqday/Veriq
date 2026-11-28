"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Archive,
  Copy,
  FilePlus2,
  GitCompareArrows,
  MoreHorizontal,
  PanelRightOpen,
  Pencil,
  RefreshCw,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../components/DataTable";
import AnchoredActionMenu from "../../components/AnchoredActionMenu";
import FilePicker from "../../components/FilePicker";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import TestCaseTemplatesPanel from "../../components/TestCaseTemplatesPanel";
import ManualTestGenerationPanel from "../../components/ManualTestGenerationPanel";
import AutomationScriptsPanel from "../../components/AutomationScriptsPanel";
import {
  testDesignSectionItems,
  testCaseSubsectionItems,
} from "@/shared/components/layout/navigation";
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
import { testingApi } from "../../services/testing.service";
import {
  docText,
  formatDate as formatDateValue,
  isApprovedCurrentRequirement,
  messageOf,
  valueLabel,
} from "../../lib/testing";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";
import ApiArtifactsPanel from "./test-design/ApiArtifactsPanel";
import TestCaseCreateForm from "./test-design/TestCaseCreateForm";
import RequirementCoverageSelector from "./test-design/RequirementCoverageSelector";
import TestSetEditorModal from "./test-design/TestSetEditorModal";
import TestCaseCompareWorkspace from "./test-design/TestCaseCompareWorkspace";
import {
  ObjectTestDataEntries,
  TechniqueSelector,
  TestTypeSelector,
} from "./test-design/TestCaseOptions";
import {
  isGroupApprovalComparisonCurrent,
  recordAiComparison,
  requiresAiComparison,
  unreviewedAiDrafts,
} from "./test-design/testCaseApproval.logic.mjs";
import TestCaseTransferPanel from "./test-design/TestCaseTransferPanel";
import { canUseAssignedDraft, testDesignAccess } from "./test-design/testDesignAccess.logic.mjs";
import {
  createTestCaseForm,
  testDataEntriesToObject,
  normalizeTestCaseVersionForDisplay,
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

function TraceGroup({ title, values = [], empty }) {
  return (
    <section className="min-w-0 rounded-control border border-border p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      {values.length ? (
        <ul className="mt-3 space-y-2">
          {values.map((value) => {
            const id = typeof value === "string" ? value : value?.id;
            const label = typeof value === "string" ? value : value?.label || id;
            return (
              <li className="break-all rounded-control bg-surface-quiet px-3 py-2 text-sm" key={id}>
                {label}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-ink-muted">{empty}</p>
      )}
    </section>
  );
}

export default function TestDesignPage({ project, workspaceView, section }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const currentUserId = project.current_membership?.user_id;
  const canReviewDraft = (item) =>
    project.can_self_approve ||
    (item.created_by !== currentUserId && !(item.content_author_ids || []).includes(currentUserId));
  const { ask, dialog } = useActionDialog();
  const pathname = usePathname();
  const router = useRouter();
  const caseListPath = `/du-an/${project._id}/ca-kiem-thu`;
  const creatingCase = workspaceView === "cases" && section?.[0] === "tao-moi";
  const creatingCasesWithAI = workspaceView === "cases" && section?.[0] === "tao-bang-ai";
  const searchParams = useSearchParams();
  const linkedCaseId = searchParams.get("case") || "";
  const forceListView = searchParams.get("view") === "list";
  const returnTestPlanId = searchParams.get("returnTestPlanId") || "";
  const returnToPlanPath = returnTestPlanId
    ? `${projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans)}/${encodeURIComponent(returnTestPlanId)}/chinh-sua`
    : "";
  const [requirements, setRequirements] = useState([]);
  const [testConditions, setTestConditions] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [tests, setTests] = useState([]);
  const [suites, setSuites] = useState([]);
  const [suiteSearch, setSuiteSearch] = useState("");
  const [suiteStatusFilter, setSuiteStatusFilter] = useState("all");
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
    suite_id: "",
    stale_status: "",
    automation_status: "",
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
  const [testDetailTab, setTestDetailTab] = useState("content");
  const [selectedCaseLoading, setSelectedCaseLoading] = useState(false);
  const [testVersions, setTestVersions] = useState([]);
  const [draftEdit, setDraftEdit] = useState(null);
  const [draftDirty, setDraftDirty] = useState(false);
  const [draftSaveState, setDraftSaveState] = useState("saved");
  const draftSequence = useRef(0);
  const draftSavesInFlight = useRef(new Set());
  const loadedDraft = useRef("");
  const [testLint, setTestLint] = useState(null);
  const [form, setForm] = useState(createTestCaseForm);
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const prefilledPlanRequirements = useRef("");
  const loadedProjectId = useRef(project._id);
  const loadSequence = useRef(0);
  const currentProjectId = useRef(project._id);
  currentProjectId.current = project._id;
  const [savingCreation, setSavingCreation] = useState(false);
  const creationInFlight = useRef(new Set());
  const testImportPanelRef = useRef(null);
  const can = (permission) => project.current_permissions?.includes(permission);
  const canDraft = (permission, draft) => canUseAssignedDraft(project, draft, permission);
  const canCreateUnassignedCase = can("testcase.create");
  const canCreateCase = canCreateUnassignedCase;
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const caseTabFromPath = pathname.split("/ca-kiem-thu/")[1]?.split("/")[0];
  const requestedCaseTab =
    {
      mau: "templates",
      "tu-dong-hoa": "automation",
      api: "api",
      "nhap-xuat": "import",
      "bo-kiem-thu": "sets",
    }[caseTabFromPath] || "cases";
  const caseTab = caseTabFromPath === "ai" ? "agent-runs" : requestedCaseTab;
  const access = testDesignAccess({ workspaceView, caseTab, permissions });
  const isCaseWorkspace = workspaceView === "" || workspaceView === "cases";
  const showCases = access.showCases;
  const showAIRuns = isCaseWorkspace && caseTab === "agent-runs";
  const designSectionItems = useMemo(() => testDesignSectionItems(project._id), [project._id]);
  const showTemplates = isCaseWorkspace && caseTab === "templates";
  const showAutomation = isCaseWorkspace && caseTab === "automation";
  const showApi = isCaseWorkspace && caseTab === "api";
  const showImport = access.showImport;
  const canReadTestCases = access.canReadTestCases;
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
      setSavingCreation(false);
      setForm(createTestCaseForm());
      setApiImport({ filename: "openapi.json", format: "openapi", content: "" });
      setRequirements([]);
      setTestConditions([]);
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
        draftValues,
        testValues,
        suiteValues,
        apiArtifactValues,
        operationValues,
        memberResult,
      ] = await Promise.all([
        (showCases || showAIRuns) && permissions.includes("requirement.read")
          ? testingApi
              .listRequirements(project._id, {
                page_size: 500,
                include_acceptance_criteria: true,
              })
              .then((items) => items.filter(isApprovedCurrentRequirement))
          : Promise.resolve([]),
        showCases && permissions.includes("testcondition.read")
          ? testingApi.listTestConditions(project._id, { status: "APPROVED", page_size: 200 })
          : Promise.resolve({ items: [] }),
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
    initialDataLoaded,
    loadedProjectId,
    permissions,
    project._id,
    showAIRuns,
    showApi,
    showCases,
    testFilters,
    testPage,
    testPageSize,
    workspaceView,
  ]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (
      initialLoading ||
      initialLoadFailed ||
      creatingCase ||
      creatingCasesWithAI ||
      !showCases ||
      !canReadTestCases ||
      linkedCaseId ||
      forceListView ||
      !tests.length
    ) {
      return;
    }
    router.replace(`${caseListPath}?case=${encodeURIComponent(tests[0]._id)}`, {
      scroll: false,
    });
  }, [
    canReadTestCases,
    caseListPath,
    creatingCase,
    creatingCasesWithAI,
    forceListView,
    initialLoadFailed,
    initialLoading,
    linkedCaseId,
    router,
    showCases,
    tests,
  ]);
  useEffect(() => {
    const requestedIds = [...new Set(searchParams.getAll("requirementVersionId"))];
    if (!creatingCase || !requestedIds.length || !requirements.length) return;
    const validIds = requestedIds.filter((id) =>
      requirements.some((item) => item.current_version_id === id),
    );
    if (!validIds.length) return;
    const key = `${project._id}:${returnTestPlanId}:${validIds.join("|")}`;
    if (prefilledPlanRequirements.current === key) return;
    prefilledPlanRequirements.current = key;
    setForm((current) =>
      current.requirementVersionIds.length
        ? current
        : { ...current, requirementVersionIds: validIds },
    );
  }, [creatingCase, project._id, requirements, returnTestPlanId, searchParams]);
  useEffect(() => {
    if (!linkedCaseId || !showCases || !canReadTestCases) return;
    let active = true;
    setSelectedTestId(linkedCaseId);
    setSelectedTestRecord(null);
    setTestDetailTab("content");
    setSelectedDraftId("");
    setComparisonDraftId("");
    setSelectedCaseLoading(true);
    setTestVersions([]);
    Promise.all([testingApi.getTestCase(linkedCaseId), testingApi.listTestVersions(linkedCaseId)])
      .then(([record, versions]) => {
        if (!active) return;
        if (record.project_id !== project._id) {
          setError("Ca kiểm thử không thuộc dự án đang mở");
          return;
        }
        setSelectedTestRecord({
          ...record,
          current_version: normalizeTestCaseVersionForDisplay(record.current_version),
        });
        setTestVersions(versions.map(normalizeTestCaseVersionForDisplay));
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
  const testCaseGroups = useMemo(() => {
    const groups = new Map();
    for (const testCase of tests) {
      const requirementId = testCase.current_version?.requirement_version_ids?.[0] || "unlinked";
      const group = groups.get(requirementId) || {
        id: requirementId,
        label:
          requirementId === "unlinked"
            ? "Chưa gắn yêu cầu"
            : requirementLabels[requirementId] || "Yêu cầu liên kết",
        items: [],
      };
      group.items.push(testCase);
      groups.set(requirementId, group);
    }
    return [...groups.values()].sort((left, right) => {
      if (left.id === "unlinked") return 1;
      if (right.id === "unlinked") return -1;
      return left.label.localeCompare(right.label, "vi");
    });
  }, [requirementLabels, tests]);
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
    const steps = (selectedDraft.steps || []).map((step) => ({
      id: step.id,
      action: docText(step.action_doc),
      data: step.test_data || {},
      expected: docText(step.expected_doc),
    }));
    const legacyTestData = selectedDraft.test_data || {};
    const legacyExpected = docText(selectedDraft.expected_result_doc);
    const hasStepData = steps.some((step) => Object.keys(step.data || {}).length > 0);
    const hasStepExpected = steps.some((step) => String(step.expected || "").trim());
    if (!selectedDraft.bdd && steps.length) {
      if (!hasStepData && Object.keys(legacyTestData).length)
        steps[0] = { ...steps[0], data: legacyTestData };
      if (!hasStepExpected && legacyExpected) steps[0] = { ...steps[0], expected: legacyExpected };
    }
    setDraftEdit({
      title: selectedDraft.title,
      module_name: selectedDraft.module_name || "",
      type: selectedDraft.type,
      priority: selectedDraft.priority,
      risk: selectedDraft.risk,
      test_level: selectedDraft.test_level || "",
      test_kind: selectedDraft.test_kind || "",
      durationMinutes: selectedDraft.duration_minutes || "",
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
      steps,
      testData: selectedDraft.bdd ? legacyTestData : {},
      expected: selectedDraft.bdd ? legacyExpected : "",
      postconditions: docText(selectedDraft.postconditions_doc),
      mainFlow: docText(selectedDraft.main_flow_doc),
      alternateFlows: docText(selectedDraft.alternate_flows_doc),
      exceptionFlows: docText(selectedDraft.exception_flows_doc),
      techniques: (selectedDraft.techniques || []).join(", "),
      tags: (selectedDraft.tags || []).join(", "),
      ownerId: selectedDraft.owner_id || "",
      automationStatus: selectedDraft.automation_status || "manual",
      attachments: selectedDraft.attachments || [],
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
  const create = (event) => {
    const saveAsDraft = event.nativeEvent.submitter?.value === "draft";
    if (form.title.trim().length < 2) {
      event.preventDefault();
      setError("Tên ca kiểm thử cần ít nhất 2 ký tự, kể cả khi lưu nháp");
      return;
    }
    if (!saveAsDraft && form.testStyle === "BDD") {
      if (
        ![form.feature, form.scenario, form.given, form.when, form.then].every((value) =>
          value.trim(),
        )
      ) {
        event.preventDefault();
        setError("Điền đủ Tính năng, Tên kịch bản, Given, When và Then trước khi lưu ca chính");
        return;
      }
    }
    if (
      !saveAsDraft &&
      form.testStyle !== "BDD" &&
      form.steps.some((step) => !docText(step.action).trim() || !docText(step.expected).trim())
    ) {
      event.preventDefault();
      setError("Mỗi bước cần có thao tác và kết quả mong đợi trước khi lưu ca chính");
      return;
    }
    if (!saveAsDraft && !form.requirementVersionIds.length && !form.acceptanceCriterionIds.length) {
      event.preventDefault();
      setError("Liên kết ca kiểm thử với ít nhất một yêu cầu trước khi lưu chính");
      return;
    }
    return submitCreation(event, async () => {
      await testingApi.createTestDraft(project._id, {
        save_as_draft: saveAsDraft,
        title: form.title,
        module_name: form.moduleName,
        type: form.type,
        ...(form.priority ? { priority: form.priority } : {}),
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
        postconditions_doc: form.postconditions,
        main_flow_doc: form.mainFlow,
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
        test_condition_ids: form.testConditionIds,
        requirement_version_ids: form.requirementVersionIds,
        acceptance_criterion_ids: form.acceptanceCriterionIds,
        coverage_item_ids: form.coverageItemIds,
        origin: form.origin || "manual",
        source_evidence: form.sourceEvidence || [],
        evidence_refs: form.evidenceRefs || [],
        evidence_quotes: form.evidenceQuotes || [],
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
      router.replace(
        returnTestPlanId
          ? `${caseListPath}?returnTestPlanId=${encodeURIComponent(returnTestPlanId)}`
          : caseListPath,
      );
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
      setError(
        "Cần đối chiếu bản gốc và đề xuất AI ở lần cập nhật hiện tại trước khi duyệt ca này",
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
      setError("Chọn các ca đang ở trạng thái chờ duyệt; nhóm không được tự bỏ qua ca khác");
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
        `Mở và đối chiếu bản gốc với đề xuất AI cho ${unreviewed.length} ca được đánh dấu trước khi duyệt nhóm`,
      );
      return;
    }
    await ask({
      title: `Duyệt nhóm ${selected.length} ca kiểm thử`,
      description: [
        "Các ca được duyệt cùng một giao dịch. Nếu một ca không hợp lệ hoặc phiên bản đã đổi, toàn bộ nhóm sẽ rollback",
        selectionSummary,
        omittedCount ? `Còn ${omittedCount} ca khác trong nhóm` : "",
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
                "Có ca đã đổi phiên bản hoặc nguồn sau lần đối chiếu. Nhóm chưa được duyệt; hãy mở lại từng ca để xem bản mới nhất",
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
              "Phản hồi duyệt nhóm không khớp danh sách đã chọn. Đã tải lại dữ liệu; hãy kiểm tra trạng thái từng ca trước khi thao tác tiếp",
            );
          }
          pendingGroupRequest.current = null;
          const approvedDraftIdSet = new Set(approvedDraftIds);
          setDrafts((current) => current.filter((draft) => !approvedDraftIdSet.has(draft._id)));
          setSelectedApprovalDraftIds([]);
          const refreshed = await load();
          if (!refreshed) {
            setError(
              `Nhóm ${response.count} ca đã được duyệt và lưu nguyên tử, nhưng chưa tải lại được danh sách. Hãy tải lại trang; không gửi lại thao tác duyệt`,
            );
            return;
          }
          if (response.derived_pending_version_ids?.length) {
            setError(
              `Đã duyệt ${response.count} ca trong giao dịch; ${response.derived_pending_version_ids.length} phiên bản đang chờ đồng bộ truy vết hoặc tìm kiếm`,
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
      title:
        action === "changes"
          ? "Yêu cầu chỉnh sửa ca kiểm thử"
          : project.can_self_approve
            ? "Chốt ca kiểm thử"
            : "Gửi ca kiểm thử để rà soát",
      description: draft.test_case_key,
      confirmLabel:
        action === "changes"
          ? "Yêu cầu chỉnh sửa"
          : project.can_self_approve
            ? "Chốt ca kiểm thử"
            : "Gửi rà soát",
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
      !["DRAFT", "READY"].includes(selectedDraft?.status) ||
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
    return suites.filter((item) => {
      const matchesQuery =
        !query ||
        [item.name, valueLabel(item.suite_type)]
          .filter(Boolean)
          .join(" ")
          .toLocaleLowerCase()
          .includes(query);
      const matchesStatus =
        suiteStatusFilter === "all" ||
        (suiteStatusFilter === "archived"
          ? item.status === "ARCHIVED"
          : item.status !== "ARCHIVED");
      return matchesQuery && matchesStatus;
    });
  }, [suiteSearch, suiteStatusFilter, suites]);
  const activeSuiteCount = suites.filter((item) => item.status !== "ARCHIVED").length;
  const archivedSuiteCount = suites.length - activeSuiteCount;
  const createSelectedCaseVersionDraft = async () => {
    if (!selectedTestRecord?.current_version || !can("testcase.version.create")) return;
    const answer = await ask({
      title: `Tạo phiên bản mới cho ${selectedTestRecord.test_case_key}`,
      description: "Phiên bản hiện tại được giữ nguyên. Bản mới sẽ được gửi rà soát và phê duyệt",
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
      const draft = await testingApi.createTestCaseVersionDraft(selectedTestRecord._id, {
        expected_current_version_id: selectedTestRecord.current_version_id,
        change_reason: answer.change_reason,
      });
      await load();
      setSelectedDraftId(draft._id);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const pageTitle = linkedCaseId
    ? "Chi tiết ca kiểm thử"
    : workspaceView === "" || workspaceView === "cases"
      ? {
          cases: "Ca kiểm thử",
          "agent-runs": "Hoạt động AI",
          templates: "Mẫu ca kiểm thử",
          automation: "Mã kiểm thử tự động",
          api: "Tích hợp API",
          import: "Nhập và xuất ca kiểm thử",
        }[caseTab]
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
      <WorkspacePage
        title="Tạo ca kiểm thử"
        actions={
          <>
            <button
              className="secondary-button"
              type="button"
              onClick={() => router.push(returnToPlanPath || caseListPath)}
              disabled={savingCreation}
            >
              {returnTestPlanId ? "Quay lại kế hoạch" : "Hủy"}
            </button>
            <button
              className="secondary-button"
              type="submit"
              form="test-case-create-form"
              value="draft"
              formNoValidate
              disabled={savingCreation || !canCreateCase}
            >
              {savingCreation ? "Đang lưu" : "Lưu nháp"}
            </button>
            <button
              className="apple-button"
              type="submit"
              form="test-case-create-form"
              value="ready"
              disabled={savingCreation || !canCreateCase}
            >
              {savingCreation ? "Đang lưu" : "Lưu ca kiểm thử"}
            </button>
          </>
        }
      >
        {error && !canCreateCase && <ErrorState message={error} />}
        {canCreateCase ? (
          <Panel title="Thông tin ca kiểm thử">
            <TestCaseCreateForm
              form={form}
              setForm={setForm}
              error={error}
              saving={savingCreation}
              testConditions={testConditions}
              requirements={requirements}
              members={projectMembers}
              canReadMembers={permissions.includes("project.members.read")}
              membersUnavailable={projectMembersUnavailable}
              onRetryMembers={() => load()}
              onSubmit={create}
            />
          </Panel>
        ) : (
          <ErrorState message="Bạn không có quyền tạo ca kiểm thử trong dự án này" />
        )}
      </WorkspacePage>
    );
  }
  if (creatingCasesWithAI) {
    return (
      <WorkspacePage
        title="Ca kiểm thử"
        actions={
          <button
            className="secondary-button"
            type="button"
            onClick={() => router.push(caseListPath)}
          >
            Hủy
          </button>
        }
      >
        {can("ai.generate_testcase") && can("testcase.create") ? (
          <ManualTestGenerationPanel
            projectId={project._id}
            requirements={requirements}
            canGenerate={can("ai.generate_testcase")}
            onSaved={load}
          />
        ) : (
          <ErrorState message="Bạn chưa được cấp quyền tạo và lưu ca kiểm thử bằng AI trong dự án này" />
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
                onClick={() => router.push(`${caseListPath}?view=list`)}
              >
                Danh sách đầy đủ
              </button>
              {can("testcase.version.create") && selectedTestRecord?.current_version && (
                <button
                  className="apple-button"
                  type="button"
                  onClick={createSelectedCaseVersionDraft}
                >
                  Tạo phiên bản mới
                </button>
              )}
            </>
          ) : (
            <ProjectCrumb projectId={project._id} />
          )}
          {!linkedCaseId && isCaseWorkspace && caseTab !== "cases" && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => router.push(caseListPath)}
            >
              Quay lại ca kiểm thử
            </button>
          )}
          {!linkedCaseId && showCases && can("testsuite.create") && (
            <button className="secondary-button" type="button" onClick={createTestSet}>
              Tạo bộ kiểm thử
            </button>
          )}
          {!linkedCaseId &&
            showCases &&
            (can("testcase.template.read") ||
              can("testcase.import") ||
              can("testcase.export") ||
              (can("testcondition.read") && testConditions.length > 0)) && (
              <details className="relative">
                <summary className="secondary-button cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  Mẫu và nhập/xuất
                </summary>
                <div className="absolute right-0 z-30 mt-1 min-w-52 rounded-control border border-border bg-surface p-1 shadow-panel">
                  {can("testcase.template.read") && (
                    <button
                      type="button"
                      className="block w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      onClick={() => router.push(`${caseListPath}/mau`)}
                    >
                      Mẫu
                    </button>
                  )}
                  {(can("testcase.import") || can("testcase.export")) && (
                    <button
                      type="button"
                      className="block w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      onClick={() => router.push(`${caseListPath}/nhap-xuat`)}
                    >
                      Nhập và xuất
                    </button>
                  )}
                  {can("testcondition.read") && testConditions.length > 0 && (
                    <button
                      type="button"
                      className="block w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      onClick={() =>
                        router.push(projectRoute(project._id, PROJECT_SECTION_SLUGS.testAnalysis))
                      }
                    >
                      Điều kiện kiểm thử đã có
                    </button>
                  )}
                </div>
              </details>
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
          {!linkedCaseId && showCases && can("ai.generate_testcase") && can("testcase.create") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => router.push(`${caseListPath}/tao-bang-ai`)}
            >
              <Sparkles aria-hidden="true" size={17} />
              Mở công cụ AI
            </button>
          )}
          {!linkedCaseId && forceListView && showCases && tests.length > 0 && (
            <button
              aria-label="Mở chế độ chia đôi"
              className="icon-button h-10 w-10"
              type="button"
              title="Mở chế độ chia đôi"
              onClick={() =>
                router.push(`${caseListPath}?case=${encodeURIComponent(tests[0]._id)}`)
              }
            >
              <PanelRightOpen aria-hidden="true" size={18} />
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {!creatingCase && returnToPlanPath && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-border bg-surface p-4">
          <p className="text-sm text-ink-muted">
            Ca đã lưu. Duyệt ca nếu cần, sau đó thêm ca đã duyệt vào phạm vi kế hoạch
          </p>
          <button
            className="secondary-button"
            type="button"
            onClick={() => router.push(returnToPlanPath)}
          >
            Quay lại kế hoạch
          </button>
        </div>
      )}
      {linkedCaseId && selectedCaseLoading && <LoadingState label="Đang tải ca kiểm thử" />}
      {!linkedCaseId && (
        <div className="lg:hidden">
          <WorkspaceSectionNav
            current={
              {
                cases: "test-cases",
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
        <div className="grid min-w-0 items-start gap-5 md:items-stretch md:grid-cols-[minmax(14rem,3fr)_minmax(0,7fr)]">
          <aside className="min-w-0 md:self-stretch" aria-label="Điều hướng ca kiểm thử">
            <Panel title="Ca kiểm thử" className="min-w-0 md:sticky md:top-20 md:self-start">
              <div className="border-b border-border p-3">
                <SearchField
                  ariaLabel="Tìm ca kiểm thử"
                  className="w-full"
                  onChange={(event) => {
                    setTestFilters((current) => ({ ...current, q: event.target.value }));
                    setTestPage(1);
                  }}
                  placeholder="Tìm mã hoặc tên ca"
                  value={testFilters.q}
                />
              </div>
              <ul className="max-h-[min(66vh,48rem)] divide-y divide-border overflow-y-auto">
                {testCaseGroups.map((group) => (
                  <li key={group.id}>
                    <details className="group/cases" open>
                      <summary className="sticky top-0 z-[1] flex cursor-pointer list-none items-center justify-between gap-2 border-y border-border bg-surface-quiet px-3 py-2 text-[11px] font-semibold text-ink-muted [&::-webkit-details-marker]:hidden">
                        <span className="min-w-0 truncate">{group.label}</span>
                        <span className="shrink-0 rounded-full border border-border bg-surface px-1.5 py-0.5 font-normal">
                          {group.items.length}
                        </span>
                      </summary>
                      <ul className="divide-y divide-border/70">
                        {group.items.map((item) => (
                          <li key={item._id}>
                            <button
                              aria-current={item._id === selectedTestId ? "page" : undefined}
                              className={`block w-full min-w-0 px-3 py-3 text-left transition ${item._id === selectedTestId ? "bg-brand-soft/60" : "hover:bg-surface-quiet"}`}
                              onClick={() =>
                                router.push(`${caseListPath}?case=${encodeURIComponent(item._id)}`)
                              }
                              type="button"
                            >
                              <span className="flex min-w-0 items-center justify-between gap-2">
                                <span className="truncate font-mono text-[11px] font-semibold text-brand">
                                  {item.test_case_key}
                                </span>
                                <StatusPill value={item.status} />
                              </span>
                              <span className="mt-1 line-clamp-2 break-words text-[13px] font-medium leading-5 [overflow-wrap:anywhere]">
                                {item.current_version?.title || item.title || "Ca kiểm thử"}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </li>
                ))}
                {!tests.length && (
                  <li className="p-4 text-sm text-ink-muted">Không có ca phù hợp</li>
                )}
              </ul>
              <div className="border-t border-border p-3">
                <Link className="text-sm font-medium text-brand" href={`${caseListPath}?view=list`}>
                  Mở danh sách đầy đủ
                </Link>
              </div>
            </Panel>
          </aside>
          <div className="min-w-0">
            <div
              className="mb-4 flex gap-1 overflow-x-auto border-b border-border"
              role="tablist"
              aria-label="Chi tiết ca kiểm thử"
            >
              {[
                ["content", "Nội dung"],
                ["versions", `Phiên bản (${testVersions.length})`],
                ["trace", "Truy vết"],
                ["review", "Rà soát"],
              ].map(([tab, label]) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={testDetailTab === tab}
                  className={`shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition ${testDetailTab === tab ? "border-brand text-brand" : "border-transparent text-ink-muted hover:text-ink"}`}
                  onClick={() => setTestDetailTab(tab)}
                >
                  {label}
                </button>
              ))}
            </div>
            {testDetailTab === "content" && (
              <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_19rem]">
                <div className="grid min-w-0 content-start gap-4">
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
                      <p className="p-4 text-sm text-ink-muted">Chưa có bước kiểm thử</p>
                    )}
                  </Panel>
                  <Panel title="Mô tả và luồng chính">
                    <div className="space-y-4 p-4">
                      <div>
                        <h3 className="text-xs font-medium text-ink-muted">Mô tả</h3>
                        <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                          {docText(selectedTestRecord.current_version?.objective_doc).trim() ||
                            "Chưa có mô tả"}
                        </p>
                      </div>
                      <div className="border-t border-border pt-3">
                        <h3 className="text-xs font-medium text-ink-muted">Luồng chính</h3>
                        <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                          {docText(selectedTestRecord.current_version?.main_flow_doc).trim() ||
                            "Chưa có nội dung"}
                        </p>
                      </div>
                    </div>
                  </Panel>
                  <details className="rounded-control border border-border bg-surface">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
                      Điều kiện, luồng thay thế và ngoại lệ
                    </summary>
                    <div className="grid gap-4 border-t border-border p-4 md:grid-cols-2">
                      {[
                        ["Tiền điều kiện", selectedTestRecord.current_version?.preconditions_doc],
                        ["Hậu điều kiện", selectedTestRecord.current_version?.postconditions_doc],
                        ["Luồng thay thế", selectedTestRecord.current_version?.alternate_flows_doc],
                        ["Luồng ngoại lệ", selectedTestRecord.current_version?.exception_flows_doc],
                      ].map(([label, content]) => (
                        <section
                          className="min-w-0 rounded-control border border-border p-3"
                          key={label}
                        >
                          <h3 className="text-xs font-medium text-ink-muted">{label}</h3>
                          <p className="mt-2 whitespace-pre-wrap break-words text-sm">
                            {docText(content).trim() || "Chưa có nội dung"}
                          </p>
                        </section>
                      ))}
                    </div>
                  </details>
                  <details className="rounded-control border border-border bg-surface">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
                      Thông tin bổ sung và liên kết
                    </summary>
                    <dl className="grid gap-4 border-t border-border p-4 sm:grid-cols-3">
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
                        ["Kỹ thuật", selectedTestRecord.current_version?.techniques],
                        ["Thẻ", selectedTestRecord.current_version?.tags],
                      ].map(([label, content]) => (
                        <div className="min-w-0" key={label}>
                          <dt className="text-xs text-ink-muted">{label}</dt>
                          <dd className="mt-1 whitespace-pre-wrap break-words text-sm">
                            {Array.isArray(content)
                              ? content.map(valueLabel).join(" · ") || "Chưa liên kết"
                              : docText(content) || "Chưa liên kết"}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                </div>
                <Panel title="Thông tin ca kiểm thử">
                  <dl className="divide-y divide-border px-4 py-1">
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Mã ca</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm font-semibold">
                        {selectedTestRecord.test_case_key}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Tên ca</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm font-medium">
                        {selectedTestRecord.current_version?.title || selectedTestRecord.title}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Module / Tính năng</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {selectedTestRecord.current_version?.module_name || "Chưa phân loại"}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Loại</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {valueLabel(
                          selectedTestRecord.current_version?.type || selectedTestRecord.type,
                        )}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Ưu tiên</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {valueLabel(
                          selectedTestRecord.current_version?.priority ||
                            selectedTestRecord.priority,
                        )}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Trạng thái</dt>
                      <dd className="min-w-0 max-w-[65%] text-right">
                        <StatusPill value={selectedTestRecord.status} />
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Phiên bản</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {selectedTestRecord.current_version?.version
                          ? `v${selectedTestRecord.current_version.version}`
                          : "Chưa có phiên bản"}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Ước lượng</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {selectedTestRecord.current_version?.duration_minutes
                          ? `${selectedTestRecord.current_version.duration_minutes} phút`
                          : "Chưa có dữ liệu"}
                      </dd>
                    </div>
                    <div className="flex min-w-0 items-start justify-between gap-4 py-2.5">
                      <dt className="shrink-0 text-xs text-ink-muted">Người phụ trách</dt>
                      <dd className="min-w-0 max-w-[65%] break-words text-right text-sm">
                        {projectMembers.find(
                          (member) =>
                            member.user_id === selectedTestRecord.current_version?.owner_id,
                        )?.user_label || "Chưa phân công"}
                      </dd>
                    </div>
                  </dl>
                </Panel>
              </div>
            )}
            {testDetailTab === "versions" && (
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
            {testDetailTab === "trace" && (
              <Panel title="Liên kết truy vết">
                <div className="grid gap-5 p-5 md:grid-cols-2">
                  <TraceGroup
                    title="Yêu cầu"
                    values={(selectedTestRecord.current_version?.requirement_version_ids || []).map(
                      (id) => {
                        const item = requirements.find(
                          (requirement) => requirement.current_version_id === id,
                        );
                        return {
                          id,
                          label: item
                            ? `${item.requirement_key} · ${item.current_version?.title || item.title || "Yêu cầu"}`
                            : id,
                        };
                      },
                    )}
                    empty="Chưa liên kết yêu cầu"
                  />
                  <TraceGroup
                    title="Tiêu chí chấp nhận"
                    values={selectedTestRecord.current_version?.acceptance_criterion_ids || []}
                    empty="Chưa liên kết tiêu chí"
                  />
                  <TraceGroup
                    title="Điều kiện kiểm thử"
                    values={selectedTestRecord.current_version?.test_condition_ids || []}
                    empty="Chưa liên kết điều kiện"
                  />
                  <TraceGroup
                    title="Điểm cần kiểm thử"
                    values={selectedTestRecord.current_version?.coverage_item_ids || []}
                    empty="Chưa liên kết điểm cần kiểm thử"
                  />
                </div>
              </Panel>
            )}
            {testDetailTab === "review" && (
              <Panel title="Rà soát ca kiểm thử">
                <div className="flex justify-end p-5">
                  {can("testcase.version.create") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={createSelectedCaseVersionDraft}
                    >
                      Tạo bản nháp để rà soát
                    </button>
                  )}
                </div>
              </Panel>
            )}
          </div>
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
                          làm phạm vi tham chiếu
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
                        Chọn các ca cần duyệt. Chỉ ca hợp lệ mới được công bố
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
                          khi đưa vào nhóm duyệt
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
                        render: (item) =>
                          item.status === "READY" ? (
                            "Đã lưu, chưa duyệt"
                          ) : (
                            <StatusPill value={item.status} />
                          ),
                      },
                      {
                        key: "action",
                        label: "Thao tác",
                        minWidth: 88,
                        hideWhenEmpty: true,
                        render: (item) => {
                          const hasActions =
                            (["DRAFT", "READY"].includes(item.status) &&
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
                              <div className="absolute right-0 top-10 z-50 w-56 max-w-[calc(100vw-2rem)] max-h-[min(70dvh,24rem)] overflow-y-auto rounded-control border border-border bg-surface p-1 shadow-panel">
                                <span className="flex flex-col gap-1">
                                  {["DRAFT", "READY"].includes(item.status) &&
                                    canDraft("testcase.submit_review", item) && (
                                      <button
                                        className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                                        type="button"
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          void reviewDraft(item, "submit");
                                        }}
                                      >
                                        {project.can_self_approve
                                          ? "Chốt ca kiểm thử"
                                          : "Gửi rà soát"}
                                      </button>
                                    )}
                                  {["DRAFT", "READY"].includes(item.status) &&
                                    canDraft("testcase.update", item) && (
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
                                            description: `${item.test_case_key} chưa được gửi rà soát và sẽ bị xóa khỏi dự án`,
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
                                  {item.status === "IN_REVIEW" &&
                                    canReviewDraft(item) &&
                                    can("testcase.review") && (
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
            <div className="border-b border-border p-4">
              <SearchField
                ariaLabel="Tìm ca kiểm thử"
                className="w-full max-w-lg"
                onChange={(event) => {
                  setTestFilters({ ...testFilters, q: event.target.value });
                  setTestPage(1);
                }}
                placeholder="Tìm theo mã hoặc tên ca"
                value={testFilters.q}
              />
            </div>
            <details className="border-b border-border px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium">Bộ lọc</summary>
              <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
                <span className="mr-1 text-sm text-ink-muted">Nhóm ca:</span>
                <button
                  type="button"
                  aria-pressed={!testFilters.suite_id}
                  className={`rounded-full border px-3 py-1.5 text-sm ${!testFilters.suite_id ? "border-brand bg-brand/10 font-medium text-brand" : "border-border text-ink-muted hover:bg-surface-quiet"}`}
                  onClick={() => {
                    setTestFilters({ ...testFilters, suite_id: "" });
                    setTestPage(1);
                  }}
                >
                  Tất cả ca
                </button>
                {suites
                  .filter((item) => item.status !== "ARCHIVED")
                  .map((item) => (
                    <button
                      type="button"
                      key={item._id}
                      aria-pressed={testFilters.suite_id === item._id}
                      className={`rounded-full border px-3 py-1.5 text-sm ${testFilters.suite_id === item._id ? "border-brand bg-brand/10 font-medium text-brand" : "border-border text-ink-muted hover:bg-surface-quiet"}`}
                      onClick={() => {
                        setTestFilters({ ...testFilters, suite_id: item._id });
                        setTestPage(1);
                      }}
                    >
                      {item.name}{" "}
                      <span className="text-xs">({item.test_case_version_ids?.length || 0})</span>
                    </button>
                  ))}
                {suites.filter((item) => item.status !== "ARCHIVED").length === 0 && (
                  <span className="text-sm text-ink-muted">
                    Chưa có bộ kiểm thử. Các ca vẫn dùng được khi chưa gom vào bộ
                  </span>
                )}
              </div>
              <div className="mt-3 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-5 2xl:grid-cols-7">
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
                      ...tests
                        .map((item) => item.current_version?.type || item.type)
                        .filter(Boolean),
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
              empty={
                testFilters.suite_id
                  ? "Bộ kiểm thử này chưa có ca kiểm thử được phê duyệt"
                  : "Chưa có ca kiểm thử được phê duyệt"
              }
              columns={[
                { key: "test_case_key", label: "Mã", minWidth: 82 },
                {
                  key: "title",
                  label: "Tên",
                  minWidth: 170,
                  render: (item) => (
                    <div className="min-w-0">
                      <span
                        className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                        title={item.current_version?.title || ""}
                      >
                        {item.current_version?.title}
                      </span>
                      <span className="mt-1 block truncate text-[11px] text-ink-muted">
                        {[
                          valueLabel(item.current_version?.type || item.type),
                          valueLabel(
                            item.current_version?.priority || item.priority || "UNASSESSED",
                          ),
                          item.latest_result ? valueLabel(item.latest_result) : "Chưa chạy",
                        ].join(" · ")}
                      </span>
                    </div>
                  ),
                  mobileRender: (item) => item.current_version?.title,
                },
                {
                  key: "status",
                  label: "Trạng thái ca",
                  minWidth: 88,
                  render: (item) => <StatusPill value={item.status} />,
                },
                {
                  key: "updated_at",
                  label: "Cập nhật",
                  minWidth: 104,
                  render: (item) => formatDate(item.updated_at),
                },
                {
                  key: "lifecycle",
                  label: "Thao tác",
                  minWidth: 64,
                  hideWhenEmpty: true,
                  render: (item) => {
                    const hasActions =
                      can("testcase.version.create") ||
                      can("testcase.clone") ||
                      (item.status !== "OBSOLETE" && can("testcase.bulk.archive")) ||
                      (item.status === "OBSOLETE" && can("testcase.restore"));
                    if (!hasActions) return null;
                    return (
                      <AnchoredActionMenu
                        label={`Thao tác ca kiểm thử ${item.test_case_key}`}
                        className="icon-button flex h-9 w-9 items-center justify-center"
                      >
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
                                  "Phiên bản hiện tại được giữ nguyên. Bản mới sẽ được gửi rà soát và phê duyệt",
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
                                  testingApi
                                    .listTestVersions(item._id)
                                    .then((versions) =>
                                      setTestVersions(
                                        versions.map(normalizeTestCaseVersionForDisplay),
                                      ),
                                    ),
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
                                  setTestVersions(
                                    (await testingApi.listTestVersions(item._id)).map(
                                      normalizeTestCaseVersionForDisplay,
                                    ),
                                  );
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
                      </AnchoredActionMenu>
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
              <p className="text-sm text-ink-muted">Lưu phần đang biên tập trước khi mở so sánh</p>
            )}
          </div>
          <Panel
            title={`${canDraft("testcase.update", selectedDraft) && ["DRAFT", "READY"].includes(selectedDraft.status) ? "Biên tập" : "Chi tiết"} ${selectedDraft.test_case_key}`}
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
                  dung hiện tại; hãy rà soát lại căn cứ trước khi duyệt
                </p>
              )}
            {canDraft("testcase.update", selectedDraft) &&
            ["DRAFT", "READY"].includes(selectedDraft.status) ? (
              <>
                <div className="test-design-form grid gap-4 p-5 lg:grid-cols-2">
                  <label className="field-label lg:col-span-2">
                    Tên ca kiểm thử
                    <input
                      className="apple-input mt-2"
                      value={draftEdit.title}
                      onChange={(event) => changeDraftEdit({ title: event.target.value })}
                    />
                  </label>
                  <label className="field-label lg:col-span-2">
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
                  <div className="space-y-4 lg:col-span-2">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="field-label">Các bước kiểm thử</p>
                      {["DRAFT", "READY"].includes(selectedDraft.status) &&
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
                          <ObjectTestDataEntries
                            key={step.id}
                            label={`Dữ liệu bước ${index + 1}`}
                            value={step.data || {}}
                            onChange={(data) => {
                              const steps = [...draftEdit.steps];
                              steps[index] = { ...step, data };
                              changeDraftEdit({ steps });
                            }}
                          />
                        </div>
                        {["DRAFT", "READY"].includes(selectedDraft.status) &&
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
                <details className="mx-5 mb-5 rounded-control border border-border">
                  <summary className="cursor-pointer p-4 font-medium">Tùy chọn</summary>
                  <div className="test-design-form grid gap-4 p-5 lg:grid-cols-2">
                    <label className="field-label">
                      Module / Tính năng
                      <input
                        className="apple-input mt-2"
                        maxLength={300}
                        value={draftEdit.module_name}
                        onChange={(event) => changeDraftEdit({ module_name: event.target.value })}
                      />
                    </label>
                    <div className="grid gap-3 lg:col-span-2 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <TestTypeSelector
                          value={draftEdit.type || draftEdit.test_kind}
                          onChange={(type) => changeDraftEdit({ type, test_kind: "" })}
                        />
                      </div>
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
                        Cấp kiểm thử
                        <select
                          aria-label="Cấp kiểm thử bản nháp"
                          className="apple-input mt-2"
                          value={draftEdit.test_level}
                          onChange={(event) => changeDraftEdit({ test_level: event.target.value })}
                        >
                          <option value="">-</option>
                          {draftTestLevelOptions.map((value) => (
                            <option key={value} value={value}>
                              {valueLabel(value)}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <div className="grid gap-4 lg:col-span-2">
                      <MultiSelect
                        showSearch={false}
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
                              description: "Phiên bản này không còn trong danh sách hiện tại",
                            })),
                        ]}
                        value={draftEdit.requirementVersionIds}
                        onChange={(requirementVersionIds) => {
                          const allowed = new Set(
                            requirements
                              .filter((item) =>
                                requirementVersionIds.includes(item.current_version_id),
                              )
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
                        showSearch={false}
                        label="Tiêu chí chấp nhận liên kết"
                        searchPlaceholder="Tìm tiêu chí chấp nhận"
                        options={[
                          ...requirements
                            .filter((item) =>
                              draftEdit.requirementVersionIds.includes(item.current_version_id),
                            )
                            .flatMap((item) =>
                              (item.current_version?.acceptance_criteria || []).map(
                                (criterion) => ({
                                  value: criterion._id,
                                  label: `${item.requirement_key} · ${criterion.key || "Tiêu chí"}`,
                                  description:
                                    criterion.plain_text || docText(criterion.content_doc),
                                }),
                              ),
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
                              description:
                                "Tiêu chí này không còn trong phiên bản yêu cầu hiện tại",
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
                    <label className="field-label lg:col-span-2">
                      Mục tiêu kiểm thử
                      <textarea
                        className="apple-input mt-2 min-h-20"
                        value={draftEdit.objective}
                        onChange={(event) => changeDraftEdit({ objective: event.target.value })}
                      />
                    </label>
                    <label className="field-label">
                      Tiền điều kiện
                      <textarea
                        className="apple-input mt-2 min-h-24"
                        value={draftEdit.preconditions}
                        onChange={(event) => changeDraftEdit({ preconditions: event.target.value })}
                      />
                    </label>
                    <MultiSelect
                      showSearch={false}
                      label="Điều kiện kiểm thử đã phê duyệt"
                      options={[
                        ...testConditions.map((item) => ({
                          value: item._id,
                          label: `${item.condition_key} ${item.title}`,
                        })),
                        ...draftEdit.testConditionIds
                          .filter((id) => !testConditions.some((item) => item._id === id))
                          .map((id) => ({ value: id, label: `Điều kiện đã liên kết (${id})` })),
                      ]}
                      searchPlaceholder="Tìm điều kiện kiểm thử"
                      value={draftEdit.testConditionIds}
                      onChange={(testConditionIds) => changeDraftEdit({ testConditionIds })}
                    />
                    <label className="field-label lg:col-span-2">
                      Hậu điều kiện
                      <textarea
                        className="apple-input mt-2 min-h-24"
                        value={draftEdit.postconditions}
                        onChange={(event) =>
                          changeDraftEdit({ postconditions: event.target.value })
                        }
                      />
                    </label>
                    <TechniqueSelector
                      value={draftEdit.techniques}
                      onChange={(techniques) => changeDraftEdit({ techniques })}
                    />
                    <label className="field-label lg:col-span-2">
                      Luồng chính
                      <textarea
                        className="apple-input mt-2 min-h-24"
                        value={draftEdit.mainFlow}
                        onChange={(event) => changeDraftEdit({ mainFlow: event.target.value })}
                      />
                    </label>
                    <fieldset className="space-y-3 rounded-control border border-border p-4 lg:col-span-2">
                      <legend className="px-1 font-medium">
                        Luồng thay thế và ngoại lệ (tùy chọn)
                      </legend>
                      <div className="grid gap-4 md:grid-cols-2">
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
                      </div>
                    </fieldset>
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
                        onChange={(event) =>
                          changeDraftEdit({ automationStatus: event.target.value })
                        }
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
                              <option value="">-</option>
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
                                nguyên
                              </span>
                            )}
                          </>
                        ) : (
                          <p className="mt-2 text-sm text-ink-muted">{draftEdit.ownerId || "-"}</p>
                        )}
                      </label>
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
                    {["DRAFT", "READY"].includes(selectedDraft.status) &&
                      canDraft("testcase.update", selectedDraft) && (
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
                </details>
              </>
            ) : (
              <dl className="grid gap-4 p-5 sm:grid-cols-2">
                {[
                  ["Module / Tính năng", draftEdit.module_name],
                  ["Loại ca", valueLabel(draftEdit.type)],
                  ["Mức ưu tiên", valueLabel(draftEdit.priority)],
                  ["Mục tiêu", draftEdit.objective],
                  ["Tiền điều kiện", draftEdit.preconditions],
                  ["Hậu điều kiện", draftEdit.postconditions],
                  ["Luồng chính", draftEdit.mainFlow],
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
                    soát mới
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
      {workspaceView === "test-sets" && access.canReadTestSets && (
        <Panel title="Danh sách bộ kiểm thử">
          <div className="space-y-5 p-4 sm:p-5">
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: "Tổng bộ kiểm thử", value: suites.length },
                { label: "Đang sử dụng", value: activeSuiteCount },
                { label: "Đã lưu trữ", value: archivedSuiteCount },
              ].map((metric) => (
                <div className="rounded-control border border-border px-4 py-3" key={metric.label}>
                  <p className="text-xs text-ink-muted">{metric.label}</p>
                  <p className="mt-1 text-xl font-semibold tabular-nums">{metric.value}</p>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
              <SearchField
                ariaLabel="Tìm bộ kiểm thử"
                className="min-w-0 flex-1 lg:max-w-xl"
                onChange={(event) => setSuiteSearch(event.target.value)}
                placeholder="Tìm theo tên hoặc loại bộ"
                value={suiteSearch}
              />
              <div className="flex flex-wrap items-center gap-2">
                <div
                  className="inline-flex max-w-full rounded-control border border-border p-1"
                  role="group"
                  aria-label="Lọc trạng thái bộ kiểm thử"
                >
                  {[
                    { id: "all", label: "Tất cả", count: suites.length },
                    { id: "active", label: "Đang sử dụng", count: activeSuiteCount },
                    { id: "archived", label: "Đã lưu trữ", count: archivedSuiteCount },
                  ].map((filter) => (
                    <button
                      aria-pressed={suiteStatusFilter === filter.id}
                      className={`rounded-[5px] px-3 py-2 text-sm transition-colors ${suiteStatusFilter === filter.id ? "bg-surface-quiet font-medium text-ink" : "text-ink-muted hover:bg-surface-quiet hover:text-ink"}`}
                      key={filter.id}
                      onClick={() => setSuiteStatusFilter(filter.id)}
                      type="button"
                    >
                      {filter.label} <span className="ml-1 tabular-nums">{filter.count}</span>
                    </button>
                  ))}
                </div>
                {can("testsuite.create") && (
                  <button className="apple-button shrink-0" type="button" onClick={createTestSet}>
                    Tạo bộ kiểm thử
                  </button>
                )}
              </div>
            </div>
            <p aria-live="polite" className="text-sm text-ink-muted">
              {visibleSuites.length} / {suites.length} bộ kiểm thử
            </p>
            {visibleSuites.length ? (
              <ul className="min-w-0 divide-y divide-border overflow-hidden rounded-control border border-border">
                {visibleSuites.map((item) => (
                  <li
                    key={item._id}
                    className="grid min-w-0 gap-3 bg-surface px-4 py-4 transition-colors hover:bg-surface-quiet/50 sm:px-5 lg:grid-cols-[minmax(0,1fr)_10rem_9rem_auto] lg:items-center"
                  >
                    <div className="min-w-0">
                      <h3 className="break-words font-semibold leading-6">{item.name}</h3>
                      <p className="mt-1 text-sm text-ink-muted">{valueLabel(item.suite_type)}</p>
                    </div>
                    <p className="text-sm text-ink-muted">
                      <span className="font-semibold text-ink tabular-nums">
                        {item.test_case_version_ids?.length || 0}
                      </span>{" "}
                      ca kiểm thử
                    </p>
                    <div className="flex items-center">
                      <StatusPill value={item.status} />
                    </div>
                    <div className="flex shrink-0 items-center gap-2 lg:justify-end">
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
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="px-5 py-10 text-center" role="status">
                <p className="font-semibold text-ink">
                  {suites.length ? "Không tìm thấy bộ kiểm thử phù hợp" : "Chưa có bộ kiểm thử"}
                </p>
                {suites.length > 0 && (
                  <button
                    className="secondary-button mt-3"
                    type="button"
                    onClick={() => {
                      setSuiteSearch("");
                      setSuiteStatusFilter("all");
                    }}
                  >
                    Xóa bộ lọc
                  </button>
                )}
              </div>
            )}
          </div>
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
