import { useEffect, useState } from "react";
import { testingApi } from "../../../services/testing.service";
import { docText, messageOf, textDoc, valueLabel } from "../../../lib/testing";
import DocumentEditor from "../../../editor/DocumentEditor";
import { REQUIREMENT_LEVELS, REQUIREMENT_TYPES } from "./requirements.model";

function templateError(reason) {
  const messages = {
    TEMPLATE_SOURCE_MISSING: "Không tìm thấy tài liệu nguồn",
    DOCUMENT_AI_ACCESS_DISABLED: "Tài liệu nguồn chưa được cho phép AI đọc",
    TEMPLATE_SOURCE_NOT_DECLARED: "Nguồn trích dẫn chưa được chọn cho mẫu",
    TEMPLATE_NOT_EDITABLE: "Mẫu này không còn ở trạng thái cho phép sửa",
    TEMPLATE_VERSION_CONFLICT: "Mẫu đã thay đổi  Hãy tải lại trước khi lưu",
    TEMPLATE_CONFLICT_RESOLUTION_REQUIRED: "Cần giải quyết mọi mâu thuẫn trước khi lưu",
    TEMPLATE_CONFLICT_REQUIRES_REVIEW: "Cần rà soát và lưu quyết định cho các mâu thuẫn",
    TEMPLATE_HAS_NO_REQUIREMENTS: "Mẫu chưa có yêu cầu để nhập",
    TEMPLATE_REQUIREMENT_INCOMPLETE: "Yêu cầu còn thiếu thông tin tối thiểu hoặc nguồn dẫn",
    TEMPLATE_SOURCE_TOO_LARGE: "Tài liệu nguồn vượt giới hạn xử lý",
    TEMPLATE_SOURCE_EMPTY: "Tài liệu nguồn không có nội dung phù hợp",
    TEMPLATE_SYNTHESIS_UNAVAILABLE: "AI chưa thể tổng hợp mẫu  Hãy thử lại",
    TEMPLATE_AI_NO_REQUIREMENTS: "AI chưa rút được yêu cầu có nguồn dẫn hợp lệ",
    TEMPLATE_AI_UNSUPPORTED_CONTEXT: "Bối cảnh AI đề xuất không có trong nguồn đã chọn",
    TEMPLATE_REVIEW_UNAVAILABLE: "AI chưa thể kiểm tra mẫu  Hãy thử lại",
    TEMPLATE_REVIEW_INVALID: "Kết quả kiểm tra mẫu không hợp lệ",
    TEMPLATE_REVIEW_UNSUPPORTED_SUGGESTION: "Đề xuất của AI không khớp tài liệu được phép đọc",
    TEMPLATE_EVIDENCE_INVALID: "Trích dẫn AI trả về không khớp tài liệu nguồn",
    TEMPLATE_SOURCE_QUOTE_INVALID: "Đoạn trích AI trả về không có trong tài liệu nguồn",
    TEMPLATE_EVIDENCE_MISSING: "Yêu cầu AI đề xuất thiếu trích dẫn nguồn",
    TEMPLATE_USER_STORY_SOURCE_REQUIRED: "Không tìm thấy nguồn chứng minh nội dung User Story",
    TEMPLATE_TOO_MANY_REQUIREMENTS: "Mẫu có quá nhiều yêu cầu",
    CUSTOM_FIELD_MANAGER_REQUIRED: "Chỉ QA quản trị dự án được định nghĩa trường mở rộng",
    CUSTOM_FIELD_EXISTS: "Mã trường mở rộng đã tồn tại",
    TEMPLATE_NOT_PUBLISHABLE: "Mẫu này chưa đủ điều kiện đề nghị phát hành",
    PUBLIC_TEMPLATE_INCOMPLETE: "Bản công khai còn thiếu nội dung yêu cầu",
    PUBLIC_TEMPLATE_PRIVATE_METADATA: "Bản công khai còn chứa thông tin riêng của dự án",
    DOCUMENT_OWNER_CONSENT_REQUIRED: "Cần chủ tài liệu đồng ý trước khi phát hành",
    DOCUMENT_OWNER_REQUIRED: "Chỉ chủ tài liệu được quyết định quyền sử dụng nguồn",
    TEMPLATE_APPROVER_REQUIRED: "Chỉ QA được duyệt mẫu dùng chung",
    TEMPLATE_APPROVAL_INVALID: "Không thể duyệt đề nghị phát hành này",
  };
  return messages[reason?.code] || messageOf(reason);
}

function emptyRequirement() {
  return {
    title: "",
    type: "functional",
    requirement_key: "",
    priority: "medium",
    risk: "medium",
    owner_id: "",
    source_status: "",
    actors: "",
    business_rules: "",
    dependencies: "",
    tags: "",
    content_doc: textDoc(""),
    acceptance: "",
    actor: "",
    goal: "",
    value: "",
    main_flow: "",
    exception_flow: "",
    data_rules: "",
    integration: "",
    quality_measure: "",
    api_operations: [],
    custom_values: {},
    source_refs: [],
    section_states: {},
  };
}

