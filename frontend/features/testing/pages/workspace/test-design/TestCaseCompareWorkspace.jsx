"use client";

import { useEffect, useRef, useState } from "react";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import DocumentEditor from "../../../editor/DocumentEditor";
import FilePicker from "../../../components/FilePicker";
import { docText, emptyDoc, messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import {
  TEST_CASE_TYPES,
  TEST_CASE_ASSESSMENT_LEVELS,
  TESTING_LEVELS,
  TEST_KINDS,
  EXPECTED_IMPACTS,
} from "./testDesign.model";
import {
  chooseFields,
  chooseStep,
  chooseStepSource,
  comparedStepIds,
  copyValue,
  fieldDifference,
  moveStep,
  removeStep,
} from "./testCaseMerge.logic.mjs";

const fields = [
  { key: "title", label: "Tên ca kiểm thử", kind: "text" },
  { key: "objective_doc", label: "Mục tiêu", kind: "document" },
  { key: "type", label: "Loại tình huống", kind: "select", options: TEST_CASE_TYPES },
  { key: "priority", label: "Mức ưu tiên", kind: "select", options: TEST_CASE_ASSESSMENT_LEVELS },
  { key: "risk", label: "Rủi ro", kind: "select", options: TEST_CASE_ASSESSMENT_LEVELS },
  {
    key: "test_level",
    label: "Cấp kiểm thử",
    kind: "select",
    options: TESTING_LEVELS,
    optional: true,
  },
  { key: "test_kind", label: "Loại kiểm thử", kind: "select", options: TEST_KINDS, optional: true },
  { key: "expected_impact", label: "Ảnh hưởng dự kiến", kind: "select", options: EXPECTED_IMPACTS },
  { key: "assessment_reason", label: "Lý do đánh giá", kind: "text" },
  { key: "bdd", label: "Kịch bản BDD", kind: "bdd" },
  { key: "preconditions_doc", label: "Điều kiện trước", kind: "document" },
  { key: "test_data", label: "Dữ liệu chung", kind: "data" },
  { key: "custom_values", label: "Thông tin mở rộng", kind: "custom" },
  { key: "expected_result_doc", label: "Kết quả mong đợi chung", kind: "document" },
  { key: "postconditions_doc", label: "Điều kiện sau", kind: "document" },
  { key: "tags", label: "Nhãn", kind: "list" },
  { key: "owner_id", label: "Người phụ trách", kind: "member", optional: true },
  { key: "attachments", label: "Tệp đính kèm", kind: "attachments" },
  { key: "required_skills", label: "Kỹ năng cần có", kind: "list" },
  { key: "techniques", label: "Kỹ thuật kiểm thử", kind: "list" },
  {
    key: "automation_status",
    label: "Trạng thái tự động hóa",
    kind: "select",
    options: ["manual", "candidate", "automated"],
  },
  { key: "data_set_version_ids", label: "Bộ dữ liệu liên kết", kind: "reference_list" },
  { key: "requirement_version_ids", label: "Yêu cầu liên kết", kind: "reference_list" },
  { key: "acceptance_criterion_ids", label: "Tiêu chí chấp nhận", kind: "reference_list" },
  { key: "coverage_item_ids", label: "Điểm cần kiểm thử liên kết", kind: "reference_list" },
  { key: "test_condition_ids", label: "Điều kiện kiểm thử liên kết", kind: "reference_list" },
  { key: "scenario_id", label: "Tình huống kiểm thử", kind: "reference", optional: true },
  { key: "repository_node_id", label: "Thư mục kho kiểm thử", kind: "reference", optional: true },
  {
    key: "duplicate_reason",
    label: "Lý do giữ ca có khả năng trùng",
    kind: "text",
    optional: true,
  },
];
const bddStepKeywords = ["Given", "When", "Then", "And", "But"];
const bddStepKeywordLabels = {
  Given: "Cho trước",
  When: "Khi",
  Then: "Thì",
  And: "Và",
  But: "Nhưng",
};
const lineageSensitiveFields = new Set([
  "title",
  "type",
  "objective_doc",
  "preconditions_doc",
  "steps",
  "steps.action_doc",
  "steps.expected_doc",
  "steps.test_data",
  "test_data",
  "expected_result_doc",
  "postconditions_doc",
  "techniques",
  "requirement_version_ids",
  "acceptance_criterion_ids",
  "data_set_version_ids",
  "test_condition_ids",
  "scenario_id",
  "coverage_item_ids",
  "bdd",
]);

function ReadValue({ value, kind, customFields = [], members = [] }) {
  if (kind === "member" && (value === undefined || value === null || value === ""))
    return <p className="text-ink-muted">Chưa phân công</p>;
  if (value === undefined || value === null) return <p className="text-ink-muted">Không có</p>;
  if (kind === "member") {
    const member = members.find((item) => item.user_id === value);
    const memberLabel = member
      ? [member.user?.full_name, member.user?.email, member.user_label].find(
          (label) => label && label !== member.user_id && label !== value,
        )
      : null;
    return (
      <p className="break-words">
        {member ? memberLabel || "Thành viên dự án" : "Người phụ trách không còn trong dự án"}
      </p>
    );
  }
  if (kind === "document")
    return (
      <p className="whitespace-pre-wrap break-words">{docText(value) || "Chưa có nội dung"}</p>
    );
  if (kind === "bdd")
    return (
      <div className="space-y-2 text-sm">
        <p>{value.feature}</p>
        <p>{value.scenario}</p>
        {value.steps?.map((step, index) => (
          <p key={step.id || index}>
            {bddStepKeywordLabels[step.keyword] || step.keyword || "Bước"}: {step.text}
          </p>
        ))}
      </div>
    );
  if (kind === "attachments")
    return value?.length ? (
      <ul className="space-y-1">
        {value.map((attachment, index) => (
          <li className="break-words" key={attachment.url || attachment.file_path || index}>
            {attachment.filename || attachment.name || "Tệp đính kèm"}
          </li>
        ))}
      </ul>
    ) : (
      <p className="text-ink-muted">Chưa có tệp đính kèm.</p>
    );
  if (kind === "reference_list") {
    const count = Array.isArray(value) ? value.length : 0;
    return <p className="text-ink-muted">{count ? `${count} liên kết đã lưu` : "Chưa liên kết"}</p>;
  }
  if (kind === "reference")
    return <p className="text-ink-muted">{value ? "Đã liên kết" : "Chưa liên kết"}</p>;
  if (kind === "custom") {
    const fieldByKey = new Map(customFields.map((field) => [field.key, field]));
    const entries = Object.entries(value || {});
    return entries.length ? (
      <dl className="space-y-2">
        {entries.map(([key, item]) => {
          const field = fieldByKey.get(key);
          return (
            <div className="min-w-0" key={key}>
              <dt className="font-medium break-words">
                {field?.label || key}
                {field?.status === "INACTIVE" ? " · Ngừng dùng" : ""}
              </dt>
              <dd className="break-words">
                {typeof item === "boolean"
                  ? item
                    ? "Có"
                    : "Không"
                  : valueLabel(String(item ?? ""))}
                {!field && <span className="ml-1 text-amber-700">(không còn cấu hình)</span>}
              </dd>
            </div>
          );
        })}
      </dl>
    ) : (
      <p className="text-ink-muted">Chưa có thông tin mở rộng.</p>
    );
  }
  if (Array.isArray(value))
    return (
      <p className="break-words">
        {value
          .map((item) => (typeof item === "string" ? valueLabel(item) : "Dữ liệu cấu trúc"))
          .join(", ") || "Chưa có"}
      </p>
    );
  if (typeof value === "object")
    return (
      <dl className="space-y-2">
        {Object.entries(value).map(([key, item]) => (
          <div key={key} className="min-w-0">
            <dt className="font-medium break-words">{key}</dt>
            <dd className="break-words">
              {item !== null && typeof item === "object"
                ? "Dữ liệu cấu trúc được giữ nguyên"
                : String(item ?? "")}
            </dd>
          </div>
        ))}
      </dl>
    );
  return <p className="whitespace-pre-wrap break-words">{valueLabel(String(value))}</p>;
}

function DataEditor({ value = {}, onChange, label }) {
  const [key, setKey] = useState("");
  if (Array.isArray(value)) {
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div className="flex min-w-0 items-start gap-2" key={index}>
            <div className="min-w-0 flex-1">
              <DataEditor
                value={item}
                label={`${label}, phần tử ${index + 1}`}
                onChange={(nextItem) =>
                  onChange(value.map((entry, position) => (position === index ? nextItem : entry)))
                }
              />
            </div>
            <button
              type="button"
              className="secondary-button shrink-0"
              aria-label={`Bỏ ${label}, phần tử ${index + 1}`}
              onClick={() => onChange(value.filter((_, position) => position !== index))}
            >
              Bỏ
            </button>
          </div>
        ))}
        <button type="button" className="secondary-button" onClick={() => onChange([...value, ""])}>
          Thêm phần tử
        </button>
      </div>
    );
  }
  if (value !== null && typeof value === "object") {
    return (
      <div className="space-y-3">
        {Object.entries(value).map(([name, item]) => (
          <div className="min-w-0 rounded-control bg-surface-quiet p-3" key={name}>
            <div className="mb-2 flex min-w-0 items-start justify-between gap-2">
              <p className="min-w-0 break-words text-sm font-medium">{name}</p>
              <button
                type="button"
                className="shrink-0 text-xs text-ink-muted underline"
                aria-label={`Bỏ dữ liệu ${label}: ${name}`}
                onClick={() =>
                  onChange(
                    Object.fromEntries(Object.entries(value).filter(([entry]) => entry !== name)),
                  )
                }
              >
                Bỏ trường
              </button>
            </div>
            <DataEditor
              value={item}
              label={`${label}: ${name}`}
              onChange={(nextItem) => onChange({ ...value, [name]: nextItem })}
            />
          </div>
        ))}
        <div className="flex min-w-0 flex-wrap gap-2">
          <input
            className="apple-input min-w-0 flex-1"
            aria-label={`Tên dữ liệu mới: ${label}`}
            placeholder="Tên dữ liệu mới"
            value={key}
            onChange={(event) => setKey(event.target.value)}
          />
          <button
            type="button"
            className="secondary-button"
            disabled={!key.trim() || Object.hasOwn(value, key.trim())}
            onClick={() => {
              onChange({ ...value, [key.trim()]: "" });
              setKey("");
            }}
          >
            Thêm trường
          </button>
        </div>
      </div>
    );
  }
  const inputType =
    typeof value === "number" ? "number" : typeof value === "boolean" ? "checkbox" : "text";
  return (
    <label className="field-label min-w-0 break-words">
      {label}
      <input
        aria-label={label}
        className="apple-input"
        type={inputType}
        step={inputType === "number" ? "any" : undefined}
        checked={inputType === "checkbox" ? value : undefined}
        value={inputType === "checkbox" ? undefined : String(value ?? "")}
        onChange={(event) => {
          const next =
            inputType === "checkbox"
              ? event.target.checked
              : inputType === "number" && event.target.value !== ""
                ? Number(event.target.value)
                : event.target.value;
          onChange(next);
        }}
      />
    </label>
  );
}

