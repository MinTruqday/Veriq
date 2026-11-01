import { useRef, useState } from "react";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import StructuredValueEditor from "./StructuredValueEditor";
import { testingApi } from "../services/testing.service";

const scopeFields = [
  ["scope_in", "Trong phạm vi"],
  ["scope_out", "Ngoài phạm vi"],
];

const conditionFields = [
  ["entry_criteria", "Tiêu chí đầu vào"],
  ["exit_criteria", "Tiêu chí đầu ra"],
  ["risks", "Rủi ro"],
  ["test_types", "Loại kiểm thử"],
  ["assumptions", "Giả định"],
  ["constraints", "Ràng buộc"],
  ["suspension_criteria", "Tiêu chí đình chỉ"],
  ["resumption_criteria", "Tiêu chí tiếp tục"],
];

const structuredFields = [
  ["dependencies", "Phụ thuộc"],
  ["stakeholders", "Các bên liên quan"],
  ["responsibility_matrix", "Ma trận trách nhiệm"],
  ["milestones", "Mốc"],
  ["deliverables", "Sản phẩm bàn giao"],
  ["tools", "Công cụ"],
  ["monitoring_metrics", "Chỉ số giám sát"],
  ["quality_targets", "Mục tiêu chất lượng"],
  ["risk_register", "Sổ đăng ký rủi ro"],
  ["communication_plan", "Kế hoạch truyền thông"],
];

const defaults = {
  name: "",
  objective: "",
  strategy_version_id: "",
  test_level: "SYSTEM",
  test_approach: "",
  environment: "staging",
  scope_in: [],
  scope_out: [],
  requirement_version_ids: [],
  test_suite_ids: [],
  test_case_version_ids: [],
  entry_criteria: [],
  exit_criteria: [],
  risks: [],
  test_types: ["FUNCTIONAL"],
  members: [],
  assumptions: [],
  constraints: [],
  suspension_criteria: [],
  resumption_criteria: [],
  dependencies: [],
  stakeholders: [],
  responsibility_matrix: [],
  estimation: {
    method: "expert_judgment",
    planned_effort_hours: 0,
    planned_people: 0,
    basis: "",
    effort_allocations: [],
  },
  schedule: { planned_start_at: "", planned_end_at: "" },
  milestones: [],
  deliverables: [],
  tools: [],
  monitoring_metrics: [],
  quality_targets: [],
  risk_register: [],
  communication_plan: {},
  release_id: "",
  build_id: "",
  environment_id: "",
  test_data_plan: { sources: [], preparation: "", privacy: "", reset_procedure: "", owner_id: "" },
  defect_management: { reporting: "", classification: "", triage: "", retest: "", closure: "" },
};

