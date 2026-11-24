import { FileText } from "lucide-react";
import FilePicker from "../../../components/FilePicker";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { REQUIREMENT_SOURCE_TYPE_OPTIONS } from "./requirements.model";

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
        <div className="grid gap-2 rounded-control border border-border p-3">
          {members.map((member) => {
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
          })}
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
    >
      <ModalHeader>
        <ModalTitle>Thêm tài liệu</ModalTitle>
      </ModalHeader>
      {error && <ErrorState message={error} />}
      <form onSubmit={onUploadPreview} className="space-y-5 p-5">
        <FilePicker
          label="Tệp tài liệu nguồn"
          accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.json,.yaml,.yml"
          multiple
          disabled={sourceProcessing}
          fileName={files.length > 1 ? `${files.length} tệp đã chọn` : firstFile?.name || ""}
          onChange={(event) => setUpload(Array.from(event.target.files || []))}
        />
        {firstFile && files.length === 1 && (
          <SourceVersionParent
            access={uploadAccess}
            documents={sourceDocuments}
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
        <DocumentAccessControl
          access={uploadAccess}
          members={members}
          onChange={setUploadAccess}
          disabled={sourceProcessing}
        />
        <p className="text-sm text-ink-muted">
          Tài liệu sẽ được lưu làm nguồn tham khảo. Tạo Requirement riêng bằng biểu mẫu; nội dung
          tệp không tự chuyển thành yêu cầu.
        </p>
        <div className="flex justify-end gap-3 border-t border-border pt-4">
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
        </div>
      </form>
    </Modal>
  );
}