function CustomValuesEditor({ value = {}, fields = [], onChange }) {
  const knownKeys = new Set(fields.map((item) => item.key));
  const unknownEntries = Object.entries(value || {}).filter(([key]) => !knownKeys.has(key));
  const update = (key, nextValue) => {
    const next = { ...value };
    if (nextValue === "" || nextValue === null) delete next[key];
    else next[key] = nextValue;
    onChange(next);
  };

  return (
    <div className="space-y-3">
      {fields.map((item) => {
        const current = value?.[item.key] ?? "";
        const disabled = item.status === "INACTIVE" && current === "";
        return (
          <label className="field-label min-w-0" key={item._id || item.key}>
            <span>
              {item.label}
              {item.required && item.status !== "INACTIVE" ? " *" : ""}
              {item.status === "INACTIVE" ? " · Trường cũ" : ""}
            </span>
            {item.value_type === "choice" ? (
              <>
                <select
                  className="apple-input"
                  value={current}
                  disabled={disabled}
                  onChange={(event) => update(item.key, event.target.value)}
                >
                  <option value="">Chưa chọn</option>
                  {current !== "" && !(item.choices || []).includes(current) && (
                    <option value={current}>Giá trị cũ: {String(current)}</option>
                  )}
                  {(item.choices || []).map((choice) => (
                    <option key={choice} value={choice}>
                      {choice}
                    </option>
                  ))}
                </select>
                {current !== "" && !(item.choices || []).includes(current) && (
                  <span className="text-xs text-amber-800">
                    Giá trị đang lưu không còn trong lựa chọn hiện tại; hãy chọn giá trị mới hoặc để
                    trống để xóa.
                  </span>
                )}
              </>
            ) : item.value_type === "boolean" ? (
              <select
                className="apple-input"
                value={current === "" ? "" : String(current)}
                disabled={disabled}
                onChange={(event) =>
                  update(item.key, event.target.value === "" ? "" : event.target.value === "true")
                }
              >
                <option value="">Chưa chọn</option>
                <option value="true">Có</option>
                <option value="false">Không</option>
              </select>
            ) : (
              <input
                className="apple-input"
                type={item.value_type === "number" ? "number" : item.value_type}
                step={item.value_type === "number" ? "any" : undefined}
                value={current}
                disabled={disabled}
                onChange={(event) =>
                  update(
                    item.key,
                    item.value_type === "number" && event.target.value !== ""
                      ? Number(event.target.value)
                      : event.target.value,
                  )
                }
              />
            )}
          </label>
        );
      })}
      {unknownEntries.map(([key, item]) => (
        <div
          className="flex min-w-0 items-start justify-between gap-2 rounded-control border border-amber-300 bg-amber-50 p-3"
          key={key}
        >
          <p className="min-w-0 break-words text-sm">
            {key}: {typeof item === "boolean" ? (item ? "Có" : "Không") : String(item ?? "")}
            <span className="ml-1 text-amber-800">(không còn cấu hình)</span>
          </p>
          <button
            className="secondary-button shrink-0"
            type="button"
            onClick={() => update(key, "")}
          >
            Bỏ trường cũ
          </button>
        </div>
      ))}
      {!fields.length && !unknownEntries.length && (
        <p className="text-sm text-ink-muted">Dự án chưa cấu hình trường mở rộng.</p>
      )}
    </div>
  );
}

