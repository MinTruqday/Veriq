"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import DeviceMatricesPanel from "../../components/DeviceMatricesPanel";
import AutomationExecutionPanel from "../../components/AutomationExecutionPanel";
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
import { docText, messageOf, textDoc, valueLabel } from "../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import RunExecutionWorkspace from "./execution/RunExecutionWorkspace";
import JUnitResultPanel from "../../components/JUnitResultPanel";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import MultiSelect from "@/shared/components/ui/MultiSelect";

export default function ExecutionPage({ project, section, workspaceView }) {
  const { ask, dialog } = useActionDialog();
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
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const [planValidation, setPlanValidation] = useState(null);
  const [creatingPlan, setCreatingPlan] = useState(false);
  const [creatingSuite, setCreatingSuite] = useState(false);
  const [creatingRun, setCreatingRun] = useState(false);
  const [runSubsection, setRunSubsection] = useState("runs");
  const [automationSubsection, setAutomationSubsection] = useState("results");
  const [runForm, setRunForm] = useState({
    name: "",
    release: "",
    build: "",
    environment: "staging",
    environmentId: "",
    releaseId: "",
    buildId: "",
    testPlanId: "",
    suiteIds: [],
    versionIds: [],
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
  const terminalResultStatuses = project.settings?.allow_not_applicable_results
    ? ["PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE"]
    : ["PASS", "FAIL", "BLOCKED", "SKIPPED"];
  const load = useCallback(async () => {
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
    }
    if (!initialDataLoaded.current) {
      setInitialLoading(true);
      setInitialLoadFailed(false);
    }
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
      ]);
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
      if (runId && permissions.includes("testrun.read")) setRun(await testingApi.getRun(runId));
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
      setError(messageOf(reason));
    } finally {
      setInitialLoading(false);
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
  const versions = tests.map((item) => item.current_version_id).filter(Boolean);
  const createRun = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createRun({
        project_id: project._id,
        name: runForm.name,
        test_plan_id: runForm.testPlanId || null,
        test_suite_ids: runForm.suiteIds,
        test_case_version_ids: runForm.versionIds,
        environment: runForm.environment,
        environment_id: runForm.environmentId || null,
        release: runForm.release,
        release_id: runForm.releaseId || null,
        build: runForm.build,
        build_id: runForm.buildId || null,
      });
      setRunForm({
        name: "",
        release: "",
        build: "",
        environment: "staging",
        environmentId: "",
        releaseId: "",
        buildId: "",
        testPlanId: "",
        suiteIds: [],
        versionIds: [],
      });
      setCreatingRun(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (execution, status, version) => {
    try {
      let resultNote = "Kết quả thực thi thủ công";
      if (status === "NOT_APPLICABLE") {
        const answer = await ask({
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
        });
        if (!answer) return;
        resultNote = answer.reason.trim();
      }
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
        setError("Mỗi bước Không áp dụng phải có lý do riêng");
        return;
      }
      await testingApi.updateExecution(project._id, execution._id, {
        status,
        step_results: status === "IN_PROGRESS" ? execution.step_results || [] : values,
        actual_result_doc: textDoc(actuals[execution._id] || docText(execution.actual_result_doc)),
        attachments: attachments[execution._id] || execution.attachments || [],
        note: resultNote,
        idempotency_key: crypto.randomUUID(),
        expected_revision: execution.revision,
      });
      setResumeContext(null);
      setRun(await testingApi.getRun(run._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createDefectFromResult = async (result, version) => {
    try {
      await testingApi.createDefect(project._id, {
        project_id: project._id,
        title: `Lỗi khi thực thi ${version.test_case_key} ${version.title}`,
        description_doc: textDoc(`Phát hiện trong lần chạy ${run.name}`),
        steps_to_reproduce: version.steps || [],
        actual_result_doc: result.actual_result_doc || textDoc(""),
        expected_result_doc: version.expected_result_doc || textDoc(""),
        severity: "major",
        priority: version.priority || "medium",
        environment: run.environment || "",
        build: run.build || "",
        attachments: result.attachments || [],
        linked_test_result_id: result._id,
        linked_test_case_version_id: version._id,
        linked_requirement_version_ids: version.requirement_version_ids || [],
      });
      setRun(await testingApi.getRun(run._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const updatePlan = async (item) => {
    const answer = await ask({
      title: "Sửa kế hoạch kiểm thử",
      description: item.name,
      confirmLabel: "Lưu kế hoạch",
      fields: [
        { name: "name", label: "Tên", initialValue: item.name, required: true, autoFocus: true },
        {
          name: "objective",
          label: "Mục tiêu",
          initialValue: item.objective || "",
          multiline: true,
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.updatePlan(item._id, {
        expected_revision: item.revision,
        name: answer.name,
        objective: answer.objective,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transitionPlan = async (item, action) => {
    const answer = await ask({
      title:
        action === "approve"
          ? "Phê duyệt kế hoạch"
          : action === "archive"
            ? "Lưu trữ kế hoạch"
            : "Gửi rà soát kế hoạch",
      description: item.name,
      confirmLabel:
        action === "approve" ? "Phê duyệt" : action === "archive" ? "Lưu trữ" : "Gửi rà soát",
      danger: action === "archive",
      fields: [
        { name: "note", label: "Ghi chú", required: true, multiline: true, autoFocus: true },
      ],
    });
    if (!answer) return;
    try {
      const payload =
        action === "archive"
          ? { expected_revision: item.revision, reason: answer.note }
          : { expected_revision: item.revision, review_note: answer.note };
      if (action === "approve") await testingApi.approvePlan(item._id, payload);
      else if (action === "archive") await testingApi.archivePlan(item._id, payload);
      else await testingApi.submitPlan(item._id, payload);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const updateSuite = async (item) => {
    const answer = await ask({
      title: "Sửa bộ kiểm thử",
      description: item.name,
      confirmLabel: "Lưu bộ kiểm thử",
      fields: [
        { name: "name", label: "Tên", initialValue: item.name, required: true, autoFocus: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.updateSuite(item._id, {
        expected_revision: item.revision,
        name: answer.name,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const archiveSuite = async (item) => {
    const answer = await ask({
      title: "Lưu trữ bộ kiểm thử",
      description: item.name,
      confirmLabel: "Lưu trữ",
      danger: true,
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.archiveSuite(item._id, {
        expected_revision: item.revision,
        reason: answer.reason,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
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
        error={error}
        can={can}
        resumeContext={resumeContext}
        onResumeChange={setResumeContext}
        ask={ask}
        onRunChange={setRun}
        onError={setError}
        onTransition={transition}
        onCreateDefect={createDefectFromResult}
        stepResults={stepResults}
        onStepResultsChange={setStepResults}
        terminalResultStatuses={terminalResultStatuses}
        actuals={actuals}
        onActualsChange={setActuals}
        attachments={attachments}
        onAttachmentsChange={setAttachments}
        dialog={dialog}
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
          {(workspaceView === "" || workspaceView === "test-runs") && can("testrun.create") && (
            <button className="apple-button" type="button" onClick={() => setCreatingRun(true)}>
              Tạo lần chạy
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
      <>
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
              strategies={strategies}
              requirements={requirements}
              suites={suites}
              tests={tests}
              onCancel={() => setCreatingPlan(false)}
              onSave={async (payload) => {
                await testingApi.createPlan(payload);
                setCreatingPlan(false);
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
            onClose={() => setCreatingRun(false)}
            ariaLabel="Tạo lần chạy"
            className="max-w-3xl max-h-[90dvh] overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>Tạo lần chạy</ModalTitle>
            </ModalHeader>
            <form className="space-y-3 p-5" onSubmit={createRun}>
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
                      environment: environment?.name || "staging",
                    });
                  }}
                >
                  <option value="">Mặc định staging</option>
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
                onChange={(event) => setRunForm({ ...runForm, testPlanId: event.target.value })}
              >
                <option value="">Không gắn kế hoạch</option>
                {plans.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.name}
                  </option>
                ))}
              </select>
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
                Ảnh chụp {runForm.versionIds.length} phiên bản được chọn cùng các phiên bản trong bộ
                kiểm thử
              </p>
              <div className="action-dialog-footer flex justify-end gap-3">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setCreatingRun(false)}
                >
                  Hủy
                </button>
                <button className="apple-button" type="submit">
                  Tạo lần chạy
                </button>
              </div>
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
              ...(can("automation.read") || can("device_matrix.read")
                ? [{ id: "integrations", label: "Kịch bản và thiết bị" }]
                : []),
              { id: "ai", label: "AI tự động hóa" },
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
          {automationSubsection === "integrations" && (
            <div className="grid gap-5 xl:grid-cols-2">
              {can("device_matrix.read") && (
                <DeviceMatricesPanel project={project} plans={plans} runs={runs} onChanged={load} />
              )}
              {can("automation.read") && <AutomationExecutionPanel project={project} />}
            </div>
          )}
          {automationSubsection === "ai" && <AgentRunPanel project={project} />}
        </div>
      )}
      {workspaceView === "" && (can("device_matrix.read") || can("automation.read")) && (
        <div className="grid gap-5 xl:grid-cols-2">
          {can("device_matrix.read") && (
            <DeviceMatricesPanel project={project} plans={plans} runs={runs} onChanged={load} />
          )}
          {can("automation.read") && <AutomationExecutionPanel project={project} />}
        </div>
      )}
      {can("testplan.read") && (workspaceView === "" || workspaceView === "test-plans") && (
        <Panel title="Danh sách kế hoạch kiểm thử">
          {planValidation && (
            <div className="border-b border-border p-4 text-sm">
              {planValidation.ready_for_approval
                ? "Kế hoạch đã đủ điều kiện phê duyệt"
                : planValidation.findings.map((item) => item.code).join(" · ")}
            </div>
          )}
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium">
              Tìm kiếm bộ lọc và sắp xếp
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <input
                aria-label="Tìm kế hoạch kiểm thử"
                className="apple-input"
                placeholder="Tìm tên hoặc mục tiêu"
                value={planFilters.q}
                onChange={(event) => setPlanFilters({ ...planFilters, q: event.target.value })}
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
                onChange={(event) => setPlanFilters({ ...planFilters, status: event.target.value })}
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
                onChange={(event) => setPlanFilters({ ...planFilters, sort: event.target.value })}
              >
                <option value="-updated_at">Mới cập nhật</option>
                <option value="updated_at">Cũ cập nhật</option>
                <option value="name">Tên tăng dần</option>
              </select>
            </div>
          </details>
          <DataTable
            items={plans}
            empty="Chưa có kế hoạch kiểm thử"
            columns={[
              { key: "name", label: "Tên" },
              { key: "release", label: "Bản phát hành" },
              { key: "build", label: "Bản dựng" },
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
                    {can("testplan.review") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async () => {
                          try {
                            setPlanValidation(await testingApi.validatePlan(item._id));
                          } catch (reason) {
                            setError(messageOf(reason));
                          }
                        }}
                      >
                        Kiểm tra đầy đủ
                      </button>
                    )}
                    {item.status === "DRAFT" && can("testplan.update") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => updatePlan(item)}
                      >
                        Sửa
                      </button>
                    )}
                    {item.status === "DRAFT" && can("testplan.submit_review") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => transitionPlan(item, "submit")}
                      >
                        Gửi rà soát
                      </button>
                    )}
                    {["DRAFT", "IN_REVIEW"].includes(item.status) && can("testplan.approve") && (
                      <button
                        className="apple-button"
                        type="button"
                        onClick={() => transitionPlan(item, "approve")}
                      >
                        Phê duyệt
                      </button>
                    )}
                    {can("testplan.create") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async () => {
                          try {
                            await testingApi.clonePlan(item._id);
                            await load();
                          } catch (reason) {
                            setError(messageOf(reason));
                          }
                        }}
                      >
                        Nhân bản
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("testplan.archive") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => transitionPlan(item, "archive")}
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
      {can("testsuite.read") && workspaceView === "" && (
        <Panel title="Danh sách bộ kiểm thử">
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium">
              Tìm kiếm bộ lọc và sắp xếp
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <input
                aria-label="Tìm bộ kiểm thử"
                className="apple-input"
                placeholder="Tìm tên bộ kiểm thử"
                value={suiteFilters.q}
                onChange={(event) => setSuiteFilters({ ...suiteFilters, q: event.target.value })}
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
          <DataTable
            items={suites}
            empty="Chưa có bộ kiểm thử"
            columns={[
              { key: "name", label: "Tên" },
              { key: "suite_type", label: "Loại", render: (item) => valueLabel(item.suite_type) },
              {
                key: "count",
                label: "Số ca",
                render: (item) => item.test_case_version_ids?.length || 0,
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
                        onClick={() => updateSuite(item)}
                      >
                        Sửa
                      </button>
                    )}
                    {can("testsuite.clone") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async () => {
                          try {
                            await testingApi.cloneSuite(item._id);
                            await load();
                          } catch (reason) {
                            setError(messageOf(reason));
                          }
                        }}
                      >
                        Nhân bản
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("testsuite.archive") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => archiveSuite(item)}
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
      {can("testrun.read") && (workspaceView === "" || workspaceView === "test-runs") && (
        <div hidden={workspaceView === "test-runs" && runSubsection !== "runs"}>
          <Panel title="Danh sách lần chạy">
            <details className="border-b border-border p-4">
              <summary className="cursor-pointer text-sm font-medium">
                Tìm kiếm bộ lọc và sắp xếp
              </summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <input
                  aria-label="Tìm lần chạy"
                  className="apple-input"
                  placeholder="Tên lần chạy"
                  value={runFilters.name}
                  onChange={(event) => {
                    setRunFilters({ ...runFilters, name: event.target.value });
                    setRunPage(1);
                  }}
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
                  value={runFilters.environment}
                  onChange={(event) => {
                    setRunFilters({ ...runFilters, environment: event.target.value });
                    setRunPage(1);
                  }}
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
            <DataTable
              onSelect={(item) =>
                window.location.assign(`/du-an/${project._id}/thuc-thi/${item._id}`)
              }
              items={runs}
              empty="Chưa có lần chạy"
              columns={[
                { key: "name", label: "Tên" },
                { key: "environment", label: "Môi trường" },
                { key: "build", label: "Bản dựng" },
                {
                  key: "count",
                  label: "Số ca kiểm thử",
                  render: (item) => item.test_case_version_ids.length,
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
              ]}
            />
            <Pagination value={runPageInfo} onChange={setRunPage} />
          </Panel>
        </div>
      )}
      {(workspaceView === "" || workspaceView === "test-runs") &&
        project.current_permissions?.includes("environmentincident.read") && (
          <div hidden={workspaceView === "test-runs" && runSubsection !== "incidents"}>
            <EnvironmentIncidentPanel project={project} />
          </div>
        )}
      {(workspaceView === "" || workspaceView === "test-runs") &&
        project.current_permissions?.includes("nfrtest.read") && (
          <div hidden={workspaceView === "test-runs" && runSubsection !== "nonfunctional"}>
            <NonFunctionalTestPanel project={project} />
          </div>
        )}
      {dialog}
    </WorkspacePage>
  );
}