export default function TestPlanEditor({
  projectId,
  initialValue,
  strategies,
  requirements,
  suites,
  tests,
  members = [],
  releases = [],
  builds = [],
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
      test_data_plan: { ...defaults.test_data_plan, ...(initialValue.test_data_plan || {}) },
      defect_management: {
        ...defaults.defect_management,
        ...(initialValue.defect_management || {}),
      },
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
  const [aiError, setAiError] = useState("");
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
      });
      setAiSuggestion(result);
    } catch (reason) {
      setAiError(reason.message || "Không thể tạo gợi ý kế hoạch");
    } finally {
      setAiBusy(false);
    }
  };
  const applyAiPlanDraft = () => {
    const suggestion = aiSuggestion?.suggestion;
    if (!suggestion) return;
    setValue((current) => ({
      ...current,
      objective: suggestion.objective || current.objective,
      scope_in: suggestion.scope_in?.length ? suggestion.scope_in : current.scope_in,
      scope_out: suggestion.scope_out?.length ? suggestion.scope_out : current.scope_out,
      test_approach: suggestion.test_approach || current.test_approach,
      test_types: suggestion.test_types?.length ? suggestion.test_types : current.test_types,
      entry_criteria: suggestion.entry_criteria?.length
        ? suggestion.entry_criteria
        : current.entry_criteria,
      exit_criteria: suggestion.exit_criteria?.length
        ? suggestion.exit_criteria
        : current.exit_criteria,
      risks: suggestion.risks?.length ? suggestion.risks : current.risks,
      assumptions: suggestion.assumptions?.length ? suggestion.assumptions : current.assumptions,
      constraints: suggestion.constraints?.length ? suggestion.constraints : current.constraints,
      test_data_plan: {
        ...current.test_data_plan,
        sources: suggestion.data_sources?.length
          ? suggestion.data_sources
          : current.test_data_plan.sources,
        preparation: suggestion.data_preparation || current.test_data_plan.preparation,
        privacy: suggestion.data_privacy || current.test_data_plan.privacy,
        reset_procedure: suggestion.data_reset || current.test_data_plan.reset_procedure,
      },
    }));
    setAiSuggestion(null);
  };
  return (
    <form
      className="space-y-5 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        if (readOnly) return;
        if (savingRef.current) return;
        setError("");
        try {
          const effortAllocations = value.estimation.effort_allocations || [];
          if (effortAllocations.some((item) => !item.user_id)) {
            setError("Chọn thành viên cho từng dòng phân bổ giờ.");
            return;
          }
          if (
            new Set(effortAllocations.map((item) => item.user_id)).size !== effortAllocations.length
          ) {
            setError("Mỗi thành viên chỉ được có một dòng phân bổ trong kế hoạch kiểm thử.");
            return;
          }
          const allocatedHours = effortAllocations.reduce(
            (sum, item) => sum + Number(item.planned_hours || 0),
            0,
          );
          if (
            effortAllocations.length &&
            Math.round(allocatedHours * 100) !==
              Math.round(Number(value.estimation.planned_effort_hours || 0) * 100)
          ) {
            setError("Tổng giờ phân bổ phải bằng tổng giờ dự kiến.");
            return;
          }
          const payload = {
            ...Object.fromEntries(Object.keys(defaults).map((key) => [key, value[key]])),
            ...Object.fromEntries(
              [...scopeFields, ...conditionFields].map(([key]) => [
                key,
                (value[key] || []).map((item) => item.trim()).filter(Boolean),
              ]),
            ),
            estimation: {
              ...value.estimation,
              planned_people: effortAllocations.length || value.estimation.planned_people,
            },
            strategy_version_id: value.strategy_version_id || null,
            release_id: value.release_id || null,
            build_id: value.build_id || null,
            environment_id: value.environment_id || null,
            test_data_plan: {
              ...value.test_data_plan,
              sources: value.test_data_plan.sources.map((item) => item.trim()).filter(Boolean),
              owner_id: value.test_data_plan.owner_id || null,
            },
          };
          if (!initialValue) {
            payload.project_id = projectId;
          }
          savingRef.current = true;
          setSaving(true);
          await onSave(payload);
        } catch (reason) {
          setError(reason.message || "Không thể lưu kế hoạch kiểm thử");
        } finally {
          savingRef.current = false;
          setSaving(false);
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      {!readOnly && (
        <section
          className="space-y-3 rounded-control border border-border p-4"
          aria-label="Gợi ý kế hoạch từ AI"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Gợi ý kế hoạch từ AI</h3>
              <p className="mt-1 text-sm text-ink-muted">
                Chỉ dựa trên các phiên bản yêu cầu đã chọn. AI không lưu hoặc duyệt kế hoạch.
              </p>
            </div>
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
              disabled={aiBusy || readOnly}
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
              <p className="text-sm font-medium text-violet-800">Bản xem trước, chưa áp dụng</p>
              <p className="text-sm">
                {aiSuggestion.suggestion.objective || "Chưa đủ căn cứ đề xuất mục tiêu."}
              </p>
              <div className="grid gap-3 text-sm md:grid-cols-2">
                <div>
                  <p className="font-medium">Trong phạm vi</p>
                  <ul className="list-disc pl-5">
                    {aiSuggestion.suggestion.scope_in?.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium">Ngoài phạm vi</p>
                  <ul className="list-disc pl-5">
                    {aiSuggestion.suggestion.scope_out?.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
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
              <button className="apple-button" type="button" onClick={applyAiPlanDraft}>
                Áp dụng vào biểu mẫu
              </button>
            </div>
          )}
        </section>
      )}
      <fieldset disabled={readOnly || saving} className="min-w-0 space-y-5">
        <section className="min-w-0 space-y-4" aria-labelledby="test-plan-basics-heading">
          <div>
            <h3 id="test-plan-basics-heading" className="text-base font-semibold text-ink">
              Thông tin kế hoạch
            </h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="field-label">
              Bản phát hành
              <select
                className="apple-input mt-2"
                value={value.release_id || ""}
                onChange={(event) =>
                  setValue((current) => ({
                    ...current,
                    release_id: event.target.value,
                    build_id: "",
                  }))
                }
              >
                <option value="">Chọn bản phát hành</option>
                {releases.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.name || item.key}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Bản dựng
              <select
                className="apple-input mt-2"
                value={value.build_id || ""}
                onChange={(event) => setField("build_id", event.target.value)}
              >
                <option value="">Chọn khi có bản dựng</option>
                {builds
                  .filter((item) => !value.release_id || item.release_id === value.release_id)
                  .map((item) => (
                    <option key={item._id} value={item._id}>
                      {item.identifier || item.name || item.key}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field-label md:col-span-2">
              Môi trường kiểm thử
              <select
                className="apple-input mt-2"
                value={value.environment_id || ""}
                onChange={(event) => setField("environment_id", event.target.value)}
              >
                <option value="">Chọn môi trường</option>
                {environments.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.name || item.key}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Tên kế hoạch
              <input
                className="apple-input mt-2"
                value={value.name}
                onChange={(event) => setField("name", event.target.value)}
                required
              />
            </label>
            <label className="field-label">
              Phiên bản chiến lược đã phê duyệt
              <select
                className="apple-input mt-2"
                value={value.strategy_version_id}
                onChange={(event) => setField("strategy_version_id", event.target.value)}
              >
                <option value="">Mặc định theo chiến lược đang áp dụng</option>
                {strategies
                  .filter((item) => item.status === "APPROVED")
                  .map((item) => (
                    <option key={item._id} value={item._id}>
                      {item.key} phiên bản {item.version}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field-label">
              Cấp kiểm thử
              <input
                className="apple-input mt-2"
                value={value.test_level}
                onChange={(event) => setField("test_level", event.target.value)}
                required
              />
            </label>
            <label className="field-label">
              Môi trường mặc định
              <input
                className="apple-input mt-2"
                value={value.environment}
                onChange={(event) => setField("environment", event.target.value)}
                required
              />
            </label>
            <label className="field-label md:col-span-2">
              Mục tiêu
              <textarea
                className="apple-input mt-2 min-h-24"
                value={value.objective}
                onChange={(event) => setField("objective", event.target.value)}
              />
            </label>
            <label className="field-label md:col-span-2">
              Cách tiếp cận kiểm thử
              <textarea
                className="apple-input mt-2 min-h-24"
                value={value.test_approach}
                onChange={(event) => setField("test_approach", event.target.value)}
              />
            </label>
          </div>
        </section>
        <section
          className="min-w-0 space-y-4 border-t border-border pt-5"
          aria-labelledby="test-plan-scope-heading"
        >
          <div>
            <h3 id="test-plan-scope-heading" className="text-base font-semibold text-ink">
              Phạm vi kiểm thử
            </h3>
          </div>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            <MultiSelect
              className="md:col-span-2"
              label="Phiên bản yêu cầu trong phạm vi"
              options={requirements.map((item) => ({
                value: item.current_version_id,
                label: `${item.requirement_key} ${item.current_version?.title || item.title || ""}`,
              }))}
              searchPlaceholder="Tìm yêu cầu"
              value={value.requirement_version_ids}
              onChange={(selected) => setField("requirement_version_ids", selected)}
            />
            <MultiSelect
              label="Bộ kiểm thử trong phạm vi"
              options={suites.map((item) => ({ value: item._id, label: item.name }))}
              searchPlaceholder="Tìm bộ kiểm thử"
              value={value.test_suite_ids}
              onChange={(selected) => setField("test_suite_ids", selected)}
            />
            <MultiSelect
              className="md:col-span-2"
              label="Phiên bản ca kiểm thử trong phạm vi"
              options={tests.map((item) => ({
                value: item.current_version_id,
                label: `${item.test_case_key} ${item.current_version?.title || item.title || ""}`,
              }))}
              searchPlaceholder="Tìm ca kiểm thử"
              value={value.test_case_version_ids}
              onChange={(selected) => setField("test_case_version_ids", selected)}
            />
            {scopeFields.map(([key, label]) => (
              <label className="field-label" key={key}>
                {label} mỗi dòng một giá trị
                <textarea
                  className="apple-input mt-2 min-h-24"
                  value={(value[key] || []).join("\n")}
                  onChange={(event) =>
                    setField(
                      key,
                      event.target.value.split("\n").map((item) => item.trim()),
                    )
                  }
                />
              </label>
            ))}
          </div>
        </section>
        <section
          className="min-w-0 space-y-4 border-t border-border pt-5"
          aria-labelledby="test-plan-conditions-heading"
        >
          <div>
            <h3 id="test-plan-conditions-heading" className="text-base font-semibold text-ink">
              Điều kiện và nguồn lực
            </h3>
          </div>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            <MultiSelect
              className="md:col-span-2"
              label="Thành viên tham gia"
              options={members
                .filter((item) => item.status === "ACTIVE")
                .map((item) => ({
                  value: item.user_id,
                  label:
                    item.user_label ||
                    item.user?.full_name ||
                    item.user?.email ||
                    "Thành viên chưa có tên",
                }))}
              value={value.members}
              onChange={(selected) => setField("members", selected)}
            />
            {conditionFields.map(([key, label]) => (
              <label className="field-label" key={key}>
                {label} mỗi dòng một giá trị
                <textarea
                  className="apple-input mt-2 min-h-24"
                  value={(value[key] || []).join("\n")}
                  onChange={(event) =>
                    setField(
                      key,
                      event.target.value.split("\n").map((item) => item.trim()),
                    )
                  }
                />
              </label>
            ))}
          </div>
        </section>
        <section
          className="space-y-4 border-t border-border pt-5"
          aria-labelledby="test-plan-data-heading"
        >
          <h3 id="test-plan-data-heading" className="text-base font-semibold">
            Dữ liệu kiểm thử
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Nguồn dữ liệu
              <textarea
                className="apple-input mt-2 min-h-20"
                value={value.test_data_plan.sources.join("\n")}
                onChange={(event) =>
                  setField("test_data_plan", {
                    ...value.test_data_plan,
                    sources: event.target.value.split("\n"),
                  })
                }
              />
            </label>
            {[
              ["preparation", "Chuẩn bị dữ liệu"],
              ["privacy", "Ẩn danh và quyền truy cập"],
              ["reset_procedure", "Khôi phục dữ liệu sau kiểm thử"],
            ].map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={value.test_data_plan[key]}
                  onChange={(event) =>
                    setField("test_data_plan", {
                      ...value.test_data_plan,
                      [key]: event.target.value,
                    })
                  }
                />
              </label>
            ))}
            <label className="field-label">
              Người chuẩn bị dữ liệu
              <select
                className="apple-input mt-2"
                value={value.test_data_plan.owner_id || ""}
                onChange={(event) =>
                  setField("test_data_plan", {
                    ...value.test_data_plan,
                    owner_id: event.target.value,
                  })
                }
              >
                <option value="">Chưa phân công</option>
                {members
                  .filter((item) => item.status === "ACTIVE")
                  .map((item) => (
                    <option key={item.user_id} value={item.user_id}>
                      {item.user_label ||
                        item.user?.full_name ||
                        item.user?.email ||
                        "Thành viên chưa có tên"}
                    </option>
                  ))}
              </select>
            </label>
          </div>
        </section>
        <section
          className="space-y-4 border-t border-border pt-5"
          aria-labelledby="test-plan-defect-heading"
        >
          <h3 id="test-plan-defect-heading" className="text-base font-semibold">
            Quy trình xử lý lỗi
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["reporting", "Thông tin và bằng chứng khi báo lỗi"],
              ["classification", "Phân loại mức độ và ưu tiên"],
              ["triage", "Phân loại, giao xử lý và báo chậm tiến độ"],
              ["retest", "Kiểm tra lại và hồi quy"],
              ["closure", "Điều kiện đóng hoặc mở lại lỗi"],
            ].map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={value.defect_management[key]}
                  onChange={(event) =>
                    setField("defect_management", {
                      ...value.defect_management,
                      [key]: event.target.value,
                    })
                  }
                />
              </label>
            ))}
          </div>
        </section>
        <section
          className="min-w-0 space-y-4 border-t border-border pt-5"
          aria-labelledby="test-plan-coordination-heading"
        >
          <div>
            <h3 id="test-plan-coordination-heading" className="text-base font-semibold text-ink">
              Phối hợp và theo dõi
            </h3>
          </div>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            {structuredFields.map(([key, label]) => (
              <div className="min-w-0 space-y-2" key={key}>
                <StructuredValueEditor
                  label={label}
                  value={value[key] ?? defaults[key]}
                  fixedType={Array.isArray(defaults[key]) ? "array" : "object"}
                  itemTypes={key === "deliverables" || key === "tools" ? undefined : ["object"]}
                  onChange={(nextValue) => setField(key, nextValue)}
                />
              </div>
            ))}
          </div>
        </section>
        <section
          className="min-w-0 space-y-3 rounded-control border border-border p-4 md:col-span-2"
          aria-labelledby="test-plan-effort-heading"
        >
          <div>
            <h3 id="test-plan-effort-heading" className="font-medium">
              Ước lượng và phân bổ giờ theo người
            </h3>
            <p className="mt-1 text-sm text-ink-muted">
              Khai báo tổng giờ dự kiến và phân bổ cho thành viên tham gia kế hoạch. Phân bổ này
              phục vụ lập kế hoạch; người thực chạy từng ca được giao riêng trong lượt chạy kiểm
              thử. Đây là dự toán nhân công, không phải chi phí thực tế.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="field-label">
              Tổng giờ dự kiến
              <input
                className="apple-input mt-2 w-full"
                type="number"
                min="0"
                step="0.25"
                value={value.estimation.planned_effort_hours}
                onChange={(event) =>
                  setField("estimation", {
                    ...value.estimation,
                    planned_effort_hours: Number(event.target.value),
                  })
                }
              />
            </label>
            <label className="field-label">
              Cách ước lượng
              <select
                className="apple-input mt-2 w-full"
                value={value.estimation.method}
                onChange={(event) =>
                  setField("estimation", { ...value.estimation, method: event.target.value })
                }
              >
                <option value="expert_judgment">Đánh giá chuyên gia</option>
                <option value="three_point">Ước lượng ba điểm</option>
                <option value="historical">Dữ liệu lịch sử</option>
                <option value="custom">Khác</option>
              </select>
            </label>
          </div>
          <label className="field-label block">
            Căn cứ ước lượng
            <textarea
              className="apple-input mt-2 min-h-20 w-full"
              value={value.estimation.basis || ""}
              onChange={(event) =>
                setField("estimation", { ...value.estimation, basis: event.target.value })
              }
            />
          </label>
          <div className="space-y-2">
            {(value.estimation.effort_allocations || []).map((allocation, index) => (
              <div
                className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_10rem_auto]"
                key={`${allocation.user_id}-${index}`}
              >
                <select
                  aria-label={`Thành viên phân bổ ${index + 1}`}
                  className="apple-input min-w-0"
                  value={allocation.user_id}
                  onChange={(event) =>
                    setField("estimation", {
                      ...value.estimation,
                      effort_allocations: value.estimation.effort_allocations.map(
                        (item, itemIndex) =>
                          itemIndex === index ? { ...item, user_id: event.target.value } : item,
                      ),
                    })
                  }
                >
                  <option value="">Chọn thành viên</option>
                  {members
                    .filter((item) => item.status === "ACTIVE")
                    .map((item) => (
                      <option
                        key={item.user_id}
                        value={item.user_id}
                        disabled={(value.estimation.effort_allocations || []).some(
                          (other, otherIndex) =>
                            otherIndex !== index && other.user_id === item.user_id,
                        )}
                      >
                        {item.user_label ||
                          item.user?.full_name ||
                          item.user?.email ||
                          "Thành viên chưa có tên"}
                      </option>
                    ))}
                </select>
                <input
                  aria-label={`Số giờ phân bổ ${index + 1}`}
                  className="apple-input min-w-0"
                  type="number"
                  min="0.25"
                  step="0.25"
                  value={allocation.planned_hours}
                  onChange={(event) =>
                    setField("estimation", {
                      ...value.estimation,
                      effort_allocations: value.estimation.effort_allocations.map(
                        (item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, planned_hours: Number(event.target.value) }
                            : item,
                      ),
                    })
                  }
                />
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setField("estimation", {
                      ...value.estimation,
                      effort_allocations: value.estimation.effort_allocations.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    })
                  }
                >
                  Xóa
                </button>
              </div>
            ))}
            <button
              className="secondary-button"
              type="button"
              disabled={!members.some((item) => item.status === "ACTIVE")}
              onClick={() =>
                setField("estimation", {
                  ...value.estimation,
                  effort_allocations: [
                    ...value.estimation.effort_allocations,
                    { user_id: "", planned_hours: 1 },
                  ],
                })
              }
            >
              Thêm người và số giờ
            </button>
            <p className="text-sm text-ink-muted">
              Đã phân bổ{" "}
              {(value.estimation.effort_allocations || []).reduce(
                (sum, item) => sum + (Number(item.planned_hours) || 0),
                0,
              )}{" "}
              / {Number(value.estimation.planned_effort_hours) || 0} giờ.
            </p>
          </div>
        </section>
        <section
          className="min-w-0 space-y-3 rounded-control border border-border p-4 md:col-span-2"
          aria-labelledby="test-plan-schedule-heading"
        >
          <div>
            <h3 id="test-plan-schedule-heading" className="font-medium">
              Thời gian kế hoạch kiểm thử
            </h3>
            <p className="mt-1 text-sm text-ink-muted">
              Thời điểm bắt đầu giúp áp dụng đúng đơn giá nhân sự khi lập dự toán.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
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
        </section>
      </fieldset>
      <div className="action-dialog-footer flex items-center justify-end gap-3">
        <button className="secondary-button" type="button" disabled={saving} onClick={onCancel}>
          {readOnly ? "Đóng" : "Hủy"}
        </button>
        {!readOnly && (
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu" : "Lưu kế hoạch"}
          </button>
        )}
      </div>
    </form>
  );
}
