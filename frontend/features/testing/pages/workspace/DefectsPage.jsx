"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Eye, Pencil } from "lucide-react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../components/DataTable";
import FilePicker from "../../components/FilePicker";
import CausalAnalysisPanel from "../../components/CausalAnalysisPanel";
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
import { docText, formatDate, messageOf, textDoc, valueLabel } from "../../lib/testing";
import { shouldReloadAfterAmbiguousMutation } from "../../lib/executionRecovery.logic.mjs";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { eligibleRetestResults } from "./defectRetest.logic.mjs";
import { defectActionAccess } from "./defectAccess.logic.mjs";
import SearchField from "@/shared/components/ui/SearchField";

const nextStates = {
  NEW: ["CONFIRMED", "REJECTED", "DUPLICATE"],
  CONFIRMED: ["IN_PROGRESS", "REJECTED", "DUPLICATE"],
  IN_PROGRESS: ["RESOLVED"],
  RESOLVED: ["READY_FOR_RETEST", "REOPENED"],
  READY_FOR_RETEST: [],
  REOPENED: ["IN_PROGRESS", "RESOLVED"],
  CLOSED: ["REOPENED"],
  REJECTED: ["REOPENED"],
  DUPLICATE: ["REOPENED"],
};

const traceReasonLabels = {
  CURRENT_LINK: "Đang được liên kết với lỗi",
  SHARED_REQUIREMENT_TRACE: "Có chung yêu cầu được truy vết",
  SIMILAR_BEHAVIOR_TEXT: "Nội dung hành vi tương đồng",
  CURRENT_REQUIREMENT_LINK: "Yêu cầu đang được liên kết với lỗi",
  LINKED_TEST_CASE_TRACE: "Liên quan qua ca kiểm thử đã liên kết",
  SIMILAR_REQUIREMENT_TEXT: "Nội dung yêu cầu tương đồng",
};

function memberDisplayName(member) {
  return (
    member?.identity?.label ||
    member?.user_label ||
    member?.full_name ||
    member?.user?.full_name ||
    member?.user?.email ||
    member?.email ||
    "Thành viên dự án"
  );
}

function displayEnvironment(value) {
  const [environment, ...details] = String(value || "").split(" · ");
  return [valueLabel(environment), ...details].filter(Boolean).join(" · ");
}