function AttachmentEditor({ value = [], onChange, disabled = false }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const upload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const response = await uploadAssetAPI(file);
      if (!response?.data || typeof response.data !== "object") {
        throw new Error("Kho tệp không trả về thông tin tệp hợp lệ.");
      }
      onChange((current = []) => [...current, response.data]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <div className="min-w-0 space-y-3">
      <FilePicker
        label="Tệp đính kèm"
        disabled={disabled || uploading}
        buttonLabel={uploading ? "Đang tải lên…" : "Chọn tệp"}
        ariaLabel="Bản kết quả: chọn tệp đính kèm"
        onChange={upload}
      />
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {value.length > 0 && (
        <ul className="space-y-2">
          {value.map((attachment, index) => (
            <li
              className="flex min-w-0 items-start justify-between gap-2 rounded-control bg-surface-quiet p-2"
              key={attachment.url || attachment.file_path || index}
            >
              <span className="min-w-0 break-words text-sm">
                {attachment.filename || attachment.name || "Tệp đính kèm"}
              </span>
              <button
                type="button"
                className="secondary-button shrink-0"
                aria-label={`Bỏ tệp ${attachment.filename || attachment.name || index + 1}`}
                disabled={disabled || uploading}
                onClick={() => onChange((current = []) => current.filter((_, i) => i !== index))}
              >
                Bỏ
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-ink-muted">Bỏ tệp khỏi bản ghép không xóa tệp khỏi kho lưu trữ.</p>
    </div>
  );
}

function FieldEditor({
  field,
  value,
  customFields,
  members,
  canReadMembers,
  membersLoaded,
  onChange,
  disabled,
  canManageAttachments,
}) {
  if (field.kind === "reference_list" || field.kind === "reference") {
    return (
      <div className="rounded-control bg-surface-quiet px-3 py-2 text-sm text-ink-muted">
        {field.kind === "reference_list"
          ? Array.isArray(value) && value.length
            ? `${value.length} liên kết đã lưu`
            : "Chưa liên kết"
          : value
            ? "Đã liên kết"
            : "Chưa liên kết"}
        <span className="ml-1">· Chọn bản gốc hoặc đề xuất AI để thay đổi liên kết</span>
      </div>
    );
  }
  if (field.kind === "bdd")
    return value ? (
      <div className="space-y-3">
        <input
          className="apple-input"
          aria-label="Bản kết quả: tính năng BDD"
          value={value.feature}
          onChange={(event) => onChange({ ...value, feature: event.target.value })}
        />
        <input
          className="apple-input"
          aria-label="Bản kết quả: tình huống BDD"
          value={value.scenario}
          onChange={(event) => onChange({ ...value, scenario: event.target.value })}
        />
        {value.steps.map((step, index) => (
          <div
            className="grid min-w-0 gap-2 sm:grid-cols-[minmax(9rem,0.35fr)_minmax(0,1fr)]"
            key={step.id || index}
          >
            <label className="field-label min-w-0">
              Loại bước BDD
              <select
                className="apple-input"
                aria-label={`Bản kết quả: loại bước BDD ${index + 1}`}
                value={step.keyword || "Given"}
                onChange={(event) =>
                  onChange({
                    ...value,
                    steps: value.steps.map((item, position) =>
                      position === index ? { ...item, keyword: event.target.value } : item,
                    ),
                  })
                }
              >
                {bddStepKeywords.map((keyword) => (
                  <option key={keyword} value={keyword}>
                    {bddStepKeywordLabels[keyword]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label min-w-0">
              Nội dung bước
              <textarea
                className="apple-input"
                aria-label={`Bản kết quả: nội dung bước BDD ${index + 1}`}
                value={step.text}
                onChange={(event) =>
                  onChange({
                    ...value,
                    steps: value.steps.map((item, position) =>
                      position === index ? { ...item, text: event.target.value } : item,
                    ),
                  })
                }
              />
            </label>
            <button
              className="secondary-button w-fit sm:col-start-2"
              type="button"
              aria-label={`Bỏ bước BDD ${index + 1}`}
              disabled={value.steps.length <= 1}
              onClick={() =>
                onChange({
                  ...value,
                  steps: value.steps.filter((_, position) => position !== index),
                })
              }
            >
              Bỏ bước
            </button>
          </div>
        ))}
        <button
          className="secondary-button w-fit"
          type="button"
          onClick={() =>
            onChange({
              ...value,
              steps: [...value.steps, { id: crypto.randomUUID(), keyword: "And", text: "" }],
            })
          }
        >
          Thêm bước BDD
        </button>
      </div>
    ) : (
      <p className="text-sm text-ink-muted">Không có kịch bản BDD.</p>
    );
  if (field.kind === "document")
    return (
      <DocumentEditor value={value || emptyDoc()} onChange={onChange} ignoreUnfocusedUpdates />
    );
  if (field.kind === "custom")
    return <CustomValuesEditor value={value || {}} fields={customFields} onChange={onChange} />;
  if (field.kind === "data")
    return <DataEditor value={value} onChange={onChange} label={field.label} />;
  if (field.kind === "attachments")
    return canManageAttachments ? (
      <AttachmentEditor value={value || []} onChange={onChange} disabled={disabled} />
    ) : (
      <ReadValue value={value} kind="attachments" />
    );
  if (field.kind === "member")
    return canReadMembers ? (
      <select
        aria-label={`Bản kết quả: ${field.label}`}
        className="apple-input"
        value={value || ""}
        disabled={disabled || !membersLoaded}
        onChange={(event) => onChange(event.target.value || null)}
      >
        <option value="">Chưa phân công</option>
        {value && !members.some((member) => member.user_id === value) && (
          <option value={value}>Người phụ trách hiện tại không còn hoạt động trong dự án</option>
        )}
        {members.map((member) => (
          <option key={member.user_id} value={member.user_id}>
            {[member.user?.full_name, member.user?.email, member.user_label].find(
              (label) => label && label !== member.user_id,
            ) || "Thành viên dự án"}
            {member.project_role ? ` · ${valueLabel(member.project_role)}` : ""}
          </option>
        ))}
      </select>
    ) : (
      <ReadValue value={value ? "Người phụ trách đã được thiết lập" : "Chưa phân công"} />
    );
  if (field.kind === "select")
    return (
      <select
        aria-label={`Bản kết quả: ${field.label}`}
        className="apple-input"
        value={value || ""}
        onChange={(event) => onChange(event.target.value || null)}
      >
        {field.optional && <option value="">Chưa phân loại</option>}
        {field.options.map((option) => (
          <option value={option} key={option}>
            {valueLabel(option)}
          </option>
        ))}
      </select>
    );
  return (
    <input
      aria-label={`Bản kết quả: ${field.label}`}
      className="apple-input"
      value={field.kind === "list" ? (value || []).join(", ") : (value ?? "")}
      onChange={(event) =>
        onChange(
          field.kind === "list"
            ? event.target.value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean)
            : field.optional && !event.target.value
              ? null
              : event.target.value,
        )
      }
    />
  );
}

function sourceTypeLabel(type) {
  return (
    {
      requirement: "Yêu cầu",
      requirement_version: "Yêu cầu",
      acceptance_criterion: "Tiêu chí chấp nhận",
      business_rule: "Quy tắc nghiệp vụ",
      api_operation: "Thao tác API",
      requirement_document: "Tài liệu yêu cầu",
      source_document: "Tài liệu nguồn",
    }[type] || "Tài liệu nguồn"
  );
}

function sourceDisplayLabel(source) {
  const title = source.title || source.label || source.filename;
  const type = sourceTypeLabel(source.artifact_type || source.source_type);
  const page = source.page_no ? ` · Trang ${source.page_no}` : "";
  return `${title || type}${page}`;
}

function evidenceReferenceLabel(reference, sources, index) {
  const source = sources.find(
    (item) =>
      item.artifact_version_id === reference ||
      item.artifact_id === reference ||
      item.source === reference,
  );
  return source ? sourceDisplayLabel(source) : `Nguồn dẫn ${index + 1}`;
}

function EvidenceValue({ value }) {
  const sources = value?.source_evidence || [];
  const quotes = value?.evidence_quotes || [];
  const references = value?.evidence_refs || [];
  if (!sources.length && !quotes.length && !references.length)
    return <p className="text-sm text-ink-muted">Chưa có bằng chứng nguồn được lưu.</p>;
  return (
    <div className="space-y-3 text-sm">
      {sources.map((source, index) => (
        <article
          className="min-w-0 rounded-control bg-surface-quiet p-3"
          key={`${source.artifact_version_id || source.artifact_id || "source"}-${index}`}
        >
          <p className="break-words text-xs font-medium">
            {sourceDisplayLabel(source)}
            {source.block_id ? " · Có vị trí trong tài liệu" : ""}
          </p>
          <p className="mt-2 whitespace-pre-wrap break-words">
            {source.text || "Không lưu đoạn trích."}
          </p>
        </article>
      ))}
      {quotes.map((quote, index) => (
        <article
          className="min-w-0 border-l-2 border-brand pl-3"
          key={`${quote.evidence_ref}-${index}`}
        >
          <p className="text-xs text-ink-muted">
            Trích dẫn từ {evidenceReferenceLabel(quote.evidence_ref, sources, index)}
          </p>
          <p className="mt-1 whitespace-pre-wrap break-words">{quote.quote}</p>
        </article>
      ))}
      {references.length > 0 && (
        <p className="break-words text-xs text-ink-muted">
          Căn cứ:{" "}
          {references
            .map((reference, index) => evidenceReferenceLabel(reference, sources, index))
            .join(", ")}
        </p>
      )}
    </div>
  );
}

function CoverageLineageValue({ value, stale = false }) {
  const obligations = value?.coverage_obligations || [];
  const snapshotIds = value?.acceptance_criteria_snapshot_ids || [];
  const sources = value?.source_evidence || [];
  const obligationEvidence = value?.obligation_evidence || [];
  const hypotheses = value?.challenge_hypotheses || [];
  if (!obligations.length && !snapshotIds.length && !hypotheses.length) {
    return (
      <p className="text-sm text-ink-muted">Chưa có dữ liệu liên kết nghĩa vụ hoặc giả thuyết.</p>
    );
  }
  return (
    <div className="space-y-3 text-sm">
      {stale && (
        <p className="rounded-control border border-warning/40 bg-warning-soft p-3 text-warning">
          Nội dung ca đã thay đổi. Căn cứ và độ phủ dưới đây thuộc bản trước khi sửa, không còn là
          bằng chứng hiệu lực; khi lưu, hệ thống sẽ yêu cầu đối chiếu lại trước khi duyệt.
        </p>
      )}
      <div>
        <p className="font-medium">Nghĩa vụ kiểm thử</p>
        {obligations.length ? (
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {obligations.map((item, index) => {
              const evidence = obligationEvidence.find((entry) => entry.obligation_key === item);
              const quote = evidence?.evidence_quotes?.[0];
              return (
                <li className="break-words" key={`${item}-${index}`}>
                  {quote?.quote || `Nghĩa vụ liên kết ${index + 1}`}
                  {quote && (
                    <span className="ml-1 text-xs text-ink-muted">
                      · {evidenceReferenceLabel(quote.evidence_ref, sources, index)}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-1 text-ink-muted">Chưa liên kết.</p>
        )}
      </div>
      <div>
        <p className="font-medium">Tiêu chí yêu cầu tại thời điểm tạo</p>
        {snapshotIds.length ? (
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {snapshotIds.map((id, index) => {
              const source = sources.find((item) => item.artifact_version_id === id);
              return (
                <li className="break-words" key={`${id}-${index}`}>
                  {source ? sourceDisplayLabel(source) : `Đã lưu tiêu chí chấp nhận ${index + 1}`}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-1 text-ink-muted">Không lưu tiêu chí chấp nhận tại thời điểm tạo.</p>
        )}
      </div>
      <div>
        <p className="font-medium">Giả thuyết cần phân biệt</p>
        {hypotheses.length ? (
          <ul className="mt-1 space-y-2">
            {hypotheses.map((item, index) => (
              <li
                className="min-w-0 rounded-control bg-surface-quiet p-2"
                key={`${item.source_ref}-${item.technique}-${index}`}
              >
                <p>{valueLabel(item.technique)}</p>
                <p className="mt-1 whitespace-pre-wrap break-words">{item.source_quote}</p>
                {item.existing_case_refs?.length > 0 && (
                  <p className="mt-1 text-xs text-ink-muted">
                    Có {item.existing_case_refs.length} ca hiện hành liên quan
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-ink-muted">Không có giả thuyết được ghi nhận.</p>
        )}
      </div>
    </div>
  );
}

export default function TestCaseCompareWorkspace({
  draftId,
  recoveryIdentity,
  canEdit,
  canManageAttachments,
  projectId,
  canReadMembers,
  onClose,
  onSaved,
  onCompared,
}) {
  const [context, setContext] = useState(null);
  const [result, setResult] = useState(null);
  const [choices, setChoices] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [revisionStale, setRevisionStale] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState("");
  const [members, setMembers] = useState([]);
  const [membersError, setMembersError] = useState("");
  const [membersLoaded, setMembersLoaded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState(() => new Set());
  const [changedFieldsOnly, setChangedFieldsOnly] = useState(false);
  const pendingRequest = useRef(null);
  const saveInFlight = useRef(false);
  const comparisonRequest = useRef(0);
  const [contextDraftId, setContextDraftId] = useState("");
  const onComparedRef = useRef(onCompared);
  const recoveryKey = recoveryIdentity
    ? `veriq:test-case-merge:${draftId}:${encodeURIComponent(recoveryIdentity)}`
    : null;
  const legacyRecoveryKey = `veriq:test-case-merge:${draftId}`;

  useEffect(() => {
    onComparedRef.current = onCompared;
  }, [onCompared]);

  useEffect(() => {
    let active = true;
    if (!projectId || !canReadMembers) {
      setMembers([]);
      setMembersError("");
      setMembersLoaded(false);
      return () => {
        active = false;
      };
    }
    setMembersError("");
    setMembersLoaded(false);
    testingApi
      .listMembers(projectId)
      .then((items) => {
        if (active) {
          setMembers((items || []).filter((item) => item.status === "ACTIVE"));
          setMembersLoaded(true);
        }
      })
      .catch(() => {
        if (active) {
          setMembersError("Không tải được danh sách thành viên dự án.");
          setMembersLoaded(false);
        }
      });
    return () => {
      active = false;
    };
  }, [projectId, canReadMembers]);

  const reloadComparison = async () => {
    if (dirty && !window.confirm("Tải lại sẽ bỏ bản ghép chưa lưu. Bạn muốn tiếp tục?")) return;
    const requestedDraftId = draftId;
    const requestId = ++comparisonRequest.current;
    setContextDraftId("");
    setError("");
    try {
      const refreshed = await testingApi.compareTestDraft(requestedDraftId);
      if (requestId !== comparisonRequest.current) return;
      setContext(refreshed);
      setContextDraftId(requestedDraftId);
      setResult(copyValue(refreshed.draft));
      setChoices([]);
      setDirty(false);
      setRevisionStale(false);
      setNotice("Đã tải lại bản gốc, nguồn và đề xuất mới nhất.");
      pendingRequest.current = null;
      try {
        if (recoveryKey) window.sessionStorage.removeItem(recoveryKey);
      } catch {}
    } catch (reason) {
      if (requestId === comparisonRequest.current) setError(messageOf(reason));
    }
  };

  useEffect(() => {
    let cancelled = false;
    const requestId = ++comparisonRequest.current;
    setContext(null);
    setContextDraftId("");
    setResult(null);
    setChoices([]);
    setError("");
    setSaving(false);
    setRevisionStale(false);
    setDirty(false);
    setNotice("");
    pendingRequest.current = null;
    testingApi
      .compareTestDraft(draftId)
      .then((data) => {
        if (cancelled || requestId !== comparisonRequest.current) return;
        setContext(data);
        setContextDraftId(draftId);
        let recovered = null;
        try {
          const saved = recoveryKey ? window.sessionStorage.getItem(recoveryKey) : null;
          recovered = saved ? JSON.parse(saved) : null;
          window.sessionStorage.removeItem(legacyRecoveryKey);
        } catch {
          recovered = null;
        }
        if (recovered?.dirty && recovered.result && recovered.draftId === draftId) {
          setResult(copyValue(recovered.result));
          setChoices(Array.isArray(recovered.choices) ? recovered.choices : []);
          setDirty(true);
          const sameComparison =
            recovered.revision === data.draft.revision &&
            recovered.comparisonToken === data.comparison_token;
          setRevisionStale(!sameComparison);
          setNotice(
            sameComparison
              ? "Đã khôi phục bản ghép chưa lưu trên thẻ trình duyệt này."
              : "Đã khôi phục nội dung đang sửa, nhưng nguồn hoặc bản nháp đã đổi. Hãy đối chiếu lại trước khi lưu.",
          );
        } else {
          setResult(copyValue(data.draft));
          if (recovered) {
            try {
              window.sessionStorage.removeItem(recoveryKey);
            } catch {}
          }
        }
        onComparedRef.current?.(data.draft, { current: !data.stale_reasons?.length });
      })
      .catch((reason) => {
        if (!cancelled && requestId === comparisonRequest.current) setError(messageOf(reason));
      });
    return () => {
      cancelled = true;
      if (requestId === comparisonRequest.current) comparisonRequest.current += 1;
    };
  }, [draftId, legacyRecoveryKey, recoveryKey]);

  useEffect(() => {
    if (!recoveryKey || !dirty || !result || !context?.draft) return;
    try {
      window.sessionStorage.setItem(
        recoveryKey,
        JSON.stringify({
          draftId,
          revision: context.draft.revision,
          comparisonToken: context.comparison_token,
          result,
          choices,
          dirty,
        }),
      );
    } catch {
      setNotice("Không thể lưu bản phục hồi trên thẻ này; hãy lưu bản ghép lên hệ thống.");
    }
  }, [choices, context, dirty, draftId, recoveryKey, result]);

  const edit = (next, field, source = "MANUAL", stepId = null) => {
    const valueUnchanged =
      typeof next !== "function" && JSON.stringify(next) === JSON.stringify(result);
    const previousChoice = choices.find(
      (choice) => choice.field === field && choice.step_id === stepId,
    );
    if (valueUnchanged && source === "MANUAL") return;
    if (valueUnchanged && previousChoice?.source === source) return;
    setResult((current) => (typeof next === "function" ? next(current) : next));
    setChoices((values) => [
      ...values.filter((choice) => choice.field !== field || choice.step_id !== stepId),
      { field, step_id: stepId, source },
    ]);
    setDirty(true);
    setNotice("");
    pendingRequest.current = null;
  };
  const close = () => {
    if (
      !saving &&
      (!dirty || window.confirm("Bản ghép chưa lưu. Đóng và bỏ các thay đổi chưa lưu?"))
    ) {
      try {
        if (recoveryKey) window.sessionStorage.removeItem(recoveryKey);
      } catch {}
      onClose();
    }
  };
  const save = async () => {
    if (saveInFlight.current || contextDraftId !== draftId || !context?.draft) return;
    saveInFlight.current = true;
    const requestedDraftId = draftId;
    const requestId = comparisonRequest.current;
    setSaving(true);
    setError("");
    const request = pendingRequest.current || {
      expected_revision: context.draft.revision,
      comparison_token: context.comparison_token,
      operation_id: crypto.randomUUID(),
      result,
      choices,
    };
    pendingRequest.current = request;
    let saved;
    try {
      saved = await testingApi.saveTestDraftMerge(requestedDraftId, request);
    } catch (reason) {
      if (requestId !== comparisonRequest.current) {
        saveInFlight.current = false;
        return;
      }
      const comparisonConflict =
        reason.code === "TEST_CASE_COMPARISON_STALE" || reason.code === "REVISION_CONFLICT";
      if (comparisonConflict) {
        setRevisionStale(true);
        setContext((current) => ({
          ...current,
          stale_reasons: [...new Set([...(current?.stale_reasons || []), reason.code])],
        }));
        setError(
          "Nguồn hoặc bản nháp đã đổi. Nội dung đang nhập được giữ nguyên; hãy tải lại và đối chiếu trước khi lưu tiếp.",
        );
      } else {
        setError(messageOf(reason));
      }
      setSaving(false);
      saveInFlight.current = false;
      return;
    }

    if (requestId !== comparisonRequest.current) {
      saveInFlight.current = false;
      return;
    }

    setDirty(false);
    pendingRequest.current = null;
    try {
      window.sessionStorage.removeItem(recoveryKey);
    } catch {}
    setNotice("Đã lưu bản ghép. Ca cần được rà soát lại trước khi duyệt.");
    onSaved(saved.draft);
    try {
      const refreshed = await testingApi.compareTestDraft(requestedDraftId);
      if (requestId !== comparisonRequest.current) return;
      setContext(refreshed);
      setContextDraftId(requestedDraftId);
      setResult(copyValue(refreshed.draft));
      setChoices([]);
      onComparedRef.current?.(refreshed.draft, { current: !refreshed.stale_reasons?.length });
    } catch {
      if (requestId !== comparisonRequest.current) return;
      setRevisionStale(true);
      setContext((current) => ({
        ...current,
        stale_reasons: [
          ...new Set([...(current?.stale_reasons || []), "POST_SAVE_REFRESH_FAILED"]),
        ],
      }));
      setError(
        "Bản ghép đã được lưu, nhưng chưa tải được phiên bản mới nhất. Tải lại dữ liệu đối chiếu trước khi tiếp tục sửa hoặc duyệt.",
      );
    } finally {
      if (requestId === comparisonRequest.current) setSaving(false);
      saveInFlight.current = false;
    }
  };
  if (!result) {
    return (
      <Modal
        isOpen
        onClose={close}
        ariaLabel="So sánh và ghép ca kiểm thử"
        className="w-[min(1600px,100%)] max-w-none max-h-[94dvh] overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>So sánh và ghép ca kiểm thử</ModalTitle>
        </ModalHeader>
        <div className="min-w-0 space-y-4 p-4 sm:p-6">
          {error ? (
            <div
              role="alert"
              className="rounded-control border border-red-200 bg-red-50 p-3 text-sm text-red-800"
            >
              {error}
            </div>
          ) : (
            <p role="status">Đang đọc bản gốc, nguồn và đề xuất AI…</p>
          )}
          {error && (
            <button
              type="button"
              className="secondary-button"
              disabled={saving}
              onClick={() => void reloadComparison()}
            >
              Thử tải dữ liệu đối chiếu lại
            </button>
          )}
        </div>
      </Modal>
    );
  }
  const original = context?.original;
  const proposal = context?.proposal;
  const stale = revisionStale || !!context?.stale_reasons?.length;
  const lineageChanged = choices.some((choice) => {
    const field = choice.field.startsWith("steps.") ? "steps" : choice.field;
    return (
      lineageSensitiveFields.has(choice.field) &&
      JSON.stringify(result?.[field] ?? null) !== JSON.stringify(context?.draft?.[field] ?? null)
    );
  });
  const editable =
    contextDraftId === draftId &&
    canEdit &&
    ["DRAFT", "IN_REVIEW"].includes(context?.draft?.status) &&
    !stale &&
    !saving;
  const acceptAll = (source) => {
    const incoming = source === "AI" ? proposal : original;
    if (!incoming) return;
    const mergeableFields = fields.filter(
      (field) =>
        (field.kind !== "attachments" || canManageAttachments) &&
        (field.kind !== "member" || (canReadMembers && membersLoaded)),
    );
    const next = chooseFields(
      result,
      incoming,
      mergeableFields.map((field) => field.key),
    );
    next.steps = copyValue(incoming.steps || []);
    setResult(next);
    setDirty(true);
    pendingRequest.current = null;
    setChoices([
      ...mergeableFields.map((field) => ({ field: field.key, source })),
      { field: "steps", source },
    ]);
  };
  const comparableFields = fields.filter(
    (field) =>
      (field.key !== "bdd" || result.bdd || original?.bdd || proposal?.bdd) &&
      (field.kind !== "member" || canReadMembers),
  );
  const changedFields = proposal
    ? comparableFields.filter(
        (field) => fieldDifference(original?.[field.key], proposal[field.key]) !== "Không thay đổi",
      )
    : [];
  const visibleFields = changedFieldsOnly ? changedFields : comparableFields;

  return (
    <Modal
      isOpen
      onClose={close}
      ariaLabel="So sánh và ghép ca kiểm thử"
      className="w-[min(1600px,100%)] max-w-none max-h-[94dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>So sánh và ghép ca kiểm thử</ModalTitle>
        <p className="mt-2 text-sm text-ink-muted">
          {context?.draft?.test_case_key} · Bản gốc và đề xuất AI chỉ đọc. Bản kết quả được lưu
          thành nháp, không tự duyệt.
        </p>
      </ModalHeader>
      <div className="min-w-0 space-y-5 p-4 sm:p-6">
        {error && (
          <div
            role="alert"
            className="rounded-control border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            {error}
          </div>
        )}
        {!context && error && (
          <button
            type="button"
            className="secondary-button"
            disabled={saving}
            onClick={() => void reloadComparison()}
          >
            Thử tải dữ liệu đối chiếu lại
          </button>
        )}
        {notice && (
          <p role="status" className="rounded-control bg-brand/10 p-3 text-sm">
            {notice}
          </p>
        )}
        {membersError && canReadMembers && (
          <p role="status" className="rounded-control bg-amber-50 p-3 text-sm text-amber-900">
            Không tải được thành viên dự án; người phụ trách hiện tại được giữ nguyên.{" "}
            {membersError}
          </p>
        )}
        {!context && !error && <p role="status">Đang đọc bản gốc, nguồn và đề xuất AI…</p>}
        {context && result && (
          <>
            {stale && (
              <p
                role="alert"
                className="rounded-control border border-amber-300 bg-amber-50 p-3 text-sm"
              >
                Nguồn hoặc phiên bản gốc không còn hiện hành. Không thể lưu/duyệt đề xuất này; cần
                tạo lại đề xuất từ nguồn đã cập nhật.
              </p>
            )}
            {stale && (
              <button type="button" className="secondary-button" onClick={reloadComparison}>
                Tải lại dữ liệu đối chiếu
              </button>
            )}
            {!context.proposal_available && (
              <p className="text-sm text-ink-muted">
                {context.draft.origin === "ai_generated"
                  ? "Bản nháp cũ không lưu đề xuất AI ban đầu. Hệ thống không coi bản đã chỉnh sửa là bản AI gốc."
                  : "Ca này không có đề xuất AI được lưu; vẫn có thể đối chiếu nguồn và chỉnh bản kết quả."}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {editable && original && (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => acceptAll("ORIGINAL")}
                >
                  Lấy nội dung bản gốc
                </button>
              )}
              {editable && proposal && (
                <button type="button" className="secondary-button" onClick={() => acceptAll("AI")}>
                  Lấy nội dung AI
                </button>
              )}
              {canEdit && (
                <button
                  type="button"
                  className="apple-button"
                  disabled={!editable || !dirty}
                  onClick={save}
                >
                  {saving ? "Đang lưu…" : "Lưu bản ghép"}
                </button>
              )}
              <button type="button" className="secondary-button" disabled={saving} onClick={close}>
                Đóng
              </button>
            </div>
            <div className="grid min-w-0 gap-3 xl:grid-cols-3">
              <section className="min-w-0 rounded-control border border-border bg-surface-quiet p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-semibold">
                    {context.is_new ? "Đặc tả nguồn — ca mới" : "Bản gốc hiện có"}
                  </h4>
                  {!context.is_new && original && (
                    <ContentOriginBadge origin={original.origin || "manual"} />
                  )}
                </div>
                {!context.is_new && original ? (
                  <div className="mt-3 space-y-1 text-sm">
                    <p className="font-medium">{original.title}</p>
                    <p className="text-ink-muted">
                      {original.test_case_key} · Phiên bản {original.version} ·{" "}
                      {(original.steps || []).length} bước
                    </p>
                  </div>
                ) : context.is_new ? (
                  <div className="mt-3 space-y-3">
                    {context.source_evidence.length ? (
                      context.source_evidence.map((item, index) => (
                        <blockquote
                          className="whitespace-pre-wrap break-words border-l-2 border-brand pl-3 text-sm"
                          key={`${item.artifact_version_id}-${index}`}
                        >
                          <p className="mb-1 font-medium">Nguồn {index + 1}</p>
                          {item.text}
                        </blockquote>
                      ))
                    ) : (
                      <p className="text-sm text-ink-muted">Chưa có đặc tả nguồn liên kết.</p>
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-ink-muted">Không có phiên bản gốc.</p>
                )}
              </section>
              <section className="min-w-0 rounded-control border border-violet-300 bg-violet-50/60 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-semibold">Đề xuất AI ban đầu</h4>
                  <ContentOriginBadge origin="ai_generated" />
                </div>
                {proposal ? (
                  <div className="mt-3 space-y-1 text-sm">
                    <p className="font-medium">{proposal.title}</p>
                    <p className="text-ink-muted">
                      {(proposal.steps || []).length} bước · {proposal.evidence_quotes?.length || 0}{" "}
                      trích dẫn nguồn
                    </p>
                    <p className="text-xs text-ink-muted">
                      Bản đề xuất gốc được giữ nguyên khi chỉnh kết quả.
                    </p>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-ink-muted">Không lưu bản đề xuất AI.</p>
                )}
              </section>
              <section className="min-w-0 rounded-control border border-brand/30 bg-brand/5 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-semibold">Bản kết quả sau chọn/ghép</h4>
                  <ContentOriginBadge origin="manual" humanLabel="Bản người dùng chọn/ghép" />
                </div>
                <div className="mt-3 space-y-1 text-sm">
                  <p className="font-medium">{result.title || "Chưa có tên ca"}</p>
                  <p className="text-ink-muted">
                    {result.test_case_key} · {result.steps?.length || 0} bước · Bản nháp lần cập
                    nhật {context.draft.revision}
                  </p>
                  <p className="text-xs text-ink-muted">
                    {editable ? "Chọn từng trường hoặc tự chỉnh sửa bên dưới." : "Chế độ chỉ đọc."}
                  </p>
                </div>
              </section>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-control bg-surface-quiet p-3">
              <p className="text-sm" aria-live="polite">
                {proposal
                  ? `${changedFields.length} / ${comparableFields.length} trường có khác biệt giữa bản gốc và đề xuất.`
                  : "Không có đề xuất AI để so sánh trường; bạn vẫn có thể chỉnh bản kết quả."}
              </p>
              <button
                type="button"
                className="secondary-button"
                aria-pressed={changedFieldsOnly}
                onClick={() => setChangedFieldsOnly((value) => !value)}
              >
                {changedFieldsOnly ? "Hiện tất cả trường" : "Chỉ xem trường khác biệt"}
              </button>
            </div>
            {visibleFields.map((field) => {
              const selectedSource = choices.find(
                (choice) => choice.field === field.key && !choice.step_id,
              )?.source;
              const selectedSourceLabel =
                selectedSource === "ORIGINAL"
                  ? "Đang chọn bản gốc"
                  : selectedSource === "AI"
                    ? "Đang chọn đề xuất AI"
                    : selectedSource === "MANUAL"
                      ? "Đã chỉnh thủ công"
                      : "Chưa chọn riêng trường này";
              return (
                <section key={field.key} className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-medium">{field.label}</h4>
                    <span className="rounded-full bg-surface-quiet px-2 py-1 text-[11px] text-ink-muted">
                      {selectedSourceLabel}
                    </span>
                    {proposal && (
                      <span className="text-xs text-ink-muted">
                        {fieldDifference(original?.[field.key], proposal[field.key])}
                      </span>
                    )}
                  </div>
                  <div className="grid min-w-0 gap-3 xl:grid-cols-3">
                    <div className="min-w-0 rounded-control border border-border p-3 text-sm">
                      <p className="mb-2 text-xs text-ink-muted lg:hidden">Bản gốc</p>
                      <ReadValue
                        value={original?.[field.key]}
                        kind={field.kind}
                        customFields={context.custom_fields || []}
                        members={members}
                      />
                      {editable &&
                        original &&
                        (field.kind !== "attachments" || canManageAttachments) &&
                        (field.kind !== "member" || (canReadMembers && membersLoaded)) && (
                          <button
                            type="button"
                            className="secondary-button mt-3"
                            onClick={() =>
                              edit(
                                chooseFields(result, original, [field.key]),
                                field.key,
                                "ORIGINAL",
                              )
                            }
                          >
                            Dùng bản gốc
                          </button>
                        )}
                    </div>
                    <div className="min-w-0 rounded-control border border-border p-3 text-sm">
                      <p className="mb-2 text-xs text-ink-muted lg:hidden">Đề xuất AI</p>
                      <ReadValue
                        value={proposal?.[field.key]}
                        kind={field.kind}
                        customFields={context.custom_fields || []}
                        members={members}
                      />
                      {editable &&
                        proposal &&
                        (field.kind !== "attachments" || canManageAttachments) &&
                        (field.kind !== "member" || canReadMembers) && (
                          <button
                            type="button"
                            className="secondary-button mt-3"
                            onClick={() =>
                              edit(chooseFields(result, proposal, [field.key]), field.key, "AI")
                            }
                          >
                            Dùng đề xuất AI
                          </button>
                        )}
                    </div>
                    <div className="min-w-0 rounded-control border border-brand/30 p-3">
                      <p className="mb-2 text-xs text-ink-muted lg:hidden">Bản kết quả</p>
                      {editable ? (
                        <FieldEditor
                          field={field}
                          value={result[field.key]}
                          customFields={context.custom_fields || []}
                          members={members}
                          canReadMembers={canReadMembers}
                          membersLoaded={membersLoaded}
                          canManageAttachments={canManageAttachments}
                          onChange={(value) => {
                            if (field.kind === "member" && (!canReadMembers || !membersLoaded))
                              return;
                            if (field.kind === "attachments" && typeof value === "function") {
                              edit(
                                (current) => ({
                                  ...current,
                                  attachments: value(current.attachments || []),
                                }),
                                field.key,
                              );
                            } else {
                              edit({ ...result, [field.key]: value }, field.key);
                            }
                          }}
                          disabled={!editable}
                        />
                      ) : (
                        <ReadValue
                          value={result[field.key]}
                          kind={field.kind}
                          customFields={context.custom_fields || []}
                          members={members}
                        />
                      )}
                    </div>
                  </div>
                </section>
              );
            })}
            <section className="min-w-0 space-y-3">
              <div>
                <h4 className="font-semibold">Nguồn dẫn và trích dẫn</h4>
                <p className="text-sm text-ink-muted">
                  Đây là dấu vết căn cứ được lưu cùng ca; không chỉnh sửa nội dung trích dẫn tại màn
                  ghép.
                </p>
              </div>
              <div className="grid min-w-0 gap-3 xl:grid-cols-3">
                {[
                  [
                    "Nguồn gốc",
                    original ||
                      (context.is_new ? { source_evidence: context.source_evidence } : null),
                  ],
                  ["Đề xuất AI", proposal],
                  ["Bản kết quả", result],
                ].map(([label, value]) => (
                  <section className="min-w-0 rounded-control border border-border p-3" key={label}>
                    <h5 className="mb-2 text-sm font-medium">{label}</h5>
                    <EvidenceValue
                      value={
                        label === "Bản kết quả"
                          ? {
                              ...value,
                              source_evidence: value?.source_evidence || context.source_evidence,
                            }
                          : value
                      }
                    />
                  </section>
                ))}
              </div>
            </section>
            <section className="min-w-0 space-y-3">
              <div>
                <h4 className="font-semibold">Liên kết độ phủ và căn cứ sinh ca</h4>
                <p className="text-sm text-ink-muted">
                  Đây là dữ liệu truy vết chỉ đọc. Sửa nội dung kiểm thử sẽ vô hiệu hóa căn cứ và độ
                  phủ hiện tại khi lưu.
                </p>
              </div>
              <div className="grid min-w-0 gap-3 xl:grid-cols-3">
                {[
                  ["Bản gốc", original],
                  ["Đề xuất AI", proposal],
                  ["Bản kết quả", result],
                ].map(([label, value]) => (
                  <section className="min-w-0 rounded-control border border-border p-3" key={label}>
                    <h5 className="mb-2 text-sm font-medium">{label}</h5>
                    <CoverageLineageValue
                      value={value}
                      stale={label === "Bản kết quả" && lineageChanged}
                    />
                  </section>
                ))}
              </div>
            </section>
            <section className="min-w-0 space-y-3">
              <h4 className="font-semibold">Các bước kiểm thử — so sánh từng bước</h4>
              {comparedStepIds(original, proposal, result).map((id) => {
                const before = original?.steps?.find((step) => step.id === id);
                const suggested = proposal?.steps?.find((step) => step.id === id);
                const final = result.steps?.find((step) => step.id === id);
                return (
                  <details
                    key={id}
                    className="min-w-0 rounded-control border border-border p-3"
                    onToggle={(event) => {
                      const isOpen = event.currentTarget.open;
                      setExpandedSteps((current) => {
                        const next = new Set(current);
                        if (isOpen) next.add(id);
                        else next.delete(id);
                        return next;
                      });
                    }}
                  >
                    <summary className="cursor-pointer break-words font-medium">
                      {final ? `Bước ${final.order}` : "Bước đã bỏ khỏi kết quả"}
                    </summary>
                    {expandedSteps.has(id) && (
                      <div className="mt-3 grid min-w-0 gap-3 xl:grid-cols-3">
                        {[before, suggested].map((step, index) => (
                          <div className="min-w-0 space-y-2 text-sm" key={index}>
                            <p className="font-medium">{index === 0 ? "Bản gốc" : "Đề xuất AI"}</p>
                            {step ? (
                              <>
                                <ReadValue value={step.action_doc} kind="document" />
                                <p className="text-xs font-medium">Dữ liệu</p>
                                <ReadValue value={step.test_data} kind="data" />
                                <p className="text-xs font-medium">Kết quả mong đợi</p>
                                <ReadValue value={step.expected_doc} kind="document" />
                                {editable && (
                                  <button
                                    className="secondary-button"
                                    type="button"
                                    onClick={() =>
                                      edit(
                                        chooseStep(result, step),
                                        "steps",
                                        index === 0 ? "ORIGINAL" : "AI",
                                        id,
                                      )
                                    }
                                  >
                                    Dùng bước này
                                  </button>
                                )}
                              </>
                            ) : (
                              <div className="space-y-2">
                                <p className="text-ink-muted">Không có bước này.</p>
                                {editable && final && (
                                  <button
                                    className="secondary-button"
                                    type="button"
                                    onClick={() =>
                                      edit(
                                        chooseStepSource(result, id, null),
                                        "steps",
                                        index === 0 ? "ORIGINAL" : "AI",
                                        id,
                                      )
                                    }
                                  >
                                    Dùng lựa chọn bỏ bước của {index === 0 ? "bản gốc" : "AI"}
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                        <div className="min-w-0 space-y-3">
                          <p className="font-medium">Bản kết quả</p>
                          {final ? (
                            <>
                              {editable ? (
                                <>
                                  {["action_doc", "expected_doc"].map((key) => (
                                    <div key={key}>
                                      <p className="mb-1 text-sm font-medium">
                                        {key === "action_doc" ? "Hành động" : "Kết quả mong đợi"}
                                      </p>
                                      <DocumentEditor
                                        value={final[key] || emptyDoc()}
                                        ignoreUnfocusedUpdates
                                        onChange={(value) =>
                                          edit(
                                            chooseStep(result, { ...final, [key]: value }),
                                            `steps.${key}`,
                                            "MANUAL",
                                            id,
                                          )
                                        }
                                      />
                                      <div className="mt-1 flex flex-wrap gap-2">
                                        {before && (
                                          <button
                                            type="button"
                                            className="secondary-button text-xs"
                                            onClick={() =>
                                              edit(
                                                chooseStep(result, {
                                                  ...final,
                                                  [key]: copyValue(before[key]),
                                                }),
                                                `steps.${key}`,
                                                "ORIGINAL",
                                                id,
                                              )
                                            }
                                          >
                                            Dùng phần gốc
                                          </button>
                                        )}
                                        {suggested && (
                                          <button
                                            type="button"
                                            className="secondary-button text-xs"
                                            onClick={() =>
                                              edit(
                                                chooseStep(result, {
                                                  ...final,
                                                  [key]: copyValue(suggested[key]),
                                                }),
                                                `steps.${key}`,
                                                "AI",
                                                id,
                                              )
                                            }
                                          >
                                            Dùng phần AI
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                  <div className="space-y-2">
                                    <DataEditor
                                      value={final.test_data || {}}
                                      label={`Bước ${final.order}`}
                                      onChange={(value) =>
                                        edit(
                                          chooseStep(result, { ...final, test_data: value }),
                                          "steps.test_data",
                                          "MANUAL",
                                          id,
                                        )
                                      }
                                    />
                                    <div className="flex flex-wrap gap-2">
                                      {before && (
                                        <button
                                          className="secondary-button text-xs"
                                          type="button"
                                          onClick={() =>
                                            edit(
                                              chooseStep(
                                                result,
                                                chooseFields(final, before, ["test_data"]),
                                              ),
                                              "steps.test_data",
                                              "ORIGINAL",
                                              id,
                                            )
                                          }
                                        >
                                          Dùng dữ liệu gốc
                                        </button>
                                      )}
                                      {suggested && (
                                        <button
                                          className="secondary-button text-xs"
                                          type="button"
                                          onClick={() =>
                                            edit(
                                              chooseStep(
                                                result,
                                                chooseFields(final, suggested, ["test_data"]),
                                              ),
                                              "steps.test_data",
                                              "AI",
                                              id,
                                            )
                                          }
                                        >
                                          Dùng dữ liệu AI
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    <button
                                      className="secondary-button"
                                      type="button"
                                      disabled={final.order === 1}
                                      onClick={() =>
                                        edit(moveStep(result, id, -1), "steps", "MANUAL", id)
                                      }
                                    >
                                      Lên
                                    </button>
                                    <button
                                      className="secondary-button"
                                      type="button"
                                      disabled={final.order === result.steps.length}
                                      onClick={() =>
                                        edit(moveStep(result, id, 1), "steps", "MANUAL", id)
                                      }
                                    >
                                      Xuống
                                    </button>
                                    <button
                                      className="secondary-button"
                                      type="button"
                                      onClick={() =>
                                        edit(removeStep(result, id), "steps", "MANUAL", id)
                                      }
                                    >
                                      Bỏ bước
                                    </button>
                                  </div>
                                </>
                              ) : (
                                <>
                                  <ReadValue value={final.action_doc} kind="document" />
                                  <ReadValue value={final.expected_doc} kind="document" />
                                </>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-ink-muted">
                              Bước không nằm trong bản kết quả.
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </details>
                );
              })}
              {editable && (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    const id = crypto.randomUUID();
                    edit(
                      chooseStep(result, {
                        id,
                        order: (result.steps?.length || 0) + 1,
                        action_doc: emptyDoc(),
                        test_data: {},
                        expected_doc: emptyDoc(),
                      }),
                      "steps",
                      "MANUAL",
                      id,
                    );
                  }}
                >
                  Thêm bước vào bản kết quả
                </button>
              )}
            </section>
            {!!context.duplicates?.length && (
              <section className="space-y-2 rounded-control border border-amber-300 bg-amber-50 p-4">
                <h4 className="font-semibold">Ca đã có nội dung gần giống</h4>
                <p className="text-sm">
                  Rà soát các ca này trước khi duyệt để tránh tạo trùng ngoài ý muốn.
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {context.duplicates.map((item) => (
                    <li key={item.version_id}>
                      {item.test_case_key} · {item.title} · v{item.version} · tương đồng{" "}
                      {Math.round(item.score * 100)}%
                      {item.reasons?.length ? ` — ${item.reasons.join(", ")}` : ""}
                    </li>
                  ))}
                </ul>
                <label className="field-label mt-3">
                  Lý do giữ ca này riêng sau khi QA rà soát trùng lặp
                  <textarea
                    className="apple-input min-h-24"
                    value={result.duplicate_reason || ""}
                    disabled={!editable}
                    onChange={(event) =>
                      edit({ ...result, duplicate_reason: event.target.value }, "duplicate_reason")
                    }
                  />
                </label>
                <p className="text-xs text-ink-muted">
                  Cần ghi lý do trước khi QA có thể duyệt một ca đang gần giống ca đã có.
                </p>
              </section>
            )}
            {!!context.findings?.length && (
              <section>
                <h4 className="font-semibold">Kết quả kiểm tra bản nháp đã lưu</h4>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                  {context.findings.map((finding, index) => (
                    <li key={index}>
                      {finding.message || finding.suggestion || "Cần rà soát nội dung ca kiểm thử."}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
