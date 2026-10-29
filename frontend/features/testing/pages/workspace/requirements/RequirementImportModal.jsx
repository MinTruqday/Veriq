import { useRef, useState } from "react";
import DataTable from "../../../components/DataTable";
import FilePicker from "../../../components/FilePicker";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import DocumentEditor from "../../../editor/DocumentEditor";
import { docText, textDoc, valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { REQUIREMENT_IMPORT_FORMATS } from "./requirements.model";
import RequirementTemplatePanel from "./RequirementTemplatePanel";

function updateAcceptanceCriterion(criteria, index, content) {
  return criteria.map((criterion, criterionIndex) => {
    if (criterionIndex !== index) return criterion;
    const updated = { ...criterion, content_doc: textDoc(content) };
    if (docText(criterion.content_doc).trim() !== content.trim()) delete updated.source_span;
    return updated;
  });
}

function addAcceptanceCriterion(criteria) {
  const keys = new Set((criteria || []).map((criterion) => criterion.key));
  const numberedKeys = [...keys].map((key) => /^AC-(\d+)$/.exec(key || "")).filter(Boolean);
  const padding = Math.max(0, ...numberedKeys.map((match) => match[1].length));
  let index = Math.max(0, ...numberedKeys.map((match) => Number(match[1]))) + 1;
  let key = `AC-${String(index).padStart(padding, "0")}`;
  while (keys.has(key)) {
    index += 1;
    key = `AC-${String(index).padStart(padding, "0")}`;
  }
  return [...(criteria || []), { key, content_doc: textDoc(""), status: "draft" }];
}

function DocumentAccessControl({
  access,
  members,
  onChange,
  privateLabel,
  name,
  disabled = false,
}) {
  const isPublic = access.visibility !== "private";
  const updateSharedWith = (userId, checked) =>
    onChange({
      ...access,
      shared_with: checked
        ? [...access.shared_with, userId]
        : access.shared_with.filter((value) => value !== userId),
    });

  return (
    <fieldset className="space-y-3">
      <legend className="field-label">Quyền xem tài liệu</legend>
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            checked={!isPublic}
            disabled={disabled}
            name={`${name}-visibility`}
            type="radio"
            onChange={() => onChange({ ...access, visibility: "private", shared_with: [] })}
          />
          {privateLabel}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            checked={isPublic}
            disabled={disabled}
            name={`${name}-visibility`}
            type="radio"
            onChange={() =>
              onChange({
                ...access,
                visibility: access.visibility === "private" ? "project" : access.visibility,
                shared_with: access.shared_with,
              })
            }
          />
          Công khai
        </label>
      </div>
      {isPublic && (
        <fieldset className="space-y-2 rounded-control border border-border bg-surface-quiet p-3">
          <legend className="px-1 text-sm font-medium">Phạm vi công khai</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              checked={access.visibility === "project"}
              disabled={disabled}
              name={`${name}-scope`}
              type="radio"
              onChange={() => onChange({ ...access, visibility: "project", shared_with: [] })}
            />
            Tất cả thành viên dự án
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              checked={access.visibility === "shared"}
              disabled={disabled}
              name={`${name}-scope`}
              type="radio"
              onChange={() =>
                onChange({ ...access, visibility: "shared", shared_with: access.shared_with })
              }
            />
            Cá nhân
          </label>
          {access.visibility === "shared" && (
            <div className="space-y-2 border-t border-border pt-3">
              <p className="text-sm font-medium">Chọn người được xem</p>
              {members.map((member) => (
                <label className="flex items-center gap-2 text-sm" key={member.user_id}>
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={access.shared_with.includes(member.user_id)}
                    onChange={(event) => updateSharedWith(member.user_id, event.target.checked)}
                  />
                  {member.user_label ||
                    member.user?.full_name ||
                    member.user?.email ||
                    "Thành viên dự án"}
                </label>
              ))}
            </div>
          )}
        </fieldset>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(access.ai_enabled)}
          disabled={disabled || Boolean(access.ai_enabled)}
          onChange={(event) => onChange({ ...access, ai_enabled: event.target.checked })}
        />
        {access.ai_enabled
          ? "Đã cho phép AI phân tích tài liệu này"
          : "Cho phép AI phân tích tài liệu này"}
      </label>
      <p className="text-xs leading-5 text-ink-muted">
        Khi bạn tạo bản xem trước, AI có thể trích xuất yêu cầu và tiêu chí được nêu trong nguồn.
        Nếu không bật, hệ thống không chạy AI; nội dung thiếu tiêu chí sẽ được giữ là đang thiếu.
      </p>
    </fieldset>
  );
}

function SourceVersionParent({ access, documents, format, project, onChange, disabled = false }) {
  const userId = project.current_membership?.user_id;
  const parents = documents.filter(
    (item) => item.format === format && item.status !== "ARCHIVED" && item.created_by === userId,
  );
  return (
    <label className="field-label block px-5">
      Phiên bản nguồn trước (không bắt buộc)
      <select
        className="apple-input mt-2"
        value={access.supersedes_document_id || ""}
        disabled={disabled}
        onChange={(event) => {
          const parent = parents.find((item) => item._id === event.target.value);
          onChange(
            parent
              ? {
                  ...access,
                  supersedes_document_id: parent._id,
                  visibility: parent.visibility || "private",
                  shared_with: parent.shared_with || [],
                  ai_enabled: Boolean(parent.ai_enabled),
                  source_type: parent.source_type || "REFERENCE",
                  ocr_language: parent.ocr_language || "",
                }
              : { ...access, supersedes_document_id: null },
          );
        }}
      >
        <option value="">Tài liệu mới, không nối phiên bản trước</option>
        {parents.map((item) => (
          <option value={item._id} key={item._id}>
            {item.filename} · phiên bản {item.source_version || item.source_version_sequence}
          </option>
        ))}
      </select>
      <span className="mt-1 block text-xs font-normal text-ink-muted">
        Chỉ tài liệu cùng dự án do bạn sở hữu; phiên bản cũ được giữ nguyên.
      </span>
      {access.supersedes_document_id && (
        <button
          className="secondary-button mt-2"
          type="button"
          disabled={disabled}
          onClick={() => onChange({ ...access, supersedes_document_id: null })}
        >
          Hủy liên kết phiên bản nguồn
        </button>
      )}
    </label>
  );
}

export default function RequirementImportModal({
  isOpen,
  onClose,
  error,
  upload,
  setUpload,
  uploadAccess,
  setUploadAccess,
  members,
  onUploadPreview,
  sourceProcessing = false,
  importValue,
  setImportValue,
  onImportPreview,
  preview,
  selectedIndexes,
  setSelectedIndexes,
  importComparison,
  separateIndexes,
  setSeparateIndexes,
  separateReasons,
  setSeparateReasons,
  onSaveReview,
  onSplit,
  onMerge,
  onReject,
  onEditCandidate,
  onConfirm,
  onResolveMatch,
  sourceDocument,
  onRetrySource,
  project,
  isPlatformAdmin,
  sourceDocuments,
  onTemplatePreview,
  onError,
}) {
  const [confirmingImport, setConfirmingImport] = useState(false);
  const [inputMethod, setInputMethod] = useState("file");
  const confirmingImportRef = useRef(false);
  const confirmImport = async () => {
    if (confirmingImportRef.current) return;
    confirmingImportRef.current = true;
    setConfirmingImport(true);
    try {
      await onConfirm();
    } finally {
      confirmingImportRef.current = false;
      setConfirmingImport(false);
    }
  };
  const updateImportValue = (patch) => setImportValue((value) => ({ ...value, ...patch }));
  const blockingMatches = (index) =>
    importComparison?.comparisons
      ?.find((entry) => entry.candidate_index === index)
      ?.matches.filter(
        (match) =>
          !["IN_IMPORT", "SAME_KEY_IN_IMPORT"].includes(match.match_type) ||
          selectedIndexes.includes(match.candidate_index),
      ) || [];
  const keyCollision = (index) => {
    const key = preview?.preview?.[index]?.requirement_key;
    return Boolean(key && blockingMatches(index).some((match) => match.requirement_key === key));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={confirmingImport ? () => {} : onClose}
      ariaLabel="Nhập tài liệu"
      className="max-w-5xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Nhập tài liệu</ModalTitle>
      </ModalHeader>
      {error && <ErrorState message={error} />}
      <div className="border-b border-border p-5">
        <p className="field-label">Chọn cách nhập</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3" role="group" aria-label="Cách nhập yêu cầu">
          {[
            { id: "file", label: "Tải tệp lên" },
            { id: "manual", label: "Soạn nội dung" },
            { id: "template", label: "Dùng mẫu" },
          ].map((method) => (
            <button
              key={method.id}
              type="button"
              className={
                inputMethod === method.id
                  ? "min-h-10 rounded-control bg-brand px-4 py-2 text-sm font-semibold text-white"
                  : "min-h-10 rounded-control border border-border bg-surface px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-quiet hover:text-ink"
              }
              aria-pressed={inputMethod === method.id}
              onClick={() => setInputMethod(method.id)}
            >
              {method.label}
            </button>
          ))}
        </div>
      </div>
      <div hidden={inputMethod !== "template"}>
        <RequirementTemplatePanel
          key={project._id}
          project={project}
          isPlatformAdmin={isPlatformAdmin}
          members={members}
          sourceDocuments={sourceDocuments}
          onPreview={onTemplatePreview}
          onError={onError}
          isOpen={isOpen}
        />
      </div>
      <form
        hidden={inputMethod !== "file"}
        onSubmit={onUploadPreview}
        className="space-y-4 border-b border-border p-5"
      >
        <FilePicker
          label="Tệp SRS, BRD hoặc bảng yêu cầu"
          accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.json,.yaml,.yml"
          disabled={sourceProcessing}
          fileName={upload?.name || ""}
          onChange={(event) => setUpload(event.target.files?.[0] || null)}
        />
        {upload && (
          <SourceVersionParent
            access={uploadAccess}
            documents={sourceDocuments}
            format={(() => {
              const extension = upload.name.split(".").pop().toLowerCase();
              return ["json", "yaml", "yml"].includes(extension) &&
                uploadAccess.source_type === "API_SPEC"
                ? uploadAccess.api_format || "openapi"
                : extension;
            })()}
            project={project}
            onChange={setUploadAccess}
            disabled={sourceProcessing}
          />
        )}
        <label className="field-label">
          Loại tài liệu nguồn
          <select
            className="apple-input mt-2"
            value={uploadAccess.source_type || "REFERENCE"}
            disabled={sourceProcessing || Boolean(uploadAccess.supersedes_document_id)}
            onChange={(event) =>
              setUploadAccess((value) => ({ ...value, source_type: event.target.value }))
            }
          >
            <option value="SRS">Đặc tả yêu cầu</option>
            <option value="USER_STORY">Câu chuyện người dùng</option>
            <option value="API_SPEC">Định nghĩa API</option>
            <option value="REFERENCE">Tài liệu khác</option>
          </select>
        </label>
        {upload && upload.name.split(".").pop().toLowerCase() === "pdf" && (
          <label className="field-label">
            Ngôn ngữ OCR (không bắt buộc)
            <input
              className="apple-input mt-2"
              autoComplete="off"
              maxLength={32}
              placeholder="Để trống để dùng cấu hình mặc định của hệ thống"
              value={uploadAccess.ocr_language || ""}
              disabled={sourceProcessing || Boolean(uploadAccess.supersedes_document_id)}
              onChange={(event) =>
                setUploadAccess((value) => ({ ...value, ocr_language: event.target.value }))
              }
            />
            <span className="mt-1 block text-xs font-normal text-ink-muted">
              Có thể nhập mã ngôn ngữ được bộ OCR hỗ trợ, ví dụ iso:vi. Tệp gốc không bị thay đổi.
            </span>
          </label>
        )}
        {uploadAccess.source_type === "API_SPEC" && (
          <label className="field-label">
            Định dạng định nghĩa API
            <select
              className="apple-input mt-2"
              value={uploadAccess.api_format || "openapi"}
              disabled={sourceProcessing || Boolean(uploadAccess.supersedes_document_id)}
              onChange={(event) =>
                setUploadAccess((value) => ({ ...value, api_format: event.target.value }))
              }
            >
              <option value="openapi">OpenAPI</option>
              <option value="postman">Postman</option>
            </select>
          </label>
        )}
        <DocumentAccessControl
          access={uploadAccess}
          members={members}
          name="upload-document"
          privateLabel="Riêng tư chỉ người tải lên"
          disabled={sourceProcessing || Boolean(uploadAccess.supersedes_document_id)}
          onChange={setUploadAccess}
        />
        <div className="action-dialog-footer flex justify-end">
          <button
            className="secondary-button"
            type="submit"
            disabled={
              sourceProcessing ||
              !upload ||
              (uploadAccess.visibility === "shared" && !uploadAccess.shared_with.length)
            }
          >
            {sourceProcessing ? "Đang xử lý tài liệu…" : "Tải lên và xem trước"}
          </button>
        </div>
      </form>
      <form hidden={inputMethod !== "manual"} onSubmit={onImportPreview} className="space-y-4 p-5">
        <label className="field-label">
          Tên tệp
          <input
            className="apple-input mt-2"
            value={importValue.filename}
            onChange={(event) => updateImportValue({ filename: event.target.value })}
          />
        </label>
        <SourceVersionParent
          access={importValue}
          documents={sourceDocuments}
          format={importValue.format}
          project={project}
          onChange={setImportValue}
        />
        <DocumentAccessControl
          access={importValue}
          members={members}
          name="manual-document"
          privateLabel="Riêng tư chỉ người tạo"
          disabled={Boolean(importValue.supersedes_document_id)}
          onChange={updateImportValue}
        />
        <label className="field-label">
          Loại tài liệu nguồn
          <select
            className="apple-input mt-2"
            value={importValue.source_type || "REFERENCE"}
            disabled={Boolean(importValue.supersedes_document_id)}
            onChange={(event) => updateImportValue({ source_type: event.target.value })}
          >
            <option value="SRS">Đặc tả yêu cầu</option>
            <option value="USER_STORY">Câu chuyện người dùng</option>
            <option value="API_SPEC">Định nghĩa API</option>
            <option value="REFERENCE">Tài liệu khác</option>
          </select>
        </label>
        <label className="field-label">
          Định dạng
          <select
            className="apple-input mt-2"
            value={importValue.format}
            disabled={Boolean(importValue.supersedes_document_id)}
            onChange={(event) => {
              const nextFormat = event.target.value;
              const nextIsApi = nextFormat === "openapi" || nextFormat === "postman";
              const currentIsApi =
                importValue.format === "openapi" || importValue.format === "postman";
              updateImportValue({
                format: nextFormat,
                content:
                  nextIsApi === currentIsApi
                    ? importValue.content
                    : nextIsApi
                      ? docText(importValue.content)
                      : textDoc(importValue.content),
              });
            }}
          >
            {REQUIREMENT_IMPORT_FORMATS.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Nội dung nguồn
          <div className="mt-2">
            {importValue.format === "openapi" || importValue.format === "postman" ? (
              <textarea
                className="apple-input min-h-64"
                aria-label="Nội dung định nghĩa API"
                value={importValue.content}
                onChange={(event) => updateImportValue({ content: event.target.value })}
              />
            ) : (
              <DocumentEditor
                label="nội dung nguồn"
                minHeight="min-h-64"
                value={importValue.content}
                onChange={(content) => updateImportValue({ content })}
              />
            )}
          </div>
        </label>
        <div className="action-dialog-footer flex justify-end">
          <button
            className="secondary-button"
            type="submit"
            disabled={
              !(typeof importValue.content === "string"
                ? importValue.content.trim()
                : docText(importValue.content)) ||
              (importValue.visibility === "shared" && !importValue.shared_with.length)
            }
          >
            Tạo bản xem trước
          </button>
        </div>
      </form>
      {preview && (
        <div className="border-t border-border p-5">
          {preview.warnings?.includes("NO_DOCUMENTED_BEHAVIOR_TO_DRAFT") && (
            <p className="mb-3 text-sm text-ink-muted">
              Tài liệu chưa mô tả hành vi đủ rõ để tạo bản nháp yêu cầu. Bạn có thể bổ sung tài liệu
              hoặc tạo yêu cầu thủ công.
            </p>
          )}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold">
                {preview.status === "CONFIRMED"
                  ? "Nguồn này đã được nhập trước đó"
                  : "Rà soát ứng viên trước khi nhập"}
              </p>
              <p className="mt-1 text-[12px] text-ink-muted">
                Đã chọn {selectedIndexes.length} trên {preview.preview.length} ứng viên
              </p>
              {preview.status === "PREVIEW_READY" && (
                <p className="mt-1 text-[12px] text-ink-muted">
                  Có thể biên tập đầy đủ nội dung đã trích xuất trước khi xác nhận nhập
                </p>
              )}
            </div>
            {preview.status === "PREVIEW_READY" && (
              <div className="flex flex-wrap gap-2">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={confirmingImport}
                  onClick={onSaveReview}
                >
                  Lưu chỉnh sửa
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={confirmingImport}
                  onClick={onSplit}
                >
                  Tách mục đã chọn
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={confirmingImport}
                  onClick={onMerge}
                >
                  Gộp các mục đã chọn
                </button>
                <button
                  className="danger-button"
                  type="button"
                  disabled={confirmingImport}
                  onClick={onReject}
                >
                  Từ chối mục đã chọn
                </button>
              </div>
            )}
          </div>
          <DataTable
            items={preview.preview.map((item, index) => ({
              ...item,
              _id: index,
              candidateIndex: index,
            }))}
            layout="cards"
            selectedIds={selectedIndexes}
            onSelectionChange={setSelectedIndexes}
            selectionLabel="Chọn ứng viên"
            selectionDisabled={preview.status !== "PREVIEW_READY" || confirmingImport}
            columns={[
              {
                key: "requirement_key",
                label: "Mã yêu cầu",
                render: (item) => (
                  <input
                    aria-label={`Mã ứng viên ${item.candidateIndex + 1}`}
                    className="apple-input w-full min-w-0 xl:min-w-40"
                    value={item.requirement_key || ""}
                    disabled={preview.status !== "PREVIEW_READY" || confirmingImport}
                    onChange={(event) =>
                      onEditCandidate(item.candidateIndex, {
                        requirement_key: event.target.value || null,
                      })
                    }
                  />
                ),
              },
              {
                key: "title",
                label: "Yêu cầu phát hiện",
                render: (item) => (
                  <input
                    aria-label={`Tên ứng viên ${item.candidateIndex + 1}`}
                    className="apple-input w-full min-w-0 xl:min-w-64"
                    value={item.title}
                    disabled={preview.status !== "PREVIEW_READY" || confirmingImport}
                    onChange={(event) =>
                      onEditCandidate(item.candidateIndex, { title: event.target.value })
                    }
                  />
                ),
              },
              {
                key: "content_doc",
                label: "Nội dung",
                minWidth: 480,
                render: (item) => (
                  <div className="w-full min-w-0">
                    <DocumentEditor
                      label={`nội dung ứng viên ${item.candidateIndex + 1}`}
                      minHeight="min-h-40"
                      readOnly={preview.status !== "PREVIEW_READY" || confirmingImport}
                      value={item.content_doc}
                      onChange={(content_doc) =>
                        onEditCandidate(item.candidateIndex, { content_doc })
                      }
                    />
                    <label className="field-label mt-3 block">Tiêu chí chấp nhận</label>
                    <div className="mt-2 space-y-3">
                      {(item.acceptance_criteria || []).map((criterion, criterionIndex) => (
                        <div
                          className="rounded-control border border-border bg-surface-quiet p-3"
                          key={`${criterion.key || "AC"}-${criterionIndex}`}
                        >
                          <label className="field-label block">
                            {criterion.key || `Tiêu chí ${criterionIndex + 1}`}
                            <textarea
                              aria-label={`Tiêu chí chấp nhận ${criterion.key || criterionIndex + 1} ứng viên ${item.candidateIndex + 1}`}
                              className="apple-input mt-2 min-h-20 w-full min-w-0 resize-y"
                              disabled={preview.status !== "PREVIEW_READY" || confirmingImport}
                              value={docText(criterion.content_doc)}
                              onChange={(event) =>
                                onEditCandidate(item.candidateIndex, {
                                  acceptance_criteria: updateAcceptanceCriterion(
                                    item.acceptance_criteria || [],
                                    criterionIndex,
                                    event.target.value,
                                  ),
                                })
                              }
                            />
                          </label>
                          <button
                            className="secondary-button mt-2"
                            type="button"
                            disabled={preview.status !== "PREVIEW_READY" || confirmingImport}
                            onClick={() =>
                              onEditCandidate(item.candidateIndex, {
                                acceptance_criteria: item.acceptance_criteria.filter(
                                  (_, index) => index !== criterionIndex,
                                ),
                              })
                            }
                          >
                            Bỏ tiêu chí này
                          </button>
                        </div>
                      ))}
                      {!item.acceptance_criteria?.length && (
                        <p className="text-sm text-ink-muted">
                          Chưa trích xuất được tiêu chí chấp nhận.
                        </p>
                      )}
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={preview.status !== "PREVIEW_READY" || confirmingImport}
                        onClick={() =>
                          onEditCandidate(item.candidateIndex, {
                            acceptance_criteria: addAcceptanceCriterion(item.acceptance_criteria),
                          })
                        }
                      >
                        Thêm tiêu chí
                      </button>
                    </div>
                    <span className="mt-2 block text-xs font-normal text-ink-muted">
                      Tiêu chí phải bám theo nội dung tài liệu nguồn. Nội dung đã sửa cần được lưu
                      và đối chiếu lại trước khi nhập.
                    </span>
                  </div>
                ),
              },
              {
                key: "type",
                label: "Loại",
                render: (item) => valueLabel(item.type),
              },
              {
                key: "candidate_relation",
                label: "Kết quả đối chiếu",
                render: (item) => {
                  if (item.candidate_relation === "merged") return "Đã gộp từ nhiều nội dung";
                  const split = /^split-(\d+)$/.exec(item.candidate_relation || "");
                  if (split) return `Mục ${split[1]} sau khi tách`;
                  return item.candidate_relation
                    ? valueLabel(item.candidate_relation)
                    : "Nội dung mới";
                },
              },
              {
                key: "source_refs",
                label: "Vị trí nguồn",
                render: (item) => {
                  const source = item.source_refs?.[0];
                  if (!source) return "Không có";
                  if (source.source_start !== undefined) {
                    return `${source.source_start} đến ${source.source_end}`;
                  }
                  if (source.candidate_index !== undefined)
                    return `Mục ${source.candidate_index + 1}`;
                  if (source.template_id) return "Mẫu nguồn";
                  if (source.operation?.path)
                    return `${source.operation.method} ${source.operation.path}`;
                  return "Nguồn đã liên kết";
                },
              },
              {
                key: "existing_matches",
                label: "Đối chiếu với yêu cầu đã có",
                render: (item) => {
                  const matches =
                    importComparison?.comparisons?.find(
                      (entry) => entry.candidate_index === item.candidateIndex,
                    )?.matches || [];
                  if (!importComparison) return "Đang đối chiếu";
                  if (!matches.length) return "Chưa thấy mục tương tự";
                  return (
                    <div className="min-w-0 space-y-2 text-sm">
                      {matches.map((match) => (
                        <div
                          className="rounded-control border border-border p-2"
                          key={match.requirement_id || `candidate-${match.candidate_index}`}
                        >
                          <p className="font-medium">{match.requirement_key || match.title}</p>
                          <p className="text-ink-muted">
                            {["ARCHIVED", "OBSOLETE"].includes(match.requirement_status)
                              ? "Mã này thuộc một yêu cầu đã lưu trữ và chưa thể dùng lại"
                              : ["IN_IMPORT", "SAME_KEY_IN_IMPORT"].includes(match.match_type)
                                ? selectedIndexes.includes(match.candidate_index)
                                  ? match.match_type === "SAME_KEY_IN_IMPORT"
                                    ? `Cùng mã với mục ${match.candidate_index + 1} đang được chọn nhập`
                                    : `Trùng với mục ${match.candidate_index + 1} đang được chọn nhập`
                                  : `Tương tự mục ${match.candidate_index + 1} đã bỏ chọn nên không cần giải quyết trùng`
                                : match.match_type === "EXACT"
                                  ? "Trùng nội dung"
                                  : match.match_type === "SAME_KEY"
                                    ? "Cùng mã yêu cầu"
                                    : "Có thể liên quan"}
                          </p>
                          <p>{match.content}</p>
                          {!!match.affected_test_cases?.length && (
                            <p className="text-ink-muted">
                              Ca kiểm thử liên quan{" "}
                              {match.affected_test_cases
                                .map((test) => test.test_case_key || "Ca kiểm thử liên quan")
                                .join(", ")}
                            </p>
                          )}
                          {match.requirement_id &&
                            !["ARCHIVED", "OBSOLETE"].includes(match.requirement_status) &&
                            preview.status === "PREVIEW_READY" && (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {match.match_type === "EXACT" && (
                                  <button
                                    className="secondary-button"
                                    type="button"
                                    disabled={confirmingImport}
                                    onClick={() =>
                                      onResolveMatch(item.candidateIndex, match, "link_source")
                                    }
                                  >
                                    Gắn nguồn vào yêu cầu này
                                  </button>
                                )}
                                <button
                                  className="secondary-button"
                                  type="button"
                                  disabled={confirmingImport}
                                  onClick={() =>
                                    onResolveMatch(item.candidateIndex, match, "create_version")
                                  }
                                >
                                  Tạo phiên bản mới từ mục này
                                </button>
                              </div>
                            )}
                        </div>
                      ))}
                      {!!blockingMatches(item.candidateIndex).length && (
                        <label className="flex items-start gap-2">
                          <input
                            type="checkbox"
                            checked={separateIndexes.includes(item.candidateIndex)}
                            disabled={
                              preview.status !== "PREVIEW_READY" ||
                              confirmingImport ||
                              keyCollision(item.candidateIndex)
                            }
                            onChange={(event) =>
                              setSeparateIndexes((values) =>
                                event.target.checked
                                  ? [...values, item.candidateIndex]
                                  : values.filter((value) => value !== item.candidateIndex),
                              )
                            }
                          />
                          Vẫn nhập thành yêu cầu riêng sau khi đã xem các mục trên
                        </label>
                      )}
                      {!!blockingMatches(item.candidateIndex).length &&
                        separateIndexes.includes(item.candidateIndex) && (
                          <label className="field-label block">
                            Lý do giữ thành yêu cầu riêng
                            <input
                              className="apple-input mt-1"
                              disabled={confirmingImport}
                              value={separateReasons[item.candidateIndex] || ""}
                              onChange={(event) =>
                                setSeparateReasons((current) => ({
                                  ...current,
                                  [item.candidateIndex]: event.target.value,
                                }))
                              }
                            />
                          </label>
                        )}
                      {!!blockingMatches(item.candidateIndex).length && (
                        <p className="text-ink-muted">
                          {keyCollision(item.candidateIndex)
                            ? "Mã yêu cầu đã tồn tại  Hãy sửa mã hoặc bỏ chọn mục này"
                            : "Bỏ chọn mục này nếu không muốn nhập trùng"}
                        </p>
                      )}
                    </div>
                  );
                },
              },
              {
                key: "quality_issues",
                label: "Cần bổ sung trước khi duyệt",
                render: (item) =>
                  item.quality_issues?.length
                    ? item.quality_issues
                        .map(
                          (code) =>
                            ({
                              REQUIREMENT_CONTENT_MISSING: "Thiếu nội dung",
                              REQUIREMENT_SOURCE_MISSING: "Thiếu nguồn",
                              ACCEPTANCE_CRITERIA_MISSING_FOR_BASELINE:
                                "Thiếu tiêu chí chấp nhận để duyệt",
                              APPLICABLE_SECTION_MISSING_FOR_BASELINE:
                                "Thiếu thông tin áp dụng để duyệt",
                            })[code] || code,
                        )
                        .join(", ")
                    : "Không",
              },
            ]}
          />
          {preview.status === "PREVIEW_READY" && (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                className="apple-button"
                type="button"
                disabled={
                  confirmingImport ||
                  selectedIndexes.length === 0 ||
                  !importComparison ||
                  selectedIndexes.some(
                    (index) =>
                      keyCollision(index) ||
                      (blockingMatches(index).length > 0 &&
                        (!separateIndexes.includes(index) || !separateReasons[index]?.trim())),
                  )
                }
                aria-busy={!importComparison}
                onClick={confirmImport}
              >
                {confirmingImport
                  ? "Đang xác nhận nhập…"
                  : `Xác nhận nhập ${selectedIndexes.length} yêu cầu`}
              </button>
              {selectedIndexes.some((index) => keyCollision(index)) && (
                <p className="text-sm text-danger">Cần sửa mã yêu cầu hoặc bỏ chọn mục trùng mã</p>
              )}
              {selectedIndexes.some(
                (index) => blockingMatches(index).length && !separateIndexes.includes(index),
              ) && (
                <p className="text-sm text-danger">
                  Cần bỏ chọn hoặc xác nhận nhập riêng các mục tương tự
                </p>
              )}
              <p className="text-[12px] text-ink-muted">
                {preview.preview.length - selectedIndexes.length} ứng viên bị loại sẽ không được ghi
              </p>
            </div>
          )}
        </div>
      )}
      {sourceDocument && (
        <div className="border-t border-border p-5 text-[12px] text-ink-muted">
          <p>Nguồn {sourceDocument.filename}</p>
          <p>Trạng thái {valueLabel(sourceDocument.status)}</p>
          <details>
            <summary className="cursor-pointer">Thông tin kiểm tra tệp</summary>
            <p className="mt-1 break-all">Mã đối chiếu nội dung: {sourceDocument.content_hash}</p>
          </details>
          {(["UPLOADED", "PARSE_FAILED"].includes(sourceDocument.status) ||
            (sourceDocument.status === "READY" && !preview)) && (
            <button
              className="secondary-button mt-3"
              type="button"
              disabled={sourceProcessing}
              onClick={onRetrySource}
            >
              {sourceProcessing
                ? "Đang phân tích tài liệu…"
                : sourceDocument.status === "READY"
                  ? "Tạo bản xem trước lại"
                  : sourceDocument.status === "UPLOADED"
                    ? "Tiếp tục xử lý tệp đã tải lên"
                    : "Thử phân tích lại từ tệp gốc"}
            </button>
          )}
        </div>
      )}
    </Modal>
  );
}