export default function DefectsPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [releases, setReleases] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [page, setPage] = useState(1);
  const [pageInfo, setPageInfo] = useState(null);
  const [searchText, setSearchText] = useState("");
  const [filters, setFilters] = useState({
    q: "",
    status: "",
    severity: "",
    priority: "",
    assignee: "",
    sort: "-updated_at",
  });
  const [results, setResults] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [traceSuggestions, setTraceSuggestions] = useState({});
  const [traceReview, setTraceReview] = useState(null);
  const [traceGeneratingId, setTraceGeneratingId] = useState("");
  const traceGenerationInFlight = useRef(false);
  const traceRequestKeys = useRef(new Map());
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const currentProjectId = useRef(project._id);
  currentProjectId.current = project._id;
  const loadGeneration = useRef(0);
  const [creating, setCreating] = useState(false);
  const [savingDefect, setSavingDefect] = useState(false);
  const savingDefectRef = useRef(false);
  const defectCreateOperation = useRef(null);
  const [form, setForm] = useState({
    title: "",
    severity: "major",
    priority: "medium",
    environment: "",
    environmentId: "",
    releaseId: "",
    release: "",
    build: "",
    buildId: "",
    description: "",
    steps: "",
    actual: "",
    expected: "",
    attachments: [],
  });
  const can = (permission) => project.current_permissions?.includes(permission);
  const memberRoles = [project.current_membership?.project_role].filter(Boolean);
  const canManageTrace = (item) => defectActionAccess(project, item).canManageTrace;
  const transitionAllowed = (item, status) => {
    if (["CONFIRMED", "REJECTED", "DUPLICATE"].includes(status)) {
      if (!defectActionAccess(project, item).canTriage) return false;
      if (status === "REJECTED") {
        const configured = project.settings?.action_policies?.["defect.rejected"];
        return Array.isArray(configured)
          ? configured.some((role) => memberRoles.includes(role))
          : memberRoles.includes("QA");
      }
      if (status === "DUPLICATE") {
        const configured = project.settings?.action_policies?.["defect.duplicate"];
        return Array.isArray(configured)
          ? configured.some((role) => memberRoles.includes(role))
          : memberRoles.includes("QA");
      }
      return true;
    }
    if (["IN_PROGRESS", "RESOLVED"].includes(status)) {
      return defectActionAccess(project, item).canRepair;
    }
    if (status === "READY_FOR_RETEST") {
      return defectActionAccess(project, item).canRepair;
    }
    if (status === "REOPENED") return defectActionAccess(project, item).canTriage;
    return false;
  };
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setItems([]);
      setResults([]);
      setReleases([]);
      setBuilds([]);
      setEnvironments([]);
      setMembers([]);
      setTraceSuggestions({});
      setTraceReview(null);
      traceRequestKeys.current.clear();
      setPageInfo(null);
    }
    if (!initialDataLoaded.current) {
      setInitialLoading(true);
      setInitialLoadFailed(false);
    }
    setError("");
    try {
      const projectPermissions = new Set(project.current_permissions || []);
      const [
        defectValues,
        resultValues,
        releaseValues,
        buildValues,
        environmentValues,
        memberValues,
      ] = await Promise.all([
        testingApi.listDefectPage(project._id, { ...filters, page, page_size: 50 }),
        projectPermissions.has("testrun.read")
          ? testingApi.listResults(project._id, "PASS,FAIL")
          : Promise.resolve([]),
        projectPermissions.has("release.read")
          ? testingApi.listReleases(project._id)
          : Promise.resolve([]),
        projectPermissions.has("build.read") && projectPermissions.has("release.read")
          ? testingApi.listBuilds(project._id)
          : Promise.resolve([]),
        projectPermissions.has("environment.read")
          ? testingApi.listEnvironments(project._id)
          : Promise.resolve([]),
        project.current_permissions?.includes("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      const traceSuggestionValues = projectPermissions.has("ai.suggest_bug_trace")
        ? await testingApi.listAutomatedDefectTraceSuggestions(
            project._id,
            defectValues.items.map((item) => item._id),
          )
        : [];
      if (requestGeneration !== loadGeneration.current) return;
      const visibleResultIds = new Set(resultValues.map((item) => item._id));
      const originalResultIds = projectPermissions.has("testrun.read")
        ? [
            ...new Set(
              defectValues.items
                .map((item) => item.linked_test_result_id)
                .filter((resultId) => resultId && !visibleResultIds.has(resultId)),
            ),
          ]
        : [];
      const originalResults = await Promise.all(
        originalResultIds.map((resultId) => testingApi.getTestResult(resultId).catch(() => null)),
      );
      if (requestGeneration !== loadGeneration.current) return;
      setItems(defectValues.items);
      setTraceSuggestions(
        Object.fromEntries(traceSuggestionValues.map((item) => [item.subject_id, item])),
      );
      setPageInfo(defectValues);
      setResults([
        ...resultValues,
        ...originalResults.filter((result) => result && !visibleResultIds.has(result._id)),
      ]);
      setReleases(releaseValues);
      setBuilds(buildValues);
      setEnvironments(environmentValues);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      if (requestGeneration !== loadGeneration.current) return;
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
      setError(messageOf(reason));
    } finally {
      if (requestGeneration === loadGeneration.current) setInitialLoading(false);
    }
  }, [filters, initialDataLoaded, loadedProjectId, page, project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => (current.q === searchText ? current : { ...current, q: searchText }));
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchText]);
  const create = async (event) => {
    event.preventDefault();
    if (savingDefectRef.current) return;
    savingDefectRef.current = true;
    setSavingDefect(true);
    setError("");
    setSuccess("");
    const payload = {
      project_id: project._id,
      title: form.title,
      description_doc: textDoc(form.description),
      steps_to_reproduce: form.steps
        .split("\n")
        .map((step) => step.trim())
        .filter(Boolean)
        .map((action) => ({ action_doc: textDoc(action), expected_doc: textDoc("") })),
      actual_result_doc: textDoc(form.actual),
      expected_result_doc: textDoc(form.expected),
      severity: form.severity,
      priority: form.priority,
      environment: form.environment,
      environment_id: can("environment.read") ? form.environmentId || null : null,
      release: form.release,
      release_id: can("release.read") ? form.releaseId || null : null,
      build: form.build,
      build_id: can("build.read") && can("release.read") ? form.buildId || null : null,
      attachments: form.attachments,
      linked_requirement_version_ids: [],
    };
    const requestFingerprint = JSON.stringify(payload);
    if (defectCreateOperation.current?.requestFingerprint !== requestFingerprint) {
      defectCreateOperation.current = {
        requestFingerprint,
        idempotencyKey: crypto.randomUUID(),
      };
    }
    try {
      await testingApi.createDefect(project._id, {
        ...payload,
        idempotency_key: defectCreateOperation.current.idempotencyKey,
      });
      defectCreateOperation.current = null;
      setSuccess("Đã tạo lỗi. Danh sách đang được làm mới.");
      setForm({
        title: "",
        severity: "major",
        priority: "medium",
        environment: "",
        environmentId: "",
        release: "",
        releaseId: "",
        build: "",
        buildId: "",
        description: "",
        steps: "",
        actual: "",
        expected: "",
        attachments: [],
      });
      setCreating(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      savingDefectRef.current = false;
      setSavingDefect(false);
    }
  };
  const transition = async (item, to_status) => {
    await ask({
      title: "Chuyển trạng thái lỗi",
      description: `${item.defect_key} từ ${valueLabel(item.status)} sang ${valueLabel(to_status)}`,
      confirmLabel: "Chuyển trạng thái",
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
          await testingApi.transitionDefect(item._id, {
            expected_revision: item.revision,
            to_status,
            reason: answer.reason,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const assignDefect = async (item) => {
    if (!defectActionAccess(project, item).canAssign) return;
    await ask({
      title: "Gán người xử lý lỗi",
      description: item.defect_key,
      confirmLabel: "Lưu người xử lý",
      fields: [
        {
          name: "assignee",
          label: "Người xử lý",
          initialValue: item.assignee || "",
          autoFocus: true,
          options: [
            { value: "", label: "Chưa gán" },
            ...members.map((member) => ({
              value: member.user_id,
              label: memberDisplayName(member),
            })),
          ],
        },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.updateDefect(item._id, {
            expected_revision: item.revision,
            assignee: answer.assignee.trim() || null,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const editTechnicalDetails = async (item) => {
    if (!defectActionAccess(project, item).canEditTechnical) return;
    const fields = [
      { name: "root_cause_detail", label: "Phân tích nguyên nhân", multiline: true },
      { name: "injected_phase", label: "Giai đoạn phát sinh lỗi" },
      { name: "escape_reason", label: "Nguyên nhân chưa phát hiện sớm", multiline: true },
    ];
    await ask({
      title: "Cập nhật phân tích lỗi",
      description: `${item.defect_key} · Mức độ: ${valueLabel(item.severity)} · Ưu tiên: ${valueLabel(item.priority)}`,
      confirmLabel: "Lưu phân tích",
      fields: fields.map((field) => ({ ...field, initialValue: item[field.name] || "" })),
      onConfirm: async (answer) => {
        const changes = Object.fromEntries(
          fields
            .filter((field) => answer[field.name] !== (item[field.name] || ""))
            .map((field) => [field.name, answer[field.name]]),
        );
        if (!Object.keys(changes).length) return;
        await testingApi.updateDefect(item._id, { expected_revision: item.revision, ...changes });
        await load();
      },
    });
  };
  const suggestTrace = async (item) => {
    if (!can("ai.suggest_bug_trace") || traceGenerationInFlight.current) return;
    traceGenerationInFlight.current = true;
    setTraceGeneratingId(item._id);
    const requestProjectId = project._id;
    const requestKey = `${project._id}:${item._id}:${item.revision}`;
    if (!traceRequestKeys.current.has(requestKey)) {
      traceRequestKeys.current.set(requestKey, crypto.randomUUID());
    }
    try {
      const result = await testingApi.suggestDefectTrace(project._id, item._id, {
        expected_revision: item.revision,
        idempotency_key: traceRequestKeys.current.get(requestKey),
      });
      if (requestProjectId !== currentProjectId.current) return;
      setTraceSuggestions((values) => ({ ...values, [item._id]: result }));
      setTraceReview({ defect: item, result });
    } catch (reason) {
      if (requestProjectId !== currentProjectId.current) return;
      setError(messageOf(reason));
    } finally {
      traceGenerationInFlight.current = false;
      setTraceGeneratingId("");
    }
  };
  const confirmTraceCandidate = async (candidate) => {
    const currentReview = traceReview;
    if (!currentReview) return;
    setTraceReview(null);
    const answer = await ask({
      title: "Xác nhận liên kết truy vết",
      description: `${currentReview.defect.defect_key} với ${candidate.requirement_key || candidate.test_case_key}`,
      confirmLabel: "Xác nhận liên kết",
      fields: [
        {
          name: "reason",
          label: "Lý do xác nhận",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        const payload = {
          expected_revision: currentReview.defect.revision,
          reason: answer.reason,
          ai_result_id: currentReview.result._id,
          accepted_candidate_ids: [candidate.candidate_id],
        };
        if (candidate.artifact_type === "requirement_version") {
          payload.linked_requirement_version_ids = [
            ...new Set([
              ...(currentReview.defect.linked_requirement_version_ids || []),
              candidate.artifact_id,
            ]),
          ];
        } else {
          payload.linked_test_case_version_id = candidate.artifact_id;
        }
        try {
          await testingApi.updateDefectTrace(project._id, currentReview.defect._id, payload);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
    if (!answer) setTraceReview(currentReview);
  };
  const renderTransition = (item) => {
    if (item.status === "READY_FOR_RETEST") {
      if (!defectActionAccess(project, item).canRetest) return null;
      const eligibleResults = eligibleRetestResults(item, results);
      if (!eligibleResults.length) return null;
      return (
        <select
          aria-label={`Kết quả retest ${item.defect_key}`}
          className="apple-input w-full min-w-0"
          value=""
          onChange={async (event) => {
            if (!event.target.value) return;
            try {
              await testingApi.retestDefect(project._id, item._id, {
                test_result_id: event.target.value,
                expected_revision: item.revision,
                note: "",
                idempotency_key: crypto.randomUUID(),
              });
              await load();
            } catch (reason) {
              if (shouldReloadAfterAmbiguousMutation(reason)) await load();
              setError(messageOf(reason));
            }
          }}
        >
          <option value="">Chọn kết quả kiểm thử lại</option>
          {eligibleResults.map((result) => (
            <option key={result._id} value={result._id}>
              {valueLabel(result.status)} ·{" "}
              {result.test_case_key || result.test_case_name || result.build || "Kết quả kiểm thử"}
            </option>
          ))}
        </select>
      );
    }
    const allowedTransitions = (nextStates[item.status] || []).filter((value) =>
      transitionAllowed(item, value),
    );
    if (!allowedTransitions.length) return null;
    return (
      <select
        aria-label={`Chuyển trạng thái ${item.defect_key}`}
        className="apple-input w-full min-w-0"
        title="Chuyển trạng thái"
        value=""
        onChange={(event) => transition(item, event.target.value)}
      >
        <option value="">Chuyển…</option>
        {allowedTransitions.map((value) => (
          <option key={value} value={value}>
            {valueLabel(value)}
          </option>
        ))}
      </select>
    );
  };
  if (initialLoading || initialLoadFailed) {
    return (
      <WorkspacePage title="Lỗi" actions={<ProjectCrumb projectId={project._id} />}>
        {initialLoading ? (
          <LoadingState />
        ) : (
          <div className="space-y-3">
            <ErrorState message={error || "Không thể tải danh sách lỗi"} />
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
      title="Lỗi"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {can("defect.create") && (
            <button
              className="apple-button"
              type="button"
              onClick={() => {
                setSuccess("");
                setCreating(true);
              }}
            >
              Tạo lỗi
            </button>
          )}
          {can("report.export") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                testingApi.exportDefects(project._id).catch((reason) => setError(messageOf(reason)))
              }
            >
              Xuất CSV
            </button>
          )}
          {can("defect.duplicate_check") && (
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                try {
                  setDuplicates(await testingApi.findDuplicateDefects(project._id));
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Tìm lỗi có thể trùng
            </button>
          )}
        </div>
      }
    >
      {success && (
        <p role="status" className="rounded-control bg-brand-soft p-4 text-[13px] text-brand">
          {success}
        </p>
      )}
      {error && (
        <div className="space-y-2">
          <ErrorState message={error} />
          <button className="secondary-button" type="button" onClick={() => void load()}>
            Tải lại danh sách lỗi
          </button>
        </div>
      )}
      {can("defect.create") && (
        <Modal
          isOpen={creating}
          onClose={() => setCreating(false)}
          ariaLabel="Tạo lỗi"
          className="max-w-3xl max-h-[90dvh] overflow-y-auto"
        >
          <ModalHeader>
            <ModalTitle>Tạo lỗi</ModalTitle>
          </ModalHeader>
          <form className="grid gap-4 p-5 md:grid-cols-2" onSubmit={create}>
            <label className="field-label md:col-span-2">
              Tên
              <input
                required
                className="apple-input mt-2"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </label>
            <label className="field-label">
              Mức độ nghiêm trọng
              <select
                className="apple-input mt-2"
                value={form.severity}
                onChange={(event) => setForm({ ...form, severity: event.target.value })}
              >
                {["blocker", "critical", "major", "minor", "trivial"].map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Mức ưu tiên
              <select
                className="apple-input mt-2"
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value })}
              >
                {["critical", "high", "medium", "low"].map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Môi trường
              {can("environment.read") ? (
                <select
                  className="apple-input mt-2"
                  value={form.environmentId}
                  onChange={(event) => {
                    const environmentId = event.target.value;
                    const environment = environments.find((item) => item._id === environmentId);
                    setForm({
                      ...form,
                      environmentId,
                      environment: environment?.name || "",
                    });
                  }}
                >
                  <option value="">Chọn môi trường</option>
                  {environments.map((item) => (
                    <option key={item._id} value={item._id}>
                      {item.name} · {valueLabel(item.environment_type)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="apple-input mt-2"
                  value={form.environment}
                  onChange={(event) =>
                    setForm({ ...form, environment: event.target.value, environmentId: "" })
                  }
                />
              )}
            </label>
            <label className="field-label">
              Bản dựng
              {can("build.read") && can("release.read") ? (
                <select
                  className="apple-input mt-2"
                  value={form.buildId}
                  onChange={(event) => {
                    const buildId = event.target.value;
                    const build = builds.find((item) => item._id === buildId);
                    setForm({
                      ...form,
                      buildId,
                      build: build?.identifier || "",
                      releaseId: build?.release_id || form.releaseId,
                      release:
                        releases.find((item) => item._id === build?.release_id)?.key ||
                        form.release,
                    });
                  }}
                >
                  <option value="">Không gắn bản dựng</option>
                  {builds
                    .filter((item) => !form.releaseId || item.release_id === form.releaseId)
                    .map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.identifier} · {item.version}
                      </option>
                    ))}
                </select>
              ) : (
                <input
                  className="apple-input mt-2"
                  value={form.build}
                  onChange={(event) => setForm({ ...form, build: event.target.value, buildId: "" })}
                />
              )}
            </label>
            <label className="field-label">
              Bản phát hành
              {can("release.read") ? (
                <select
                  className="apple-input mt-2"
                  value={form.releaseId}
                  onChange={(event) => {
                    const releaseId = event.target.value;
                    const release = releases.find((item) => item._id === releaseId);
                    setForm({
                      ...form,
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
              ) : (
                <input
                  className="apple-input mt-2"
                  value={form.release}
                  onChange={(event) =>
                    setForm({ ...form, release: event.target.value, releaseId: "", buildId: "" })
                  }
                />
              )}
            </label>
            <label className="field-label md:col-span-2">
              Các bước tái hiện
              <textarea
                required
                className="apple-input mt-2 min-h-24"
                placeholder="Mỗi dòng là một bước"
                value={form.steps}
                onChange={(event) => setForm({ ...form, steps: event.target.value })}
              />
            </label>
            <label className="field-label">
              Mô tả
              <textarea
                className="apple-input mt-2 min-h-24"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </label>
            <label className="field-label">
              Kết quả thực tế
              <textarea
                className="apple-input mt-2 min-h-24"
                value={form.actual}
                onChange={(event) => setForm({ ...form, actual: event.target.value })}
              />
            </label>
            <label className="field-label md:col-span-2">
              Kết quả mong đợi
              <textarea
                className="apple-input mt-2 min-h-24"
                value={form.expected}
                onChange={(event) => setForm({ ...form, expected: event.target.value })}
              />
            </label>
            <div className="min-w-0 md:col-span-2">
              <FilePicker
                label="Tệp bằng chứng"
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  try {
                    const uploaded = await uploadAssetAPI(file);
                    setForm({ ...form, attachments: [...form.attachments, uploaded.data] });
                  } catch (reason) {
                    setError(messageOf(reason));
                  }
                }}
              />
              {form.attachments.map((attachment) => (
                <span
                  className="mt-2 block break-all text-[11px] text-ink-muted"
                  key={attachment.url}
                >
                  {attachment.filename}
                </span>
              ))}
            </div>
            <div className="action-dialog-footer flex justify-end gap-3 md:col-span-2">
              <button
                className="secondary-button"
                type="button"
                disabled={savingDefect}
                onClick={() => setCreating(false)}
              >
                Hủy
              </button>
              <button className="apple-button" type="submit" disabled={savingDefect}>
                {savingDefect ? "Đang lưu…" : "Lưu lỗi"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {duplicates.length > 0 && (
        <Panel title="Các lỗi có thể bị trùng">
          <DataTable
            items={duplicates}
            columns={[
              {
                key: "left",
                label: "Lỗi thứ nhất",
                render: (item) => `${item.left.defect_key} ${item.left.title}`,
              },
              {
                key: "right",
                label: "Lỗi thứ hai",
                render: (item) => `${item.right.defect_key} ${item.right.title}`,
              },
              {
                key: "similarity",
                label: "Mức tương đồng",
                render: (item) => `${Math.round(item.similarity * 100)}%`,
              },
              { key: "reason", label: "Lý do" },
            ]}
          />
        </Panel>
      )}
      {traceReview && (
        <Modal
          isOpen={Boolean(traceReview)}
          onClose={() => setTraceReview(null)}
          ariaLabel={`Gợi ý liên kết cho ${traceReview.defect.defect_key}`}
          className="max-w-6xl"
        >
          <ModalHeader>
            <ModalTitle>Gợi ý liên kết cho {traceReview.defect.defect_key}</ModalTitle>
            <p className="mt-2 text-sm text-ink-muted">
              Gợi ý chưa thay đổi lỗi. Chỉ liên kết sau khi người có quyền xác nhận.
            </p>
          </ModalHeader>
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-5 py-3 text-sm font-semibold text-ink">
            Yêu cầu được đề xuất
            <ContentOriginBadge origin="ai_suggested" />
          </div>
          <DataTable
            items={traceReview.result.requirement_candidates}
            empty="Không tìm thấy yêu cầu liên quan trong dự án"
            columns={[
              { key: "requirement_key", label: "Yêu cầu" },
              { key: "title", label: "Tên" },
              {
                key: "confidence_band",
                label: "Mức độ liên quan",
                render: (item) => valueLabel(item.confidence_band),
              },
              {
                key: "reason_codes",
                label: "Bằng chứng",
                render: (item) =>
                  item.reason_codes
                    .map((code) => traceReasonLabels[code] || "Có thông tin liên quan")
                    .join(", "),
              },
              {
                key: "action",
                label: "Quyết định",
                render: (candidate) =>
                  canManageTrace(traceReview.defect) ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => void confirmTraceCandidate(candidate)}
                    >
                      Xác nhận yêu cầu
                    </button>
                  ) : null,
              },
            ]}
          />
          <div className="flex flex-wrap items-center gap-2 border-y border-border px-5 py-3 text-sm font-semibold text-ink">
            Ca kiểm thử được đề xuất
            <ContentOriginBadge origin="ai_suggested" />
          </div>
          <DataTable
            items={traceReview.result.test_case_candidates}
            empty="Không tìm thấy ca kiểm thử liên quan trong dự án"
            columns={[
              { key: "test_case_key", label: "Ca kiểm thử" },
              { key: "title", label: "Tên" },
              {
                key: "confidence_band",
                label: "Mức độ liên quan",
                render: (item) => valueLabel(item.confidence_band),
              },
              {
                key: "reason_codes",
                label: "Bằng chứng",
                render: (item) =>
                  item.reason_codes
                    .map((code) => traceReasonLabels[code] || "Có thông tin liên quan")
                    .join(", "),
              },
              {
                key: "action",
                label: "Quyết định",
                render: (candidate) =>
                  canManageTrace(traceReview.defect) ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => void confirmTraceCandidate(candidate)}
                    >
                      Xác nhận ca kiểm thử
                    </button>
                  ) : null,
              },
            ]}
          />
        </Modal>
      )}
      <Panel title="Danh sách lỗi">
        <details className="border-b border-border p-4" open>
          <summary className="cursor-pointer text-sm font-medium">Tìm và lọc lỗi</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <SearchField
              ariaLabel="Tìm lỗi"
              className="xl:col-span-2"
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Tìm theo mã hoặc tên"
              value={searchText}
            />
            <select
              aria-label="Lọc trạng thái lỗi"
              className="apple-input"
              value={filters.status}
              onChange={(event) => {
                setFilters({ ...filters, status: event.target.value });
                setPage(1);
              }}
            >
              <option value="">Mọi trạng thái</option>
              {Object.keys(nextStates).map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
            <select
              aria-label="Lọc mức độ lỗi"
              className="apple-input"
              value={filters.severity}
              onChange={(event) => {
                setFilters({ ...filters, severity: event.target.value });
                setPage(1);
              }}
            >
              <option value="">Mọi mức độ</option>
              {["blocker", "critical", "major", "minor", "trivial"].map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
            <select
              aria-label="Lọc người xử lý lỗi"
              className="apple-input"
              value={filters.assignee}
              onChange={(event) => {
                setFilters({ ...filters, assignee: event.target.value });
                setPage(1);
              }}
            >
              <option value="">Mọi người xử lý</option>
              {members.map((item) => (
                <option key={item.user_id} value={item.user_id}>
                  {memberDisplayName(item)}
                </option>
              ))}
            </select>
            <select
              aria-label="Sắp xếp lỗi"
              className="apple-input"
              value={filters.sort}
              onChange={(event) => {
                setFilters({ ...filters, sort: event.target.value });
                setPage(1);
              }}
            >
              <option value="-updated_at">Mới cập nhật</option>
              <option value="updated_at">Cũ cập nhật</option>
              <option value="severity">Theo mức độ</option>
              <option value="priority">Theo ưu tiên</option>
            </select>
          </div>
        </details>
        {items.length ? (
          <ul aria-label="Danh sách lỗi" className="divide-y divide-border">
            {items.map((item) => {
              const assignee = members.find((member) => member.user_id === item.assignee);
              const currentTrace =
                traceSuggestions[item._id]?.source_event_revision === item.revision;
              const reproductionSteps = (item.steps_to_reproduce || [])
                .map((step) => ({
                  action: docText(step.action_doc || step.action || step.description),
                  expected: docText(step.expected_doc || step.expected),
                }))
                .filter((step) => step.action || step.expected);
              const hasResultDetails = Boolean(
                reproductionSteps.length ||
                  docText(item.expected_result_doc) ||
                  docText(item.actual_result_doc),
              );
              return (
                <li className="min-w-0 px-4 py-4 sm:px-5" key={item._id}>
                  <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-ink-muted">{item.defect_key}</p>
                      <h3 className="mt-1 break-words text-[15px] font-semibold leading-6 text-ink">
                        {item.title}
                      </h3>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill value={item.status} />
                      <span className="rounded-control border border-border px-2.5 py-1 text-xs text-ink">
                        {valueLabel(item.severity)}
                      </span>
                      <span className="rounded-control border border-border px-2.5 py-1 text-xs text-ink-muted">
                        Ưu tiên {valueLabel(item.priority)}
                      </span>
                    </div>
                  </div>
                  {item.description && (
                    <p className="mt-2 line-clamp-2 break-words text-[13px] leading-5 text-ink-muted">
                      {item.description}
                    </p>
                  )}
                  <dl className="mt-3 grid min-w-0 gap-x-6 gap-y-2 text-[12px] sm:grid-cols-2 xl:grid-cols-4">
                    <div className="min-w-0">
                      <dt className="text-ink-faint">Người xử lý</dt>
                      <dd className="mt-0.5 break-words font-medium text-ink">
                        {defectActionAccess(project, item).canAssign ? (
                          <button
                            className="text-left text-brand hover:underline"
                            type="button"
                            onClick={() => assignDefect(item)}
                          >
                            {assignee
                              ? memberDisplayName(assignee)
                              : item.assignee
                                ? "Thành viên dự án"
                                : "Gán người xử lý"}
                          </button>
                        ) : assignee ? (
                          memberDisplayName(assignee)
                        ) : item.assignee ? (
                          "Thành viên dự án"
                        ) : (
                          "Chưa gán"
                        )}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-ink-faint">Liên kết kiểm thử</dt>
                      <dd className="mt-0.5 break-words font-medium text-ink">
                        {item.linked_test_case_version_id
                          ? "Đã liên kết ca kiểm thử"
                          : "Chưa liên kết ca kiểm thử"}
                      </dd>
                    </div>
                    {(item.environment || item.build || item.release) && (
                      <div className="min-w-0 sm:col-span-2">
                        <dt className="text-ink-faint">Môi trường và phiên bản</dt>
                        <dd className="mt-0.5 break-words font-medium text-ink">
                          {[
                            item.environment ? displayEnvironment(item.environment) : "",
                            item.build,
                            item.release,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </dd>
                      </div>
                    )}
                  </dl>
                  {hasResultDetails && (
                    <details className="mt-3 rounded-control border border-border px-3 py-2">
                      <summary className="cursor-pointer text-[13px] font-medium text-ink">
                        Các bước và kết quả
                      </summary>
                      <div className="mt-3 grid gap-4 text-[13px] leading-5 md:grid-cols-2">
                        {reproductionSteps.length > 0 && (
                          <div className="min-w-0">
                            <h4 className="font-semibold text-ink">Các bước tái hiện</h4>
                            <ol className="mt-2 list-inside list-decimal space-y-1 text-ink-muted">
                              {reproductionSteps.map((step, index) => (
                                <li className="break-words" key={`${item._id}-step-${index}`}>
                                  {step.action}
                                  {step.expected && (
                                    <span className="mt-1 block pl-5 text-ink-faint">
                                      Kết quả mong đợi: {step.expected}
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ol>
                          </div>
                        )}
                        {docText(item.expected_result_doc) && (
                          <div className="min-w-0">
                            <h4 className="font-semibold text-ink">Kết quả mong đợi</h4>
                            <p className="mt-2 break-words text-ink-muted">
                              {docText(item.expected_result_doc)}
                            </p>
                          </div>
                        )}
                        {docText(item.actual_result_doc) && (
                          <div className="min-w-0">
                            <h4 className="font-semibold text-ink">Kết quả thực tế</h4>
                            <p className="mt-2 break-words text-ink-muted">
                              {docText(item.actual_result_doc)}
                            </p>
                          </div>
                        )}
                      </div>
                    </details>
                  )}
                  <div className="mt-3 flex min-w-0 flex-wrap items-center gap-2">
                    {renderTransition(item)}
                    {can("ai.suggest_bug_trace") &&
                      (currentTrace ? (
                        <button
                          aria-label={`Xem gợi ý AI cho ${item.defect_key}`}
                          className="icon-button h-9 w-9"
                          title="Xem gợi ý AI"
                          type="button"
                          onClick={() =>
                            setTraceReview({ defect: item, result: traceSuggestions[item._id] })
                          }
                        >
                          <Eye aria-hidden="true" size={16} />
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="secondary-button text-violet-800"
                          disabled={Boolean(traceGeneratingId)}
                          onClick={() => void suggestTrace(item)}
                        >
                          {traceGeneratingId === item._id
                            ? "Đang tìm liên kết…"
                            : "Đề xuất liên kết"}
                        </button>
                      ))}
                    {item.linked_test_case_version_id && canManageTrace(item) && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async () => {
                          await ask({
                            title: "Thu hồi liên kết lỗi",
                            description: `${item.defect_key} sẽ không còn liên kết với ca kiểm thử hiện tại`,
                            confirmLabel: "Thu hồi liên kết",
                            danger: true,
                            onConfirm: async () => {
                              try {
                                await testingApi.updateDefectTrace(project._id, item._id, {
                                  expected_revision: item.revision,
                                  reason: "Người dùng xác nhận thu hồi liên kết truy vết hiện tại",
                                  linked_test_case_version_id: null,
                                  linked_requirement_version_ids: [],
                                });
                                await load();
                              } catch (reason) {
                                throw new Error(messageOf(reason));
                              }
                            },
                          });
                        }}
                      >
                        Thu hồi liên kết
                      </button>
                    )}
                    {defectActionAccess(project, item).canEditTechnical && (
                      <button
                        type="button"
                        className="icon-button h-9 w-9"
                        title="Cập nhật phân tích lỗi"
                        aria-label={`Cập nhật phân tích ${item.defect_key}`}
                        onClick={() => void editTechnicalDetails(item)}
                      >
                        <Pencil aria-hidden="true" size={16} />
                      </button>
                    )}
                    {item.updated_at && (
                      <span className="ml-auto text-xs text-ink-faint">
                        Cập nhật {formatDate(item.updated_at)}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="px-5 py-5 text-[13px] text-ink-muted" role="status">
            Chưa có lỗi
          </p>
        )}
        <Pagination value={pageInfo} onChange={setPage} />
      </Panel>
      {project.current_permissions?.includes("causalanalysis.read") && (
        <CausalAnalysisPanel project={project} />
      )}
      {dialog}
    </WorkspacePage>
  );
}