function fromStored(item) {
  const details = item.details || {};
  return {
    ...emptyRequirement(),
    ...item,
    content_doc: item.content_doc || textDoc(""),
    actors: (item.actors || []).join("\n"),
    business_rules: (item.business_rules || []).join("\n"),
    dependencies: (item.dependencies || []).join("\n"),
    tags: (item.tags || []).join(", "),
    acceptance: (item.acceptance_criteria || [])
      .map((value) => docText(value.content_doc))
      .join("\n"),
    actor: details.user_story?.actor || "",
    goal: details.user_story?.goal || "",
    value: details.user_story?.value || "",
    source_status: details.source_status || "",
    main_flow: details.main_flow || "",
    exception_flow: details.exception_flow || "",
    data_rules: details.data_rules || "",
    integration: details.integration || "",
    quality_measure: details.quality_measure || "",
    api_operations: details.api_operations || [],
    section_states: Object.fromEntries(
      Object.entries(item.section_states || {}).map(([key, state]) => [
        key.startsWith("user_story.") ? key.slice("user_story.".length) : key,
        state,
      ]),
    ),
  };
}

function toStored(item, fields) {
  const details = {};
  if (item.actor || item.goal || item.value) {
    details.user_story = { actor: item.actor, goal: item.goal, value: item.value };
  }
  if (item.source_status) details.source_status = item.source_status;
  if (item.api_operations?.length) details.api_operations = item.api_operations;
  for (const key of [
    "main_flow",
    "exception_flow",
    "data_rules",
    "integration",
    "quality_measure",
  ]) {
    if (item[key]) details[key] = item[key];
  }
  const custom_values = {};
  for (const field of fields) {
    const value = item.custom_values?.[field.key];
    if (value === undefined || value === "") continue;
    custom_values[field.key] = field.value_type === "number" ? Number(value) : value;
  }
  const section_states = Object.fromEntries(
    Object.entries(item.section_states || {}).map(([key, state]) => [
      new Set(["actor", "goal", "value"]).has(key) ? `user_story.${key}` : key,
      state,
    ]),
  );
  if (details.user_story) section_states.user_story = "provided";
  else delete section_states.user_story;
  return {
    requirement_key: item.requirement_key || null,
    title: item.title.trim(),
    type: item.type,
    priority: item.priority,
    risk: item.risk,
    owner_id: item.owner_id || null,
    actors: item.actors
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean),
    business_rules: item.business_rules
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean),
    dependencies: item.dependencies
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean),
    tags: item.tags
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    content_doc: item.content_doc,
    acceptance_criteria: item.acceptance
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean)
      .map((value, index) => ({ key: `AC-${index + 1}`, content_doc: textDoc(value) })),
    details,
    section_states,
    custom_values,
    source_refs: item.source_refs || [],
  };
}

