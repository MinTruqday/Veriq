"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import {
  createInitialRequirementForm,
  parseAcceptanceCriteria,
  parseCommaValues,
  splitRequirementBlocks,
} from "./requirements/requirements.model";

export default function RequirementsPage({ project, section }) {
  const { ask, dialog } = useActionDialog();
  const requirementId = section[0] && !["new", "import"].includes(section[0]) ? section[0] : "";
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [customFields, setCustomFields] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [selected, setSelected] = useState(null);
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
  const [checkingWithAi, setCheckingWithAi] = useState(false);
  const [importValue, setImportValue] = useState({
    filename: "requirements.md",
    format: "md",
    content: textDoc(""),
    visibility: "private",
    shared_with: [],
    ai_enabled: false,
    source_type: "SRS",
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
  });
  const [sourceDocument, setSourceDocument] = useState(null);
  const [sourceDocuments, setSourceDocuments] = useState([]);
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
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const values = await testingApi.listRequirementPage(project._id, {
        q: query,
        ...filters,
        page,
        page_size: 50,
      });
      setItems(values.items);
      setPageInfo(values);
      setCustomFields(await testingApi.listRequirementFields(project._id));
      if (project.current_permissions?.includes("project.members.read")) {
        setMembers(
          (await testingApi.listMembers(project._id)).filter((item) => item.status === "ACTIVE"),
        );
      }
      if (project.current_permissions?.includes("requirement_document.read")) {
        setSourceDocuments(await testingApi.listRequirementDocuments(project._id));
      }
      if (requirementId) {
        const detail = await testingApi.getRequirement(requirementId);
        setSelected(detail);
        const history = await testingApi.listRequirementVersions(requirementId);
        setVersions(history);
        setCompareFrom(history[1]?._id || history[0]?._id || "");
        setCompareTo(history[0]?._id || "");
      }
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [filters, page, project._id, project.current_permissions, query, requirementId]);
  const can = useCallback(
    (permission) => project.current_permissions?.includes(permission),
    [project.current_permissions],
  );
  useEffect(() => {
    void load();
  }, [load]);
  const current = selected?.current_version;
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
  const review = async (action) => {
    const answer = await ask({
      title: action === "approve" ? "Phê duyệt yêu cầu" : "Rà soát yêu cầu",
      description: `${selected.requirement_key} phiên bản ${current.version}`,
      confirmLabel: action === "changes" ? "Yêu cầu chỉnh sửa" : "Xác nhận",
      fields: [
        {
          name: "note",
          label: action === "changes" ? "Nội dung cần chỉnh sửa" : "Ghi chú rà soát",
          initialValue:
            action === "changes"
              ? "Cần cập nhật theo nhận xét rà soát"
              : "Đã rà soát nội dung và nguồn",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
    });
    if (!answer) return;
    try {
      const saved = await saveDraft();
      const savedVersion = saved?.current_version || current;
      const payload = { expected_revision: savedVersion.revision, review_note: answer.note };
      if (action === "submit") {
        await testingApi.submitRequirementReview(project._id, selected._id, payload);
      } else if (action === "changes") {
        await testingApi.requestRequirementChanges(project._id, selected._id, payload);
      } else {
        await testingApi.approveRequirement(project._id, selected._id, payload);
      }
      await load();
    } catch (reason) {
      if (reason?.code === "REQUIREMENT_LINT_BLOCKED") {
        setLint({
          valid: false,
          degraded_mode: null,
          findings: reason.details?.findings || [],
          suggestions: [],
        });
        setError("Yêu cầu còn nội dung bắt buộc cần hoàn thiện trước khi gửi rà soát");
      } else {
        setError(messageOf(reason));
      }
    }
  };
  const saveDraft = async () => {
    if (!draftDirty && saveState === "saved") return selected;
    return (await persistDraft(draft, draftSequence.current)) || selected;
  };
  const createVersion = async () => {
    const answer = await ask({
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
    });
    if (!answer) return;
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
    } catch (reasonValue) {
      setError(messageOf(reasonValue));
    }
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
    try {
      const document = await testingApi.createRequirementDocument(project._id, importValue);
      rememberSourceDocument(document);
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
      rememberSourceDocument(await testingApi.getRequirementDocument(document._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const confirmImport = async () => {
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
      setPreview(null);
      setSelectedIndexes([]);
      setImporting(false);
      await load();
    } catch (reason) {
      setError(
        reason?.code === "IMPORT_REQUIREMENT_KEY_CONFLICT"
          ? "Mã yêu cầu đã tồn tại trong dự án hoặc trùng với mục đang nhập  Hãy sửa mã trong bản xem trước hoặc bỏ chọn mục trùng"
          : messageOf(reason),
      );
    }
  };
  const resolveImportMatch = async (candidateIndex, match, action) => {
    const candidate = preview?.preview?.[candidateIndex];
    if (!candidate || !match.requirement_id) return;
    const answer = await ask({
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
    });
    if (!answer) return;
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
      setError(messageOf(reason));
    }
  };
  const uploadPreview = async (event) => {
    event.preventDefault();
    if (!upload) return;
    const extension = upload.name.split(".").pop().toLowerCase();
    const format =
      ["json", "yaml", "yml"].includes(extension) && uploadAccess.source_type === "API_SPEC"
        ? uploadAccess.api_format || "openapi"
        : extension;
    try {
      const document = await testingApi.uploadRequirementDocument(
        project._id,
        upload,
        format,
        uploadAccess,
      );
      rememberSourceDocument(document);
      if (document.status === "PARSE_FAILED") {
        setPreview(null);
        setError("Tệp gốc đã được lưu nhưng bộ phân tích không đọc được nội dung");
        return;
      }
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
      rememberSourceDocument(await testingApi.getRequirementDocument(document._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const retrySourceDocument = async () => {
    try {
      const document = await testingApi.retryRequirementDocumentParse(
        sourceDocument._id,
        sourceDocument.revision,
      );
      rememberSourceDocument(document);
      if (document.status !== "READY") {
        setError("Bộ phân tích vẫn chưa đọc được tệp gốc");
        return;
      }
      const result = await testingApi.extractRequirementDocument(
        document._id,
        `source-${document.content_hash}`,
      );
      setPreview(result);
      setSelectedIndexes(result.preview.map((_, index) => index));
    } catch (reason) {
      setError(messageOf(reason));
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
    try {
      const result = await testingApi.updateRequirementImport(preview._id, {
        expected_revision: preview.revision,
        preview: nextPreview,
        review_note: reviewNote,
      });
      setPreview(result);
      setSelectedIndexes(nextSelection.filter((index) => index < result.preview.length));
    } catch (reason) {
      setError(messageOf(reason));
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
    try {
      const result = await testingApi.mergeRequirementCandidates(preview._id, {
        expected_revision: preview.revision,
        candidate_ids: candidates.map((candidate) => candidate.candidate_id),
        merged,
        reason: "Gộp các ứng viên yêu cầu",
      });
      setPreview(result);
      setSelectedIndexes([firstIndex]);
    } catch (reason) {
      setError(messageOf(reason));
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
      setPreview(result);
      setSelectedIndexes(split.map((_, offset) => index + offset));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const rejectCandidate = async () => {
    if (selectedIndexes.length !== 1) {
      setError("Cần chọn đúng một ứng viên để từ chối");
      return;
    }
    const index = selectedIndexes[0];
    const candidate = preview.preview[index];
    const answer = await ask({
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
    });
    if (!answer) return;
    try {
      const result = await testingApi.rejectRequirementCandidate(
        preview._id,
        candidate.candidate_id,
        { expected_revision: preview.revision, reason: answer.reason },
      );
      setPreview(result);
      setSelectedIndexes([]);
    } catch (reason) {
      setError(messageOf(reason));
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
      defaultParts = [sourceText, "Nội dung yêu cầu mới cần hoàn thiện"];
    }
    const currentCriteria = (current.acceptance_criteria || []).map((item) =>
      docText(item.content_doc),
    );
    const answer = await ask({
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
            .map(
              (_, index) =>
                currentCriteria[index] || currentCriteria[0] || "Cần bổ sung tiêu chí chấp nhận",
            )
            .join("\n---\n"),
          required: true,
          multiline: true,
        },
        {
          name: "reason",
          label: "Lý do tách",
          initialValue: "Tách các trách nhiệm nghiệp vụ độc lập để quản lý và truy vết chính xác",
          required: true,
          multiline: true,
        },
      ],
    });
    if (!answer) return;
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
      setError("Số tên nội dung và nhóm tiêu chí phải bằng nhau và có ít nhất hai phần");
      return;
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
      setError(messageOf(reason));
    }
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
    const answer = await ask({
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
    });
    if (!answer) return;
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
        merged ? `/du-an/${project._id}/yeu-cau/${merged._id}` : `/du-an/${project._id}/yeu-cau`,
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
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
    const answer = await ask({
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
    });
    if (!answer) return;
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
      setError(messageOf(reason));
    }
  };
  const bulkArchiveRequirements = async () => {
    const answer = await ask({
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
    });
    if (!answer) return;
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
      setError(messageOf(reason));
    }
  };
  return (
    <WorkspacePage
      title={selected ? `${selected.requirement_key} ${current?.title || ""}` : "Yêu cầu"}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {!selected && can("requirement_document.upload") && (
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
          {!selected && can("requirement.create") && (
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
      {error && !importing && <ErrorState message={error} />}
      {selected ? (
        <>
          <RequirementCurrentVersionPanel
            current={current}
            selected={selected}
            draft={draft}
            members={members}
            customFields={customFields}
            saveState={saveState}
            can={can}
            checkingWithAi={checkingWithAi}
            onCheckingChange={setCheckingWithAi}
            onLint={setLint}
            onError={setError}
            saveDraft={saveDraft}
            onCreateVersion={createVersion}
            onSplit={splitBaseline}
            ask={ask}
            reload={load}
            onReview={review}
            onDraftChange={changeDraft}
          />
          <RequirementTracePanel current={current} sourceDocuments={sourceDocuments} />
          <RequirementQualityPanel
            lint={lint}
            current={current}
            selected={selected}
            can={can}
            onSelectedChange={setSelected}
            onLintChange={setLint}
            onError={setError}
          />
          <RequirementHistoryPanel
            projectId={project._id}
            selected={selected}
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
          />
          {project.current_permissions?.includes("reviewsession.read") && (
            <FormalReviewPanel
              project={project}
              artifactType="REQUIREMENT"
              artifactId={selected._id}
              artifactVersionId={current._id}
              reviewType="REQUIREMENT_REVIEW"
            />
          )}
          <CollaborationPanel
            project={project}
            artifactType="requirement"
            artifactId={selected._id}
            onResolved={load}
          />
        </>
      ) : (
        <>
          <RequirementsListPanel
            projectId={project._id}
            loading={loading}
            items={items}
            query={query}
            setQuery={setQuery}
            filters={filters}
            setFilters={setFilters}
            setPage={setPage}
            members={members}
            selectedIds={selectedIds}
            setSelectedIds={setSelectedIds}
            pageInfo={pageInfo}
            can={can}
            onBulkTags={bulkUpdateTags}
            onScanDuplicates={scanDuplicates}
            onMerge={mergeBaselines}
            onBulkArchive={bulkArchiveRequirements}
          />
          <RequirementDuplicatePanel result={duplicateScan} />
          {can("requirement_document.read") && (
            <RequirementSourceDocumentsPanel
              items={sourceDocuments}
              members={members}
              can={can}
              ask={ask}
              reload={load}
              onError={setError}
            />
          )}
          <div className="grid gap-5 xl:grid-cols-2">
            {can("requirement.create") && (
              <RequirementCreateModal
                isOpen={creating}
                onClose={() => setCreating(false)}
                error={error}
                form={form}
                setForm={setForm}
                members={members}
                customFields={customFields}
                saving={saving}
                onSubmit={create}
              />
            )}
            {can("requirement_document.upload") && (
              <RequirementImportModal
                isOpen={importing}
                onClose={() => setImporting(false)}
                error={error}
                upload={upload}
                setUpload={setUpload}
                uploadAccess={uploadAccess}
                setUploadAccess={setUploadAccess}
                members={members}
                onUploadPreview={uploadPreview}
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
                sourceDocuments={sourceDocuments}
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
