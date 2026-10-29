"use client";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { messageOf, textDoc, valueLabel } from "../../lib/testing";
import { shouldReloadAfterAmbiguousMutation } from "../../lib/executionRecovery.logic.mjs";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { eligibleRetestResults } from "./defectRetest.logic.mjs";

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

export default function DefectsPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [releases, setReleases] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [page, setPage] = useState(1);
  const [pageInfo, setPageInfo] = useState(null);
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
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const loadGeneration = useRef(0);
  const [creating, setCreating] = useState(false);
  const [savingDefect, setSavingDefect] = useState(false);
  const savingDefectRef = useRef(false);
  const defectCreateOperation = useRef(null);
  const [form, setForm] = useState({
    title: "",
    severity: "major",
    priority: "medium",
    environment: "staging",
    environmentId: "",
    releaseId: "",
    release: "",
    build: "",
    buildId: "",
    description: "",
    actual: "",
    expected: "",
    attachments: [],
  });
  const can = (permission) => project.current_permissions?.includes(permission);
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const userId = project.current_membership?.user_id;
  const canManageTrace = (item) =>
    can("defect.trace.manage") || (memberRoles.includes("DEVELOPER") && item.assignee === userId);
  const transitionAllowed = (item, status) => {
    if (["CONFIRMED", "REJECTED", "DUPLICATE"].includes(status)) {
      if (!can("defect.triage")) return false;
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
      return (
        can("defect.transition.developer") ||
        (memberRoles.includes("DEVELOPER") && item.assignee === userId)
      );
    }
    if (["READY_FOR_RETEST", "REOPENED"].includes(status)) return can("defect.retest");
    if (status === "CLOSED") return can("defect.close");
    return can("defect.update");
  };
  const hasTransitionActions = (item) =>
    item.status === "READY_FOR_RETEST"
      ? can("defect.retest") && eligibleRetestResults(item, results).length > 0
      : (nextStates[item.status] || []).some((status) => transitionAllowed(item, status));
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
    if (!project.current_permissions?.includes("ai.suggest_bug_trace") || !items.length) {
      return undefined;
    }
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || pending) return;
      pending = true;
      try {
        const values = await testingApi.listAutomatedDefectTraceSuggestions(
          project._id,
          items.map((item) => item._id),
        );
        if (active) {
          setTraceSuggestions(Object.fromEntries(values.map((item) => [item.subject_id, item])));
        }
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
  }, [items, project._id, project.current_permissions]);
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
      steps_to_reproduce: [],
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
        environment: "staging",
        environmentId: "",
        release: "",
        releaseId: "",
        build: "",
        buildId: "",
        description: "",
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
          initialValue: "Đã xác minh điều kiện chuyển trạng thái",
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
              label: member.user_label || member.user?.email || "Thành viên dự án",
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
  const confirmTraceCandidate = async (candidate) => {
    await ask({
      title: "Xác nhận liên kết truy vết",
      description: `${traceReview.defect.defect_key} với ${candidate.requirement_key || candidate.test_case_key}`,
      confirmLabel: "Xác nhận liên kết",
      fields: [
        {
          name: "reason",
          label: "Lý do xác nhận",
          initialValue: "Đã đối chiếu bằng chứng và xác nhận liên kết phù hợp",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        const payload = {
          expected_revision: traceReview.defect.revision,
          reason: answer.reason,
          ai_result_id: traceReview.result._id,
          accepted_candidate_ids: [candidate.candidate_id],
        };
        if (candidate.artifact_type === "requirement_version") {
          payload.linked_requirement_version_ids = [
            ...new Set([
              ...(traceReview.defect.linked_requirement_version_ids || []),
              candidate.artifact_id,
            ]),
          ];
        } else {
          payload.linked_test_case_version_id = candidate.artifact_id;
        }
        try {
          await testingApi.updateDefectTrace(project._id, traceReview.defect._id, payload);
          setTraceReview(null);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
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
        <Panel title="Ứng viên lỗi trùng cần người dùng xác nhận">
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
        <Panel title={`Gợi ý liên kết cho ${traceReview.defect.defect_key}`}>
          <div className="border-b border-border px-5 py-3 text-sm text-ink-muted">
            Gợi ý chưa thay đổi lỗi. Chỉ liên kết sau khi người có quyền xác nhận.
          </div>
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
        </Panel>
      )}
      <Panel title="Danh sách lỗi">
        <details className="border-b border-border p-4">
          <summary className="cursor-pointer text-sm font-medium">Tìm và lọc lỗi</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <input
              aria-label="Tìm lỗi"
              className="apple-input xl:col-span-2"
              placeholder="Tìm theo mã hoặc tên"
              value={filters.q}
              onChange={(event) => {
                setFilters({ ...filters, q: event.target.value });
                setPage(1);
              }}
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
                  {item.user_label || item.user?.email || "Thành viên dự án"}
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
        <DataTable
          layout="wide-table"
          items={items}
          empty="Chưa có lỗi"
          columns={[
            { key: "defect_key", label: "Mã" },
            { key: "title", label: "Tên" },
            { key: "severity", label: "Mức độ", render: (item) => valueLabel(item.severity) },
            { key: "priority", label: "Ưu tiên", render: (item) => valueLabel(item.priority) },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "trace",
              label: "Truy vết",
              render: (item) => (
                <span className="flex min-w-0 flex-col items-start gap-2 sm:min-w-48">
                  <span className="text-[11px] text-ink-muted">
                    {item.linked_test_case_version_id
                      ? "Đã liên kết ca kiểm thử"
                      : "Chưa liên kết ca kiểm thử"}
                  </span>
                  <span className="flex flex-wrap gap-2">
                    {can("ai.suggest_bug_trace") &&
                      traceSuggestions[item._id]?.source_event_revision === item.revision && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() =>
                            setTraceReview({ defect: item, result: traceSuggestions[item._id] })
                          }
                        >
                          Xem gợi ý tự động
                        </button>
                      )}
                    {can("ai.suggest_bug_trace") &&
                      (!traceSuggestions[item._id] ||
                        traceSuggestions[item._id].source_event_revision !== item.revision) && (
                        <span className="text-xs text-ink-muted">Chưa có đề xuất tự động</span>
                      )}
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
                        Thu hồi
                      </button>
                    )}
                  </span>
                </span>
              ),
            },
            {
              key: "assignee",
              label: "Người xử lý",
              render: (item) =>
                can("defect.assign") ? (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => assignDefect(item)}
                  >
                    {members.find((member) => member.user_id === item.assignee)?.user_label ||
                      members.find((member) => member.user_id === item.assignee)?.user?.email ||
                      (item.assignee ? "Người xử lý không còn trong danh sách thành viên" : null) ||
                      "Gán người xử lý"}
                  </button>
                ) : (
                  members.find((member) => member.user_id === item.assignee)?.user_label ||
                  members.find((member) => member.user_id === item.assignee)?.user?.email ||
                  (item.assignee ? "Người xử lý không còn trong danh sách thành viên" : null) ||
                  "Chưa gán"
                ),
            },
            ...(items.some(hasTransitionActions)
              ? [
                  {
                    key: "transition",
                    label: "Chuyển trạng thái",
                    render: (item) => {
                      if (item.status === "READY_FOR_RETEST") {
                        if (!can("defect.retest")) return null;
                        const eligibleResults = eligibleRetestResults(item, results);
                        if (!eligibleResults.length) return null;
                        return (
                          <select
                            aria-label={`Kết quả retest ${item.defect_key}`}
                            className="apple-input min-w-44"
                            value=""
                            onChange={async (event) => {
                              if (!event.target.value) return;
                              try {
                                await testingApi.retestDefect(project._id, item._id, {
                                  test_result_id: event.target.value,
                                  expected_revision: item.revision,
                                  note: "Kiểm thử lại từ giao diện quản lý lỗi",
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
                                {result.test_case_key ||
                                  result.test_case_name ||
                                  result.build ||
                                  "Kết quả kiểm thử"}
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
                          className="apple-input min-w-44"
                          value=""
                          onChange={(event) => transition(item, event.target.value)}
                        >
                          <option value="">Chọn</option>
                          {allowedTransitions.map((value) => (
                            <option key={value} value={value}>
                              {valueLabel(value)}
                            </option>
                          ))}
                        </select>
                      );
                    },
                  },
                ]
              : []),
          ]}
        />
        <Pagination value={pageInfo} onChange={setPage} />
      </Panel>
      {project.current_permissions?.includes("causalanalysis.read") && (
        <CausalAnalysisPanel project={project} />
      )}
      {dialog}
    </WorkspacePage>
  );
}
