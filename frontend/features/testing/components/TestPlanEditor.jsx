import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { testingApi } from "../services/testing.service";
import { messageOf, valueLabel } from "../lib/testing";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../routes";

const conditionFields = [
  ["entry_criteria", "Điều kiện bắt đầu"],
  ["exit_criteria", "Tiêu chí hoàn thành"],
];

function environmentOptionLabel(item) {
  const typeLabels = {
    WEB: "Web",
    API: "API",
    MOBILE: "Di động",
    DESKTOP: "Máy tính",
    OTHER: "Khác",
  };
  const details = [
    typeLabels[item.environment_type],
    item.operating_system,
    [item.browser, item.browser_version].filter(Boolean).join(" "),
    item.device,
  ]
    .filter(Boolean)
    .join(" · ");
  return details ? `${item.name} · ${details}` : item.name || item.key;
}

const defaults = {
  name: "",
  test_period_id: "",
  owner_id: "",
  objective: "",
  test_level: "",
  environment_id: "",
  scope_out: [],
  requirement_version_ids: [],
  test_suite_ids: [],
  test_case_version_ids: [],
  entry_criteria: [],
  exit_criteria: [],
  test_types: [],
  schedule: { planned_start_at: "", planned_end_at: "" },
  risk_register: [],
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
  canCreateCases = false,
  initialRequirementVersionIds = [],
  onSave,
  onCancel,
  sourcePeriodId = "",
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
      requirement_version_ids: initialValue.requirement_version_ids ?? initialRequirementVersionIds,
      schedule: {
        ...defaults.schedule,
        ...(initialValue.schedule || {}),
        planned_start_at: localDateTime(initialValue.schedule?.planned_start_at),
        planned_end_at: localDateTime(initialValue.schedule?.planned_end_at),
      },
    };
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testPeriods, setTestPeriods] = useState([]);
  const [newPeriodName, setNewPeriodName] = useState("");
  const [newPeriodSourceId, setNewPeriodSourceId] = useState(sourcePeriodId);
  const [showNewPeriod, setShowNewPeriod] = useState(false);

  const selectedTestTypes = value.test_types || [];
  const selectedPeriod = testPeriods.find((period) => period._id === value.test_period_id);
  const carryOverItems = selectedPeriod?.carry_over_items || [];
  const selectedSuiteIds = new Set(value.test_suite_ids || []);
  const suiteCaseVersionIds = new Set(
    suites
      .filter((suite) => selectedSuiteIds.has(suite._id))
      .flatMap((suite) => suite.test_case_version_ids || []),
  );
  const knownCaseIds = new Set(tests.map((test) => test.current_version_id).filter(Boolean));
  const caseScopeOptions = [
    ...suites.map((suite) => ({
      value: `suite:${suite._id}`,
      label: `Bộ · ${suite.name} (${(suite.test_case_version_ids || []).length} ca)`,
    })),
    ...tests
      .filter(
        (test) => test.current_version_id && !suiteCaseVersionIds.has(test.current_version_id),
      )
      .map((test) => ({
        value: `case:${test.current_version_id}`,
        label: `Ca · ${test.test_case_key} ${test.current_version?.title || test.title || ""}`,
      })),
    ...(value.test_case_version_ids || [])
      .filter((versionId) => !knownCaseIds.has(versionId) && !suiteCaseVersionIds.has(versionId))
      .map((versionId) => ({ value: `case:${versionId}`, label: `Ca · ${versionId}` })),
  ];
  const caseScopeSelection = [
    ...(value.test_suite_ids || []).map((suiteId) => `suite:${suiteId}`),
    ...(value.test_case_version_ids || [])
      .filter((versionId) => !suiteCaseVersionIds.has(versionId))
      .map((versionId) => `case:${versionId}`),
  ];
  const createCaseParams = new URLSearchParams();
  (value.requirement_version_ids || []).forEach((versionId) =>
    createCaseParams.append("requirementVersionId", versionId),
  );
  if (initialValue?._id) createCaseParams.set("returnTestPlanId", initialValue._id);
  const createCaseHref = `${projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases)}/tao-moi?${createCaseParams.toString()}`;
  const riskRows = value.risk_register?.length
    ? value.risk_register
    : [{ title: "", response: "" }];
  const testTypeOptions = [
    ["functional", "Chức năng"],
    ["non_functional", "Phi chức năng"],
    ["black_box", "Hộp đen"],
    ["white_box", "Hộp trắng"],
    ...(selectedTestTypes.includes("change_related")
      ? [["change_related", "Liên quan đến thay đổi (dữ liệu cũ)"]]
      : []),
  ];
  const savingRef = useRef(false);
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));

  useEffect(() => {
    let active = true;
    testingApi
      .listTestPeriods(projectId)
      .then((items) => {
        if (!active) return;
        const periods = Array.isArray(items) ? items : [];
        setTestPeriods(periods);
        if (!sourcePeriodId || initialValue?._id) return;
        const source = periods.find((period) => period._id === sourcePeriodId);
        if (!source || source.status !== "CLOSED") return;
        setNewPeriodSourceId(source._id);
        setNewPeriodName(`Chu kỳ ${source.sequence + 1}`);
        setShowNewPeriod(true);
        setValue((current) => ({
          ...current,
          test_period_id: "",
          test_case_version_ids: [
            ...new Set([
              ...(current.test_case_version_ids || []),
              ...(source.carry_over_items || []).map((item) => item.test_case_version_id),
            ]),
          ],
        }));
      })
      .catch(() => {
        if (active) setTestPeriods([]);
      });
    return () => {
      active = false;
    };
  }, [initialValue?._id, projectId, sourcePeriodId]);

  return (
    <form
      id="test-plan-editor"
      className="test-design-form space-y-5 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        if (readOnly) return;
        if (savingRef.current) return;
        setError("");
        const saveAsDraft = event.nativeEvent.submitter?.value === "draft";
        if (String(value.name || "").trim().length < 2) {
          setError("Tên kế hoạch cần ít nhất 2 ký tự.");
          return;
        }
        if (
          (value.risk_register || []).some(
            (risk) => !String(risk.title || "").trim() && String(risk.response || "").trim(),
          )
        ) {
          setError("Nhập nội dung rủi ro cho cách ứng phó đã điền.");
          return;
        }
        if (!saveAsDraft) {
          if (!String(value.objective || "").trim()) {
            setError("Nhập mục tiêu của kế hoạch.");
            return;
          }
          if (!value.requirement_version_ids?.length) {
            setError("Chọn ít nhất một phiên bản yêu cầu trong phạm vi.");
            return;
          }
        }
        try {
          const payload = {
            ...Object.fromEntries(
              [
                "name",
                "test_period_id",
                "objective",
                "environment_id",
                "requirement_version_ids",
                "test_suite_ids",
                "test_case_version_ids",
                "test_types",
                "test_level",
                "owner_id",
                "schedule",
                "risk_register",
              ].map((key) => [key, value[key]]),
            ),
            ...Object.fromEntries(
              conditionFields.map(([key]) => [
                key,
                (value[key] || []).map((item) => item.trim()).filter(Boolean),
              ]),
            ),
            owner_id: value.owner_id || null,
            environment_id: value.environment_id || null,
            test_level: value.test_level || null,
            risk_register: (value.risk_register || []).filter((risk) =>
              String(risk.title || "").trim(),
            ),
            scope_out: (value.scope_out || []).map((item) => item.trim()).filter(Boolean),
            test_case_version_ids: [...new Set(value.test_case_version_ids || [])],
          };
          payload.save_as_draft = saveAsDraft;
          if (!initialValue?._id) {
            payload.project_id = projectId;
            if (newPeriodName.trim()) {
              payload.test_period_id = null;
              payload.new_test_period = {
                name: newPeriodName.trim(),
                source_period_id: newPeriodSourceId || null,
              };
            }
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
              Tên kế hoạch <span className="text-danger">*</span>
              <input
                className="apple-input mt-2"
                value={value.name}
                onChange={(event) => setField("name", event.target.value)}
                required
              />
            </label>
            <div className="field-label md:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>Chu kỳ (không bắt buộc)</span>
                {!initialValue?._id && !showNewPeriod && (
                  <button
                    type="button"
                    className="text-sm font-medium text-accent hover:underline"
                    onClick={() => {
                      setField("test_period_id", "");
                      setNewPeriodName("");
                      setNewPeriodSourceId("");
                      setShowNewPeriod(true);
                    }}
                  >
                    + Tạo chu kỳ
                  </button>
                )}
              </div>
              {showNewPeriod ? (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    aria-label="Tên chu kỳ mới"
                    className="apple-input min-w-0 flex-1"
                    maxLength={200}
                    minLength={2}
                    placeholder="Tên chu kỳ"
                    required
                    value={newPeriodName}
                    onChange={(event) => setNewPeriodName(event.target.value)}
                  />
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setNewPeriodName("");
                      setNewPeriodSourceId("");
                      setShowNewPeriod(false);
                    }}
                  >
                    Hủy
                  </button>
                </div>
              ) : (
                <select
                  aria-label="Chu kỳ"
                  className="apple-input mt-2"
                  value={value.test_period_id || ""}
                  onChange={(event) => {
                    const periodId = event.target.value || null;
                    const previousCarryIds = new Set(
                      (
                        testPeriods.find((period) => period._id === value.test_period_id)
                          ?.carry_over_items || []
                      ).map((item) => item.test_case_version_id),
                    );
                    const nextCarryItems =
                      testPeriods.find((period) => period._id === periodId)?.carry_over_items || [];
                    setValue((current) => ({
                      ...current,
                      test_period_id: periodId || "",
                      test_case_version_ids: [
                        ...new Set([
                          ...(current.test_case_version_ids || []).filter(
                            (id) => !previousCarryIds.has(id),
                          ),
                          ...nextCarryItems.map((item) => item.test_case_version_id),
                        ]),
                      ],
                    }));
                    setNewPeriodSourceId("");
                  }}
                >
                  <option value="">Không thuộc chu kỳ nào</option>
                  {testPeriods
                    .filter((period) => period.status !== "CLOSED")
                    .map((period) => (
                      <option key={period._id} value={period._id}>
                        Chu kỳ {period.sequence}: {period.name}
                      </option>
                    ))}
                </select>
              )}
            </div>
            {carryOverItems.length > 0 && (
              <div className="md:col-span-2 rounded-control border border-border bg-surface-quiet p-3">
                <p className="text-sm font-medium">Ca được chuyển tiếp từ chu kỳ trước</p>
                <ul className="mt-2 space-y-1 text-sm text-ink-muted">
                  {carryOverItems.map((item) => {
                    const testCase = (tests || []).find(
                      (candidate) => candidate.current_version_id === item.test_case_version_id,
                    );
                    return (
                      <li key={item.test_case_version_id}>
                        {testCase
                          ? `${testCase.test_case_key} · ${testCase.current_version?.title || testCase.title}`
                          : item.test_case_version_id}
                        {item.source_status ? ` · ${valueLabel(item.source_status)}` : ""}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
            <label className="field-label md:col-span-2">
              Mục tiêu <span className="text-danger">*</span>
              <textarea
                className="apple-input mt-2 min-h-20"
                value={value.objective}
                onChange={(event) => setField("objective", event.target.value)}
              />
            </label>
            <MultiSelect
              className="md:col-span-2"
              label={
                <span>
                  Yêu cầu trong phạm vi <span className="text-danger">*</span>
                </span>
              }
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
            <div className="md:col-span-2">
              <MultiSelect
                label={
                  <span>
                    Ca kiểm thử trong phạm vi <span className="text-danger">*</span>
                  </span>
                }
                options={caseScopeOptions}
                searchPlaceholder="Tìm ca hoặc bộ kiểm thử"
                value={caseScopeSelection}
                onChange={(selected) => {
                  const suitesSelected = selected
                    .filter((item) => item.startsWith("suite:"))
                    .map((item) => item.slice("suite:".length));
                  const casesSelected = selected
                    .filter((item) => item.startsWith("case:"))
                    .map((item) => item.slice("case:".length));
                  setValue((current) => ({
                    ...current,
                    test_suite_ids: suitesSelected,
                    test_case_version_ids: casesSelected,
                  }));
                }}
                disabled={readOnly}
              />
              <p className="mt-2 text-sm text-ink-muted">
                Chọn ca đã được duyệt hoặc bộ ca đã có nội dung. Có thể lưu kế hoạch trước khi có
                ca, nhưng cần ít nhất một ca trong phạm vi trước khi gửi duyệt.
              </p>
              {canCreateCases &&
                !readOnly &&
                initialValue?._id &&
                value.requirement_version_ids?.length > 0 && (
                  <Link
                    className="mt-2 inline-flex text-sm font-medium text-brand underline underline-offset-2"
                    href={createCaseHref}
                  >
                    Tạo ca từ các yêu cầu đã chọn
                  </Link>
                )}
            </div>
            <label className="field-label md:col-span-2">
              Ngoài phạm vi (tùy chọn)
              <textarea
                className="apple-input mt-2 min-h-20"
                value={(value.scope_out || []).join("\n")}
                onChange={(event) => setField("scope_out", event.target.value.split("\n"))}
              />
            </label>
          </div>
        </section>
        <section className="order-2 space-y-4 rounded-control border border-border bg-surface p-4">
          <h3 className="text-base font-semibold text-ink">Phân loại kiểm thử (tùy chọn)</h3>
          <fieldset className="space-y-2">
            <legend className="field-label">Loại kiểm thử</legend>
            <p className="text-sm text-ink-muted">
              Chọn một hoặc nhiều loại áp dụng cho phạm vi kế hoạch. Kỹ thuật như phân vùng tương
              đương hoặc giá trị biên được ghi ở ca kiểm thử.
            </p>
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
            </div>
          </fieldset>
          <label className="field-label block">
            Cấp kiểm thử (tùy chọn)
            <select
              className="apple-input mt-2"
              value={value.test_level || ""}
              onChange={(event) => setField("test_level", event.target.value || null)}
            >
              <option value="">-</option>
              <option value="component">Thành phần</option>
              <option value="component_integration">Tích hợp thành phần</option>
              <option value="system">Hệ thống</option>
              <option value="system_integration">Tích hợp hệ thống</option>
              <option value="acceptance">Chấp nhận</option>
              {value.test_level === "integration" && (
                <option value="integration">Tích hợp (dữ liệu cũ)</option>
              )}
            </select>
          </label>
        </section>
        <section className="order-3 space-y-4 rounded-control border border-border bg-surface p-4">
          <h3 className="text-base font-semibold text-ink">Môi trường kiểm thử</h3>
          <label className="field-label block">
            Môi trường dự kiến (tùy chọn)
            <select
              className="apple-input mt-2"
              value={value.environment_id || ""}
              onChange={(event) => {
                const environmentId = event.target.value;
                setValue((current) => ({
                  ...current,
                  environment_id: environmentId,
                }));
              }}
            >
              <option value="">-</option>
              {environments.map((item) => (
                <option key={item._id} value={item._id}>
                  {environmentOptionLabel(item)}
                </option>
              ))}
            </select>
          </label>
          {environments.length === 0 ? (
            <p className="text-sm text-ink-muted">
              Dự án chưa có môi trường để chọn. Có thể thêm môi trường trong{" "}
              <Link
                className="font-medium text-brand underline underline-offset-2"
                href={`${projectRoute(projectId, PROJECT_SECTION_SLUGS.settings)}?section=environments`}
              >
                Cài đặt dự án
              </Link>
              .
            </p>
          ) : (
            <p className="text-sm text-ink-muted">
              Môi trường này được dùng làm mặc định khi tạo lần chạy. Có thể đổi môi trường ở từng
              lần chạy.
            </p>
          )}
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
          <summary className="cursor-pointer font-medium">Nhân sự và thời gian (tùy chọn)</summary>
          <div className="mt-4 grid min-w-0 gap-4 md:grid-cols-2">
            <label className="field-label md:col-span-2">
              Người phụ trách kế hoạch
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
              <span className="mt-1 block text-sm font-normal text-ink-muted">
                Chịu trách nhiệm cập nhật kế hoạch. Người thực hiện được chọn ở từng lần chạy.
              </span>
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
            <p className="text-sm text-ink-muted md:col-span-2">
              Đây là thời gian của kế hoạch. Ngày chung của chu kỳ được quản lý riêng.
            </p>
          </div>
        </details>
        <details className="order-6 rounded-control border border-border bg-surface p-4">
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
