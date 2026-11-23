import { useRef, useState } from "react";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

const aiPlanFields = [
  ["objective", "Mục tiêu", true],
  ["scope_in", "Trong phạm vi", true],
  ["scope_out", "Ngoài phạm vi", true],
  ["test_approach", "Cách tiếp cận", true],
];

function hasSuggestedValue(value) {
  return Array.isArray(value)
    ? value.some((item) => String(item || "").trim())
    : Boolean(String(value || "").trim());
}

function planFieldValue(plan, field) {
  if (field === "risks") return (plan.risk_register || []).map((item) => item.title);
  return plan[field];
}

function displayPlanFieldValue(value) {
  if (Array.isArray(value)) return value.filter(Boolean).join("\n");
  return String(value || "").trim();
}

const scopeFields = [
  ["scope_in", "Trong phạm vi"],
  ["scope_out", "Ngoài phạm vi"],
];

const conditionFields = [
  ["entry_criteria", "Điều kiện bắt đầu"],
  ["exit_criteria", "Tiêu chí hoàn thành"],
];

const defaults = {
  name: "",
  owner_id: "",
  scenario_ids: [],
  objective: "",
  test_level: "",
  test_approach: "",
  environment: "",
  environment_id: "",
  environment_notes: "",
  test_data_notes: "",
  scope_in: [],
  scope_out: [],
  requirement_version_ids: [],
  test_suite_ids: [],
  test_case_version_ids: [],
  entry_criteria: [],
  exit_criteria: [],
  test_types: [],
  members: [],
  assumptions: [],
  constraints: [],
  dependencies: [],
  estimation: {
    method: "expert_judgment",
    planned_effort_hours: 0,
    basis: "",
    effort_allocations: [],
  },
  schedule: { planned_start_at: "", planned_end_at: "" },
  quality_targets: [],
  risk_register: [],
  communication_plan: { channel: "", status_report_frequency: "", recipients: [] },
};

