"use client";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Archive, ClipboardCheck, Copy, Pencil, Send, Check } from "lucide-react";
import DeviceMatricesPanel from "../../components/DeviceMatricesPanel";
import AgentRunPanel from "../../components/AgentRunPanel";
import TestPlanEditor from "../../components/TestPlanEditor";
import EnvironmentIncidentPanel from "../../components/EnvironmentIncidentPanel";
import NonFunctionalTestPanel from "../../components/NonFunctionalTestPanel";
import {
  ErrorState,
  LoadingState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { testingApi } from "../../services/testing.service";
import {
  docText,
  formatDate as formatDateValue,
  messageOf,
  textDoc,
  valueLabel,
} from "../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import SearchField from "@/shared/components/ui/SearchField";
import RunExecutionWorkspace from "./execution/RunExecutionWorkspace";
import JUnitResultPanel from "../../components/JUnitResultPanel";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import {
  operationForRetry,
  shouldReloadAfterAmbiguousMutation,
} from "../../lib/executionRecovery.logic.mjs";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

const testPlanFindingLabels = {
  TEST_PLAN_STRATEGY_REQUIRED:
    "Chọn chiến lược đã duyệt hoặc bổ sung cách tiếp cận kiểm thử trong kế hoạch.",
  TEST_PLAN_OBJECTIVE_REQUIRED: "Bổ sung mục tiêu của kế hoạch.",
  TEST_PLAN_SCOPE_REQUIRED: "Bổ sung phạm vi kiểm thử.",
  TEST_PLAN_REQUIREMENT_SCOPE_REQUIRED: "Chọn phiên bản yêu cầu trong phạm vi.",
  TEST_PLAN_ENTRY_CRITERIA_REQUIRED: "Bổ sung điều kiện bắt đầu.",
  TEST_PLAN_EXIT_CRITERIA_REQUIRED: "Bổ sung điều kiện kết thúc.",
  TEST_PLAN_TEST_TYPE_REQUIRED: "Chọn loại kiểm thử.",
  TEST_PLAN_QUALITY_TARGET_REQUIRED: "Bổ sung mục tiêu chất lượng.",
  TEST_PLAN_SCHEDULE_REQUIRED: "Bổ sung thời gian dự kiến bắt đầu và kết thúc.",
  TEST_PLAN_RELEASE_REQUIRED: "Chọn bản phát hành.",
  TEST_PLAN_ENVIRONMENT_REQUIRED: "Chọn môi trường kiểm thử.",
};

export default function ExecutionPage({ project, section, workspaceView }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const { ask, dialog } = useActionDialog();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sourceRequirementId = searchParams.get("requirementVersionId") || "";
  const openedRequirement = useRef("");
  const runId = section[0] || "";
  const [plans, setPlans] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [suites, setSuites] = useState([]);
  const [releases, setReleases] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [runs, setRuns] = useState([]);
  const [runPage, setRunPage] = useState(1);
  const [runPageInfo, setRunPageInfo] = useState(null);
  const [runNameSearch, setRunNameSearch] = useState("");
  const [runEnvironmentSearch, setRunEnvironmentSearch] = useState("");
  const [runFilters, setRunFilters] = useState({
    name: "",
    status: "",
    environment: "",
    sort: "-updated_at",
  });
  const [planFilters, setPlanFilters] = useState({
    q: "",
    release: "",
    status: "",
    sort: "-updated_at",
  });
  const [suiteFilters, setSuiteFilters] = useState({
    q: "",
    suite_type: "",
    status: "",
    sort: "-updated_at",
  });
  const [tests, setTests] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [members, setMembers] = useState([]);
  const [run, setRun] = useState(null);
  const [creatingDefectResultIds, setCreatingDefectResultIds] = useState(() => new Set());
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const loadedRunRoute = useRef(`${project._id}:${runId}`);
  const loadGeneration = useRef(0);
  const [planValidation, setPlanValidation] = useState(null);
  const [creatingPlan, setCreatingPlan] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [viewingPlan, setViewingPlan] = useState(null);
  const [creatingSuite, setCreatingSuite] = useState(false);
  const [creatingRun, setCreatingRun] = useState(false);
  const [savingRun, setSavingRun] = useState(false);
  const [savingExecution, setSavingExecution] = useState(false);
  const savingExecutionRef = useRef(false);
  const runCreationInFlight = useRef(false);
  const runCreateOperation = useRef(null);
  const defectCreateOperations = useRef(new Map());
  const defectCreateInFlight = useRef(new Set());
  const [runSubsection, setRunSubsection] = useState("runs");
  const [automationSubsection, setAutomationSubsection] = useState("results");
  const [runForm, setRunForm] = useState({
    name: "",
    release: "",
    build: "",
    environment: "",
    environmentId: "",
    releaseId: "",
    buildId: "",
    testPlanId: "",
    suiteIds: [],
    versionIds: [],
    assignmentStrategy: "MANUAL",
  });
  const [actuals, setActuals] = useState({});
  const [stepResults, setStepResults] = useState({});
  const [attachments, setAttachments] = useState({});
  const [resumeContext, setResumeContext] = useState(null);
  const can = (permission) => project.current_permissions?.includes(permission);
  const runSubsectionTabs = [
    ...(can("testrun.read") ? [{ id: "runs", label: "Lần chạy" }] : []),
    ...(can("environmentincident.read") ? [{ id: "incidents", label: "Sự cố môi trường" }] : []),
    ...(can("nfrtest.read") ? [{ id: "nonfunctional", label: "Kiểm thử phi chức năng" }] : []),
  ];
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const canReadAiRuns =
    permissions.includes("automation.read") || permissions.includes("proposal.read");
  const terminalResultStatuses = project.settings?.allow_not_applicable_results
    ? ["PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE"]
    : ["PASS", "FAIL", "BLOCKED", "SKIPPED"];
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    const routeKey = `${project._id}:${runId}`;
    if (loadedRunRoute.current !== routeKey) {
      loadedRunRoute.current = routeKey;
      setRun(null);
      setResumeContext(null);
      setActuals({});
      setStepResults({});
      setAttachments({});
      if (runId) {
        setInitialLoading(true);
        setInitialLoadFailed(false);
      }
    }
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
    }
    if (!initialDataLoaded.current) {
      setInitialLoading(true);
      setInitialLoadFailed(false);
    }
    let memberLoadError = "";
    try {
      const [
        planValues,
        suiteValues,
        runValues,
        testValues,
        releaseValues,
        buildValues,
        environmentValues,
        strategyValues,
        requirementValues,
        memberValues,
      ] = await Promise.all([
        permissions.includes("testplan.read")
          ? testingApi.listPlans(project._id, planFilters)
          : Promise.resolve([]),
        permissions.includes("testsuite.read")
          ? testingApi.listSuites(project._id, suiteFilters)
          : Promise.resolve([]),
        permissions.includes("testrun.read")
          ? testingApi.listRunPage(project._id, { ...runFilters, page: runPage, page_size: 50 })
          : Promise.resolve({ items: [] }),
        permissions.includes("testcase.read")
          ? testingApi.listTestCases(project._id, { page_size: 500 })
          : Promise.resolve([]),
        permissions.includes("release.read")
          ? testingApi.listReleases(project._id)
          : Promise.resolve([]),
        permissions.includes("build.read")
          ? testingApi.listBuilds(project._id)
          : Promise.resolve([]),
        permissions.includes("environment.read")
          ? testingApi.listEnvironments(project._id)
          : Promise.resolve([]),
        permissions.includes("teststrategy.read")
          ? testingApi.listTestStrategies(project._id, { page_size: 200 })
          : Promise.resolve({ items: [] }),
        permissions.includes("requirement.read")
          ? testingApi.listRequirements(project._id, { page_size: 500, status: "BASELINED" })
          : Promise.resolve([]),
        permissions.includes("project.members.read") &&
        (permissions.includes("testrun.assign") ||
          permissions.includes("testplan.create") ||
          permissions.includes("testplan.update"))
          ? testingApi.listMembers(project._id).catch((reason) => {
              memberLoadError = `Không tải được danh sách thành viên để phân công: ${messageOf(reason)}`;
              return [];
            })
          : Promise.resolve([]),
      ]);
      const runValue =
        runId && permissions.includes("testrun.read") ? await testingApi.getRun(runId) : null;
      if (requestGeneration !== loadGeneration.current) return;
      if (runValue && runValue.project_id !== project._id) {
        throw new Error("Lần chạy không thuộc dự án đang mở");
      }
      if (memberLoadError) setError(memberLoadError);
      setPlans(planValues);
      setSuites(suiteValues);
      setRuns(runValues.items);
      setRunPageInfo(runValues);
      setTests(testValues);
      setReleases(releaseValues);
      setBuilds(buildValues);
      setEnvironments(environmentValues);
      setStrategies(strategyValues.items || []);
      setRequirements(requirementValues);
      setMembers(memberValues);
      setRun(runValue);
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      if (requestGeneration !== loadGeneration.current) return;
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
      setError(messageOf(reason));
    } finally {
      if (requestGeneration === loadGeneration.current) setInitialLoading(false);
    }
  }, [
    initialDataLoaded,
    loadedProjectId,
    planFilters,
    project._id,
    permissions,
    runFilters,
    runId,
    runPage,
    suiteFilters,
  ]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setRunPage(1);
      setRunFilters((current) => {
        if (current.name === runNameSearch && current.environment === runEnvironmentSearch) {
          return current;
        }
        return {
          ...current,
          name: runNameSearch,
          environment: runEnvironmentSearch,
        };
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [runEnvironmentSearch, runNameSearch]);
  useEffect(() => {
    const key = `${project._id}:${sourceRequirementId}`;
    if (
      workspaceView === "test-plans" &&
      sourceRequirementId &&
      openedRequirement.current !== key &&
      project.current_permissions?.includes("testplan.create") &&
      requirements.some((item) => item.current_version_id === sourceRequirementId)
    ) {
      openedRequirement.current = key;
      setCreatingPlan(true);
    }
  }, [project._id, project.current_permissions, sourceRequirementId, requirements, workspaceView]);
  const versions = tests.map((item) => item.current_version_id).filter(Boolean);
  const selectRunPlan = (planId) => {
    const plan = plans.find((item) => item._id === planId);
    const scope = plan?.approved_snapshot || plan;
    setRunForm((current) => ({
      ...current,
      testPlanId: planId,
      ...(scope
        ? {
            versionIds: scope.test_case_version_ids || [],
            suiteIds: [],
            releaseId: scope.release_id || "",
            release: scope.release || "",
            buildId: scope.build_id || "",
            build: scope.build || "",
            environmentId: scope.environment_id || "",
            environment: scope.environment || "",
          }
        : {}),
    }));
  };
  const createRun = async (event) => {
    event.preventDefault();
    if (runCreationInFlight.current) return;
    const payload = {
      project_id: project._id,
      name: runForm.name,
      test_plan_id: runForm.testPlanId || null,
      expected_test_plan_snapshot_hash:
        plans.find((item) => item._id === runForm.testPlanId)?.approved_snapshot_hash || null,
      test_suite_ids: runForm.suiteIds,
      test_case_version_ids: runForm.versionIds,
      assignment_strategy: runForm.assignmentStrategy,
      environment: runForm.environment || undefined,
      environment_id: runForm.environmentId || null,
      release: runForm.release,
      release_id: runForm.releaseId || null,
      build: runForm.build,
      build_id: runForm.buildId || null,
    };
    const signature = JSON.stringify(payload);
    runCreateOperation.current = operationForRetry(
      runCreateOperation.current,
      signature,
      crypto.randomUUID(),
    );
    runCreationInFlight.current = true;
    setSavingRun(true);
    try {
      await testingApi.createRun({
        ...payload,
        idempotency_key: runCreateOperation.current.idempotencyKey,
      });
      runCreateOperation.current = null;
      setRunForm({
        name: "",
        release: "",
        build: "",
        environment: "",
        environmentId: "",
        releaseId: "",
        buildId: "",
        testPlanId: "",
        suiteIds: [],
        versionIds: [],
        assignmentStrategy: "MANUAL",
      });
      setCreatingRun(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      runCreationInFlight.current = false;
      setSavingRun(false);
    }
  };
  const transition = async (execution, status, version) => {
    const saveResult = async (resultNote) => {
      if (savingExecutionRef.current) {
        throw new Error("Kết quả thực thi đang được lưu. Hãy chờ thao tác này hoàn tất.");
      }
      savingExecutionRef.current = true;
      setSavingExecution(true);
      try {
        await saveExecutionResult(execution, status, version, resultNote);
      } finally {
        savingExecutionRef.current = false;
        setSavingExecution(false);
      }
    };
    try {
      const resultNote = "Kết quả thực thi thủ công";
      if (status === "NOT_APPLICABLE") {
        await ask({
          title: "Ghi nhận kết quả Không áp dụng",
          description: `${version.test_case_key} ${version.title}`,
          confirmLabel: "Ghi nhận",
          fields: [
            {
              name: "reason",
              label: "Lý do Không áp dụng",
              required: true,
              multiline: true,
              autoFocus: true,
            },
          ],
          onConfirm: async (answer) => {
            try {
              await saveResult(answer.reason.trim());
            } catch (reason) {
              throw new Error(messageOf(reason));
            }
          },
        });
        return;
      }
      await saveResult(resultNote);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const saveExecutionResult = async (execution, status, version, resultNote) => {
    const values = (version.steps || []).map((step) => {
      const existing = execution.step_results?.find((item) => item.step_id === step.id);
      const edited = stepResults[execution._id]?.[step.id];
      return {
        step_id: step.id,
        status: edited?.status || existing?.status || "PASS",
        actual_doc: textDoc(edited?.actual || docText(existing?.actual_doc)),
        attachments: existing?.attachments || [],
        note: edited?.note ?? existing?.note ?? "",
      };
    });
    const invalidStep = values.find(
      (item) => item.status === "NOT_APPLICABLE" && item.note.trim().length < 2,
    );
    if (invalidStep) {
      throw new Error("Mỗi bước Không áp dụng phải có lý do riêng");
    }
    try {
      await testingApi.updateExecution(project._id, execution._id, {
        status,
        step_results: status === "IN_PROGRESS" ? execution.step_results || [] : values,
        actual_result_doc: textDoc(actuals[execution._id] || docText(execution.actual_result_doc)),
        attachments: attachments[execution._id] || execution.attachments || [],
        note: resultNote,
        idempotency_key: crypto.randomUUID(),
        expected_revision: execution.revision,
      });
    } catch (reason) {
      if (shouldReloadAfterAmbiguousMutation(reason)) {
        try {
          setRun(await testingApi.getRun(run._id));
        } catch {}
      }
      throw reason;
    }
    setResumeContext(null);
    setRun(await testingApi.getRun(run._id));
  };
  const createDefectFromResult = async (result, version, aiDraft = null) => {
    const defaultSteps = (version.steps || [])
      .map((step) => docText(step.action_doc))
      .filter(Boolean)
      .join("\n");
    const defaultExpected = (version.steps || [])
      .map((step) => docText(step.expected_doc))
      .filter(Boolean)
      .join("\n");
    const activeStrategy = strategies.find((item) => item.active_approved);
    const defectSeverities = (activeStrategy?.risk_model?.severity_scale || [])
      .map((item) => String(item.label || "").trim())
      .filter(Boolean);
    const defectPriorities = (activeStrategy?.risk_model?.priority_scale || [])
      .map((item) => String(item.label || "").trim())
      .filter(Boolean);
    const initialPriority = String(version.priority || "").toLowerCase();
    await ask({
      title: aiDraft ? "Rà soát bản nháp lỗi từ AI" : "Tạo lỗi từ kết quả kiểm thử",
      description: aiDraft
        ? "AI chỉ tạo bản nháp dựa trên kết quả đã lưu. Kiểm tra và chỉnh các trường, sau đó xác nhận để tạo lỗi."
        : `Kiểm tra thông tin của ${version.test_case_key} trước khi tạo lỗi liên kết với lần chạy ${run.name}.`,
      confirmLabel: "Xác nhận tạo lỗi",
      fields: [
        {
          name: "title",
          label: "Tiêu đề",
          initialValue:
            aiDraft?.title || `Lỗi khi thực thi ${version.test_case_key} ${version.title}`,
          required: true,
          autoFocus: true,
        },
        {
          name: "description",
          label: "Mô tả",
          initialValue: aiDraft?.description || `Phát hiện trong lần chạy ${run.name}`,
          required: true,
          multiline: true,
        },
        {
          name: "steps",
          label: "Các bước tái hiện",
          initialValue: aiDraft?.steps_to_reproduce?.join("\n") || defaultSteps,
          multiline: true,
        },
        {
          name: "expected",
          label: "Kết quả mong đợi",
          initialValue: aiDraft?.expected_result || defaultExpected,
          multiline: true,
        },
        {
          name: "actual",
          label: "Kết quả thực tế",
          initialValue: aiDraft?.actual_result || docText(result.actual_result_doc),
          multiline: true,
        },
        {
          name: "severity",
          label: "Mức độ ảnh hưởng",
          required: true,
          options: [
            { value: "", label: "Chọn mức độ" },
            ...defectSeverities.map((value) => ({ value, label: value })),
          ],
        },
        {
          name: "priority",
          label: "Ưu tiên xử lý",
          required: true,
          initialValue:
            defectPriorities.find((value) => value.toLowerCase() === initialPriority) ||
            defectPriorities[0] ||
            "",
          options: [
            { value: "", label: "Chọn mức ưu tiên" },
            ...defectPriorities.map((value) => ({ value, label: value })),
          ],
        },
      ],
      onConfirm: async (values) => {
        if (defectCreateInFlight.current.has(result._id)) return;
        defectCreateInFlight.current.add(result._id);
        setCreatingDefectResultIds((current) => new Set(current).add(result._id));
        const operationKey = `${project._id}:${result._id}`;
        let idempotencyKey = defectCreateOperations.current.get(operationKey);
        if (!idempotencyKey) {
          idempotencyKey = crypto.randomUUID();
          defectCreateOperations.current.set(operationKey, idempotencyKey);
        }
        try {
          await testingApi.createDefect(project._id, {
            idempotency_key: idempotencyKey,
            project_id: project._id,
            title: values.title,
            description_doc: textDoc(values.description),
            steps_to_reproduce: values.steps
              .split("\n")
              .map((step) => step.trim())
              .filter(Boolean)
              .map((action) => ({ action_doc: textDoc(action), expected_doc: textDoc("") })),
            actual_result_doc: textDoc(values.actual),
            expected_result_doc: textDoc(values.expected),
            severity: values.severity,
            priority: values.priority,
            environment: run.environment || "",
            build: run.build || "",
            attachments: result.attachments || [],
            linked_test_result_id: result._id,
            linked_test_case_version_id: version._id,
            linked_requirement_version_ids: version.requirement_version_ids || [],
          });
          setRun(await testingApi.getRun(run._id));
          defectCreateOperations.current.delete(operationKey);
        } catch (reason) {
          throw new Error(messageOf(reason));
        } finally {
          defectCreateInFlight.current.delete(result._id);
          setCreatingDefectResultIds((current) => {
            const next = new Set(current);
            next.delete(result._id);
            return next;
          });
        }
      },
    });
  };
  const updatePlan = async (item) => {
    setEditingPlan(item);
  };
  const transitionPlan = async (item, action) => {
    if (action === "approve" && can("testplan.review")) {
      try {
        const validation = await testingApi.validatePlan(item._id);
        setPlanValidation({ ...validation, planId: item._id, revision: item.revision });
        if (!validation.ready_for_approval) {
          setError(
            validation.findings
              .map(
                (finding) =>
                  testPlanFindingLabels[finding.code] || "Cần bổ sung thông tin kế hoạch",
              )
              .join(" "),
          );
          return;
        }
      } catch (reason) {
        setError(messageOf(reason));
        return;
      }
    }
    await ask({
      title:
        action === "revise"
          ? "Yêu cầu chỉnh sửa kế hoạch"
          : action === "approve"
            ? "Phê duyệt kế hoạch"
            : action === "archive"
              ? "Lưu trữ kế hoạch"
              : "Gửi rà soát kế hoạch",
      description: item.name,
      confirmLabel:
        action === "revise"
          ? "Yêu cầu chỉnh sửa"
          : action === "approve"
            ? "Phê duyệt"
            : action === "archive"
              ? "Lưu trữ"
              : "Gửi rà soát",
      danger: action === "archive",
      fields: [
        { name: "note", label: "Ghi chú", required: true, multiline: true, autoFocus: true },
      ],
      onConfirm: async (answer) => {
        try {
          const payload =
            action === "archive"
              ? { expected_revision: item.revision, reason: answer.note }
              : { expected_revision: item.revision, review_note: answer.note };
          if (action === "revise") await testingApi.requestPlanRevision(item._id, payload);
          else if (action === "approve") await testingApi.approvePlan(item._id, payload);
          else if (action === "archive") await testingApi.archivePlan(item._id, payload);
          else await testingApi.submitPlan(item._id, payload);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const createBuild = async () => {
    await ask({
      title: "Tạo bản dựng",
      description: "Khai báo bản dựng để liên kết với kế hoạch, lần chạy và báo cáo hoàn tất.",
      confirmLabel: "Tạo bản dựng",
      fields: [
        {
          name: "identifier",
          label: "Mã bản dựng",
          required: true,
          maxLength: 200,
          autoFocus: true,
        },
        { name: "version", label: "Phiên bản", required: true, maxLength: 120 },
        {
          name: "release_id",
          label: "Bản phát hành",
          options: [
            { value: "", label: "Chưa liên kết" },
            ...releases.map((item) => ({
              value: item._id,
              label: `${item.key} · ${item.name}`,
            })),
          ],
        },
        { name: "commit_ref", label: "Mã commit hoặc tham chiếu", maxLength: 300 },
        { name: "notes", label: "Ghi chú", multiline: true, maxLength: 5000 },
      ],
      onConfirm: async (values) => {
        try {
          await testingApi.createBuild(project._id, {
            identifier: values.identifier.trim(),
            version: values.version.trim(),
            release_id: values.release_id || null,
            commit_ref: values.commit_ref || null,
            notes: values.notes || "",
            idempotency_key: crypto.randomUUID(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const manageBuild = async (build) => {
    await ask({
      title: `Sửa bản dựng ${build.identifier}`,
      confirmLabel: "Lưu thay đổi",
      fields: [
        {
          name: "commit_ref",
          label: "Mã commit hoặc tham chiếu",
          initialValue: build.commit_ref || "",
          maxLength: 300,
        },
        {
          name: "notes",
          label: "Ghi chú",
          initialValue: build.notes || "",
          multiline: true,
          maxLength: 5000,
        },
      ],
      onConfirm: async (values) => {
        try {
          await testingApi.updateBuild(build._id, {
            expected_revision: build.revision,
            commit_ref: values.commit_ref || null,
            notes: values.notes || "",
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const setCurrentBuild = async (build) => {
    try {
      await testingApi.setCurrentBuild(build._id, build.revision);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const updateSuite = async (item) => {
    await ask({
      title: "Sửa bộ kiểm thử",
      description: item.name,
      confirmLabel: "Lưu bộ kiểm thử",
      fields: [
        { name: "name", label: "Tên", initialValue: item.name, required: true, autoFocus: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.updateSuite(item._id, {
            expected_revision: item.revision,
            name: answer.name,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const archiveSuite = async (item) => {
    await ask({
      title: "Lưu trữ bộ kiểm thử",
      description: item.name,
      confirmLabel: "Lưu trữ",
      danger: true,
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.archiveSuite(item._id, {
            expected_revision: item.revision,
            reason: answer.reason,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const pageTitle =
    workspaceView === "test-plans"
      ? "Kế hoạch kiểm thử"
      : workspaceView === "test-runs"
        ? "Lần chạy kiểm thử"
        : workspaceView === "automation"
          ? "Tự động hóa kiểm thử"
          : "Thực thi kiểm thử";
  if (initialLoading || initialLoadFailed) {
    return (
      <WorkspacePage title={pageTitle} actions={<ProjectCrumb projectId={project._id} />}>
        {initialLoading ? (
          <LoadingState />
        ) : (
          <div className="space-y-3">
            <ErrorState message={error || "Không thể tải dữ liệu thực thi kiểm thử"} />
            <button className="secondary-button" type="button" onClick={() => void load()}>
              Tải lại
            </button>
          </div>
        )}
      </WorkspacePage>
    );
  }
  if (run)
    return (
      <RunExecutionWorkspace
        run={run}
        projectId={project._id}
        members={members}
        error={error}
        can={can}
        resumeContext={resumeContext}
        onResumeChange={setResumeContext}
        ask={ask}
        onRunChange={setRun}
        onError={setError}
        onTransition={transition}
        onCreateDefect={createDefectFromResult}
        creatingDefectResultIds={creatingDefectResultIds}
        stepResults={stepResults}
        onStepResultsChange={setStepResults}
        terminalResultStatuses={terminalResultStatuses}
        actuals={actuals}
        onActualsChange={setActuals}
        attachments={attachments}
        onAttachmentsChange={setAttachments}
        dialog={dialog}
        savingExecution={savingExecution}
      />
    );
  return (
    <WorkspacePage
      title={pageTitle}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <ProjectCrumb projectId={project._id} />
          {(workspaceView === "" || workspaceView === "test-plans") && can("testplan.create") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => setCreatingPlan(true)}
            >
              Tạo kế hoạch
            </button>
          )}
          {!workspaceView && can("testsuite.create") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => setCreatingSuite(true)}
            >
              Tạo bộ kiểm thử
            </button>
          )}
          {(workspaceView === "" || (workspaceView === "test-runs" && runSubsection === "runs")) &&
            can("testrun.create") && (
              <button className="apple-button" type="button" onClick={() => setCreatingRun(true)}>
                Tạo lần chạy
              </button>
            )}
          {can("build.create") && (
            <button className="secondary-button" type="button" onClick={createBuild}>
              Tạo bản dựng
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {workspaceView === "test-runs" && runSubsectionTabs.length > 1 && (
        <SegmentedTabs
          label="Khu vực lần chạy kiểm thử"
          value={
            runSubsectionTabs.some((item) => item.id === runSubsection)
              ? runSubsection
              : runSubsectionTabs[0].id
          }
          onChange={setRunSubsection}
          tabs={runSubsectionTabs}
        />
      )}
      {can("build.read") && (
        <Panel title="Bản dựng của dự án">
          {builds.length ? (
            <ul className="divide-y divide-border" aria-label="Bản dựng của dự án">
              {builds.map((build) => (
                <li
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                  key={build._id}
                >
                  <div className="min-w-0">
                    <p className="break-words text-sm font-medium text-ink">
                      {build.identifier} · {build.version}
                      {build.is_current ? " · Bản dựng hiện tại" : ""}
                    </p>
                    <p className="mt-1 break-words text-xs text-ink-muted">
                      {build.release_id
                        ? releases.find((release) => release._id === build.release_id)?.key ||
                          "Đã liên kết bản phát hành"
                        : "Chưa liên kết bản phát hành"}
                      {build.commit_ref ? ` · ${build.commit_ref}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {can("build.manage") && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Sửa bản dựng ${build.identifier}`}
                        title={`Sửa bản dựng ${build.identifier}`}
                        onClick={() => manageBuild(build)}
                      >
                        <Pencil size={16} aria-hidden="true" />
                      </button>
                    )}
                    {!build.is_current && can("build.manage") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setCurrentBuild(build)}
                      >
                        Đặt làm hiện tại
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-5 py-4 text-sm text-ink-muted" role="status">
              Chưa có bản dựng. Tạo bản dựng để liên kết với lần chạy và báo cáo hoàn tất.
            </p>
          )}
        </Panel>
      )}
      <>
        {viewingPlan && (
          <Modal
            isOpen
            onClose={() => setViewingPlan(null)}
            ariaLabel="Chi tiết kế hoạch kiểm thử"
            className="max-h-[94dvh] max-w-5xl overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>{viewingPlan.name}</ModalTitle>
            </ModalHeader>
            <TestPlanEditor
              key={`${viewingPlan._id}:${viewingPlan.revision}`}
              readOnly
              projectId={project._id}
              initialValue={viewingPlan}
              strategies={strategies}
              requirements={requirements}
              suites={suites}
              tests={tests}
              members={members}
              releases={releases}
              builds={builds}
              environments={environments}
              onCancel={() => setViewingPlan(null)}
            />
            <nav
              aria-label="Tiếp tục kế hoạch kiểm thử"
              className="flex flex-wrap gap-3 border-t border-border p-5"
            >
              {can("testcondition.read") && (
                <Link
                  className="secondary-button"
                  href={`/du-an/${project._id}/phan-tich-kiem-thu`}
                >
                  Phân tích kiểm thử
                </Link>
              )}
              {can("testscenario.read") && can("testcase.read") && (
                <Link
                  className="secondary-button"
                  href={`/du-an/${project._id}/ca-kiem-thu/kich-ban`}
                >
                  Kịch bản kiểm thử
                </Link>
              )}
              {can("testcase.read") && (
                <Link className="secondary-button" href={`/du-an/${project._id}/ca-kiem-thu`}>
                  Ca kiểm thử
                </Link>
              )}
              {viewingPlan.status === "APPROVED" && can("testrun.create") && (
                <button
                  type="button"
                  className="apple-button"
                  onClick={() => {
                    selectRunPlan(viewingPlan._id);
                    setViewingPlan(null);
                    setCreatingRun(true);
                  }}
                >
                  Tạo đợt chạy từ kế hoạch
                </button>
              )}
            </nav>
          </Modal>
        )}
        {can("testplan.create") && (
          <Modal
            isOpen={creatingPlan}
            onClose={() => setCreatingPlan(false)}
            ariaLabel="Tạo kế hoạch kiểm thử"
            className="max-h-[94dvh] max-w-5xl overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>Tạo kế hoạch kiểm thử</ModalTitle>
            </ModalHeader>
            <TestPlanEditor
              projectId={project._id}
              initialRequirementVersionIds={sourceRequirementId ? [sourceRequirementId] : []}
              strategies={strategies}
              requirements={requirements}
              suites={suites}
              tests={tests}
              members={members}
              releases={releases}
              builds={builds}
              environments={environments}
              onCancel={() => setCreatingPlan(false)}
              onSave={async (payload) => {
                await testingApi.createPlan(payload);
                setCreatingPlan(false);
                await load();
              }}
            />
          </Modal>
        )}
        {editingPlan && can("testplan.update") && (
          <Modal
            isOpen
            onClose={() => setEditingPlan(null)}
            ariaLabel="Sửa kế hoạch kiểm thử"
            className="max-h-[94dvh] max-w-5xl overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>Sửa kế hoạch kiểm thử</ModalTitle>
            </ModalHeader>
            <TestPlanEditor
              key={`${editingPlan._id}:${editingPlan.revision}`}
              projectId={project._id}
              initialValue={editingPlan}
              strategies={strategies}
              requirements={requirements}
              suites={suites}
              tests={tests}
              members={members}
              releases={releases}
              builds={builds}
              environments={environments}
              onCancel={() => setEditingPlan(null)}
              onSave={async (payload) => {
                await testingApi.updatePlan(editingPlan._id, {
                  ...payload,
                  expected_revision: editingPlan.revision,
                });
                setEditingPlan(null);
                await load();
              }}
            />
          </Modal>
        )}
        {can("testsuite.create") && (
          <Modal
            isOpen={creatingSuite}
            onClose={() => setCreatingSuite(false)}
            ariaLabel="Tạo bộ kiểm thử"
            className="max-w-xl"
          >
            <ModalHeader>
              <ModalTitle>Tạo bộ kiểm thử</ModalTitle>
            </ModalHeader>
            <form
              className="space-y-3 p-5"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const value = new FormData(form);
                try {
                  await testingApi.createSuite({
                    project_id: project._id,
                    name: value.get("name"),
                    suite_type: value.get("type"),
                    test_case_version_ids: versions,
                  });
                  form.reset();
                  setCreatingSuite(false);
                  await load();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              <input
                aria-label="Tên bộ kiểm thử"
                name="name"
                required
                className="apple-input"
                placeholder="Tên bộ kiểm thử"
              />
              <select aria-label="Loại bộ kiểm thử" name="type" className="apple-input">
                <option value="smoke">{valueLabel("smoke")}</option>
                <option value="regression">{valueLabel("regression")}</option>
                <option value="feature">{valueLabel("feature")}</option>
              </select>
              <div className="action-dialog-footer flex justify-end gap-3">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setCreatingSuite(false)}
                >
                  Hủy
                </button>
                <button className="apple-button" type="submit">
                  Lưu bộ kiểm thử
                </button>
              </div>
            </form>
          </Modal>
        )}
        {can("testrun.create") && (
          <Modal
            isOpen={creatingRun}
            onClose={() => {
              if (!savingRun) setCreatingRun(false);
            }}
            ariaLabel="Tạo lần chạy"
            className="max-w-3xl max-h-[90dvh] overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>Tạo lần chạy</ModalTitle>
            </ModalHeader>
            <form className="space-y-3 p-5" onSubmit={createRun}>
              <fieldset className="min-w-0 space-y-3" disabled={savingRun}>
                <legend className="sr-only">Thông tin lần chạy kiểm thử</legend>
                <input
                  aria-label="Tên lần chạy"
                  required
                  className="apple-input"
                  value={runForm.name}
                  onChange={(event) => setRunForm({ ...runForm, name: event.target.value })}
                  placeholder="Tên lần chạy"
                />
                <div className="grid gap-3 sm:grid-cols-3">
                  <select
                    aria-label="Bản phát hành"
                    className="apple-input"
                    value={runForm.releaseId}
                    onChange={(event) => {
                      const releaseId = event.target.value;
                      const release = releases.find((item) => item._id === releaseId);
                      setRunForm({
                        ...runForm,
                        releaseId,
                        release: release?.key || "",
                        buildId: "",
                        build: "",
                      });
                    }}
                  >
                    <option value="">Không gắn bản phát hành</option>
                    {releases.map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.key} · {item.name}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Bản dựng"
                    className="apple-input"
                    value={runForm.buildId}
                    onChange={(event) => {
                      const buildId = event.target.value;
                      const build = builds.find((item) => item._id === buildId);
                      setRunForm({
                        ...runForm,
                        buildId,
                        build: build?.identifier || "",
                        releaseId: build?.release_id || runForm.releaseId,
                        release:
                          releases.find((item) => item._id === build?.release_id)?.key ||
                          runForm.release,
                      });
                    }}
                  >
                    <option value="">Không gắn bản dựng</option>
                    {builds
                      .filter((item) => !runForm.releaseId || item.release_id === runForm.releaseId)
                      .map((item) => (
                        <option key={item._id} value={item._id}>
                          {item.identifier} · {item.version}
                        </option>
                      ))}
                  </select>
                  <select
                    aria-label="Môi trường"
                    className="apple-input"
                    value={runForm.environmentId}
                    onChange={(event) => {
                      const environmentId = event.target.value;
                      const environment = environments.find((item) => item._id === environmentId);
                      setRunForm({
                        ...runForm,
                        environmentId,
                        environment: environment?.name || "",
                      });
                    }}
                  >
                    <option value="">Dùng mặc định của hệ thống</option>
                    {environments.map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.name} · {valueLabel(item.environment_type)}
                      </option>
                    ))}
                  </select>
                </div>
                <select
                  aria-label="Kế hoạch kiểm thử"
                  className="apple-input"
                  value={runForm.testPlanId}
                  onChange={(event) => selectRunPlan(event.target.value)}
                >
                  <option value="">Không gắn kế hoạch</option>
                  {plans
                    .filter((item) => item.status === "APPROVED")
                    .map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.name}
                      </option>
                    ))}
                </select>
                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="run-assignment-strategy">
                    Cách phân công
                  </label>
                  <select
                    id="run-assignment-strategy"
                    className="apple-input"
                    value={runForm.assignmentStrategy}
                    onChange={(event) =>
                      setRunForm({ ...runForm, assignmentStrategy: event.target.value })
                    }
                  >
                    <option value="MANUAL">Tạo lần chạy chưa phân công</option>
                  </select>
                  <p className="text-xs text-ink-muted">
                    Sau khi tạo, người có quyền phân công có thể yêu cầu AI gợi ý người thực hiện
                    dựa trên kỹ năng và số ca đang phụ trách, rồi duyệt gợi ý hoặc tự phân công.
                  </p>
                </div>
                <MultiSelect
                  label="Bộ kiểm thử"
                  options={suites.map((item) => ({ value: item._id, label: item.name }))}
                  searchPlaceholder="Tìm bộ kiểm thử"
                  value={runForm.suiteIds}
                  onChange={(suiteIds) => setRunForm((current) => ({ ...current, suiteIds }))}
                />
                <MultiSelect
                  label="Phiên bản ca kiểm thử"
                  options={tests.map((item) => ({
                    value: item.current_version_id,
                    label: `${item.test_case_key} ${item.current_version?.title || ""}`,
                  }))}
                  searchPlaceholder="Tìm ca kiểm thử"
                  value={runForm.versionIds}
                  onChange={(versionIds) => setRunForm((current) => ({ ...current, versionIds }))}
                />
                <p className="text-[12px] text-ink-muted">
                  Phạm vi lần chạy gồm {runForm.versionIds.length} phiên bản đã chọn và các phiên
                  bản thuộc bộ kiểm thử.
                </p>
                <div className="action-dialog-footer flex justify-end gap-3">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={savingRun}
                    onClick={() => setCreatingRun(false)}
                  >
                    Hủy
                  </button>
                  <button className="apple-button" type="submit" disabled={savingRun}>
                    {savingRun ? "Đang tạo lần chạy…" : "Tạo lần chạy"}
                  </button>
                </div>
              </fieldset>
            </form>
          </Modal>
        )}
      </>
      {workspaceView === "" && can("automation.read") && (
        <JUnitResultPanel
          project={project}
          runs={runs}
          tests={tests}
          can={can}
          onError={setError}
        />
      )}
      {workspaceView === "automation" && (
        <div className="grid gap-5">
          <SegmentedTabs
            label="Khu vực tự động hóa"
            value={automationSubsection}
            onChange={setAutomationSubsection}
            tabs={[
              ...(can("automation.read")
                ? [{ id: "results", label: "Kết quả kiểm thử tự động" }]
                : []),
              ...(canReadAiRuns ? [{ id: "ai", label: "Hoạt động AI" }] : []),
            ]}
          />
          {automationSubsection === "results" && can("automation.read") && (
            <JUnitResultPanel
              project={project}
              runs={runs}
              tests={tests}
              can={can}
              onError={setError}
            />
          )}
          {automationSubsection === "ai" && canReadAiRuns && <AgentRunPanel project={project} />}
        </div>
      )}
      {workspaceView === "" && can("device_matrix.read") && (
        <DeviceMatricesPanel project={project} plans={plans} runs={runs} onChanged={load} />
      )}
      {can("testplan.read") && (workspaceView === "" || workspaceView === "test-plans") && (
        <div className="w-full">
          <Panel title="Danh sách kế hoạch kiểm thử">
            {workspaceView === "test-plans" ? (
              <details className="border-b border-border p-4" open>
                <summary className="cursor-pointer text-sm font-medium">
                  Tìm kiếm, lọc và sắp xếp
                </summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <SearchField
                    ariaLabel="Tìm kế hoạch kiểm thử"
                    onChange={(event) => setPlanFilters({ ...planFilters, q: event.target.value })}
                    placeholder="Tìm tên hoặc mục tiêu"
                    value={planFilters.q}
                  />
                  <input
                    aria-label="Lọc bản phát hành kế hoạch"
                    className="apple-input"
                    placeholder="Bản phát hành"
                    value={planFilters.release}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, release: event.target.value })
                    }
                  />
                  <select
                    aria-label="Lọc trạng thái kế hoạch"
                    className="apple-input"
                    value={planFilters.status}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, status: event.target.value })
                    }
                  >
                    <option value="">Mọi trạng thái</option>
                    {["DRAFT", "IN_REVIEW", "APPROVED", "ARCHIVED"].map((value) => (
                      <option value={value} key={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Sắp xếp kế hoạch"
                    className="apple-input"
                    value={planFilters.sort}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, sort: event.target.value })
                    }
                  >
                    <option value="-updated_at">Mới cập nhật</option>
                    <option value="updated_at">Cũ cập nhật</option>
                    <option value="name">Tên tăng dần</option>
                  </select>
                </div>
              </details>
            ) : (
              <details className="border-b border-border p-4">
                <summary className="cursor-pointer text-sm font-medium">
                  Tìm kiếm, lọc và sắp xếp
                </summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <SearchField
                    ariaLabel="Tìm kế hoạch kiểm thử"
                    onChange={(event) => setPlanFilters({ ...planFilters, q: event.target.value })}
                    placeholder="Tìm tên hoặc mục tiêu"
                    value={planFilters.q}
                  />
                  <input
                    aria-label="Lọc bản phát hành kế hoạch"
                    className="apple-input"
                    placeholder="Bản phát hành"
                    value={planFilters.release}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, release: event.target.value })
                    }
                  />
                  <select
                    aria-label="Lọc trạng thái kế hoạch"
                    className="apple-input"
                    value={planFilters.status}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, status: event.target.value })
                    }
                  >
                    <option value="">Mọi trạng thái</option>
                    {["DRAFT", "IN_REVIEW", "APPROVED", "ARCHIVED"].map((value) => (
                      <option value={value} key={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Sắp xếp kế hoạch"
                    className="apple-input"
                    value={planFilters.sort}
                    onChange={(event) =>
                      setPlanFilters({ ...planFilters, sort: event.target.value })
                    }
                  >
                    <option value="-updated_at">Mới cập nhật</option>
                    <option value="updated_at">Cũ cập nhật</option>
                    <option value="name">Tên tăng dần</option>
                  </select>
                </div>
              </details>
            )}
            {plans.length ? (
              <ul className="divide-y divide-border" aria-label="Kế hoạch kiểm thử">
                {plans.map((item) => {
                  const schedule = [item.schedule?.planned_start_at, item.schedule?.planned_end_at]
                    .filter(Boolean)
                    .map((value) => formatDate(value));
                  const testTypes = Array.isArray(item.test_types)
                    ? item.test_types.map(valueLabel).join(" · ")
                    : "";
                  return (
                    <li className="min-w-0 px-4 py-4 sm:px-5" key={item._id}>
                      <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2">
                        <button
                          className="min-w-0 flex-1 text-left text-[15px] font-semibold leading-6 text-ink hover:text-brand"
                          type="button"
                          onClick={() => setViewingPlan(item)}
                        >
                          <span className="line-clamp-2 break-words [overflow-wrap:anywhere]">
                            {item.name}
                          </span>
                        </button>
                        <StatusPill value={item.status} />
                      </div>
                      {item.objective && (
                        <p className="mt-1 line-clamp-2 max-w-4xl break-words text-[13px] leading-5 text-ink-muted">
                          {item.objective}
                        </p>
                      )}
                      <dl className="mt-3 grid min-w-0 gap-x-6 gap-y-2 text-[12px] sm:grid-cols-2 xl:grid-cols-4">
                        <div className="min-w-0">
                          <dt className="text-ink-faint">Bản phát hành</dt>
                          <dd className="mt-0.5 break-words font-medium text-ink">
                            {item.release || "Chưa chọn"}
                          </dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-faint">Bản dựng</dt>
                          <dd className="mt-0.5 break-all font-medium text-ink">
                            {item.build || "Chưa chọn"}
                          </dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-faint">Thời gian dự kiến</dt>
                          <dd className="mt-0.5 break-words font-medium text-ink">
                            {schedule.length ? schedule.join(" – ") : "Chưa xác định"}
                          </dd>
                        </div>
                        {testTypes && (
                          <div className="min-w-0">
                            <dt className="text-ink-faint">Loại kiểm thử</dt>
                            <dd className="mt-0.5 break-words font-medium text-ink">{testTypes}</dd>
                          </div>
                        )}
                      </dl>
                      {planValidation?.planId === item._id &&
                        planValidation?.revision === item.revision && (
                          <p
                            className={`mt-3 rounded-control px-3 py-2 text-xs ${planValidation.ready_for_approval ? "bg-success-soft text-success" : "bg-warning-soft text-warning"}`}
                            role="status"
                          >
                            {planValidation.ready_for_approval
                              ? "Đã đủ điều kiện phê duyệt"
                              : planValidation.findings
                                  .map(
                                    (finding) =>
                                      testPlanFindingLabels[finding.code] ||
                                      "Cần bổ sung thông tin kế hoạch",
                                  )
                                  .join(" · ")}
                          </p>
                        )}
                      <div
                        className="mt-3 flex flex-wrap items-center justify-between gap-3"
                        aria-label={`Thao tác kế hoạch ${item.name}`}
                      >
                        <span className="text-[12px] text-ink-faint">
                          {item.updated_at ? `Cập nhật ${formatDate(item.updated_at)}` : ""}
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {item.status === "IN_REVIEW" && can("testplan.review") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Yêu cầu chỉnh sửa kế hoạch"
                              title="Yêu cầu chỉnh sửa kế hoạch"
                              onClick={() => transitionPlan(item, "revise")}
                            >
                              <Pencil size={16} aria-hidden="true" />
                            </button>
                          )}
                          {can("testplan.review") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Kiểm tra đầy đủ"
                              title="Kiểm tra đầy đủ"
                              onClick={async () => {
                                try {
                                  setPlanValidation({
                                    ...(await testingApi.validatePlan(item._id)),
                                    planId: item._id,
                                    revision: item.revision,
                                  });
                                } catch (reason) {
                                  setError(messageOf(reason));
                                }
                              }}
                            >
                              <ClipboardCheck size={17} aria-hidden="true" />
                            </button>
                          )}
                          {item.status === "DRAFT" && can("testplan.update") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Sửa kế hoạch"
                              title="Sửa kế hoạch"
                              onClick={() => updatePlan(item)}
                            >
                              <Pencil size={16} aria-hidden="true" />
                            </button>
                          )}
                          {item.status === "DRAFT" && can("testplan.submit_review") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Gửi rà soát"
                              title="Gửi rà soát"
                              onClick={() => transitionPlan(item, "submit")}
                            >
                              <Send size={16} aria-hidden="true" />
                            </button>
                          )}
                          {item.status === "IN_REVIEW" &&
                            item.created_by !== project.current_membership?.user_id &&
                            item.submitted_by !== project.current_membership?.user_id &&
                            can("testplan.approve") && (
                              <button
                                className="apple-button inline-flex size-10 items-center justify-center p-0"
                                type="button"
                                aria-label="Phê duyệt"
                                title="Phê duyệt"
                                onClick={() => transitionPlan(item, "approve")}
                              >
                                <Check size={17} aria-hidden="true" />
                              </button>
                            )}
                          {can("testplan.create") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Nhân bản"
                              title="Nhân bản"
                              onClick={async () => {
                                try {
                                  await testingApi.clonePlan(item._id);
                                  await load();
                                } catch (reason) {
                                  setError(messageOf(reason));
                                }
                              }}
                            >
                              <Copy size={16} aria-hidden="true" />
                            </button>
                          )}
                          {item.status !== "ARCHIVED" && can("testplan.archive") && (
                            <button
                              className="icon-button h-10 w-10"
                              type="button"
                              aria-label="Lưu trữ"
                              title="Lưu trữ"
                              onClick={() => transitionPlan(item, "archive")}
                            >
                              <Archive size={16} aria-hidden="true" />
                            </button>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="px-5 py-5 text-[13px] text-ink-muted" role="status">
                Chưa có kế hoạch kiểm thử
              </p>
            )}
          </Panel>
        </div>
      )}
      {can("testsuite.read") && workspaceView === "" && (
        <Panel title="Danh sách bộ kiểm thử">
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium">
              Tìm kiếm, lọc và sắp xếp
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SearchField
                ariaLabel="Tìm bộ kiểm thử"
                onChange={(event) => setSuiteFilters({ ...suiteFilters, q: event.target.value })}
                placeholder="Tìm tên bộ kiểm thử"
                value={suiteFilters.q}
              />
              <select
                aria-label="Lọc loại bộ kiểm thử"
                className="apple-input"
                value={suiteFilters.suite_type}
                onChange={(event) =>
                  setSuiteFilters({ ...suiteFilters, suite_type: event.target.value })
                }
              >
                <option value="">Mọi loại</option>
                {[
                  "smoke",
                  "regression",
                  "sanity",
                  "feature",
                  "api",
                  "ui",
                  "integration",
                  "custom",
                ].map((value) => (
                  <option value={value} key={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Lọc trạng thái bộ kiểm thử"
                className="apple-input"
                value={suiteFilters.status}
                onChange={(event) =>
                  setSuiteFilters({ ...suiteFilters, status: event.target.value })
                }
              >
                <option value="">Mọi trạng thái</option>
                {["ACTIVE", "ARCHIVED"].map((value) => (
                  <option value={value} key={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sắp xếp bộ kiểm thử"
                className="apple-input"
                value={suiteFilters.sort}
                onChange={(event) => setSuiteFilters({ ...suiteFilters, sort: event.target.value })}
              >
                <option value="-updated_at">Mới cập nhật</option>
                <option value="updated_at">Cũ cập nhật</option>
                <option value="name">Tên tăng dần</option>
              </select>
            </div>
          </details>
          {suites.length ? (
            <ul aria-label="Danh sách bộ kiểm thử" className="divide-y divide-border">
              {suites.map((item) => (
                <li
                  className="flex min-w-0 flex-wrap items-start justify-between gap-4 px-4 py-4 sm:px-5"
                  key={item._id}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                      <h3 className="break-words text-[15px] font-semibold leading-6 text-ink">
                        {item.name}
                      </h3>
                      <StatusPill value={item.status} />
                    </div>
                    <dl className="mt-2 flex min-w-0 flex-wrap gap-x-6 gap-y-1 text-[12px]">
                      <div>
                        <dt className="sr-only">Loại</dt>
                        <dd className="text-ink-muted">{valueLabel(item.suite_type)}</dd>
                      </div>
                      <div>
                        <dt className="sr-only">Số ca kiểm thử</dt>
                        <dd className="text-ink-muted">
                          {item.test_case_version_ids?.length || 0} ca kiểm thử
                        </dd>
                      </div>
                      {item.updated_at && (
                        <div>
                          <dt className="sr-only">Cập nhật</dt>
                          <dd className="text-ink-faint">Cập nhật {formatDate(item.updated_at)}</dd>
                        </div>
                      )}
                    </dl>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    {can("testsuite.update") && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Sửa bộ kiểm thử ${item.name}`}
                        title="Sửa bộ kiểm thử"
                        onClick={() => updateSuite(item)}
                      >
                        <Pencil aria-hidden="true" size={16} />
                      </button>
                    )}
                    {can("testsuite.clone") && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Nhân bản bộ kiểm thử ${item.name}`}
                        title="Nhân bản bộ kiểm thử"
                        onClick={async () => {
                          try {
                            await testingApi.cloneSuite(item._id);
                            await load();
                          } catch (reason) {
                            setError(messageOf(reason));
                          }
                        }}
                      >
                        <Copy aria-hidden="true" size={16} />
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("testsuite.archive") && (
                      <button
                        className="icon-button h-9 w-9"
                        type="button"
                        aria-label={`Lưu trữ bộ kiểm thử ${item.name}`}
                        title="Lưu trữ bộ kiểm thử"
                        onClick={() => archiveSuite(item)}
                      >
                        <Archive aria-hidden="true" size={16} />
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-5 py-5 text-[13px] text-ink-muted" role="status">
              Chưa có bộ kiểm thử
            </p>
          )}
        </Panel>
      )}
      {can("testrun.read") &&
        (workspaceView === "" || (workspaceView === "test-runs" && runSubsection === "runs")) && (
          <div>
            <Panel title="Danh sách lần chạy">
              <details className="border-b border-border p-4" open={workspaceView === "test-runs"}>
                <summary className="cursor-pointer text-sm font-medium">
                  Tìm kiếm, lọc và sắp xếp
                </summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <SearchField
                    ariaLabel="Tìm lần chạy"
                    onChange={(event) => setRunNameSearch(event.target.value)}
                    placeholder="Tên lần chạy"
                    value={runNameSearch}
                  />
                  <select
                    aria-label="Lọc trạng thái lần chạy"
                    className="apple-input"
                    value={runFilters.status}
                    onChange={(event) => {
                      setRunFilters({ ...runFilters, status: event.target.value });
                      setRunPage(1);
                    }}
                  >
                    <option value="">Mọi trạng thái</option>
                    {["DRAFT", "READY", "IN_PROGRESS", "COMPLETED", "ABORTED"].map((value) => (
                      <option key={value} value={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Lọc môi trường lần chạy"
                    className="apple-input"
                    placeholder="Môi trường"
                    value={runEnvironmentSearch}
                    onChange={(event) => setRunEnvironmentSearch(event.target.value)}
                  />
                  <select
                    aria-label="Sắp xếp lần chạy"
                    className="apple-input"
                    value={runFilters.sort}
                    onChange={(event) => {
                      setRunFilters({ ...runFilters, sort: event.target.value });
                      setRunPage(1);
                    }}
                  >
                    <option value="-updated_at">Mới cập nhật</option>
                    <option value="updated_at">Cũ cập nhật</option>
                    <option value="name">Tên tăng dần</option>
                  </select>
                </div>
              </details>
              {runs.length > 0 ? (
                <ul className="divide-y divide-border" aria-label="Lần chạy kiểm thử">
                  {runs.map((item) => {
                    const name = item.name || "Lần chạy chưa có tên";
                    const caseCount = Array.isArray(item.test_case_version_ids)
                      ? item.test_case_version_ids.length
                      : null;
                    return (
                      <li className="min-w-0 px-4 py-4 sm:px-5" key={item._id}>
                        <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                          <button
                            className="min-w-0 flex-1 text-left text-[15px] font-semibold leading-6 text-ink hover:text-brand"
                            type="button"
                            onClick={() =>
                              router.push(
                                projectRoute(project._id, PROJECT_SECTION_SLUGS.testRuns, item._id),
                              )
                            }
                          >
                            <span className="line-clamp-2 break-words [overflow-wrap:anywhere]">
                              {name}
                            </span>
                          </button>
                          <StatusPill value={item.status} />
                        </div>
                        <dl className="mt-3 grid min-w-0 gap-x-6 gap-y-2 text-[12px] sm:grid-cols-2 xl:grid-cols-4">
                          <div className="min-w-0">
                            <dt className="text-ink-faint">Môi trường</dt>
                            <dd className="mt-0.5 break-words font-medium text-ink">
                              {item.environment || "Chưa xác định"}
                            </dd>
                          </div>
                          <div className="min-w-0">
                            <dt className="text-ink-faint">Bản dựng</dt>
                            <dd className="mt-0.5 break-all font-medium text-ink">
                              {item.build || "Chưa có bản dựng"}
                            </dd>
                          </div>
                          <div className="min-w-0">
                            <dt className="text-ink-faint">Ca kiểm thử</dt>
                            <dd className="mt-0.5 font-medium text-ink">
                              {caseCount === null ? "Chưa có dữ liệu" : caseCount}
                            </dd>
                          </div>
                          {item.updated_at && (
                            <div className="min-w-0">
                              <dt className="text-ink-faint">Cập nhật lúc</dt>
                              <dd className="mt-0.5 font-medium text-ink">
                                {formatDate(item.updated_at)}
                              </dd>
                            </div>
                          )}
                        </dl>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="px-5 py-5 text-[13px] text-ink-muted" role="status">
                  Chưa có lần chạy
                </p>
              )}
              <Pagination value={runPageInfo} onChange={setRunPage} />
            </Panel>
          </div>
        )}
      {(workspaceView === "" || workspaceView === "test-runs") &&
        project.current_permissions?.includes("environmentincident.read") &&
        (workspaceView === "" || runSubsection === "incidents") && (
          <EnvironmentIncidentPanel project={project} />
        )}
      {(workspaceView === "" || workspaceView === "test-runs") &&
        project.current_permissions?.includes("nfrtest.read") &&
        (workspaceView === "" || runSubsection === "nonfunctional") && (
          <NonFunctionalTestPanel project={project} />
        )}
      {dialog}
    </WorkspacePage>
  );
}
