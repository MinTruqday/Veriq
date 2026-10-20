import DataTable from "../../../components/DataTable";
import FilePicker from "../../../components/FilePicker";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import DocumentEditor from "../../../editor/DocumentEditor";
import { docText, textDoc, valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { REQUIREMENT_IMPORT_FORMATS } from "./requirements.model";
import RequirementTemplatePanel from "./RequirementTemplatePanel";

function DocumentAccessControl({ access, members, onChange, privateLabel, name }) {
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
            name={`${name}-visibility`}
            type="radio"
            onChange={() => onChange({ ...access, visibility: "private", shared_with: [] })}
          />
          {privateLabel}
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            checked={isPublic}
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
              name={`${name}-scope`}
              type="radio"
              onChange={() => onChange({ ...access, visibility: "project", shared_with: [] })}
            />
            Tất cả thành viên dự án
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              checked={access.visibility === "shared"}
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
                    checked={access.shared_with.includes(member.user_id)}
                    onChange={(event) => updateSharedWith(member.user_id, event.target.checked)}
                  />
                  {member.user_label || member.user_id}
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
          disabled={Boolean(access.ai_enabled)}
          onChange={(event) => onChange({ ...access, ai_enabled: event.target.checked })}
        />
        {access.ai_enabled
          ? "Đã cho phép AI truy cập tài liệu này"
          : "Cho phép AI truy cập tài liệu này"}
      </label>
    </fieldset>
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
  sourceDocuments,
  onTemplatePreview,
  onError,
}) {
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
      onClose={onClose}
      ariaLabel="Nhập tài liệu"
      className="max-w-5xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Nhập tài liệu</ModalTitle>
      </ModalHeader>
      {error && <ErrorState message={error} />}
      <RequirementTemplatePanel
        project={project}
        members={members}
        sourceDocuments={sourceDocuments}
        onPreview={onTemplatePreview}
        onError={onError}
        isOpen={isOpen}
      />
      <form onSubmit={onUploadPreview} className="space-y-4 border-b border-border p-5">
        <FilePicker
          label="Tệp SRS, BRD hoặc bảng yêu cầu"
          accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.json,.yaml,.yml"
          fileName={upload?.name || ""}
          onChange={(event) => setUpload(event.target.files?.[0] || null)}
        />
        <label className="field-label">
          Loại tài liệu nguồn
          <select
            className="apple-input mt-2"
            value={uploadAccess.source_type || "REFERENCE"}
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
        {uploadAccess.source_type === "API_SPEC" && (
          <label className="field-label">
            Định dạng định nghĩa API
            <select
              className="apple-input mt-2"
              value={uploadAccess.api_format || "openapi"}
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
          onChange={setUploadAccess}
        />
        <div className="action-dialog-footer flex justify-end">
          <button
            className="secondary-button"
            type="submit"
            disabled={
              !upload || (uploadAccess.visibility === "shared" && !uploadAccess.shared_with.length)
            }
          >
            Tải lên và xem trước
          </button>
        </div>
      </form>
      <form onSubmit={onImportPreview} className="space-y-4 p-5">
        <label className="field-label">
          Tên tệp
          <input
            className="apple-input mt-2"
            value={importValue.filename}
            onChange={(event) => updateImportValue({ filename: event.target.value })}
          />
        </label>
        <DocumentAccessControl
          access={importValue}
          members={members}
          name="manual-document"
          privateLabel="Riêng tư chỉ người tạo"
          onChange={updateImportValue}
        />
        <label className="field-label">
          Loại tài liệu nguồn
          <select
            className="apple-input mt-2"
            value={importValue.source_type || "REFERENCE"}
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
              Tài liệu chưa mô tả hành vi đủ rõ để tạo bản nháp yêu cầu Bạn có thể bổ sung tài liệu
              hoặc tạo mẫu thủ công
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
                <button className="secondary-button" type="button" onClick={onSaveReview}>
                  Lưu chỉnh sửa
                </button>
                <button className="secondary-button" type="button" onClick={onSplit}>
                  Tách mục đã chọn
                </button>
                <button className="secondary-button" type="button" onClick={onMerge}>
                  Gộp các mục đã chọn
                </button>
                <button className="danger-button" type="button" onClick={onReject}>
                  Từ chối mục đã chọn
                </button>
              </div>
            )}
          </div>
          <DataTable
            items={preview.preview.map((item, index) => ({
              ...item,
              _id: `candidate-${index}`,
              candidateIndex: index,
            }))}
            columns={[
              {
                key: "selected",
                label: "Nhập",
                render: (item) => (
                  <input
                    aria-label={`Chọn ứng viên ${item.candidateIndex + 1}`}
                    type="checkbox"
                    checked={selectedIndexes.includes(item.candidateIndex)}
                    disabled={preview.status !== "PREVIEW_READY"}
                    onChange={(event) =>
                      setSelectedIndexes((values) =>
                        event.target.checked
                          ? [...values, item.candidateIndex].sort((left, right) => left - right)
                          : values.filter((value) => value !== item.candidateIndex),
                      )
                    }
                  />
                ),
              },
              {
                key: "requirement_key",
                label: "Mã yêu cầu",
                render: (item) => (
                  <input
                    aria-label={`Mã ứng viên ${item.candidateIndex + 1}`}
                    className="apple-input w-full min-w-0 xl:min-w-40"
                    value={item.requirement_key || ""}
                    disabled={preview.status !== "PREVIEW_READY"}
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
                    disabled={preview.status !== "PREVIEW_READY"}
                    onChange={(event) =>
                      onEditCandidate(item.candidateIndex, { title: event.target.value })
                    }
                  />
                ),
              },
              {
                key: "content_doc",
                label: "Nội dung",
                render: (item) => (
                  <div className="w-full min-w-0">
                    <DocumentEditor
                      label={`nội dung ứng viên ${item.candidateIndex + 1}`}
                      minHeight="min-h-40"
                      readOnly={preview.status !== "PREVIEW_READY"}
                      value={item.content_doc}
                      onChange={(content_doc) =>
                        onEditCandidate(item.candidateIndex, { content_doc })
                      }
                    />
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
                label: "Quan hệ ứng viên",
                render: (item) => item.candidate_relation || "Nguyên bản",
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
                  if (source.template_id) return `Mẫu ${source.template_id}`;
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
                                .map((test) => test.test_case_key || test.test_case_id)
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
                onClick={onConfirm}
              >
                Xác nhận nhập {selectedIndexes.length} yêu cầu
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
          <p className="break-all">SHA256 {sourceDocument.content_hash}</p>
          {sourceDocument.status === "PARSE_FAILED" && (
            <button className="secondary-button mt-3" type="button" onClick={onRetrySource}>
              Thử phân tích lại từ tệp gốc
            </button>
          )}
        </div>
      )}
    </Modal>
  );
}