export default function RequirementTemplatePanel({
  project,
  members,
  sourceDocuments,
  onPreview,
  onError,
  isOpen,
}) {
  const [templates, setTemplates] = useState([]);
  const [fields, setFields] = useState([]);
  const [selectedTemplateIds, setSelectedTemplateIds] = useState([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [active, setActive] = useState(null);
  const [name, setName] = useState("");
  const [productTypes, setProductTypes] = useState([project.project_type || "web"]);
  const [context, setContext] = useState({
    objectives: "",
    in_scope: "",
    out_of_scope: "",
    stakeholders: "",
    actors_and_systems: "",
    glossary: "",
    assumptions: "",
    constraints: "",
  });
  const [requirements, setRequirements] = useState([emptyRequirement()]);
  const [resolutions, setResolutions] = useState([]);
  const [publicName, setPublicName] = useState("");
  const [publicContext, setPublicContext] = useState("");
  const [publicRequirements, setPublicRequirements] = useState([
    { title: "", type: "functional", content: "", acceptance: "" },
  ]);
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState(null);
  const [fieldDraft, setFieldDraft] = useState({
    key: "",
    label: "",
    value_type: "text",
    required: false,
    choices: "",
  });

  useEffect(() => {
    if (!isOpen) return;
    Promise.all([
      testingApi.listRequirementTemplates(project._id),
      testingApi.listRequirementFields(project._id),
    ])
      .then(([values, definitions]) => {
        setTemplates(values);
        setFields(definitions);
      })
      .catch((reason) => onError(templateError(reason)));
  }, [isOpen, project._id, onError]);

  const loadTemplate = (template) => {
    setReview(null);
    setActive(template);
    setName(template.name);
    setProductTypes(template.product_types || [project.project_type || "web"]);
    setContext(template.context || {});
    setRequirements(
      template.requirements?.length ? template.requirements.map(fromStored) : [emptyRequirement()],
    );
    setSelectedDocumentIds(template.source_document_ids || []);
    setSelectedTemplateIds(template.source_template_ids || []);
    setResolutions((template.synthesis?.conflicts || []).map(() => ""));
  };

  const updateRequirement = (index, patch) =>
    setRequirements((items) =>
      items.map((item, position) => (position === index ? { ...item, ...patch } : item)),
    );

  const run = async (action) => {
    setBusy(true);
    try {
      await action();
    } catch (reason) {
      onError(templateError(reason));
    } finally {
      setBusy(false);
    }
  };

  const synthesize = () =>
    run(async () => {
      const template = await testingApi.synthesizeRequirementTemplate(project._id, {
        name: name.trim() || "Mẫu yêu cầu tổng hợp",
        product_types: productTypes,
        source_document_ids: selectedDocumentIds,
        source_template_ids: selectedTemplateIds,
      });
      setTemplates((items) => [template, ...items]);
      loadTemplate(template);
    });

  const save = () =>
    run(async () => {
      const payload = {
        name: name.trim(),
        description: "",
        product_types: productTypes,
        context: Object.fromEntries(
          Object.entries(context).map(([key, value]) => [
            key,
            typeof value === "string" ? value.trim() : value,
          ]),
        ),
        requirements: requirements
          .filter((item) => item.title.trim() || docText(item.content_doc).trim())
          .map((item) => toStored(item, fields)),
        source_document_ids: selectedDocumentIds,
        source_template_ids: selectedTemplateIds.filter((id) => id !== active?._id),
      };
      const template =
        active?.project_id === project._id && active.status === "DRAFT"
          ? await testingApi.updateRequirementTemplate(project._id, active._id, {
              ...payload,
              expected_version: active.version,
              conflict_resolutions: resolutions,
            })
          : await testingApi.createRequirementTemplate(project._id, payload);
      setTemplates((items) => [template, ...items.filter((item) => item._id !== template._id)]);
      loadTemplate(template);
    });

  const preview = () =>
    run(async () => {
      const job = await testingApi.previewRequirementTemplate(project._id, active._id);
      if (job.status !== "PREVIEW_READY") {
        onError(
          job.status === "CONFIRMED"
            ? "Phiên bản mẫu này đã được nhập  Hãy cập nhật mẫu thành phiên bản mới nếu có nội dung cần nhập thêm"
            : "Lần nhập từ phiên bản mẫu này đang được xử lý  Hãy kiểm tra lại sau",
        );
        return;
      }
      onError("");
      onPreview(job);
    });

  const reviewSaved = () =>
    run(async () => {
      setReview(null);
      setReview(await testingApi.reviewRequirementTemplate(project._id, active._id));
    });

  const addField = () =>
    run(async () => {
      const field = await testingApi.createRequirementField(project._id, {
        ...fieldDraft,
        choices:
          fieldDraft.value_type === "choice"
            ? fieldDraft.choices
                .split("\n")
                .map((value) => value.trim())
                .filter(Boolean)
            : [],
        requirement_types: [],
      });
      setFields((items) => [...items, field]);
      setFieldDraft({ key: "", label: "", value_type: "text", required: false, choices: "" });
    });

  const refreshTemplate = (template) => {
    setTemplates((items) => [template, ...items.filter((item) => item._id !== template._id)]);
    loadTemplate(template);
  };

  const requestPublication = () =>
    run(async () => {
      const template = await testingApi.requestRequirementTemplatePublication(
        project._id,
        active._id,
        {
          expected_version: active.version,
          public_template: {
            name: publicName.trim(),
            description: "",
            product_types: productTypes,
            context: { objectives: publicContext.trim() },
            requirements: publicRequirements
              .filter((item) => item.title.trim() && item.content.trim())
              .map((item) => ({
                title: item.title.trim(),
                type: item.type,
                content_doc: textDoc(item.content.trim()),
                acceptance_criteria: item.acceptance
                  .split("\n")
                  .map((value) => value.trim())
                  .filter(Boolean)
                  .map((value, index) => ({ key: `AC-${index + 1}`, content_doc: textDoc(value) })),
              })),
            source_document_ids: [],
            source_template_ids: [],
          },
        },
      );
      refreshTemplate(template);
    });

  const consent = (documentId, approved) =>
    run(async () => {
      refreshTemplate(
        await testingApi.consentRequirementTemplatePublication(project._id, active._id, {
          document_id: documentId,
          approved,
        }),
      );
    });

  const approve = () =>
    run(async () => {
      refreshTemplate(
        await testingApi.approveRequirementTemplatePublication(project._id, active._id),
      );
    });

  const toggle = (values, value, setter) =>
    setter(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  const publicationPreview =
    active?.status === "PENDING_PUBLICATION" ? active.public_template || active : null;

  return (
    <section className="space-y-5 border-b border-border p-5">
      <div>
        <h3 className="text-base font-semibold">Mẫu yêu cầu</h3>
        <p className="text-sm text-ink-muted">
          Tạo mẫu riêng của dự án hoặc tổng hợp từ mẫu và tài liệu đã cho phép AI đọc
        </p>
        {busy && (
          <p className="mt-2 text-sm" role="status">
            AI hoặc hệ thống đang xử lý mẫu yêu cầu
          </p>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2 rounded-control border border-border p-3">
          <p className="text-sm font-medium">Mẫu thư viện và mẫu dự án</p>
          {templates.map((template) => (
            <div className="flex items-center justify-between gap-2 text-sm" key={template._id}>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedTemplateIds.includes(template._id)}
                  onChange={() => toggle(selectedTemplateIds, template._id, setSelectedTemplateIds)}
                />
                {template.name}{" "}
                {template.status === "STARTER" ? "Mẫu khởi đầu" : `v${template.version}`}
              </label>
              <button
                className="text-accent underline"
                type="button"
                onClick={() => loadTemplate(template)}
              >
                Mở
              </button>
            </div>
          ))}
        </div>
        <div className="space-y-2 rounded-control border border-border p-3">
          <p className="text-sm font-medium">Tài liệu nguồn cho AI</p>
          {sourceDocuments
            .filter((document) => document.ai_enabled)
            .map((document) => (
              <label className="flex items-center gap-2 text-sm" key={document._id}>
                <input
                  type="checkbox"
                  checked={selectedDocumentIds.includes(document._id)}
                  onChange={() => toggle(selectedDocumentIds, document._id, setSelectedDocumentIds)}
                />
                {document.filename}
              </label>
            ))}
          {!sourceDocuments.some((document) => document.ai_enabled) && (
            <p className="text-sm text-ink-muted">Chưa có tài liệu được cho phép AI đọc</p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="field-label grow">
          Tên mẫu
          <input
            className="apple-input mt-2"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="field-label">
          Loại sản phẩm
          <select
            className="apple-input mt-2"
            value={productTypes[0] || "web"}
            onChange={(event) => setProductTypes([event.target.value])}
          >
            {["web", "mobile", "api", "desktop", "embedded", "other"].map((value) => (
              <option key={value} value={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="secondary-button"
          type="button"
          disabled={busy || !(selectedTemplateIds.length || selectedDocumentIds.length)}
          onClick={synthesize}
        >
          AI tổng hợp bản nháp
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={() =>
            loadTemplate({
              name: "",
              product_types: [project.project_type || "web"],
              context: {},
              requirements: [],
              status: "NEW",
            })
          }
        >
          Tạo mẫu mới
        </button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {[
          ["objectives", "Mục tiêu"],
          ["in_scope", "Trong phạm vi"],
          ["out_of_scope", "Ngoài phạm vi"],
          ["stakeholders", "Các bên liên quan"],
          ["actors_and_systems", "Tác nhân và hệ thống"],
          ["glossary", "Thuật ngữ"],
          ["assumptions", "Giả định"],
          ["constraints", "Ràng buộc dự án"],
        ].map(([key, label]) => (
          <label className="field-label" key={key}>
            {label}
            <textarea
              className="apple-input mt-2"
              rows={2}
              value={Array.isArray(context[key]) ? context[key].join("\n") : context[key] || ""}
              onChange={(event) => setContext((value) => ({ ...value, [key]: event.target.value }))}
            />
          </label>
        ))}
      </div>
      {(active?.synthesis?.conflicts || []).map((conflict, index) => (
        <label className="field-label block" key={index}>
          Mâu thuẫn cần quyết định {conflict.title || index + 1}
          <span className="mt-1 block text-sm text-ink-muted">
            {{
              DUPLICATE_TITLE_SAME_CONTENT: "Yêu cầu bị lặp tên và nội dung",
              DUPLICATE_TITLE_DIFFERENT_CONTENT: "Cùng tên nhưng khác nội dung",
              DUPLICATE_CONTENT_DIFFERENT_TITLE: "Cùng nội dung nhưng khác tên",
              CONTEXT_SOURCE_CONFLICT: "Bối cảnh từ các nguồn không thống nhất",
            }[conflict.reason] || conflict.reason}
            {conflict.values?.length ? `  ${conflict.values.join("  hoặc  ")}` : ""}
          </span>
          <span className="mt-1 block text-sm text-ink-muted">
            {conflict.reason === "CONTEXT_SOURCE_CONFLICT"
              ? "Chọn nội dung cuối cùng ở phần Bối cảnh rồi nhập lại chính nội dung đó vào ô dưới"
              : "Sửa hoặc bỏ yêu cầu trùng trong danh sách trước khi ghi quyết định vào ô dưới"}
          </span>
          <input
            className="apple-input mt-2"
            value={resolutions[index] || ""}
            onChange={(event) =>
              setResolutions((items) =>
                items.map((value, position) => (position === index ? event.target.value : value)),
              )
            }
          />
        </label>
      ))}
      {active?.synthesis?.warnings?.length > 0 && (
        <div className="rounded-control border border-border p-3 text-sm">
          <p className="font-medium">Lưu ý khi tổng hợp</p>
          {active.synthesis.warnings.map((warning, index) => (
            <p className="mt-1" key={index}>
              {warning === "SOURCE_TEMPLATES_HAVE_NO_REQUIREMENTS"
                ? "Các mẫu nguồn chỉ có cấu trúc  Cần bổ sung yêu cầu trước khi nhập"
                : warning === "TEMPLATE_CONTEXT_FIELD_IGNORED"
                  ? "AI đề xuất một trường bối cảnh ngoài cấu trúc mẫu  Trường đó đã bị bỏ qua"
                  : warning === "TEMPLATE_CONTEXT_NOT_IN_SOURCE"
                    ? "AI đề xuất bối cảnh không có trong tài liệu nguồn  Nội dung đó đã bị bỏ qua"
                    : warning}
            </p>
          ))}
        </div>
      )}
      <div className="space-y-3">
        {requirements.map((item, index) => (
          <div className="space-y-3 rounded-control border border-border p-4" key={index}>
            <div className="flex justify-between">
              <p className="font-medium">Yêu cầu {index + 1}</p>
              <button
                className="text-sm text-danger underline"
                type="button"
                onClick={() =>
                  setRequirements((items) => items.filter((_, position) => position !== index))
                }
              >
                Bỏ mục
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="field-label">
                Tên yêu cầu
                <input
                  className="apple-input mt-2"
                  value={item.title}
                  onChange={(event) => updateRequirement(index, { title: event.target.value })}
                />
              </label>
              <label className="field-label">
                Loại yêu cầu
                <select
                  className="apple-input mt-2"
                  value={item.type}
                  onChange={(event) => updateRequirement(index, { type: event.target.value })}
                >
                  {REQUIREMENT_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Mã yêu cầu
                <input
                  className="apple-input mt-2"
                  value={item.requirement_key || ""}
                  onChange={(event) =>
                    updateRequirement(index, { requirement_key: event.target.value })
                  }
                />
              </label>
              <label className="field-label">
                Người phụ trách
                <select
                  className="apple-input mt-2"
                  value={item.owner_id || ""}
                  onChange={(event) => updateRequirement(index, { owner_id: event.target.value })}
                >
                  <option value="">Chưa phân công</option>
                  {members.map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {member.user_label || member.user_id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Trạng thái trong tài liệu nguồn
                <input
                  className="apple-input mt-2"
                  value={item.source_status}
                  onChange={(event) =>
                    updateRequirement(index, { source_status: event.target.value })
                  }
                />
              </label>
              <label className="field-label">
                Ưu tiên
                <select
                  className="apple-input mt-2"
                  value={item.priority}
                  onChange={(event) => updateRequirement(index, { priority: event.target.value })}
                >
                  {REQUIREMENT_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Rủi ro
                <select
                  className="apple-input mt-2"
                  value={item.risk}
                  onChange={(event) => updateRequirement(index, { risk: event.target.value })}
                >
                  {REQUIREMENT_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <DocumentEditor
              label={`Nội dung yêu cầu ${index + 1}`}
              value={item.content_doc}
              onChange={(content_doc) => updateRequirement(index, { content_doc })}
            />
            <label className="field-label block">
              Tiêu chí chấp nhận, mỗi dòng một tiêu chí
              <textarea
                className="apple-input mt-2"
                rows={2}
                value={item.acceptance}
                onChange={(event) =>
                  updateRequirement(index, {
                    acceptance: event.target.value,
                    section_states: {
                      ...item.section_states,
                      acceptance_criteria: event.target.value.trim() ? "provided" : "missing",
                    },
                  })
                }
              />
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              {[
                ["actors", "Tác nhân"],
                ["business_rules", "Quy tắc nghiệp vụ"],
                ["dependencies", "Phụ thuộc"],
              ].map(([key, label]) => (
                <label className="field-label" key={key}>
                  {label}, mỗi dòng một mục
                  <textarea
                    className="apple-input mt-2"
                    rows={2}
                    value={item[key]}
                    onChange={(event) =>
                      updateRequirement(index, {
                        [key]: event.target.value,
                        section_states: {
                          ...item.section_states,
                          [key]: event.target.value.trim() ? "provided" : "missing",
                        },
                      })
                    }
                  />
                </label>
              ))}
              <label className="field-label">
                Nhãn, ngăn cách bằng dấu phẩy
                <input
                  className="apple-input mt-2"
                  value={item.tags}
                  onChange={(event) => updateRequirement(index, { tags: event.target.value })}
                />
              </label>
            </div>
            <details>
              <summary className="cursor-pointer text-sm">Thông tin theo loại yêu cầu</summary>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {[
                  ["actor", "Vai trò trong User Story"],
                  ["goal", "Mục tiêu trong User Story"],
                  ["value", "Giá trị trong User Story"],
                  ["main_flow", "Luồng chính"],
                  ["exception_flow", "Luồng ngoại lệ"],
                  ["data_rules", "Dữ liệu và quy tắc"],
                  ["integration", "Giao diện hoặc tích hợp"],
                  ["quality_measure", "Thuộc tính chất lượng và mức đo"],
                ].map(([key, label]) => (
                  <div className="space-y-2" key={key}>
                    <label className="field-label">
                      {label}
                      <textarea
                        className="apple-input mt-2"
                        rows={2}
                        value={item[key]}
                        onChange={(event) =>
                          updateRequirement(index, {
                            [key]: event.target.value,
                            section_states: {
                              ...item.section_states,
                              [key]: event.target.value.trim() ? "provided" : "missing",
                            },
                          })
                        }
                      />
                    </label>
                    <select
                      className="apple-input"
                      aria-label={`Trạng thái ${label}`}
                      value={item.section_states?.[key] || ""}
                      onChange={(event) => {
                        const states = { ...item.section_states };
                        if (event.target.value) states[key] = event.target.value;
                        else delete states[key];
                        updateRequirement(index, { section_states: states });
                      }}
                    >
                      <option value="">Chưa xác định</option>
                      <option value="missing">Còn thiếu</option>
                      <option value="provided">Đã có</option>
                      <option value="not_applicable">Không áp dụng</option>
                    </select>
                  </div>
                ))}
                {fields
                  .filter(
                    (field) =>
                      !field.requirement_types?.length ||
                      field.requirement_types.includes(item.type),
                  )
                  .map((field) => (
                    <label className="field-label" key={field.key}>
                      {field.label}
                      {field.value_type === "boolean" ? (
                        <input
                          className="ml-2"
                          type="checkbox"
                          checked={Boolean(item.custom_values?.[field.key])}
                          onChange={(event) =>
                            updateRequirement(index, {
                              custom_values: {
                                ...item.custom_values,
                                [field.key]: event.target.checked,
                              },
                            })
                          }
                        />
                      ) : field.value_type === "choice" ? (
                        <select
                          className="apple-input mt-2"
                          value={item.custom_values?.[field.key] || ""}
                          onChange={(event) =>
                            updateRequirement(index, {
                              custom_values: {
                                ...item.custom_values,
                                [field.key]: event.target.value,
                              },
                            })
                          }
                        >
                          <option value="">Chưa chọn</option>
                          {field.choices.map((choice) => (
                            <option key={choice}>{choice}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          className="apple-input mt-2"
                          type={
                            field.value_type === "number"
                              ? "number"
                              : field.value_type === "date"
                                ? "date"
                                : "text"
                          }
                          value={item.custom_values?.[field.key] ?? ""}
                          onChange={(event) =>
                            updateRequirement(index, {
                              custom_values: {
                                ...item.custom_values,
                                [field.key]: event.target.value,
                              },
                            })
                          }
                        />
                      )}
                    </label>
                  ))}
              </div>
              {!!item.api_operations?.length && (
                <div className="mt-3 space-y-2 text-sm">
                  <p className="font-medium">Thao tác API đã liên kết</p>
                  {item.api_operations.map((operation, operationIndex) => (
                    <div
                      className="flex items-center justify-between gap-3 rounded-control border border-border p-2"
                      key={`${operation.requirement_document_id}-${operation.method}-${operation.path || operation.url_template}-${operationIndex}`}
                    >
                      <span>
                        {operation.method} {operation.path || operation.url_template}
                      </span>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() =>
                          updateRequirement(index, {
                            api_operations: item.api_operations.filter(
                              (_, currentIndex) => currentIndex !== operationIndex,
                            ),
                          })
                        }
                      >
                        Bỏ liên kết
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </details>
            {item.source_refs?.length > 0 && (
              <details className="rounded-control border border-border p-2 text-xs">
                <summary className="cursor-pointer text-ink-muted">
                  Xem {item.source_refs.length} vị trí nguồn đã liên kết
                </summary>
                <div className="mt-2 space-y-2">
                  {item.source_refs.map((reference, referenceIndex) => (
                    <div className="rounded-control border border-border p-2" key={referenceIndex}>
                      <p>
                        {sourceDocuments.find(
                          (document) => document._id === reference.requirement_document_id,
                        )?.filename ||
                          reference.requirement_document_id ||
                          reference.template_id}
                        {reference.source_start !== undefined &&
                          `  vị trí ${reference.source_start} đến ${reference.source_end}`}
                      </p>
                      {reference.source_quote && <p className="mt-1">{reference.source_quote}</p>}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        <button
          className="secondary-button"
          type="button"
          onClick={() => setRequirements((items) => [...items, emptyRequirement()])}
        >
          Thêm yêu cầu
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="apple-button"
          type="button"
          disabled={busy || !name.trim()}
          onClick={save}
        >
          Lưu mẫu dự án
        </button>
        {active?._id && active.status !== "STARTER" && active.status !== "NEW" && (
          <button
            className="secondary-button"
            type="button"
            disabled={busy || Boolean(active.synthesis?.conflicts?.length)}
            onClick={preview}
          >
            Xem trước yêu cầu để nhập
          </button>
        )}
        {active?.project_id === project._id && (
          <button className="secondary-button" type="button" disabled={busy} onClick={reviewSaved}>
            AI kiểm tra mẫu đã lưu
          </button>
        )}
      </div>
      {review && (
        <section className="space-y-2 rounded-control border border-border p-3" aria-live="polite">
          <p className="text-sm font-medium">
            {review.readiness === "ready_for_import"
              ? "Mẫu đủ điều kiện xem trước để nhập"
              : review.readiness === "conflict"
                ? "Mẫu còn mâu thuẫn cần quyết định"
                : "Mẫu còn thông tin cần làm rõ"}
          </p>
          <p className="text-xs text-ink-muted">Kết quả áp dụng cho phiên bản mẫu đã lưu</p>
          {review.warnings?.includes("BATCHED_REVIEW_REQUIRES_HUMAN_RECONCILIATION") && (
            <p className="text-sm text-ink-muted">
              AI đã rà {review.reviewed_parts} phần của mẫu lớn Cần người dùng đối chiếu mâu thuẫn
              giữa các phần trước khi nhập
            </p>
          )}
          {(review.findings || []).map((finding, index) => (
            <div
              className="rounded-control border border-border p-2 text-sm"
              key={`${index}-${finding.field}`}
            >
              <p>
                {finding.requirement_index === null || finding.requirement_index === undefined
                  ? "Bối cảnh mẫu"
                  : `Yêu cầu ${finding.requirement_index + 1}`}{" "}
                ·{" "}
                {valueLabel(finding.field) === finding.field && !finding.field.includes(" ")
                  ? "Thông tin cần làm rõ"
                  : valueLabel(finding.field)}
              </p>
              <p>{finding.issue}</p>
              {finding.suggested_source_quote && (
                <p className="text-ink-muted">Nguồn gợi ý {finding.suggested_source_quote}</p>
              )}
              <p className="text-xs text-ink-muted">
                Nguồn dẫn {(finding.evidence_refs || []).join(", ")}
              </p>
            </div>
          ))}
        </section>
      )}
      {active?.project_id === project._id && active.status === "DRAFT" && (
        <details className="rounded-control border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">
            Đề nghị phát hành mẫu dùng chung
          </summary>
          <p className="mt-2 text-sm text-ink-muted">
            Viết lại bản công khai không chứa nội dung hay định danh riêng của dự án Chủ tài liệu
            nguồn phải đồng ý trước khi QA khác duyệt
          </p>
          <div className="mt-3 space-y-3">
            <label className="field-label block">
              Tên mẫu công khai
              <input
                className="apple-input mt-2"
                value={publicName}
                onChange={(event) => setPublicName(event.target.value)}
              />
            </label>
            <label className="field-label block">
              Bối cảnh khái quát
              <textarea
                className="apple-input mt-2"
                value={publicContext}
                onChange={(event) => setPublicContext(event.target.value)}
              />
            </label>
            {publicRequirements.map((item, index) => (
              <div className="space-y-2 rounded-control border border-border p-3" key={index}>
                <label className="field-label block">
                  Tên yêu cầu khái quát
                  <input
                    className="apple-input mt-2"
                    value={item.title}
                    onChange={(event) =>
                      setPublicRequirements((items) =>
                        items.map((value, position) =>
                          position === index ? { ...value, title: event.target.value } : value,
                        ),
                      )
                    }
                  />
                </label>
                <label className="field-label block">
                  Loại yêu cầu
                  <select
                    className="apple-input mt-2"
                    value={item.type}
                    onChange={(event) =>
                      setPublicRequirements((items) =>
                        items.map((value, position) =>
                          position === index ? { ...value, type: event.target.value } : value,
                        ),
                      )
                    }
                  >
                    {REQUIREMENT_TYPES.map((value) => (
                      <option key={value} value={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field-label block">
                  Nội dung khái quát
                  <textarea
                    className="apple-input mt-2"
                    value={item.content}
                    onChange={(event) =>
                      setPublicRequirements((items) =>
                        items.map((value, position) =>
                          position === index ? { ...value, content: event.target.value } : value,
                        ),
                      )
                    }
                  />
                </label>
                <label className="field-label block">
                  Tiêu chí chấp nhận khái quát
                  <textarea
                    className="apple-input mt-2"
                    value={item.acceptance}
                    onChange={(event) =>
                      setPublicRequirements((items) =>
                        items.map((value, position) =>
                          position === index ? { ...value, acceptance: event.target.value } : value,
                        ),
                      )
                    }
                  />
                </label>
              </div>
            ))}
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                setPublicRequirements((items) => [
                  ...items,
                  { title: "", type: "functional", content: "", acceptance: "" },
                ])
              }
            >
              Thêm mục công khai
            </button>
            <button
              className="apple-button ml-2"
              type="button"
              disabled={
                busy ||
                !publicName.trim() ||
                !publicRequirements.some((item) => item.title.trim() && item.content.trim())
              }
              onClick={requestPublication}
            >
              Gửi đề nghị phát hành
            </button>
          </div>
        </details>
      )}
      {active?.project_id === project._id && active.status === "PENDING_PUBLICATION" && (
        <div className="space-y-3 rounded-control border border-border p-3">
          <p className="font-medium">Chờ đồng ý nguồn và duyệt phát hành</p>
          <div className="space-y-2 rounded-control border border-border p-3 text-sm">
            <p className="font-medium">Nội dung sẽ dùng chung</p>
            <p>{publicationPreview?.name}</p>
            {Object.entries(publicationPreview?.context || {}).map(([key, value]) => (
              <p key={key}>
                {{
                  objectives: "Mục tiêu",
                  in_scope: "Trong phạm vi",
                  out_of_scope: "Ngoài phạm vi",
                  stakeholders: "Các bên liên quan",
                  actors_and_systems: "Tác nhân và hệ thống",
                  glossary: "Thuật ngữ",
                  assumptions: "Giả định",
                  constraints: "Ràng buộc dự án",
                }[key] || key}{" "}
                {Array.isArray(value) ? value.join("  ") : String(value || "")}
              </p>
            ))}
            {(publicationPreview?.requirements || []).map((item, index) => (
              <div className="rounded-control border border-border p-2" key={index}>
                <p className="font-medium">{item.title}</p>
                <p>{docText(item.content_doc)}</p>
                {(item.acceptance_criteria || []).map((criterion, criterionIndex) => (
                  <p key={criterionIndex}>{docText(criterion.content_doc)}</p>
                ))}
              </div>
            ))}
          </div>
          {(active.publication_source_document_ids || active.source_document_ids || []).map(
            (documentId) => {
              const document = sourceDocuments.find((item) => item._id === documentId);
              const consentValue = active.consents?.[documentId];
              return (
                <div className="flex items-center gap-3 text-sm" key={documentId}>
                  <span>{document?.filename || documentId}</span>
                  <span>{consentValue?.approved ? "Đã đồng ý" : "Chưa đồng ý"}</span>
                  {document?.created_by === project.current_membership?.user_id && (
                    <>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={busy}
                        onClick={() => consent(documentId, true)}
                      >
                        Đồng ý sử dụng nguồn
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={busy}
                        onClick={() => consent(documentId, false)}
                      >
                        Từ chối sử dụng nguồn
                      </button>
                    </>
                  )}
                </div>
              );
            },
          )}
          {project.current_permissions?.includes("project.update") && (
            <button
              className="apple-button"
              type="button"
              disabled={
                busy || active.publication_requested_by === project.current_membership?.user_id
              }
              onClick={approve}
            >
              Duyệt phát hành
            </button>
          )}
        </div>
      )}
      {project.current_permissions?.includes("project.update") && (
        <details className="rounded-control border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">Trường mở rộng của dự án</summary>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="field-label">
              Mã trường
              <input
                className="apple-input mt-2"
                value={fieldDraft.key}
                onChange={(event) =>
                  setFieldDraft((value) => ({ ...value, key: event.target.value }))
                }
              />
            </label>
            <label className="field-label">
              Tên hiển thị
              <input
                className="apple-input mt-2"
                value={fieldDraft.label}
                onChange={(event) =>
                  setFieldDraft((value) => ({ ...value, label: event.target.value }))
                }
              />
            </label>
            <label className="field-label">
              Kiểu dữ liệu
              <select
                className="apple-input mt-2"
                value={fieldDraft.value_type}
                onChange={(event) =>
                  setFieldDraft((value) => ({ ...value, value_type: event.target.value }))
                }
              >
                {["text", "number", "boolean", "date", "choice"].map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            {fieldDraft.value_type === "choice" && (
              <label className="field-label">
                Các lựa chọn, mỗi dòng một giá trị
                <textarea
                  className="apple-input mt-2"
                  value={fieldDraft.choices}
                  onChange={(event) =>
                    setFieldDraft((value) => ({ ...value, choices: event.target.value }))
                  }
                />
              </label>
            )}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={fieldDraft.required}
                onChange={(event) =>
                  setFieldDraft((value) => ({ ...value, required: event.target.checked }))
                }
              />
              Bắt buộc
            </label>
          </div>
          <button
            className="secondary-button mt-3"
            type="button"
            disabled={busy || !fieldDraft.key || !fieldDraft.label}
            onClick={addField}
          >
            Thêm trường
          </button>
        </details>
      )}
    </section>
  );
}
