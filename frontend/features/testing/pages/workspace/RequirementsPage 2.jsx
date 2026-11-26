"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "next/navigation";
import TraceabilityPage from "./TraceabilityPage";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import CollaborationPanel from "../../components/CollaborationPanel";
import {
  ErrorState,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { docText, messageOf, textDoc } from "../../lib/testing";
import RequirementCurrentVersionPanel from "./requirements/RequirementCurrentVersionPanel";
import RequirementCreateModal from "./requirements/RequirementCreateModal";
import RequirementDuplicatePanel from "./requirements/RequirementDuplicatePanel";
import RequirementHistoryPanel from "./requirements/RequirementHistoryPanel";
import RequirementImpactPanel from "./requirements/RequirementImpactPanel";
import RequirementImportModal from "./requirements/RequirementImportModal";
import RequirementSourceDocumentsPanel from "./requirements/RequirementSourceDocumentsPanel";
import RequirementTracePanel from "./requirements/RequirementTracePanel";
import RequirementsListPanel from "./requirements/RequirementsListPanel";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import {
  createInitialRequirementForm,
  parseAcceptanceCriteria,
  parseCommaValues,
  splitRequirementBlocks,
} from "./requirements/requirements.model";

export default function RequirementsPage({ project, section, workspaceView }) {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const { ask, dialog } = useActionDialog();
  const documentsView = workspaceView === "documents";
  const sectionKey = documentsView ? "" : section[0] || "";
  const requirementId = sectionKey && !["new", "import"].includes(sectionKey) ? sectionKey : "";
  const [items, setItems] = useState([]);
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const [members, setMembers] = useState([]);
  const [customFields, setCustomFields] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedContextKey, setSelectedContextKey] = useState("");
  const [detailTab, setDetailTab] = useState("requirement");
  const [versions, setVersions] = useState([]);
  const [form, setForm] = useState(createInitialRequirementForm);
  const creating = sectionKey === "new";
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    coverage: "",
    tag: "",
    owner: "",
    sort: "-updated_at",
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pageInfo, setPageInfo] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [focusAcceptanceCriterionId, setFocusAcceptanceCriterionId] = useState("");
  const [upload, setUpload] = useState([]);
  const [uploadAccess, setUploadAccess] = useState({
    visibility: "private",
    shared_with: [],
    ai_enabled: false,
    source_type: "SRS",
    ocr_language: "",
    supersedes_document_id: null,
  });
  const [sourceDocument, setSourceDocument] = useState(null);
  const [sourceDocuments, setSourceDocuments] = useState([]);
  const [pendingExtractionDocumentId, setPendingExtractionDocumentId] = useState("");
  const [pendingExtractionProjectId, setPendingExtractionProjectId] = useState(project._id);
  const [uploadingSource, setUploadingSource] = useState(false);
  const [retryingSource, setRetryingSource] = useState(false);
  const loadSequence = useRef(0);
  const activeProjectId = useRef(project._id);
  activeProjectId.current = project._id;
  const handleDocumentDuplicateMatches = async (
    filename,
    matches,
    { allowIndependent = true, allowExactIndependent = false } = {},
  ) => {
    if (!matches?.length) return "continue";
    const reusable = matches.filter((match) => match.reusable);
    const choices = [
      { value: "", label: "Chọn cách xử lý" },
      ...reusable.map((match) => ({
        value: `reuse:${match.document_id}`,
        label: `${match.project_name} · ${match.filename} · ${match.match_type.startsWith("EXACT") ? "Khớp 100%" : `Giống khoảng ${match.similarity_percent}%`}`,
      })),
    ];
    const hasExactSameProject = matches.some(
      (match) => match.same_project && ["EXACT_FILE", "EXACT_CONTENT"].includes(match.match_type),
    );
    if (
      allowIndependent &&
      !hasExactSameProject &&
      (allowExactIndependent || matches.some((match) => match.match_type === "SIMILAR_CONTENT"))
    ) {
      choices.push({ value: "continue", label: "Tiếp tục như tài liệu riêng" });
    }
    choices.push({ value: "discard", label: "Bỏ tệp đang import" });
    const details = matches
      .slice(0, 6)
      .map(
        (match) =>
          `${match.match_type.startsWith("EXACT") ? "100%" : `Độ giống ước tính ${match.similarity_percent}%`} · ${match.filename} · ${match.project_name} · ${match.status}${match.difference_summary ? ` · ${match.difference_summary}` : ""}`,
      )
      .join("\n");
    const result = await ask({
      title: "Tìm thấy tài liệu trùng hoặc tương tự",
      description: `Tài liệu “${filename}” có ${matches.length} kết quả để đối chiếu:\n${details}\nChọn tài liệu có sẵn để mở dự án chứa bản đó; việc này không tạo bản sao hay chạy AI lại.`,
      confirmLabel: "Tiếp tục",
      fields: [
        {
          name: "action",
          label: "Cách xử lý",
          options: choices,
          required: true,
        },
      ],
    });
    const action = result?.action || "";
    if (action.startsWith("reuse:")) {
      const documentId = action.slice("reuse:".length);
      const match = reusable.find((item) => item.document_id === documentId);
      if (match) {
        window.location.assign(
          projectRoute(match.project_id, PROJECT_SECTION_SLUGS.documentReader, documentId),
        );
      }
      return "reuse";
    }
    if (action === "continue") return "continue";
    if (action === "discard") return "discard";
    return "stop";
  };
  const pendingExtractionStorageKey = `veriq:requirement-import:${project._id}`;
  const rememberPendingExtraction = useCallback(
    (documentId) => {
      setPendingExtractionProjectId(project._id);
      setPendingExtractionDocumentId(documentId || "");
      try {
        if (documentId) window.sessionStorage.setItem(pendingExtractionStorageKey, documentId);
        else window.sessionStorage.removeItem(pendingExtractionStorageKey);
      } catch {}
    },
    [pendingExtractionStorageKey, project._id],
  );
  useEffect(() => {
    try {
      const documentId = window.sessionStorage.getItem(pendingExtractionStorageKey);
      setPendingExtractionProjectId(project._id);
      setPendingExtractionDocumentId(documentId || "");
    } catch {}
  }, [pendingExtractionStorageKey, project._id]);
  useEffect(() => {
    if (sectionKey === "import") setImporting(true);
  }, [sectionKey]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setFocusAcceptanceCriterionId(params.get("acceptanceCriterionId") || "");
  }, [requirementId]);
  const rememberSourceDocument = (document) => {
    setSourceDocument(document);
    setSourceDocuments((items) => [document, ...items.filter((item) => item._id !== document._id)]);
  };
  useEffect(() => {
    if (!pendingExtractionDocumentId || pendingExtractionProjectId !== project._id)
      return undefined;
    let active = true;
    let timer;
    let checking = false;
    const poll = async () => {
      if (checking) return;
      checking = true;
      try {
        const document = await testingApi.getRequirementDocument(pendingExtractionDocumentId);
        if (!active) return;
        rememberSourceDocument(document);
        if (document.status === "READY") {
          setError("");
          rememberPendingExtraction("");
          return;
        }
        if (document.status === "PARSE_FAILED") {
          setError(
            document.parse_error_type === "TimeoutError"
              ? "Đã hết thời gian phân tích tài liệu; tệp gốc vẫn được lưu để bạn thử lại."
              : "Tệp gốc đã được lưu nhưng bộ phân tích không đọc được nội dung.",
          );
          rememberPendingExtraction("");
          return;
        }
      } catch (reason) {
        if (active) {
          setError(messageOf(reason));
          if ([401, 403, 404].includes(reason?.status)) {
            rememberPendingExtraction("");
            return;
          }
        }
      } finally {
        checking = false;
      }
      if (active) timer = window.setTimeout(poll, 2000);
    };
    timer = window.setTimeout(poll, 1000);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [
    pendingExtractionDocumentId,
    pendingExtractionProjectId,
    project._id,
    rememberPendingExtraction,
  ]);
  const hasPendingSourceParse = sourceDocuments.some((item) =>
    ["UPLOADED", "PARSING"].includes(item.status),
  );
  useEffect(() => {
    if (
      !hasPendingSourceParse ||
      !project.current_permissions?.includes("requirement_document.read")
    ) {
      return undefined;
    }
    let active = true;
    let timer;
    const refresh = async () => {
      try {
        const documents = await testingApi.listRequirementDocuments(project._id);
        if (active) setSourceDocuments(documents);
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
      if (active) timer = window.setTimeout(refresh, 3000);
    };
    timer = window.setTimeout(refresh, 3000);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [hasPendingSourceParse, project._id, project.current_permissions]);
  const [draft, setDraft] = useState(null);
  const [draftDirty, setDraftDirty] = useState(false);
  const [saveState, setSaveState] = useState("saved");
  const draftSequence = useRef(0);
  const saveInFlight = useRef(null);
  const savedSequence = useRef(0);
  const loadedVersion = useRef("");
  const [comparison, setComparison] = useState(null);
  const [duplicateScan, setDuplicateScan] = useState(null);
  const [compareFrom, setCompareFrom] = useState("");
  const [compareTo, setCompareTo] = useState("");
  const projectScopeRef = useRef(project._id);
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    const requestedProjectId = project._id;
    setLoading(true);
    try {
      const values = documentsView
        ? { items: [] }
        : await testingApi.listRequirementPage(requestedProjectId, {
            q: query,
            ...filters,
            page,
            page_size: pageSize,
          });
      if (sequence !== loadSequence.current) return;
      setItems(values.items);
      setPageInfo(values);
      const fields = documentsView
        ? []
        : await testingApi.listRequirementFields(requestedProjectId);
      if (sequence !== loadSequence.current) return;
      setCustomFields(fields);
      if (project.current_permissions?.includes("project.members.read")) {
        const memberValues = await testingApi.listMembers(requestedProjectId);
        if (sequence !== loadSequence.current) return;
        setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      } else {
        setMembers([]);
      }
      if (project.current_permissions?.includes("requirement_document.read")) {
        const documents = await testingApi.listRequirementDocuments(requestedProjectId);
        if (sequence !== loadSequence.current) return;
        setSourceDocuments(documents);
      } else {
        setSourceDocuments([]);
        setSourceDocument(null);
      }
      if (requirementId) {
        const detail = await testingApi.getRequirement(requirementId);
        if (sequence !== loadSequence.current) return;
        const history = await testingApi.listRequirementVersions(requirementId);
        if (sequence !== loadSequence.current) return;
        setSelected(detail);
        setSelectedContextKey(`${requestedProjectId}:${requirementId}`);
        setVersions(history);
        setCompareFrom(history[1]?._id || history[0]?._id || "");
        setCompareTo(history[0]?._id || "");
      } else {
        setSelected(null);
        setSelectedContextKey(`${requestedProjectId}:`);
        setVersions([]);
      }
      if (sequence === loadSequence.current) setLoadedProjectId(requestedProjectId);
    } catch (reason) {
      if (sequence === loadSequence.current) setError(messageOf(reason));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [
    documentsView,
    filters,
    page,
    pageSize,
    project._id,
    project.current_permissions,
    query,
    requirementId,
  ]);
  const can = useCallback(
    (permission) => project.current_permissions?.includes(permission),
    [project.current_permissions],
  );
  const routeSelected = selectedContextKey === `${project._id}:${requirementId}` ? selected : null;
  const projectDataReady = loadedProjectId === project._id;
  const visibleItems = useMemo(() => (projectDataReady ? items : []), [items, projectDataReady]);
  const visibleMembers = projectDataReady ? members : [];
  const visibleSourceDocuments = projectDataReady ? sourceDocuments : [];
  useEffect(() => {
    if (projectScopeRef.current === project._id) return;
    projectScopeRef.current = project._id;
    loadSequence.current += 1;
    setLoadedProjectId("");
    setSelected(null);
    setSelectedContextKey("");
    setVersions([]);
    setDraft(null);
    setDraftDirty(false);
    setSaveState("saved");
    setSelectedIds([]);
    setComparison(null);
    setDuplicateScan(null);
    setImporting(false);
    setForm(createInitialRequirementForm());
    setUpload([]);
    setUploadAccess({
      visibility: "private",
      shared_with: [],
      ai_enabled: false,
      source_type: "SRS",
      ocr_language: "",
      supersedes_document_id: null,
    });
    setSourceDocument(null);
    setSourceDocuments([]);
    setPendingExtractionDocumentId("");
    setPendingExtractionProjectId(project._id);
    setError("");
  }, [project._id]);
  useEffect(() => {
    setDetailTab("requirement");
  }, [routeSelected?._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const current = routeSelected?.current_version;
  useEffect(() => {
    if (!current) return;
    const previousVersionId = loadedVersion.current.split(":", 1)[0];
    const versionKey = `${current._id}:${current.revision || 0}`;
    if (loadedVersion.current === versionKey) return;
    if (previousVersionId === current._id && draftDirty) return;
    loadedVersion.current = versionKey;
    setDraft({
      title: current.title,
      type: current.type,
      priority: current.priority,
      content_doc: current.content_doc,
      acceptance: (current.acceptance_criteria || [])
        .map((item) => docText(item.content_doc))
        .join("\n"),
      businessRules: (current.business_rules || []).join("\n"),
      dependencies: (current.dependencies || []).join("\n"),
      tags: (selected.tags || current.tags || []).join(", "),
      ownerId: selected.owner_id || current.owner_id || "",
      details: current.details || {},
      sectionStates: current.section_states || {},
      customValues: current.custom_values || {},
    });
    setDraftDirty(false);
    setSaveState("saved");
  }, [current, draftDirty, selected]);
  const changeDraft = (patch) => {
    draftSequence.current += 1;
    setDraft((value) => ({ ...value, ...patch }));
    setDraftDirty(true);
    setSaveState("pending");
  };
  const persistDraft = useCallback(
    async (snapshot, sequence) => {
      if (!snapshot || !current || !selected) return;
      let baseVersion = current;
      if (saveInFlight.current) {
        const running = saveInFlight.current;
        const saved = await running;
        if (saveInFlight.current === running) saveInFlight.current = null;
        if (sequence <= savedSequence.current) return saved;
        baseVersion = saved?.current_version || current;
      }
      const request = (async () => {
        setSaveState("saving");
        try {
          const result = await testingApi.applyRequirementCollaborationOperation(
            project._id,
            selected._id,
            {
              base_revision: baseVersion.revision,
              operation_id: crypto.randomUUID(),
              changes: {
                title: snapshot.title,
                type: snapshot.type,
                priority: snapshot.priority,
                content_doc: snapshot.content_doc,
                acceptance_criteria: snapshot.acceptance
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .map((line, index) => ({
                    key: `AC-${index + 1}`,
                    content_doc: textDoc(line),
                    status: "draft",
                  })),
                business_rules: snapshot.businessRules
                  .split("\n")
                  .map((value) => value.trim())
                  .filter(Boolean),
                dependencies: snapshot.dependencies
                  .split("\n")
                  .map((value) => value.trim())
                  .filter(Boolean),
                tags: snapshot.tags
                  .split(",")
                  .map((value) => value.trim())
                  .filter(Boolean),
                owner_id: snapshot.ownerId.trim() || null,
                details: snapshot.details,
                section_states: snapshot.sectionStates,
                custom_values: snapshot.customValues,
              },
            },
          );
          savedSequence.current = Math.max(savedSequence.current, sequence);
          setSelected(result);
          if (draftSequence.current === sequence) {
            setDraftDirty(false);
            setSaveState("saved");
          } else {
            setSaveState("pending");
          }
          return result;
        } catch (reason) {
          setSaveState("error");
          setError(messageOf(reason));
          throw reason;
        }
      })();
      saveInFlight.current = request;
      try {
        return await request;
      } finally {
        if (saveInFlight.current === request) saveInFlight.current = null;
      }
    },
    [current, project._id, selected],
  );
  useEffect(() => {
    if (!draftDirty || saveState === "saving" || current?.status !== "DRAFT" || !draft)
      return undefined;
    const sequence = draftSequence.current;
    const timer = window.setTimeout(() => {
      void persistDraft(draft, sequence);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [current?.status, draft, draftDirty, persistDraft, saveState]);
  const criteria = useMemo(
    () =>
      form.acceptance
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line, index) => ({
          key: `AC-${index + 1}`,
          content_doc: textDoc(line),
          status: "draft",
        })),
    [form.acceptance],
  );
  const create = async (event) => {
    event.preventDefault();
    if (saving) return;
    if (!docText(form.content_doc).trim()) {
      setError("Nhập nội dung yêu cầu trước khi lưu.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await testingApi.createRequirement(project._id, {
        save_as_draft: event.nativeEvent.submitter?.value === "draft",
        title: form.title,
        type: form.type,
        priority: form.priority,
        content_doc: form.content_doc,
        acceptance_criteria: criteria,
        business_rules: form.businessRules
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        dependencies: form.dependencies
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        source_refs: [],
        details: {
          ...(form.designReference.trim() ? { design_reference: form.designReference.trim() } : {}),
          ...(form.progressStatus ? { progress_status: form.progressStatus } : {}),
        },
        tags: form.tags
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        owner_id: form.ownerId.trim() || null,
        custom_values: form.customValues,
      });
      setForm(createInitialRequirementForm());
      await load();
      window.location.assign(projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };
  const saveDraft = async () => {
    if (!draftDirty && saveState === "saved") return selected;
    return (await persistDraft(draft, draftSequence.current)) || selected;
  };
  const createVersion = async () => {
    await ask({
      title: "Mở bản nháp để chỉnh sửa yêu cầu",
      description: `${selected.requirement_key} sẽ được tạo thành phiên bản nháp tiếp theo. Phiên bản hiện tại được giữ lại để truy vết.`,
      confirmLabel: "Mở bản nháp",
      fields: [
        {
          name: "title",
          label: "Tên yêu cầu",
          initialValue: current.title,
          required: true,
          autoFocus: true,
        },
        {
          name: "reason",
          label: "Nội dung thay đổi (tùy chọn)",
          initialValue: "",
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.createRequirementVersion(selected._id, {
            requirement_key: selected.requirement_key,
            title: answer.title,
            type: current.type,
            priority: current.priority,
            content_doc: current.content_doc,
            acceptance_criteria: (current.acceptance_criteria || []).map((item) => ({
              key: item.key,
              content_doc: item.content_doc,
              status: item.status,
            })),
            business_rules: current.business_rules || [],
            dependencies: current.dependencies || [],
            source_refs: current.source_refs || [],
            tags: selected.tags || current.tags || [],
            owner_id: selected.owner_id || current.owner_id || null,
            details: { ...(current.details || {}), change_impact: {} },
            section_states: current.section_states || {},
            custom_values: current.custom_values || {},
            change_reason: answer.reason,
            expected_current_version_id: selected.current_version_id,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const uploadPreview = async (event) => {
    event.preventDefault();
    const uploads = Array.isArray(upload) ? upload : upload ? [upload] : [];
    if (!uploads.length || uploadingSource || pendingExtractionDocumentId) return;
    setUploadingSource(true);
    const requestedProjectId = project._id;
    const formats = uploads.map((file) => {
      const extension = file.name.split(".").pop().toLowerCase();
      return ["json", "yaml", "yml"].includes(extension) && uploadAccess.source_type === "API_SPEC"
        ? uploadAccess.api_format || "openapi"
        : extension;
    });
    try {
      const duplicateCheck = await testingApi.compareRequirementDocumentBatch(
        requestedProjectId,
        uploads,
        formats,
      );
      const projectMatches = duplicateCheck.matching_projects || [];
      let keepProjectIndependent = false;
      if (projectMatches.length) {
        const projectChoice = await ask({
          title: "Bộ tài liệu đã có trong dự án khác",
          description: projectMatches
            .map((match) => `${match.project_name} · ${match.document_count} tài liệu`)
            .join("\n"),
          confirmLabel: "Tiếp tục",
          fields: [
            {
              name: "action",
              label: "Cách xử lý bộ tài liệu",
              required: true,
              options: [
                { value: "", label: "Chọn cách xử lý" },
                ...projectMatches.map((match) => ({
                  value: `open:${match.project_id}`,
                  label: `Mở và dùng dự án ${match.project_name}`,
                })),
                { value: "keep", label: "Giữ dự án này và import độc lập" },
                { value: "discard", label: "Bỏ cả lô tệp" },
              ],
            },
          ],
        });
        if (projectChoice?.action?.startsWith("open:")) {
          const match = projectMatches.find(
            (item) => item.project_id === projectChoice.action.slice("open:".length),
          );
          if (match) window.location.assign(`/du-an/${encodeURIComponent(match.project_id)}`);
          return;
        }
        if (projectChoice?.action !== "keep") return;
        keepProjectIndependent = true;
      }
      const acceptedFiles = [];
      const acceptedCandidateIndexes = new Set();
      const matchingProjectIds = new Set(projectMatches.map((match) => match.project_id));
      for (let index = 0; index < uploads.length; index += 1) {
        const allMatches = duplicateCheck.files?.[index]?.matches || [];
        const batchMatches = allMatches.filter((match) => Number.isInteger(match.candidate_index));
        const exactBatchMatches = batchMatches.filter((match) => match.match_type === "IN_IMPORT");
        if (exactBatchMatches.length) {
          const hasAcceptedEarlierCopy = exactBatchMatches.some((match) =>
            acceptedCandidateIndexes.has(match.candidate_index),
          );
          const choice = await ask({
            title: "Tệp bị lặp trong lô import",
            description: `Tệp “${uploads[index].name}” khớp 100% với ${exactBatchMatches
              .map((match) => `“${match.filename}”`)
              .join(", ")}. Dùng tệp xuất hiện trước và bỏ bản lặp này?`,
            confirmLabel: "Tiếp tục",
            fields: [
              {
                name: "action",
                label: "Cách xử lý",
                required: true,
                options: [
                  { value: "", label: "Chọn cách xử lý" },
                  hasAcceptedEarlierCopy
                    ? { value: "keep_previous", label: "Dùng tệp xuất hiện trước" }
                    : { value: "keep_current", label: "Giữ tệp này trong lô" },
                  { value: "discard_batch", label: "Hủy cả lô import" },
                ],
              },
            ],
          });
          if (choice?.action === "keep_previous") continue;
          if (choice?.action !== "keep_current") return;
        }
        const similarBatchMatches = batchMatches.filter(
          (match) => match.match_type === "SIMILAR_CONTENT_IN_IMPORT",
        );
        if (similarBatchMatches.length) {
          const hasAcceptedEarlierCopy = similarBatchMatches.some((match) =>
            acceptedCandidateIndexes.has(match.candidate_index),
          );
          const choice = await ask({
            title: "Tệp tương tự trong lô import",
            description: `Tệp “${uploads[index].name}” tương tự ${similarBatchMatches
              .map((match) => `${match.similarity_percent}% với “${match.filename}”`)
              .join(", ")}.`,
            confirmLabel: "Tiếp tục",
            fields: [
              {
                name: "action",
                label: "Cách xử lý",
                required: true,
                options: [
                  { value: "", label: "Chọn cách xử lý" },
                  hasAcceptedEarlierCopy
                    ? { value: "keep_previous", label: "Dùng tệp xuất hiện trước" }
                    : { value: "continue", label: "Giữ tệp này trong lô" },
                  ...(hasAcceptedEarlierCopy
                    ? [{ value: "continue", label: "Import thành tài liệu riêng" }]
                    : []),
                  { value: "discard_batch", label: "Hủy cả lô import" },
                ],
              },
            ],
          });
          if (choice?.action === "keep_previous") continue;
          if (choice?.action !== "continue") return;
        }
        const matches = allMatches.filter((match) => !Number.isInteger(match.candidate_index));
        const coveredByProjectChoice =
          keepProjectIndependent &&
          matches.length > 0 &&
          matches.every(
            (match) =>
              !match.same_project &&
              matchingProjectIds.has(match.project_id) &&
              ["EXACT_FILE", "EXACT_CONTENT"].includes(match.match_type),
          );
        if (coveredByProjectChoice) {
          acceptedFiles.push({
            file: uploads[index],
            format: formats[index],
            duplicate_confirmed: true,
            duplicate_confirmed_document_ids: matches.map((match) => match.document_id),
            batch_duplicate_candidate_indexes: batchMatches.map((match) => match.candidate_index),
            candidate_index: index,
          });
          acceptedCandidateIndexes.add(index);
          continue;
        }
        const duplicateAction = await handleDocumentDuplicateMatches(uploads[index].name, matches, {
          allowIndependent: true,
          allowExactIndependent: keepProjectIndependent,
        });
        if (duplicateAction === "stop" || duplicateAction === "reuse") return;
        if (duplicateAction === "discard") continue;
        if (duplicateAction === "continue") {
          acceptedFiles.push({
            file: uploads[index],
            format: formats[index],
            duplicate_confirmed: allMatches.length > 0,
            duplicate_confirmed_document_ids: matches.map((match) => match.document_id),
            batch_duplicate_candidate_indexes: batchMatches.map((match) => match.candidate_index),
            candidate_index: index,
          });
          acceptedCandidateIndexes.add(index);
        }
      }
      if (!acceptedFiles.length) return;
      const createdDocuments = [];
      const uploadedDocumentIdsByCandidate = new Map();
      for (const item of acceptedFiles) {
        const confirmedDocumentIds = [
          ...item.duplicate_confirmed_document_ids,
          ...item.batch_duplicate_candidate_indexes
            .map((candidateIndex) => uploadedDocumentIdsByCandidate.get(candidateIndex))
            .filter(Boolean),
        ];
        const created = await testingApi.uploadRequirementDocument(
          requestedProjectId,
          item.file,
          item.format,
          {
            ...uploadAccess,
            duplicate_confirmed: item.duplicate_confirmed,
            duplicate_confirmed_document_ids: confirmedDocumentIds,
          },
        );
        if (activeProjectId.current !== requestedProjectId) return;
        createdDocuments.push(created);
        uploadedDocumentIdsByCandidate.set(item.candidate_index, created._id);
      }
      if (createdDocuments.length > 1) await load();
      const document = createdDocuments[0];
      rememberSourceDocument(document);
      if (document.status === "PARSE_FAILED") {
        setError(
          document.parse_error_type === "TimeoutError"
            ? "Đã hết thời gian phân tích tài liệu; tệp gốc vẫn được lưu để bạn thử lại."
            : "Tệp gốc đã được lưu nhưng bộ phân tích không đọc được nội dung",
        );
        return;
      }
      if (document.status !== "READY") {
        setError("");
        rememberPendingExtraction(document._id);
        return;
      }
      rememberPendingExtraction("");
      setError("");
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    } finally {
      if (activeProjectId.current === requestedProjectId) setUploadingSource(false);
    }
  };
  const retrySourceDocument = async () => {
    if (!sourceDocument || retryingSource) return;
    setRetryingSource(true);
    const requestedProjectId = project._id;
    try {
      const document = await testingApi.retryRequirementDocumentParse(
        sourceDocument._id,
        sourceDocument.revision,
      );
      if (activeProjectId.current !== requestedProjectId) return;
      rememberSourceDocument(document);
      if (document.status !== "READY") {
        setError("");
        rememberPendingExtraction(document._id);
        return;
      }
      setError("");
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    } finally {
      if (activeProjectId.current === requestedProjectId) setRetryingSource(false);
    }
  };
  const splitBaseline = async () => {
    const sourceText = docText(current.content_doc).trim();
    let defaultParts = sourceText
      .split(/\n+/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (defaultParts.length < 2) {
      defaultParts = (sourceText.match(/[^.!?;]+[.!?;]?/g) || [])
        .map((item) => item.trim())
        .filter(Boolean);
    }
    if (defaultParts.length < 2) {
      defaultParts = [sourceText, ""];
    }
    const currentCriteria = (current.acceptance_criteria || []).map((item) =>
      docText(item.content_doc),
    );
    await ask({
      title: "Tách yêu cầu đã phê duyệt",
      description: `${selected.requirement_key} sẽ chuyển sang trạng thái được thay thế và các phần mới được tạo dưới dạng bản nháp`,
      confirmLabel: "Xác nhận tách",
      fields: [
        {
          name: "titles",
          label: "Tên các yêu cầu mới mỗi dòng một tên",
          initialValue: defaultParts.map((item) => item.slice(0, 120)).join("\n"),
          required: true,
          multiline: true,
          autoFocus: true,
        },
        {
          name: "contents",
          label: "Nội dung từng yêu cầu phân cách bằng một dòng ---",
          initialValue: defaultParts.join("\n---\n"),
          required: true,
          multiline: true,
        },
        {
          name: "acceptance",
          label: "Tiêu chí từng yêu cầu phân cách bằng một dòng ---",
          initialValue: defaultParts
            .map((_, index) => currentCriteria[index] || currentCriteria[0] || "")
            .join("\n---\n"),
          required: true,
          multiline: true,
        },
        {
          name: "reason",
          label: "Lý do tách",
          initialValue: "",
          required: true,
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        const titles = answer.titles
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean);
        const contents = splitRequirementBlocks(answer.contents);
        const criteriaBlocks = splitRequirementBlocks(answer.acceptance);
        if (
          contents.length < 2 ||
          titles.length !== contents.length ||
          criteriaBlocks.length !== contents.length
        ) {
          throw new Error("Số tên nội dung và nhóm tiêu chí phải bằng nhau và có ít nhất hai phần");
        }
        try {
          const result = await testingApi.splitRequirement(project._id, selected._id, {
            expected_source_version_id: current._id,
            idempotency_key: crypto.randomUUID(),
            reason: answer.reason,
            drafts: contents.map((content, index) => ({
              title: titles[index],
              type: current.type,
              priority: current.priority,
              content_doc: textDoc(content),
              acceptance_criteria: parseAcceptanceCriteria(criteriaBlocks[index]),
              business_rules: current.business_rules || [],
              dependencies: current.dependencies || [],
              source_refs: [],
              tags: selected.tags || current.tags || [],
              owner_id: selected.owner_id || current.owner_id || null,
            })),
          });
          const first = result.requirements?.[0];
          window.location.assign(
            first ? `/du-an/${project._id}/yeu-cau/${first._id}` : `/du-an/${project._id}/yeu-cau`,
          );
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const mergeBaselines = async () => {
    const sourceSummaries = items.filter((item) => selectedIds.includes(item._id));
    if (sourceSummaries.length < 2) {
      setError("Cần chọn ít nhất hai yêu cầu để gộp");
      return;
    }
    if (sourceSummaries.some((item) => item.status !== "BASELINED")) {
      setError("Chỉ có thể gộp các yêu cầu đã phê duyệt hiện hành");
      return;
    }
    let sources;
    try {
      sources = await Promise.all(
        sourceSummaries.map((item) => testingApi.getRequirement(item._id)),
      );
    } catch (reason) {
      setError(messageOf(reason));
      return;
    }
    if (sources.some((item) => item.current_version?.status !== "BASELINED")) {
      setError("Một yêu cầu đã thay đổi sau khi danh sách được tải vui lòng tải lại và chọn lại");
      return;
    }
    await ask({
      title: "Gộp các yêu cầu đã phê duyệt",
      description: `${sources.map((item) => item.requirement_key).join(", ")} sẽ được giữ lịch sử và chuyển sang trạng thái được thay thế`,
      confirmLabel: "Xác nhận gộp",
      fields: [
        {
          name: "title",
          label: "Tên yêu cầu hợp nhất",
          initialValue: sources
            .map((item) => item.current_version.title)
            .join(" và ")
            .slice(0, 300),
          required: true,
          autoFocus: true,
        },
        {
          name: "content",
          label: "Nội dung hợp nhất",
          initialValue: sources
            .map((item) => docText(item.current_version.content_doc))
            .join("\n\n"),
          required: true,
          multiline: true,
        },
        {
          name: "acceptance",
          label: "Tiêu chí chấp nhận mỗi dòng một điều kiện",
          initialValue: sources
            .flatMap((item) => item.current_version.acceptance_criteria || [])
            .map((item) => docText(item.content_doc))
            .join("\n"),
          required: true,
          multiline: true,
        },
        {
          name: "type",
          label: "Loại yêu cầu",
          initialValue: sources[0].current_version.type,
          required: true,
        },
        {
          name: "reason",
          label: "Lý do gộp",
          initialValue: "Hợp nhất các yêu cầu trùng hoặc cùng một trách nhiệm nghiệp vụ",
          required: true,
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const result = await testingApi.mergeRequirements(project._id, {
            source_requirement_ids: sources.map((item) => item._id),
            expected_source_version_ids: Object.fromEntries(
              sources.map((item) => [item._id, item.current_version_id]),
            ),
            idempotency_key: crypto.randomUUID(),
            reason: answer.reason,
            draft: {
              title: answer.title,
              type: answer.type,
              priority: sources[0].current_version.priority,
              content_doc: textDoc(answer.content),
              acceptance_criteria: parseAcceptanceCriteria(answer.acceptance),
              business_rules: [
                ...new Set(sources.flatMap((item) => item.current_version.business_rules || [])),
              ],
              dependencies: [
                ...new Set(sources.flatMap((item) => item.current_version.dependencies || [])),
              ],
              source_refs: [],
              tags: [
                ...new Set(sources.flatMap((item) => item.tags || item.current_version.tags || [])),
              ],
              owner_id: sources[0].owner_id || sources[0].current_version.owner_id || null,
            },
          });
          setSelectedIds([]);
          const merged = result.requirements?.[0];
          window.location.assign(
            merged
              ? `/du-an/${project._id}/yeu-cau/${merged._id}`
              : `/du-an/${project._id}/yeu-cau`,
          );
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const scanDuplicates = async () => {
    if (selectedIds.length === 1) {
      setError("Chọn ít nhất hai yêu cầu hoặc bỏ chọn để kiểm tra toàn bộ dự án");
      return;
    }
    try {
      setDuplicateScan(
        await testingApi.findDuplicateRequirements(project._id, {
          requirement_ids: selectedIds,
          threshold: 0.72,
          limit: 100,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const bulkUpdateTags = async () => {
    await ask({
      title: "Cập nhật nhãn hàng loạt",
      description: `${selectedIds.length} yêu cầu đã chọn`,
      confirmLabel: "Cập nhật nhãn",
      fields: [
        {
          name: "add",
          label: "Nhãn cần thêm phân cách bằng dấu phẩy",
          autoFocus: true,
        },
        { name: "remove", label: "Nhãn cần gỡ phân cách bằng dấu phẩy" },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.bulkTags(project._id, {
            artifact_type: "requirement",
            ids: selectedIds,
            add_tags: parseCommaValues(answer.add),
            remove_tags: parseCommaValues(answer.remove),
            idempotency_key: crypto.randomUUID(),
          });
          setSelectedIds([]);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const bulkArchiveRequirements = async () => {
    await ask({
      title: "Lưu trữ yêu cầu hàng loạt",
      description: `${selectedIds.length} yêu cầu vẫn được giữ toàn bộ lịch sử`,
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
            artifact_type: "requirement",
            ids: selectedIds,
            reason: answer.reason,
            idempotency_key: crypto.randomUUID(),
          });
          setSelectedIds([]);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const detailTabs = [
    { id: "requirement", label: "Yêu cầu" },
    { id: "history", label: "Lịch sử và rà soát" },
  ];
  const activeDetailTab = detailTabs.some((item) => item.id === detailTab)
    ? detailTab
    : detailTabs[0].id;
  if (!documentsView && !sectionKey && searchParams.get("view") === "links" && can("trace.read")) {
    return <TraceabilityPage project={project} embedded />;
  }
  if (creating) {
    return (
      <WorkspacePage
        title="Tạo yêu cầu"
        actions={
          <>
            <button
              className="secondary-button"
              type="button"
              disabled={saving}
              onClick={() =>
                window.location.assign(
                  projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements),
                )
              }
            >
              Hủy
            </button>
            <button
              className="secondary-button"
              type="submit"
              form="requirement-create-form"
              name="save_mode"
              value="draft"
              formNoValidate
              disabled={saving || !projectDataReady || !can("requirement.create")}
            >
              Lưu nháp
            </button>
            <button
              className="apple-button"
              type="submit"
              form="requirement-create-form"
              name="save_mode"
              value="ready"
              disabled={saving || !projectDataReady || !can("requirement.create")}
            >
              {saving ? "Đang lưu" : "Lưu yêu cầu"}
            </button>
          </>
        }
      >
        {projectDataReady && can("requirement.create") ? (
          <RequirementCreateModal
            error={error}
            form={form}
            setForm={setForm}
            customFields={customFields}
            onSubmit={create}
          />
        ) : (
          <p>Đang tải dữ liệu hoặc bạn không có quyền tạo yêu cầu.</p>
        )}
      </WorkspacePage>
    );
  }
  return (
    <WorkspacePage
      title={
        documentsView
          ? "Tài liệu dự án"
          : routeSelected
            ? current?.title || selected.requirement_key
            : "Yêu cầu"
      }
      description={
        routeSelected
          ? `${selected.requirement_key}${current?.version ? ` · Phiên bản ${current.version}` : ""}`
          : undefined
      }
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {!routeSelected &&
            projectDataReady &&
            documentsView &&
            can("requirement_document.upload") && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setError("");
                  setImporting(true);
                }}
              >
                Nhập tài liệu
              </button>
            )}
          {!routeSelected && projectDataReady && !workspaceView && can("trace.read") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                window.location.assign(
                  `${projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements)}?view=links`,
                );
              }}
            >
              Liên kết kiểm thử
            </button>
          )}
          {!routeSelected && projectDataReady && !workspaceView && can("requirement.create") && (
            <button
              type="button"
              className="apple-button"
              onClick={() => {
                setError("");
                window.location.assign(
                  projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements, "new"),
                );
              }}
            >
              Tạo yêu cầu
            </button>
          )}
        </div>
      }
    >
      {pendingExtractionDocumentId && pendingExtractionProjectId === project._id && (
        <div className="status-banner" role="status" aria-live="polite">
          Tài liệu đã được lưu. Đang phân tích và chuẩn bị bản xem trước; bạn có thể rời trang, hệ
          thống vẫn tiếp tục xử lý.
        </div>
      )}
      {error && !importing && !creating && (
        <div className="space-y-2">
          <ErrorState message={error} />
          {!projectDataReady && (
            <button
              aria-label="Tải lại yêu cầu"
              className="icon-button h-9 w-9"
              title="Tải lại yêu cầu"
              type="button"
              onClick={() => void load()}
            >
              <RefreshCw aria-hidden="true" size={16} />
            </button>
          )}
        </div>
      )}
      {routeSelected ? (
        <>
          <SegmentedTabs
            label="Nội dung yêu cầu"
            value={activeDetailTab}
            onChange={setDetailTab}
            tabs={detailTabs}
          />
          <div className="space-y-6" hidden={activeDetailTab !== "requirement"}>
            <RequirementCurrentVersionPanel
              projectId={project._id}
              current={current}
              currentUserId={user?._id || user?.id || project.current_membership?.user_id}
              canSelfApprove={project.can_self_approve}
              selected={routeSelected}
              focusAcceptanceCriterionId={focusAcceptanceCriterionId}
              draft={draft}
              members={visibleMembers}
              customFields={customFields}
              saveState={saveState}
              can={can}
              saveDraft={saveDraft}
              onCreateVersion={createVersion}
              onSplit={splitBaseline}
              ask={ask}
              reload={load}
              onDraftChange={changeDraft}
              onError={setError}
            />
            {can("testcase.read") && <RequirementImpactPanel version={current} project={project} />}
            <RequirementHistoryPanel
              projectId={project._id}
              selected={routeSelected}
              versions={versions.map((version) =>
                version._id === current._id ? current : version,
              )}
              compareFrom={compareFrom}
              setCompareFrom={setCompareFrom}
              compareTo={compareTo}
              setCompareTo={setCompareTo}
              comparison={comparison}
              setComparison={setComparison}
              onError={setError}
            />
            {can("requirement_document.read") && (
              <RequirementTracePanel current={current} sourceDocuments={visibleSourceDocuments} />
            )}
          </div>
          <div className="space-y-6" hidden={activeDetailTab !== "history"}>
            <RequirementHistoryPanel
              projectId={project._id}
              selected={routeSelected}
              versions={versions}
              compareFrom={compareFrom}
              setCompareFrom={setCompareFrom}
              compareTo={compareTo}
              setCompareTo={setCompareTo}
              comparison={comparison}
              setComparison={setComparison}
              onError={setError}
            />
            <ReviewCommentsPanel
              projectId={project._id}
              artifactType="requirement_version"
              artifactId={current._id}
              permissions={project.current_permissions || []}
              currentUserId={project.current_membership?.user_id}
            />
            <CollaborationPanel
              project={project}
              artifactType="requirement"
              artifactId={routeSelected._id}
              onResolved={load}
            />
          </div>
        </>
      ) : (
        <>
          {!documentsView && (
            <RequirementsListPanel
              projectId={project._id}
              loading={loading}
              items={visibleItems}
              query={query}
              setQuery={setQuery}
              filters={filters}
              setFilters={setFilters}
              setPage={setPage}
              members={visibleMembers}
              selectedIds={selectedIds}
              setSelectedIds={setSelectedIds}
              pageInfo={projectDataReady ? pageInfo : null}
              pageSize={pageSize}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
              can={workspaceView ? () => false : can}
              onBulkTags={bulkUpdateTags}
              onScanDuplicates={scanDuplicates}
              onMerge={mergeBaselines}
              onBulkArchive={bulkArchiveRequirements}
              onSelect={(item) => {
                window.location.assign(
                  projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements, item._id),
                );
              }}
              title="Danh sách yêu cầu"
            />
          )}
          {!workspaceView && <RequirementDuplicatePanel result={duplicateScan} />}
          {documentsView && can("requirement_document.read") && (
            <RequirementSourceDocumentsPanel
              projectId={project._id}
              projectLocale={project.locale}
              userLocale={user?.locale}
              items={visibleSourceDocuments}
              members={visibleMembers}
              can={can}
              currentUserId={user?._id || user?.id || ""}
              isPlatformAdmin={user?.system_role === "ADMIN"}
              ask={ask}
              reload={load}
              onError={setError}
            />
          )}
          <div className="grid gap-5 xl:grid-cols-2">
            {can("requirement_document.upload") && (
              <RequirementImportModal
                isOpen={importing && projectDataReady}
                onClose={() => setImporting(false)}
                error={error}
                upload={upload}
                setUpload={setUpload}
                uploadAccess={uploadAccess}
                setUploadAccess={setUploadAccess}
                members={visibleMembers}
                onUploadPreview={uploadPreview}
                sourceProcessing={
                  uploadingSource || retryingSource || Boolean(pendingExtractionDocumentId)
                }
                sourceDocument={sourceDocument}
                onRetrySource={retrySourceDocument}
                project={project}
                sourceDocuments={visibleSourceDocuments}
                onError={setError}
              />
            )}
          </div>
        </>
      )}
      {dialog}
    </WorkspacePage>
  );
}