export default function TestPlanEditor({
  projectId,
  initialValue,
  requirements,
  suites,
  tests,
  members = [],
  environments = [],
  readOnly = false,
  initialRequirementVersionIds = [],
  onSave,
  onCancel,
}) {
  const [value, setValue] = useState(() => {
    if (!initialValue)
      return { ...defaults, requirement_version_ids: initialRequirementVersionIds };
    const localDateTime = (value) => {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return local.toISOString().slice(0, 16);
    };
    return {
      ...defaults,
      ...initialValue,
      schedule: {
        ...defaults.schedule,
        ...(initialValue.schedule || {}),
        planned_start_at: localDateTime(initialValue.schedule?.planned_start_at),
        planned_end_at: localDateTime(initialValue.schedule?.planned_end_at),
      },
      estimation: {
        ...defaults.estimation,
        ...(initialValue.estimation || {}),
        effort_allocations: initialValue.estimation?.effort_allocations || [],
      },
    };
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [selectedAiFields, setSelectedAiFields] = useState(() => new Set());
  const [appliedAiFields, setAppliedAiFields] = useState(() => new Set());
  const [aiError, setAiError] = useState("");
  const [customTestType, setCustomTestType] = useState("");
  const selectedTestTypes = value.test_types || [];
  const riskRows = value.risk_register?.length
    ? value.risk_register
    : [{ title: "", response: "" }];
  const testTypeOptions = [
    ["functional", "Chức năng"],
    ["non_functional", "Phi chức năng"],
    ["black_box", "Hộp đen"],
    ["white_box", "Hộp trắng"],
    ["confirmation", "Xác nhận"],
    ["regression", "Hồi quy"],
    ...selectedTestTypes
      .filter(
        (item) =>
          ![
            "functional",
            "non_functional",
            "black_box",
            "white_box",
            "confirmation",
            "regression",
          ].includes(item),
      )
      .map((item) => [item, { ui_ux: "Giao diện", api: "API" }[item] || item]),
  ];
  const savingRef = useRef(false);
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));
  const requestAiPlanDraft = async () => {
    if (aiBusy || !value.requirement_version_ids.length) return;
    setAiBusy(true);
    setAiError("");
    setAiSuggestion(null);
    try {
      const result = await testingApi.suggestTestPlanDraft(projectId, {
        requirement_version_ids: value.requirement_version_ids,
        instruction: aiInstruction,
        current_test_plan: {
          objective: value.objective,
          scope_in: value.scope_in,
          scope_out: value.scope_out,
          test_approach: value.test_approach,
        },
      });
      setAiSuggestion(result);
      const suggestion = result?.suggestion || {};
      const selectableFields = aiPlanFields
        .filter(([field, , applicable]) => applicable && hasSuggestedValue(suggestion[field]))
        .map(([field]) => field);
      setSelectedAiFields(
        new Set(
          selectableFields.filter((field) => !hasSuggestedValue(planFieldValue(value, field))),
        ),
      );
      setAppliedAiFields(new Set());
    } catch (reason) {
      setAiError(messageOf(reason) || "Không thể tạo gợi ý kế hoạch");
    } finally {
      setAiBusy(false);
    }
  };
  const applyAiPlanDraft = () => {
    const suggestion = aiSuggestion?.suggestion;
    if (!suggestion || !selectedAiFields.size) return;
    const selected = new Set(selectedAiFields);
    setValue((current) => {
      const next = { ...current };
      for (const field of selected) {
        if (field === "risks") {
          next.risk_register = suggestion.risks.map((risk) => ({
            risk_id: crypto.randomUUID(),
            title: String(risk).slice(0, 500),
            description: String(risk),
          }));
        } else {
          next[field] = suggestion[field];
        }
      }
      return next;
    });
    setAppliedAiFields((current) => new Set([...current, ...selected]));
    setSelectedAiFields(new Set());
  };
  return (
    <form
      id="test-plan-editor"
      className="test-design-form space-y-5 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        if (readOnly) return;
        if (savingRef.current) return;
        setError("");
        if (
          (value.risk_register || []).some(
            (risk) => !String(risk.title || "").trim() && String(risk.response || "").trim(),
          )
        ) {
          setError("Nhập nội dung rủi ro cho cách ứng phó đã điền.");
          return;
        }
        try {
          const payload = {
            ...Object.fromEntries(
              [
                "name",
                "objective",
                "test_approach",
                "environment",
                "environment_id",
                "environment_notes",
                "test_data_notes",
                "requirement_version_ids",
                "test_suite_ids",
                "test_case_version_ids",
                "test_types",
                "owner_id",
                "schedule",
                "risk_register",
              ].map((key) => [key, value[key]]),
            ),
            ...Object.fromEntries(
              [...scopeFields, ...conditionFields].map(([key]) => [
                key,
                (value[key] || []).map((item) => item.trim()).filter(Boolean),
              ]),
            ),
            owner_id: value.owner_id || null,
            environment_id: value.environment_id || null,
            risk_register: (value.risk_register || []).filter((risk) =>
              String(risk.title || "").trim(),
            ),
          };
          if (!initialValue) {
            payload.project_id = projectId;
            payload.save_as_draft = event.nativeEvent.submitter?.value === "draft";
          }
          savingRef.current = true;
          setSaving(true);
          await onSave(payload);
        } catch (reason) {
          setError(messageOf(reason) || "Không thể lưu kế hoạch kiểm thử");
        } finally {
          savingRef.current = false;
          setSaving(false);
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      <fieldset disabled={readOnly || saving || aiBusy} className="flex min-w-0 flex-col gap-5">
        <section
          className="order-1 min-w-0 space-y-4 rounded-control border border-border bg-surface p-4"
          aria-labelledby="test-plan-info-heading"
        >
          <div>
            <h3 id="test-plan-info-heading" className="text-base font-semibold text-ink">
              Thông tin và phạm vi
            </h3>
          </div>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Tên kế hoạch
              <input
                className="apple-input mt-2"
                value={value.name}
                onChange={(event) => setField("name", event.target.value)}
                required
              />
            </label>
            <label className="field-label md:col-span-2">
              Mục tiêu
              <textarea
                className="apple-input mt-2 min-h-20"
                value={value.objective}
                onChange={(event) => setField("objective", event.target.value)}
              />
            </label>
            <label className="field-label">
              Trong phạm vi
              <textarea
                className="apple-input mt-2 min-h-20"
                value={(value.scope_in || []).join("\n")}
                onChange={(event) => setField("scope_in", event.target.value.split("\n"))}
              />
            </label>
            <label className="field-label">
              Ngoài phạm vi
              <textarea
                className="apple-input mt-2 min-h-20"
                value={(value.scope_out || []).join("\n")}
                onChange={(event) => setField("scope_out", event.target.value.split("\n"))}
              />
            </label>
          </div>
        </section>
        <section className="order-2 space-y-4 rounded-control border border-border bg-surface p-4">
          <h3 className="text-base font-semibold text-ink">Loại hình và cách tiếp cận</h3>
          <fieldset className="space-y-2">
            <legend className="field-label">Loại kiểm thử</legend>
            <div className="space-y-3">
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                {testTypeOptions.map(([type, label]) => (
                  <label className="flex items-center gap-2 text-sm" key={type}>
                    <input
                      type="checkbox"
                      checked={selectedTestTypes.includes(type)}
                      onChange={(event) =>
                        setField(
                          "test_types",
                          event.target.checked
                            ? [...selectedTestTypes, type]
                            : selectedTestTypes.filter((item) => item !== type),
                        )
                      }
                    />
                    {label}
                  </label>
                ))}
              </div>
              {!readOnly && (
                <div className="flex gap-2">
                  <input
                    className="apple-input min-w-0 flex-1"
                    aria-label="Loại kiểm thử khác"
                    value={customTestType}
                    onChange={(event) => setCustomTestType(event.target.value)}
                    placeholder="Nhập loại kiểm thử khác"
                  />
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={!customTestType.trim()}
                    onClick={() => {
                      const name = customTestType.trim();
                      const matched = testTypeOptions.find(([type, label]) =>
                        [type, label].some(
                          (item) => item.toLocaleLowerCase() === name.toLocaleLowerCase(),
                        ),
                      );
                      const type = matched?.[0] || name;
                      if (!selectedTestTypes.includes(type))
                        setField("test_types", [...selectedTestTypes, type]);
                      setCustomTestType("");
                    }}
                  >
                    Thêm
                  </button>
                </div>
              )}
            </div>
          </fieldset>
          <label className="field-label block">
            Cách tiếp cận kiểm thử
            <textarea
              className="apple-input mt-2 min-h-20"
              value={value.test_approach}
              onChange={(event) => setField("test_approach", event.target.value)}
            />
          </label>
        </section>
        <section className="order-3 space-y-4 rounded-control border border-border bg-surface p-4">
          <h3 className="text-base font-semibold text-ink">Môi trường và dữ liệu kiểm thử</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Môi trường kiểm thử
              <input
                className="apple-input mt-2"
                value={value.environment}
                onChange={(event) =>
                  setValue((current) => ({
                    ...current,
                    environment: event.target.value,
                    environment_id: "",
                  }))
                }
              />
            </label>
            <label className="field-label md:col-span-2">
              Trình duyệt, thiết bị và cấu hình
              <textarea
                className="apple-input mt-2 min-h-20"
                value={value.environment_notes || ""}
                onChange={(event) => setField("environment_notes", event.target.value)}
              />
            </label>
            <label className="field-label md:col-span-2">
              Dữ liệu kiểm thử cần chuẩn bị
              <textarea
                className="apple-input mt-2 min-h-20"
                value={value.test_data_notes || ""}
                onChange={(event) => setField("test_data_notes", event.target.value)}
              />
            </label>
          </div>
        </section>
        <section className="order-4 space-y-4 rounded-control border border-border bg-surface p-4">
          <h3 className="text-base font-semibold text-ink">Tiêu chí bắt đầu và kết thúc</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {conditionFields.map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={(value[key] || []).join("\n")}
                  onChange={(event) => setField(key, event.target.value.split("\n"))}
                />
              </label>
            ))}
          </div>
        </section>
        <details className="order-5 rounded-control border border-border bg-surface p-4">
          <summary className="cursor-pointer font-medium">Liên kết (tùy chọn)</summary>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Môi trường đã cấu hình
              <select
                className="apple-input mt-2"
                value={value.environment_id || ""}
                onChange={(event) => {
                  const environmentId = event.target.value;
                  const selected = environments.find((item) => item._id === environmentId);
                  setValue((current) => ({
                    ...current,
                    environment_id: environmentId,
                    environment: selected
                      ? selected.name || selected.key || ""
                      : current.environment,
                  }));
                }}
              >
                <option value="">-</option>
                {environments.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.name || item.key}
                  </option>
                ))}
              </select>
            </label>
            <MultiSelect
              className="md:col-span-2"
              label="Phiên bản yêu cầu trong phạm vi"
              showSearch={false}
              options={requirements.map((item) => ({
                value: item.current_version_id,
                label: `${item.requirement_key} ${item.current_version?.title || item.title || ""}`,
              }))}
              searchPlaceholder="Tìm yêu cầu"
              value={value.requirement_version_ids}
              onChange={(selected) => {
                setField("requirement_version_ids", selected);
                setAiSuggestion(null);
                setSelectedAiFields(new Set());
                setAppliedAiFields(new Set());
              }}
              disabled={readOnly}
            />
            <MultiSelect
              className="md:col-span-2"
              label="Phiên bản ca kiểm thử trong phạm vi"
              showSearch={false}
              options={tests.map((item) => ({
                value: item.current_version_id,
                label: `${item.test_case_key} ${item.current_version?.title || item.title || ""}`,
              }))}
              searchPlaceholder="Tìm ca kiểm thử"
              value={value.test_case_version_ids}
              onChange={(selected) => setField("test_case_version_ids", selected)}
              disabled={readOnly}
            />
            <MultiSelect
              className="md:col-span-2"
              label="Bộ kiểm thử liên kết"
              showSearch={false}
              options={suites.map((item) => ({ value: item._id, label: item.name }))}
              searchPlaceholder="Tìm bộ kiểm thử"
              value={value.test_suite_ids}
              onChange={(selected) => setField("test_suite_ids", selected)}
              disabled={readOnly}
            />
          </div>
        </details>
        <details className="order-6 rounded-control border border-border bg-surface p-4">
          <summary className="cursor-pointer font-medium">Nhân sự và thời gian (tùy chọn)</summary>
          <div className="mt-4 grid min-w-0 gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Người phụ trách
              <select
                className="apple-input mt-2"
                value={value.owner_id || ""}
                onChange={(event) => setField("owner_id", event.target.value)}
              >
                <option value="">-</option>
                {members
                  .filter((item) => item.status === "ACTIVE" || item.user_id === value.owner_id)
                  .map((item) => (
                    <option key={item.user_id} value={item.user_id}>
                      {item.user_label ||
                        item.user?.full_name ||
                        item.user?.email ||
                        "Thành viên dự án"}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field-label">
              Bắt đầu dự kiến
              <input
                aria-label="Thời điểm bắt đầu dự kiến"
                className="apple-input mt-2 w-full"
                type="datetime-local"
                value={value.schedule.planned_start_at || ""}
                onChange={(event) =>
                  setField("schedule", { ...value.schedule, planned_start_at: event.target.value })
                }
              />
            </label>
            <label className="field-label">
              Kết thúc dự kiến
              <input
                aria-label="Thời điểm kết thúc dự kiến"
                className="apple-input mt-2 w-full"
                type="datetime-local"
                value={value.schedule.planned_end_at || ""}
                onChange={(event) =>
                  setField("schedule", { ...value.schedule, planned_end_at: event.target.value })
                }
              />
            </label>
          </div>
        </details>
        <details className="order-7 rounded-control border border-border bg-surface p-4">
          <summary className="cursor-pointer font-medium">
            Rủi ro và cách ứng phó (tùy chọn)
          </summary>
          <div className="mt-4 space-y-3">
            {riskRows.map((risk, index) => (
              <div className="rounded-control border border-border p-4" key={risk.risk_id || index}>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold">{index + 1}.</span>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      aria-label={`Xóa rủi ro ${index + 1}`}
                      className="icon-button h-9 w-9 text-lg"
                      type="button"
                      onClick={() =>
                        setField(
                          "risk_register",
                          riskRows.filter((_, position) => position !== index),
                        )
                      }
                    >
                      −
                    </button>
                    {index === riskRows.length - 1 && (
                      <button
                        aria-label="Thêm rủi ro"
                        className="icon-button h-9 w-9 text-lg"
                        type="button"
                        onClick={() =>
                          setField("risk_register", [
                            ...riskRows.map((item) => ({
                              ...item,
                              risk_id: item.risk_id || crypto.randomUUID(),
                            })),
                            { risk_id: crypto.randomUUID(), title: "", response: "" },
                          ])
                        }
                      >
                        +
                      </button>
                    )}
                  </div>
                </div>
                <div className="grid min-w-0 gap-4 md:grid-cols-2">
                  <label className="field-label">
                    Rủi ro
                    <textarea
                      className="apple-input mt-2 min-h-20"
                      value={risk.title || ""}
                      onChange={(event) =>
                        setField(
                          "risk_register",
                          riskRows.map((item, position) =>
                            position === index
                              ? {
                                  ...item,
                                  risk_id: item.risk_id || crypto.randomUUID(),
                                  title: event.target.value,
                                }
                              : item,
                          ),
                        )
                      }
                    />
                  </label>
                  <label className="field-label">
                    Cách ứng phó
                    <textarea
                      className="apple-input mt-2 min-h-20"
                      value={risk.response || ""}
                      onChange={(event) =>
                        setField(
                          "risk_register",
                          riskRows.map((item, position) =>
                            position === index
                              ? {
                                  ...item,
                                  risk_id: item.risk_id || crypto.randomUUID(),
                                  response: event.target.value,
                                }
                              : item,
                          ),
                        )
                      }
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </details>
      </fieldset>
      {!readOnly && (
        <details className="rounded-control border border-border bg-surface p-4">
          <summary className="cursor-pointer font-medium">Gợi ý kế hoạch từ AI</summary>
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink-muted">
                Chỉ gợi ý mục tiêu, phạm vi và cách tiếp cận có căn cứ từ yêu cầu đã chọn.
              </p>
              <button
                className="secondary-button border-violet-300 text-violet-800"
                type="button"
                disabled={aiBusy || !value.requirement_version_ids.length}
                onClick={requestAiPlanDraft}
              >
                {aiBusy ? "Đang tạo gợi ý" : "Tạo gợi ý"}
              </button>
            </div>
            <label className="field-label block">
              Hướng dẫn bổ sung
              <textarea
                className="apple-input mt-2 min-h-16"
                value={aiInstruction}
                disabled={aiBusy}
                onChange={(event) => setAiInstruction(event.target.value)}
              />
            </label>
            {aiError && (
              <p role="alert" className="text-sm text-danger">
                {aiError}
              </p>
            )}
            {aiSuggestion?.suggestion && (
              <div className="space-y-3 rounded-control border border-violet-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-violet-800">
                    So sánh đề xuất với nội dung đang có
                  </p>
                  <ContentOriginBadge origin="ai_generated" />
                </div>
                <p className="text-sm text-ink-muted">
                  Chỉ các trường đang để trống được chọn sẵn. Bỏ chọn trường muốn giữ nguyên; đề
                  xuất không được lưu hoặc duyệt cho đến khi bạn lưu kế hoạch.
                </p>
                <div className="grid gap-3 md:grid-cols-2">
                  {aiPlanFields
                    .filter(([field]) => hasSuggestedValue(aiSuggestion.suggestion[field]))
                    .map(([field, label, applicable]) => {
                      const selected = selectedAiFields.has(field);
                      const applied = appliedAiFields.has(field);
                      const currentValue = displayPlanFieldValue(planFieldValue(value, field));
                      const proposedValue = displayPlanFieldValue(aiSuggestion.suggestion[field]);
                      const fieldEvidence = (aiSuggestion.suggestion.field_evidence || []).find(
                        (item) => item.field === field,
                      );
                      return (
                        <article
                          className="min-w-0 rounded-control border border-border p-3"
                          key={field}
                        >
                          <div className="flex items-start gap-2 text-sm font-medium">
                            {applicable && (
                              <input
                                className="mt-1"
                                type="checkbox"
                                checked={selected}
                                onChange={(event) =>
                                  setSelectedAiFields((current) => {
                                    const next = new Set(current);
                                    if (event.target.checked) next.add(field);
                                    else next.delete(field);
                                    return next;
                                  })
                                }
                              />
                            )}
                            <span>
                              {label}
                              {!applicable ? " · chỉ tham khảo" : ""}
                            </span>
                          </div>
                          <div className="mt-3 space-y-2 text-sm">
                            <div>
                              <p className="text-xs font-medium text-ink-muted">Đang có</p>
                              <p className="mt-1 whitespace-pre-wrap break-words">
                                {currentValue || "Chưa có nội dung"}
                              </p>
                            </div>
                            <div className="border-t border-border pt-2">
                              <p className="text-xs font-medium text-violet-800">AI đề xuất</p>
                              <p className="mt-1 whitespace-pre-wrap break-words">
                                {proposedValue}
                              </p>
                            </div>
                            {fieldEvidence?.evidence_quotes?.length > 0 && (
                              <details className="border-t border-border pt-2">
                                <summary className="cursor-pointer text-xs font-medium text-violet-800">
                                  Căn cứ cho trường này
                                </summary>
                                <ul className="mt-2 space-y-2 text-xs font-normal">
                                  {fieldEvidence.evidence_quotes.map((item, index) => (
                                    <li key={`${item.evidence_ref}-${index}`}>
                                      <span className="text-ink-muted">{item.evidence_ref}: </span>
                                      {item.quote}
                                    </li>
                                  ))}
                                </ul>
                              </details>
                            )}
                            {applied && (
                              <p className="text-xs font-medium text-violet-800">
                                Đã áp dụng vào biểu mẫu; cần lưu kế hoạch để ghi nhận.
                              </p>
                            )}
                          </div>
                        </article>
                      );
                    })}
                </div>
                {!aiPlanFields.some(([field]) =>
                  hasSuggestedValue(aiSuggestion.suggestion[field]),
                ) && (
                  <p className="text-sm text-ink-muted">
                    Chưa có trường nào đủ căn cứ để đề xuất. Xem các thông tin còn thiếu bên dưới.
                  </p>
                )}
                {!!aiSuggestion.suggestion.evidence_quotes?.length && (
                  <details className="text-sm">
                    <summary className="cursor-pointer">Căn cứ từ yêu cầu nguồn</summary>
                    <ul className="mt-2 space-y-2">
                      {aiSuggestion.suggestion.evidence_quotes.map((item, index) => (
                        <li
                          className="border-l-2 border-violet-300 pl-3"
                          key={`${item.evidence_ref}-${index}`}
                        >
                          <span className="text-ink-muted">{item.evidence_ref}: </span>
                          {item.quote}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                {!!aiSuggestion.warnings?.length && (
                  <ul className="list-disc pl-5 text-sm text-ink-muted">
                    {aiSuggestion.warnings.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                )}
                <button
                  className="apple-button"
                  type="button"
                  disabled={!selectedAiFields.size}
                  onClick={applyAiPlanDraft}
                >
                  Áp dụng{" "}
                  {selectedAiFields.size
                    ? `${selectedAiFields.size} trường đã chọn`
                    : "trường đã chọn"}
                </button>
              </div>
            )}
          </div>
        </details>
      )}
      {readOnly && (
        <div className="action-dialog-footer flex items-center justify-end">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Đóng
          </button>
        </div>
      )}
    </form>
  );
}
