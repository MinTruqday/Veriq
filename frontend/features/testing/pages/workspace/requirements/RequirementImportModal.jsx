import { FileText, X } from "lucide-react";
import FilePicker from "../../../components/FilePicker";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import { Modal, ModalFooter, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { REQUIREMENT_SOURCE_TYPE_OPTIONS } from "./requirements.model";

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocumentAccessControl({ access, members, onChange, disabled = false }) {
  return (
    <fieldset className="space-y-3">
      <legend className="field-label">Quyền xem tài liệu</legend>
      <div className="flex flex-wrap gap-4">
        {[
          { value: "private", label: "Riêng tư" },
          { value: "project", label: "Dự án" },
          { value: "shared", label: "Chia sẻ" },
        ].map((option) => (
          <label className="flex items-center gap-2 text-sm" key={option.value}>
            <input
              type="radio"
              name="document-visibility"
              checked={access.visibility === option.value}
              disabled={disabled}
              onChange={() =>
                onChange({
                  ...access,
                  visibility: option.value,
                  shared_with: option.value === "shared" ? access.shared_with : [],
                })
              }
            />
            {option.label}
          </label>
        ))}
      </div>
      {access.visibility === "shared" && (
        <div className="grid gap-2 rounded-control border border-border bg-surface p-3">
          {members.length ? (
            members.map((member) => {
              const id = member.user_id;
              const checked = (access.shared_with || []).includes(id);
              return (
                <label className="flex items-center gap-2 text-sm" key={id}>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled}
                    onChange={() =>
                      onChange({
                        ...access,
                        shared_with: checked
                          ? access.shared_with.filter((value) => value !== id)
                          : [...(access.shared_with || []), id],
                      })
                    }
                  />
                  {member.user_label ||
                    member.user?.full_name ||
                    member.user?.email ||
                    "Thành viên dự án"}
                </label>
              );
            })
          ) : (
            <p className="text-sm text-ink-muted">Dự án chưa có thành viên để chia sẻ</p>
          )}
        </div>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(access.ai_enabled)}
          disabled={disabled || Boolean(access.ai_enabled)}
          onChange={(event) => onChange({ ...access, ai_enabled: event.target.checked })}
        />
        Cho phép AI đọc tài liệu để tóm tắt
      </label>
    </fieldset>
  );
}

function SourceVersionParent({ access, documents, project, onChange, disabled }) {
  const userId = project.current_membership?.user_id;
  const parents = documents.filter(
    (item) => item.status !== "ARCHIVED" && item.created_by === userId,
  );
  return (
    <label className="field-label block">
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
  project,
  sourceDocuments,
}) {
  const files = Array.isArray(upload) ? upload : upload ? [upload] : [];
  const firstFile = files[0];
  return (
    <Modal
      isOpen={isOpen}
      onClose={sourceProcessing ? () => {} : onClose}
      ariaLabel="Thêm tài liệu"
      placement="right"
      className="flex flex-col"
    >
      <ModalHeader>
        <ModalTitle>Thêm tài liệu</ModalTitle>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          Tệp được lưu làm nguồn tham khảo của dự án. Nội dung tệp không tự tạo Requirement
        </p>
      </ModalHeader>
      <form onSubmit={onUploadPreview} className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto overscroll-contain px-5 py-5 sm:px-7">
          {error && <ErrorState message={error} />}
          <section aria-labelledby="requirement-source-files" className="grid gap-3">
            <div>
              <h2 id="requirement-source-files" className="text-sm font-semibold text-ink">
                Tệp nguồn
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                PDF, Word, văn bản, bảng tính hoặc đặc tả API
              </p>
            </div>
            <FilePicker
              label="Chọn tệp tài liệu"
              accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.json,.yaml,.yml"
              multiple
              disabled={sourceProcessing}
              fileName={files.length > 1 ? `${files.length} tệp đã chọn` : firstFile?.name || ""}
              onChange={(event) => setUpload(Array.from(event.target.files || []))}
            />
            {files.length > 0 && (
              <ul aria-label="Tệp sẽ tải lên" className="grid gap-2">
                {files.map((file, index) => (
                  <li
                    className="flex min-w-0 items-center gap-3 rounded-control border border-border bg-surface p-3"
                    key={`${file.name}-${file.size}-${file.lastModified}`}
                  >
                    <FileText aria-hidden="true" className="shrink-0 text-ink-muted" size={18} />
                    <span className="min-w-0 flex-1">
                      <span className="block break-all text-sm font-medium text-ink">
                        {file.name}
                      </span>
                      <span className="text-xs text-ink-muted">{formatFileSize(file.size)}</span>
                    </span>
                    <button
                      aria-label={`Bỏ tệp ${file.name}`}
                      className="icon-button h-9 w-9 shrink-0"
                      disabled={sourceProcessing}
                      onClick={() => setUpload(files.filter((_, fileIndex) => fileIndex !== index))}
                      type="button"
                    >
                      <X aria-hidden="true" size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="requirement-source-settings" className="grid gap-4">
            <div className="border-t border-border pt-5">
              <h2 id="requirement-source-settings" className="text-sm font-semibold text-ink">
                Nguồn và phiên bản
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                Phân loại tài liệu và nối với nguồn trước nếu đây là phiên bản cập nhật
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="field-label block">
                Loại tài liệu nguồn
                <select
                  className="apple-input mt-2"
                  value={uploadAccess.source_type || "REFERENCE"}
                  disabled={sourceProcessing}
                  onChange={(event) =>
                    setUploadAccess((value) => ({ ...value, source_type: event.target.value }))
                  }
                >
                  {REQUIREMENT_SOURCE_TYPE_OPTIONS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              {firstFile && files.length === 1 && (
                <SourceVersionParent
                  access={uploadAccess}
                  documents={sourceDocuments}
                  project={project}
                  onChange={setUploadAccess}
                  disabled={sourceProcessing}
                />
              )}
            </div>
          </section>

          <section aria-labelledby="requirement-source-access" className="grid gap-4">
            <div className="border-t border-border pt-5">
              <h2 id="requirement-source-access" className="text-sm font-semibold text-ink">
                Quyền truy cập
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                Chọn phạm vi người có thể xem và việc AI có được phép đọc nguồn này
              </p>
            </div>
            <DocumentAccessControl
              access={uploadAccess}
              members={members}
              onChange={setUploadAccess}
              disabled={sourceProcessing}
            />
          </section>
        </div>
        <ModalFooter>
          <button
            className="secondary-button"
            type="button"
            disabled={sourceProcessing}
            onClick={onClose}
          >
            Hủy
          </button>
          <button
            className="apple-button inline-flex items-center gap-2"
            type="submit"
            disabled={sourceProcessing || files.length === 0}
          >
            <FileText size={16} aria-hidden="true" />
            {sourceProcessing ? "Đang lưu tài liệu…" : "Lưu tài liệu"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
