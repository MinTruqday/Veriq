"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import ReviewCommentsPanel from "../../components/ReviewCommentsPanel";
import FormalReviewPanel from "../../components/FormalReviewPanel";
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
import RequirementImportModal from "./requirements/RequirementImportModal";
import RequirementQualityPanel from "./requirements/RequirementQualityPanel";
import RequirementSourceDocumentsPanel from "./requirements/RequirementSourceDocumentsPanel";
import RequirementTracePanel from "./requirements/RequirementTracePanel";
import RequirementsListPanel from "./requirements/RequirementsListPanel";
import TestAdequacyPanel from "./design/TestAdequacyPanel";
import RequirementClarificationPanel from "./requirements/RequirementClarificationPanel";
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
  const { ask, dialog } = useActionDialog();
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const sectionKey = section[0] || "";
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
  const [creating, setCreating] = useState(false);
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
  const [pageInfo, setPageInfo] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [lint, setLint] = useState(null);
  const [importValue, setImportValue] = useState({
    filename: "requirements.md",
    format: "md",
    content: textDoc(""),
    visibility: "private",
    shared_with: [],
    ai_enabled: false,
    source_type: "SRS",
    supersedes_document_id: null,
  });
  const [preview, setPreview] = useState(null);
  const [selectedIndexes, setSelectedIndexes] = useState([]);
  const [importComparison, setImportComparison] = useState(null);
  const [separateIndexes, setSeparateIndexes] = useState([]);
  const [separateReasons, setSeparateReasons] = useState({});
  const [upload, setUpload] = useState(null);
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
  const clearImportPreview = () => {
    setPreview(null);
    setSelectedIndexes([]);
    setImportComparison(null);
    setSeparateIndexes([]);
    setSeparateReasons({});
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
    if (!preview?._id || preview.status !== "PREVIEW_READY") {
      setImportComparison(null);
      setSeparateIndexes([]);
      setSeparateReasons({});
      return;
    }
    let active = true;
    setImportComparison(null);
    setSeparateIndexes([]);
    setSeparateReasons({});
    testingApi.compareRequirementImport(preview._id).then(
      (value) => {
        if (active) setImportComparison(value);
      },
      (reason) => {
        if (active) setError(messageOf(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [preview?._id, preview?.revision, preview?.status]);
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
        setSourceDocument(document);
        setSourceDocuments((items) => [
          document,
          ...items.filter((item) => item._id !== document._id),
        ]);
        if (document.status === "READY") {
          try {
            const result = await testingApi.extractRequirementDocument(
              document._id,
              `source-${document.content_hash}`,
            );
            if (active) {
              setPreview(result);
              setSelectedIndexes(result.preview.map((_, index) => index));
              setError("");
              rememberPendingExtraction("");
            }
          } catch (reason) {
            if (active) {
              setError(messageOf(reason));
              rememberPendingExtraction("");
            }
          }
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
      const values = await testingApi.listRequirementPage(requestedProjectId, {
        q: query,
        ...filters,
        page,
        page_size: 50,
      });
      if (sequence !== loadSequence.current) return;
      setItems(values.items);
      setPageInfo(values);
      const fields = await testingApi.listRequirementFields(requestedProjectId);
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
  }, [filters, page, project._id, project.current_permissions, query, requirementId]);
  const can = useCallback(
    (permission) => project.current_permissions?.includes(permission),
    [project.current_permissions],
  );
  const routeSelected = selectedContextKey === `${project._id}:${requirementId}` ? selected : null;
  const projectDataReady = loadedProjectId === project._id;
  const visibleItems = projectDataReady ? items : [];
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
    setCreating(false);
    setForm(createInitialRequirementForm());
    setPreview(null);
    setSelectedIndexes([]);
    setImportComparison(null);
    setSeparateIndexes([]);
    setSeparateReasons({});
    setUpload(null);
    setUploadAccess({
      visibility: "private",
      shared_with: [],
      ai_enabled: false,
      source_type: "SRS",
      ocr_language: "",
      supersedes_document_id: null,
    });
    setImportValue({
      filename: "requirements.md",
      format: "md",
      content: textDoc(""),
      visibility: "private",
      shared_with: [],
      ai_enabled: false,
      source_type: "SRS",
      supersedes_document_id: null,
    });
    setSourceDocument(null);
    setSourceDocuments([]);
    setPendingExtractionDocumentId("");
    setPendingExtractionProjectId(project._id);
    setError("");
  }, [project._id]);
  useEffect(() => {
    setDetailTab(
      workspaceView === "assurance"
        ? "assurance"
        : workspaceView === "clarifications"
          ? "clarifications"
          : "requirement",
    );
  }, [routeSelected?._id, workspaceView]);
  useEffect(() => {
    void load();
  }, [load]);
  const current = routeSelected?.current_version;
  useEffect(() => {
    if (!current?._id || !project.current_permissions?.includes("requirement.read")) {
      setLint(null);
      return undefined;
    }
    let active = true;
    setLint(null);
    testingApi.getLatestRequirementQualityAnalysis(current._id).then(
      (result) => {
        if (active) setLint(result || null);
      },
      (reason) => {
        if (active && reason?.status !== 404) setError(messageOf(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [current?._id, current?.revision, project.current_permissions]);
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
      risk: current.risk,
      content_doc: current.content_doc,
      acceptance: (current.acceptance_criteria || [])
        .map((item) => docText(item.content_doc))
        .join("\n"),
      businessRules: (current.business_rules || []).join("\n"),
      actors: (current.actors || []).join(", "),
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
                risk: snapshot.risk,
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
                actors: snapshot.actors
                  .split(",")
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
    setSaving(true);
    setError("");
    try {
      await testingApi.createRequirement(project._id, {
        title: form.title,
        type: form.type,
        priority: form.priority,
        risk: form.risk,
        content_doc: form.content_doc,
        acceptance_criteria: criteria,
        business_rules: form.businessRules
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        actors: form.actors
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        dependencies: form.dependencies
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        source_refs: [],
        tags: form.tags
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        owner_id: form.ownerId.trim() || null,
        custom_values: form.customValues,
      });
      setForm(createInitialRequirementForm());
      setCreating(false);
      await load();
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
      title: "Tạo phiên bản yêu cầu mới",
      description: `${selected.requirement_key} sẽ giữ nguyên phiên bản chuẩn hiện tại để truy vết`,
      confirmLabel: "Tạo phiên bản",
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
          label: "Lý do thay đổi",
          initialValue: "Cập nhật quy tắc nghiệp vụ",
          required: true,
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
            risk: current.risk,
            content_doc: current.content_doc,
            acceptance_criteria: (current.acceptance_criteria || []).map((item) => ({
              key: item.key,
              content_doc: item.content_doc,
              status: item.status,
            })),
            business_rules: current.business_rules || [],
            actors: current.actors || [],
            dependencies: current.dependencies || [],
            source_refs: current.source_refs || [],
            tags: selected.tags || current.tags || [],
            owner_id: selected.owner_id || current.owner_id || null,
            details: current.details || {},
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
  const importPreview = async (event) => {
    event.preventDefault();
    if (
      !(
        typeof importValue.content === "string" ? importValue.content : docText(importValue.content)
      ).trim()
    ) {
      setError("Nhập nội dung tài liệu trước khi tạo bản xem trước");
      return;
    }
    clearImportPreview();
    const requestedProjectId = project._id;
    try {
      const document = await testingApi.createRequirementDocument(requestedProjectId, importValue);
      if (activeProjectId.current !== requestedProjectId) return;
      rememberSourceDocument(document);
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
      const refreshedDocument = await testingApi.getRequirementDocument(document._id);
      if (activeProjectId.current === requestedProjectId) rememberSourceDocument(refreshedDocument);
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    }
  };
  const confirmImport = async () => {
    const requestedProjectId = project._id;
    try {
      if (!importComparison || importComparison.revision !== preview.revision) {
        setError("Cần đối chiếu với yêu cầu hiện có trước khi xác nhận nhập");
        return;
      }
      const activeSeparateIndexes = separateIndexes.filter(
        (index) =>
          selectedIndexes.includes(index) &&
          importComparison.comparisons?.some(
            (entry) =>
              entry.candidate_index === index &&
              entry.matches.some(
                (match) =>
                  !["IN_IMPORT", "SAME_KEY_IN_IMPORT"].includes(match.match_type) ||
                  selectedIndexes.includes(match.candidate_index),
              ),
          ),
      );
      await testingApi.confirmRequirementImport(
        preview._id,
        selectedIndexes,
        preview.revision,
        activeSeparateIndexes,
        Object.fromEntries(
          Object.entries(separateReasons).filter(([index]) =>
            activeSeparateIndexes.includes(Number(index)),
          ),
        ),
      );
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(null);
      setSelectedIndexes([]);
      setImporting(false);
      await load();
    } catch (reason) {
      if (activeProjectId.current !== requestedProjectId) return;
      setError(
        reason?.code === "IMPORT_REQUIREMENT_KEY_CONFLICT"
          ? "Mã yêu cầu đã tồn tại trong dự án hoặc trùng với mục đang nhập. Hãy sửa mã trong bản xem trước hoặc bỏ chọn mục trùng."
          : messageOf(reason),
      );
    }
  };
  const resolveImportMatch = async (candidateIndex, match, action) => {
    const candidate = preview?.preview?.[candidateIndex];
    if (!candidate || !match.requirement_id) return;
    await ask({
      title:
        action === "link_source" ? "Gắn nguồn vào yêu cầu hiện có" : "Tạo phiên bản yêu cầu mới",
      description:
        action === "link_source"
          ? `Gắn nguồn của ${candidate.title} vào ${match.requirement_key || match.title} mà không đổi nội dung`
          : `Tạo bản nháp mới cho ${match.requirement_key || match.title} từ đúng nội dung ứng viên ${candidate.title}  Trường không có trong ứng viên sẽ để trống  Phiên bản cũ vẫn được lưu`,
      confirmLabel: action === "link_source" ? "Gắn nguồn" : "Tạo phiên bản nháp",
      fields: [
        {
          name: "reason",
          label: "Lý do đối chiếu",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const selectedCandidateIds = new Set(
            selectedIndexes.map((index) => preview.preview[index]?.candidate_id).filter(Boolean),
          );
          const updated = await testingApi.resolveRequirementImportCandidate(
            preview._id,
            candidate.candidate_id,
            {
              expected_revision: preview.revision,
              target_requirement_id: match.requirement_id,
              expected_target_version_id: match.version_id,
              action,
              reason: answer.reason,
            },
          );
          setPreview(updated);
          setSelectedIndexes(
            updated.preview.flatMap((item, index) =>
              selectedCandidateIds.has(item.candidate_id) ? [index] : [],
            ),
          );
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const uploadPreview = async (event) => {
    event.preventDefault();
    if (!upload || uploadingSource || pendingExtractionDocumentId) return;
    clearImportPreview();
    setUploadingSource(true);
    const requestedProjectId = project._id;
    const extension = upload.name.split(".").pop().toLowerCase();
    const format =
      ["json", "yaml", "yml"].includes(extension) && uploadAccess.source_type === "API_SPEC"
        ? uploadAccess.api_format || "openapi"
        : extension;
    try {
      const document = await testingApi.uploadRequirementDocument(
        requestedProjectId,
        upload,
        format,
        uploadAccess,
      );
      if (activeProjectId.current !== requestedProjectId) return;
      rememberSourceDocument(document);
      if (document.status === "PARSE_FAILED") {
        setPreview(null);
        setError(
          document.parse_error_type === "TimeoutError"
            ? "Đã hết thời gian phân tích tài liệu; tệp gốc vẫn được lưu để bạn thử lại."
            : "Tệp gốc đã được lưu nhưng bộ phân tích không đọc được nội dung",
        );
        return;
      }
      if (document.status !== "READY") {
        setPreview(null);
        setError("");
        rememberPendingExtraction(document._id);
        return;
      }
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
      const refreshedDocument = await testingApi.getRequirementDocument(document._id);
      if (activeProjectId.current === requestedProjectId) rememberSourceDocument(refreshedDocument);
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    } finally {
      if (activeProjectId.current === requestedProjectId) setUploadingSource(false);
    }
  };
  const retrySourceDocument = async () => {
    if (!sourceDocument || retryingSource) return;
    clearImportPreview();
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
        setError(
          document.parse_error_type === "TimeoutError"
            ? "Đã hết thời gian phân tích tài liệu; bạn có thể thử lại."
            : "Bộ phân tích vẫn chưa đọc được tệp gốc",
        );
        return;
      }
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
      setError("");
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    } finally {
      if (activeProjectId.current === requestedProjectId) setRetryingSource(false);
    }
  };
  const editCandidate = (index, patch) => {
    setImportComparison(null);
    setSeparateIndexes([]);
    setSeparateReasons({});
    setPreview((value) => ({
      ...value,
      preview: value.preview.map((candidate, candidateIndex) =>
        candidateIndex === index ? { ...candidate, ...patch } : candidate,
      ),
    }));
  };
  const saveImportReview = async (nextPreview, reviewNote, nextSelection = selectedIndexes) => {
    const requestedProjectId = project._id;
    try {
      const result = await testingApi.updateRequirementImport(preview._id, {
        expected_revision: preview.revision,
        preview: nextPreview,
        review_note: reviewNote,
      });
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes(nextSelection.filter((index) => index < result.preview.length));
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    }
  };
  const mergeCandidates = async () => {
    const indexes = [...selectedIndexes].sort((left, right) => left - right);
    if (indexes.length < 2) {
      setError("Cần chọn ít nhất hai ứng viên để gộp");
      return;
    }
    const candidates = indexes.map((index) => preview.preview[index]);
    const firstIndex = indexes[0];
    const merged = {
      ...candidates[0],
      title: candidates
        .map((candidate) => candidate.title)
        .join(" và ")
        .slice(0, 300),
      content_doc: textDoc(
        candidates.map((candidate) => docText(candidate.content_doc)).join("\n\n"),
      ),
      acceptance_criteria: candidates.flatMap((candidate) => candidate.acceptance_criteria || []),
      business_rules: [
        ...new Set(candidates.flatMap((candidate) => candidate.business_rules || [])),
      ],
      actors: [...new Set(candidates.flatMap((candidate) => candidate.actors || []))],
      dependencies: [...new Set(candidates.flatMap((candidate) => candidate.dependencies || []))],
      source_refs: candidates.flatMap((candidate) => candidate.source_refs || []),
      candidate_relation: "merged",
    };
    const requestedProjectId = project._id;
    try {
      const result = await testingApi.mergeRequirementCandidates(preview._id, {
        expected_revision: preview.revision,
        candidate_ids: candidates.map((candidate) => candidate.candidate_id),
        merged,
        reason: "Gộp các ứng viên yêu cầu",
      });
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes([firstIndex]);
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    }
  };
  const splitCandidate = async () => {
    if (selectedIndexes.length !== 1) {
      setError("Cần chọn đúng một ứng viên để tách");
      return;
    }
    const index = selectedIndexes[0];
    const candidate = preview.preview[index];
    const sourceText = docText(candidate.content_doc).trim();
    let parts = sourceText
      .split(/\n+/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length < 2) {
      parts = (sourceText.match(/[^.!?;]+[.!?;]?/g) || [])
        .map((part) => part.trim())
        .filter(Boolean);
    }
    if (parts.length < 2) {
      setError("Nội dung cần ít nhất hai dòng hoặc hai câu để tách");
      return;
    }
    const split = parts.map((part) => ({
      ...candidate,
      title: part.slice(0, 300),
      content_doc: textDoc(part),
    }));
    const requestedProjectId = project._id;
    try {
      const result = await testingApi.splitRequirementCandidate(
        preview._id,
        candidate.candidate_id,
        {
          expected_revision: preview.revision,
          drafts: split,
          reason: "Tách ứng viên yêu cầu",
        },
      );
      if (activeProjectId.current !== requestedProjectId) return;
      setPreview(result);
      setSelectedIndexes(split.map((_, offset) => index + offset));
    } catch (reason) {
      if (activeProjectId.current === requestedProjectId) setError(messageOf(reason));
    }
  };
  const rejectCandidate = async () => {
    if (selectedIndexes.length !== 1) {
      setError("Cần chọn đúng một ứng viên để từ chối");
      return;
    }
    const index = selectedIndexes[0];
    const candidate = preview.preview[index];
    await ask({
      title: "Từ chối ứng viên yêu cầu",
      description: candidate.title,
      confirmLabel: "Từ chối ứng viên",
      danger: true,
      fields: [
        {
          name: "reason",
          label: "Lý do",
          initialValue: "Không thuộc phạm vi hoặc không tạo thành yêu cầu độc lập",
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const result = await testingApi.rejectRequirementCandidate(
            preview._id,
            candidate.candidate_id,
            { expected_revision: preview.revision, reason: answer.reason },
          );
          setPreview(result);
          setSelectedIndexes([]);
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
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
              risk: current.risk,
              content_doc: textDoc(content),
              acceptance_criteria: parseAcceptanceCriteria(criteriaBlocks[index]),
              business_rules: current.business_rules || [],
              actors: current.actors || [],
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
          options: [
            { value: "functional", label: "Chức năng" },
            { value: "non_functional", label: "Phi chức năng" },
            { value: "business_rule", label: "Quy tắc nghiệp vụ" },
            { value: "api", label: "API" },
            { value: "ui", label: "Giao diện" },
            { value: "data", label: "Dữ liệu" },
            { value: "permission", label: "Phân quyền" },
            { value: "integration", label: "Tích hợp" },
            { value: "constraint", label: "Ràng buộc" },
          ],
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
              risk: sources[0].current_version.risk,
              content_doc: textDoc(answer.content),
              acceptance_criteria: parseAcceptanceCriteria(answer.acceptance),
              business_rules: [
                ...new Set(sources.flatMap((item) => item.current_version.business_rules || [])),
              ],
              actors: [...new Set(sources.flatMap((item) => item.current_version.actors || []))],
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
    ...(can("testcase.read") ? [{ id: "assurance", label: "Hồ sơ đảm bảo" }] : []),
    ...(can("requirement.read") ? [{ id: "clarifications", label: "Phiếu làm rõ" }] : []),
    { id: "history", label: "Lịch sử và rà soát" },
  ];
  const activeDetailTab = detailTabs.some((item) => item.id === detailTab)
    ? detailTab
    : detailTabs[0].id;
  return (
    <WorkspacePage
      title={
        routeSelected
          ? current?.title || selected.requirement_key
          : workspaceView === "assurance"
            ? "Hồ sơ đảm bảo yêu cầu"
            : workspaceView === "clarifications"
              ? "Phiếu làm rõ yêu cầu"
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
            !workspaceView &&
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
          {!routeSelected && projectDataReady && !workspaceView && can("requirement.create") && (
            <button
              type="button"
              className="apple-button"
              onClick={() => {
                setError("");
                setCreating(true);
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
            <button type="button" className="secondary-button" onClick={() => void load()}>
              Tải lại yêu cầu
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
              current={current}
              selected={routeSelected}
              draft={draft}
              members={visibleMembers}
              customFields={customFields}
              saveState={saveState}
              can={can}
              onError={setError}
              saveDraft={saveDraft}
              onCreateVersion={createVersion}
              onSplit={splitBaseline}
              ask={ask}
              reload={load}
              onDraftChange={changeDraft}
            />
            {can("requirement_document.read") && (
              <RequirementTracePanel current={current} sourceDocuments={visibleSourceDocuments} />
            )}
            <RequirementQualityPanel lint={lint} />
          </div>
          {can("testcase.read") && (
            <div className="space-y-6" hidden={activeDetailTab !== "assurance"}>
              <TestAdequacyPanel
                requirementVersionId={current._id}
                canDecide={memberRoles.includes("QA") && can("testcase.read")}
                canCreateClarification={memberRoles.includes("QA") && can("requirement.review")}
                canApprove={memberRoles.includes("QA") && can("testcase.review")}
                canSubmit={can("testcase.submit_review")}
              />
            </div>
          )}
          <div className="space-y-6" hidden={activeDetailTab !== "clarifications"}>
            <RequirementClarificationPanel
              requirementVersionId={current._id}
              roles={memberRoles}
              permissions={project.current_permissions || []}
            />
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
            {project.current_permissions?.includes("reviewsession.read") && (
              <FormalReviewPanel
                project={project}
                artifactType="REQUIREMENT"
                artifactId={routeSelected._id}
                artifactVersionId={current._id}
                reviewType="REQUIREMENT_REVIEW"
                readOnly
              />
            )}
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
            can={workspaceView ? () => false : can}
            onBulkTags={bulkUpdateTags}
            onScanDuplicates={scanDuplicates}
            onMerge={mergeBaselines}
            onBulkArchive={bulkArchiveRequirements}
            onSelect={(item) => {
              const sectionSlug =
                workspaceView === "assurance"
                  ? PROJECT_SECTION_SLUGS.assurance
                  : workspaceView === "clarifications"
                    ? PROJECT_SECTION_SLUGS.clarifications
                    : PROJECT_SECTION_SLUGS.requirements;
              window.location.assign(projectRoute(project._id, sectionSlug, item._id));
            }}
            title={workspaceView === "clarifications" ? "Chọn yêu cầu" : "Danh sách yêu cầu"}
          />
          {!workspaceView && <RequirementDuplicatePanel result={duplicateScan} />}
          {!workspaceView && can("requirement_document.read") && (
            <RequirementSourceDocumentsPanel
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
            {can("requirement.create") && (
              <RequirementCreateModal
                isOpen={creating && projectDataReady}
                onClose={() => setCreating(false)}
                error={error}
                form={form}
                setForm={setForm}
                members={visibleMembers}
                customFields={customFields}
                saving={saving}
                onSubmit={create}
              />
            )}
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
                importValue={importValue}
                setImportValue={setImportValue}
                onImportPreview={importPreview}
                preview={preview}
                selectedIndexes={selectedIndexes}
                setSelectedIndexes={setSelectedIndexes}
                importComparison={importComparison}
                separateIndexes={separateIndexes}
                setSeparateIndexes={setSeparateIndexes}
                separateReasons={separateReasons}
                setSeparateReasons={setSeparateReasons}
                onSaveReview={() =>
                  saveImportReview(preview.preview, "Chỉnh sửa nội dung ứng viên yêu cầu")
                }
                onSplit={splitCandidate}
                onMerge={mergeCandidates}
                onReject={rejectCandidate}
                onEditCandidate={editCandidate}
                onConfirm={confirmImport}
                onResolveMatch={resolveImportMatch}
                sourceDocument={sourceDocument}
                onRetrySource={retrySourceDocument}
                project={project}
                isPlatformAdmin={user?.system_role === "ADMIN"}
                sourceDocuments={visibleSourceDocuments}
                onTemplatePreview={(job) => {
                  setPreview(job);
                  setSelectedIndexes(job.preview.map((_, index) => index));
                }}
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
