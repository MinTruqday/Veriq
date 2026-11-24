import { useEffect, useRef, useState } from "react";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

const scopeFields = [
  ["scope_in", "Trong phạm vi"],
  ["scope_out", "Ngoài phạm vi"],
];

const conditionFields = [
  ["entry_criteria", "Điều kiện bắt đầu"],
  ["exit_criteria", "Tiêu chí hoàn thành"],
];

const testTechniqueGroups = [
  [
    "Hộp đen",
    [
      ["equivalence_partitioning", "Phân vùng tương đương"],
      ["boundary_value_analysis", "Phân tích giá trị biên"],
      ["decision_table_testing", "Bảng quyết định"],
      ["state_transition_testing", "Chuyển đổi trạng thái"],
    ],
  ],
  [
    "Hộp trắng",
    [
      ["statement_testing", "Kiểm thử câu lệnh"],
      ["branch_testing", "Kiểm thử nhánh"],
    ],
  ],
  [
    "Dựa trên kinh nghiệm",
    [
      ["error_guessing", "Đoán lỗi"],
      ["exploratory_testing", "Kiểm thử thăm dò"],
      ["checklist_based_testing", "Kiểm thử dựa trên danh sách kiểm tra"],
    ],
  ],
];

const defaults = {
  name: "",
  phase: "",
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
  carry_over_items: [],
  entry_criteria: [],
  exit_criteria: [],
  test_types: [],
  test_techniques: [],
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
  runs = [],
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
  const [customTestType, setCustomTestType] = useState("");
  const [carrySourceRunId, setCarrySourceRunId] = useState(
    () => initialValue?.carry_over_items?.[0]?.source_test_run_id || "",
  );
  const [carrySourceRun, setCarrySourceRun] = useState(null);
  const [carrySourceLoading, setCarrySourceLoading] = useState(false);
  const selectedTestTypes = value.test_types || [];
  const riskRows = value.risk_register?.length
    ? value.risk_register
    : [{ title: "", response: "" }];
  const testTypeOptions = [
    ["functional", "Chức năng"],
    ["non_functional", "Phi chức năng"],
    ["confirmation", "Xác nhận"],
    ["regression", "Hồi quy"],
    ...selectedTestTypes
      .filter(
        (item) => !["functional", "non_functional", "confirmation", "regression"].includes(item),
      )
      .map((item) => [
        item,
        { ui_ux: "Giao diện", api: "API", black_box: "Hộp đen", white_box: "Hộp trắng" }[item] ||
          item,
      ]),
  ];
  const savingRef = useRef(false);
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));

  useEffect(() => {
    if (!carrySourceRunId) {
      setCarrySourceRun(null);
      return;
    }
    let active = true;
    setCarrySourceLoading(true);
    testingApi
      .getRun(carrySourceRunId)
      .then((run) => {
        if (active) setCarrySourceRun(run);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason) || "Không tải được lần chạy nguồn");
      })
      .finally(() => {
        if (active) setCarrySourceLoading(false);
      });
    return () => {
      active = false;
    };
  }, [carrySourceRunId]);
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
        if ((value.carry_over_items || []).some((item) => !String(item.reason || "").trim())) {
          setError("Nhập lý do cho từng ca kiểm thử được chuyển tiếp.");
          return;
        }
        try {
          const payload = {
            ...Object.fromEntries(
              [
                "name",
                "phase",
                "objective",
                "test_approach",
                "environment",
                "environment_id",
                "environment_notes",
                "test_data_notes",
                "requirement_version_ids",
                "test_suite_ids",
                "test_case_version_ids",
                "carry_over_items",
                "test_types",
                "owner_id",
                "schedule",
                "risk_register",
                "quality_targets",
              ].map((key) => [key, value[key]]),
            ),
            ...(initialValue && Object.hasOwn(initialValue, "test_techniques")
              ? { test_techniques: value.test_techniques || [] }
              : {}),
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
            test_case_version_ids: [
              ...new Set([
                ...(value.test_case_version_ids || []),
                ...(value.carry_over_items || []).map((item) => item.test_case_version_id),
              ]),
            ],
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
      <fieldset disabled={readOnly || saving} className="flex min-w-0 flex-col gap-5">
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
              Giai đoạn (Sprint/Phase)
              <input
                className="apple-input mt-2"
                value={value.phase || ""}
                onChange={(event) => setField("phase", event.target.value)}
                maxLength={120}
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
          {!!initialValue?.test_techniques?.length && (
            <fieldset className="space-y-2">
              <legend className="field-label">Kỹ thuật đã lưu</legend>
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                {initialValue.test_techniques.map((technique) => {
                  const label =
                    testTechniqueGroups
                      .flatMap(([, items]) => items)
                      .find(([id]) => id === technique)?.[1] || technique;
                  return (
                    <label className="flex items-center gap-2 text-sm" key={technique}>
                      <input
                        type="checkbox"
                        checked={(value.test_techniques || []).includes(technique)}
                        onChange={(event) =>
                          setField(
                            "test_techniques",
                            event.target.checked
                              ? [...(value.test_techniques || []), technique]
                              : (value.test_techniques || []).filter((item) => item !== technique),
                          )
                        }
                      />
                      {label}
                    </label>
                  );
                })}
              </div>
            </fieldset>
          )}
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
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={(value.quality_targets || []).some(
                (item) => item.type === "OPEN_CRITICAL_HIGH_MAX",
              )}
              onChange={(event) => {
                const remaining = (value.quality_targets || []).filter(
                  (item) => item.type !== "OPEN_CRITICAL_HIGH_MAX",
                );
                setField(
                  "quality_targets",
                  event.target.checked
                    ? [
                        ...remaining,
                        {
                          criterion_id: "OPEN-CRITICAL-HIGH",
                          criterion:
                            "Không còn lỗi nghiêm trọng hoặc cao đang mở trong các lần chạy của kế hoạch",
                          type: "OPEN_CRITICAL_HIGH_MAX",
                          threshold: 0,
                        },
                      ]
                    : remaining,
                );
              }}
            />
            Không còn lỗi nghiêm trọng hoặc cao đang mở trong các lần chạy của kế hoạch
          </label>
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
            <div className="md:col-span-2 rounded-control border border-border p-4">
              <h4 className="font-medium text-ink">Ca chuyển tiếp từ giai đoạn trước (tùy chọn)</h4>
              <label className="field-label mt-3 block">
                Lần chạy nguồn
                <select
                  className="apple-input mt-2"
                  value={carrySourceRunId}
                  onChange={(event) => setCarrySourceRunId(event.target.value)}
                  disabled={readOnly}
                >
                  <option value="">-</option>
                  {runs.map((run) => (
                    <option
                      key={run._id}
                      value={run._id}
                      disabled={
                        !run.phase ||
                        run.phase.trim().toLocaleLowerCase() ===
                          String(value.phase || "")
                            .trim()
                            .toLocaleLowerCase()
                      }
                    >
                      {[run.phase, run.name].filter(Boolean).join(" · ")}
                    </option>
                  ))}
                </select>
              </label>
              {carrySourceLoading && (
                <p className="mt-3 text-sm text-muted">Đang tải ca kiểm thử...</p>
              )}
              {carrySourceRun &&
                (() => {
                  const results = new Map(
                    (carrySourceRun.results || []).map((result) => [
                      result.test_case_version_id,
                      result,
                    ]),
                  );
                  const versions = new Map(
                    (carrySourceRun.test_case_versions || []).map((version) => [
                      version._id,
                      version,
                    ]),
                  );
                  const eligible = (carrySourceRun.test_case_version_ids || []).filter((id) => {
                    const status = results.get(id)?.status || "NOT_RUN";
                    return ["NOT_RUN", "IN_PROGRESS", "FAIL", "BLOCKED", "SKIPPED"].includes(
                      status,
                    );
                  });
                  return (
                    <div className="mt-3 space-y-3">
                      {!eligible.length && (
                        <p className="text-sm text-muted">
                          Không có ca chưa chạy hoặc chưa đạt trong lần chạy này.
                        </p>
                      )}
                      {eligible.map((id) => {
                        const status = results.get(id)?.status || "NOT_RUN";
                        const version = versions.get(id);
                        const chosen = (value.carry_over_items || []).some(
                          (item) =>
                            item.source_test_run_id === carrySourceRun._id &&
                            item.test_case_version_id === id,
                        );
                        return (
                          <div
                            key={id}
                            className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] rounded-control bg-subtle p-3"
                          >
                            <label className="flex items-start gap-2 text-sm">
                              <input
                                type="checkbox"
                                checked={chosen}
                                disabled={readOnly}
                                onChange={(event) =>
                                  setValue((current) => ({
                                    ...current,
                                    test_case_version_ids: event.target.checked
                                      ? [...new Set([...(current.test_case_version_ids || []), id])]
                                      : (current.test_case_version_ids || []).filter(
                                          (versionId) => versionId !== id,
                                        ),
                                    carry_over_items: event.target.checked
                                      ? [
                                          ...(current.carry_over_items || []).filter(
                                            (item) => item.test_case_version_id !== id,
                                          ),
                                          {
                                            source_test_run_id: carrySourceRun._id,
                                            test_case_version_id: id,
                                            reason: "",
                                          },
                                        ]
                                      : (current.carry_over_items || []).filter(
                                          (item) => item.test_case_version_id !== id,
                                        ),
                                  }))
                                }
                              />
                              <span>
                                {version?.test_case_key || version?.test_case_id || id} ·{" "}
                                {version?.title || "Ca kiểm thử"} ({status})
                              </span>
                            </label>
                            {chosen && (
                              <input
                                className="apple-input"
                                aria-label="Lý do chuyển tiếp"
                                placeholder="Lý do chuyển tiếp"
                                value={
                                  value.carry_over_items.find(
                                    (item) => item.test_case_version_id === id,
                                  )?.reason || ""
                                }
                                onChange={(event) =>
                                  setValue((current) => ({
                                    ...current,
                                    carry_over_items: (current.carry_over_items || []).map(
                                      (item) =>
                                        item.test_case_version_id === id
                                          ? { ...item, reason: event.target.value }
                                          : item,
                                    ),
                                  }))
                                }
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              {(value.carry_over_items || []).length > 0 && (
                <div className="mt-4 border-t border-border pt-3">
                  <p className="text-sm font-medium text-ink">
                    Đã chọn {value.carry_over_items.length} ca chuyển tiếp
                  </p>
                  <ul className="mt-2 space-y-2">
                    {value.carry_over_items.map((item) => {
                      const runName =
                        item.source_run_name ||
                        runs.find((run) => run._id === item.source_test_run_id)?.name ||
                        item.source_test_run_id;
                      const testCase = tests.find(
                        (test) => test.current_version_id === item.test_case_version_id,
                      );
                      return (
                        <li
                          key={`${item.source_test_run_id}:${item.test_case_version_id}`}
                          className="flex items-start justify-between gap-3 text-sm"
                        >
                          <span>
                            {testCase?.test_case_key || item.test_case_version_id} · {runName}
                            {item.source_status ? ` · ${item.source_status}` : ""}
                            {item.reason ? ` · ${item.reason}` : ""}
                          </span>
                          {!readOnly && (
                            <button
                              type="button"
                              className="text-danger"
                              onClick={() =>
                                setValue((current) => ({
                                  ...current,
                                  carry_over_items: current.carry_over_items.filter(
                                    (candidate) =>
                                      candidate.test_case_version_id !== item.test_case_version_id,
                                  ),
                                  test_case_version_ids: (
                                    current.test_case_version_ids || []
                                  ).filter((versionId) => versionId !== item.test_case_version_id),
                                }))
                              }
                            >
                              Bỏ
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
            <MultiSelect
              className="md:col-span-2"
              label="Phiên bản ca kiểm thử trong phạm vi"
              showSearch={false}
              options={[
                ...tests.map((item) => ({
                  value: item.current_version_id,
                  label: `${item.test_case_key} ${item.current_version?.title || item.title || ""}`,
                })),
                ...(carrySourceRun?.test_case_versions || [])
                  .filter(
                    (version) => !tests.some((test) => test.current_version_id === version._id),
                  )
                  .map((version) => ({
                    value: version._id,
                    label: `${version.test_case_key || version.test_case_id || "Ca kiểm thử"} ${version.title || ""}`,
                  })),
              ]}
              searchPlaceholder="Tìm ca kiểm thử"
              value={value.test_case_version_ids}
              onChange={(selected) =>
                setField("test_case_version_ids", [
                  ...new Set([
                    ...selected,
                    ...(value.carry_over_items || []).map((item) => item.test_case_version_id),
                  ]),
                ])
              }
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
