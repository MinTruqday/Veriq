"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";
import { messageOf } from "../lib/testing";
import StructuredValueEditor, { StructuredValueView } from "./StructuredValueEditor";
import { testingApi } from "../services/testing.service";

const splitLines = (value) =>
  String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

function StructuredPlanFieldsModal({ planType, initialValues, saving, error, onClose, onSave }) {
  const [values, setValues] = useState(() => structuredClone(initialValues));
  const [responseTargetType, setResponseTargetType] = useState(
    typeof initialValues.response_time_target === "object" &&
      initialValues.response_time_target !== null
      ? "object"
      : "number",
  );
  const [concurrencyType, setConcurrencyType] = useState(
    typeof initialValues.concurrency === "object" && initialValues.concurrency !== null
      ? "object"
      : "number",
  );
  const set = (key, value) => setValues((current) => ({ ...current, [key]: value }));
  const submit = (event) => {
    event.preventDefault();
    onSave(values, { responseTargetType, concurrencyType });
  };
  const security = planType === "SECURITY_TEST_PLAN";
  return (
    <Modal
      isOpen
      ariaLabel={security ? "Kế hoạch kiểm thử bảo mật" : "Kế hoạch kiểm thử hiệu năng"}
      className="max-h-[94dvh] max-w-5xl overflow-y-auto"
      onClose={onClose}
    >
      <form onSubmit={submit}>
        <ModalHeader>
          <ModalTitle>
            {security ? "Thông số kiểm thử bảo mật" : "Thông số kiểm thử hiệu năng"}
          </ModalTitle>
        </ModalHeader>
        <ModalContent className="space-y-5">
          {error && (
            <div
              className="rounded-control border border-danger/30 bg-danger/5 p-3 text-sm text-danger"
              role="alert"
            >
              {error}
            </div>
          )}
          <p className="text-sm text-ink-muted">
            Mỗi nhóm thuộc tính giữ nguyên kiểu dữ liệu trong đặc tả. Có thể mở rộng danh sách lồng
            nhau.
          </p>
          {security ? (
            <div className="space-y-5">
              <StructuredValueEditor
                label="Môi trường"
                value={values.environment || {}}
                fixedType="object"
                onChange={(value) => set("environment", value)}
              />
              <StructuredValueEditor
                label="Bằng chứng"
                value={values.evidence || []}
                fixedType="array"
                itemTypes={["string", "object"]}
                onChange={(value) => set("evidence", value)}
              />
              <StructuredValueEditor
                label="Rủi ro tồn dư"
                value={values.residual_risk || []}
                fixedType="array"
                itemTypes={["string", "object"]}
                onChange={(value) => set("residual_risk", value)}
              />
            </div>
          ) : (
            <div className="space-y-5">
              {[
                ["workload_model", "Mô hình tải"],
                ["baseline", "Đường cơ sở"],
                ["load", "Tải thông thường"],
                ["stress", "Tải cực hạn"],
                ["spike", "Tải tăng đột biến"],
                ["soak", "Tải kéo dài"],
                ["data", "Dữ liệu tải"],
                ["environment", "Môi trường"],
              ].map(([key, label]) => (
                <StructuredValueEditor
                  key={key}
                  label={label}
                  value={values[key] || {}}
                  fixedType="object"
                  onChange={(value) => set(key, value)}
                />
              ))}
              <label className="field-label block min-w-0">
                Thời lượng cấu hình (phút)
                <input
                  className="apple-input mt-2 w-full"
                  min="1"
                  max="10080"
                  step="1"
                  type="number"
                  value={values.duration_minutes ?? ""}
                  onChange={(event) => set("duration_minutes", event.target.value)}
                />
              </label>
              <label className="field-label block min-w-0">
                Kiểu số người dùng đồng thời
                <select
                  className="apple-input mt-2 w-full"
                  value={concurrencyType}
                  onChange={(event) => {
                    const type = event.target.value;
                    setConcurrencyType(type);
                    set("concurrency", type === "object" ? {} : "");
                  }}
                >
                  <option value="number">Số nguyên</option>
                  <option value="object">Nhóm thuộc tính</option>
                </select>
                {concurrencyType === "object" ? (
                  <div className="mt-2">
                    <StructuredValueEditor
                      label="Số người dùng đồng thời"
                      value={values.concurrency || {}}
                      fixedType="object"
                      onChange={(value) => set("concurrency", value)}
                    />
                  </div>
                ) : (
                  <input
                    className="apple-input mt-2 w-full"
                    min="0"
                    step="1"
                    type="number"
                    value={values.concurrency ?? ""}
                    onChange={(event) => set("concurrency", event.target.value)}
                  />
                )}
              </label>
              <label className="field-label block min-w-0">
                Kiểu mục tiêu thời gian phản hồi
                <select
                  className="apple-input mt-2 w-full"
                  value={responseTargetType}
                  onChange={(event) => {
                    const type = event.target.value;
                    setResponseTargetType(type);
                    set("response_time_target", type === "object" ? {} : "");
                  }}
                >
                  <option value="number">Một giá trị số</option>
                  <option value="object">Nhóm thuộc tính</option>
                </select>
                {responseTargetType === "object" ? (
                  <div className="mt-2">
                    <StructuredValueEditor
                      label="Mục tiêu thời gian phản hồi"
                      value={values.response_time_target || {}}
                      fixedType="object"
                      onChange={(value) => set("response_time_target", value)}
                    />
                  </div>
                ) : (
                  <input
                    className="apple-input mt-2 w-full"
                    min="0"
                    step="any"
                    type="number"
                    value={values.response_time_target ?? ""}
                    onChange={(event) => set("response_time_target", event.target.value)}
                  />
                )}
              </label>
            </div>
          )}
        </ModalContent>
        <ModalFooter>
          <button className="secondary-button" disabled={saving} type="button" onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" disabled={saving} type="submit">
            {saving ? "Đang lưu" : "Áp dụng thông số"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}

function ExternalEvidenceModal({ saving, error, onClose, onSave }) {
  const [values, setValues] = useState({
    provider: "GENERIC",
    externalRunRef: "",
    executedAt: "",
    evidenceRefs: "",
    resultSummary: {},
    rawResultHash: "",
  });
  return (
    <Modal
      isOpen
      ariaLabel="Nhập bằng chứng thực thi bên ngoài"
      className="max-h-[94dvh] max-w-4xl overflow-y-auto"
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSave(values);
        }}
      >
        <ModalHeader>
          <ModalTitle>Nhập bằng chứng thực thi bên ngoài</ModalTitle>
        </ModalHeader>
        <ModalContent className="space-y-4">
          {error && <ErrorState message={error} />}
          <label className="field-label block">
            Công cụ
            <select
              className="apple-input mt-2 w-full"
              value={values.provider}
              onChange={(event) =>
                setValues((current) => ({ ...current, provider: event.target.value }))
              }
            >
              {["GENERIC", "K6", "JMETER", "OWASP_ZAP", "PLAYWRIGHT"].map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label block">
            Mã lần chạy
            <input
              className="apple-input mt-2 w-full"
              required
              value={values.externalRunRef}
              onChange={(event) =>
                setValues((current) => ({ ...current, externalRunRef: event.target.value }))
              }
            />
          </label>
          <label className="field-label block">
            Thời điểm chạy
            <input
              className="apple-input mt-2 w-full"
              type="datetime-local"
              required
              value={values.executedAt}
              onChange={(event) =>
                setValues((current) => ({ ...current, executedAt: event.target.value }))
              }
            />
          </label>
          <label className="field-label block">
            Tham chiếu bằng chứng, mỗi dòng một mục
            <textarea
              className="apple-input mt-2 min-h-24 w-full"
              required
              value={values.evidenceRefs}
              onChange={(event) =>
                setValues((current) => ({ ...current, evidenceRefs: event.target.value }))
              }
            />
          </label>
          <StructuredValueEditor
            label="Số liệu kết quả"
            value={values.resultSummary}
            fixedType="object"
            onChange={(resultSummary) => setValues((current) => ({ ...current, resultSummary }))}
          />
          <label className="field-label block">
            Mã kiểm tra tệp kết quả (SHA256)
            <input
              className="apple-input mt-2 w-full"
              required
              value={values.rawResultHash}
              onChange={(event) =>
                setValues((current) => ({ ...current, rawResultHash: event.target.value }))
              }
            />
          </label>
        </ModalContent>
        <ModalFooter>
          <button className="secondary-button" disabled={saving} type="button" onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" disabled={saving} type="submit">
            {saving ? "Đang nhập" : "Nhập bằng chứng"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}

export default function NonFunctionalTestPanel({ project }) {
  const [items, setItems] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [planEditor, setPlanEditor] = useState(null);
  const [planEditorError, setPlanEditorError] = useState("");
  const [savingPlan, setSavingPlan] = useState(false);
  const [evidenceEditor, setEvidenceEditor] = useState(false);
  const [evidenceError, setEvidenceError] = useState("");
  const [savingEvidence, setSavingEvidence] = useState(false);
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      const permissions = new Set(project.current_permissions || []);
      const [result, conditionResult, caseValues] = await Promise.all([
        testingApi.listNonFunctionalTestPlans(project._id),
        permissions.has("testcondition.read")
          ? testingApi.listTestConditions(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("testcase.read")
          ? testingApi.listTestCases(project._id, { page_size: 500 })
          : Promise.resolve([]),
      ]);
      setItems(result.items || []);
      setConditions(conditionResult.items || []);
      setCases(caseValues);
      if (selected?._id) setSelected(await testingApi.getNonFunctionalTestPlan(selected._id));
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions, selected?._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    setPlanEditorError("");
    const typeAnswer = await ask({
      title: "Tạo kế hoạch kiểm thử phi chức năng",
      confirmLabel: "Tiếp tục",
      fields: [
        {
          name: "plan_type",
          label: "Loại",
          options: [
            { value: "SECURITY_TEST_PLAN", label: "Kế hoạch kiểm thử bảo mật" },
            { value: "PERFORMANCE_TEST_PLAN", label: "Kế hoạch kiểm thử hiệu năng" },
          ],
        },
      ],
    });
    if (!typeAnswer) return;
    const security = typeAnswer.plan_type === "SECURITY_TEST_PLAN";
    const answer = await ask({
      title: security ? "Kế hoạch kiểm thử bảo mật" : "Kế hoạch kiểm thử hiệu năng",
      confirmLabel: "Tạo",
      fields: [
        { name: "name", label: "Tên", required: true },
        { name: "objective", label: "Mục tiêu", required: true, multiline: true },
        { name: "scope", label: "Phạm vi mỗi dòng một mục", required: true, multiline: true },
        { name: "approach", label: "Cách tiếp cận", required: true, multiline: true },
        { name: "entry_criteria", label: "Điều kiện bắt đầu mỗi dòng một mục", multiline: true },
        { name: "exit_criteria", label: "Điều kiện kết thúc mỗi dòng một mục", multiline: true },
        { name: "tool_refs", label: "Tham chiếu công cụ mỗi dòng một mục", multiline: true },
        {
          name: "requirement_refs",
          label: "Mã phiên bản yêu cầu cách nhau bởi dấu phẩy",
        },
        ...(can("testcondition.read")
          ? [
              {
                name: "condition_ids",
                label: "Mã điều kiện kiểm thử cách nhau bởi dấu phẩy",
                initialValue: conditions.map((item) => item._id).join(","),
              },
            ]
          : []),
        ...(can("testcase.read")
          ? [
              {
                name: "case_ids",
                label: "Mã phiên bản ca kiểm thử cách nhau bởi dấu phẩy",
                initialValue: cases
                  .map((item) => item.current_version_id)
                  .filter(Boolean)
                  .join(","),
              },
            ]
          : []),
        ...(security
          ? [
              { name: "risk_refs", label: "Tham chiếu rủi ro mỗi dòng một mục", multiline: true },
              { name: "categories", label: "Nhóm kiểm thử mỗi dòng một mục", multiline: true },
            ]
          : [
              { name: "throughput_target", label: "Mục tiêu thông lượng", type: "number" },
              { name: "error_rate_target", label: "Mục tiêu tỷ lệ lỗi phần trăm", type: "number" },
              { name: "external_tool_ref", label: "Tham chiếu công cụ bên ngoài" },
            ]),
      ],
    });
    if (!answer) return;
    setPlanEditor({
      mode: "create",
      idempotencyKey: crypto.randomUUID(),
      planType: typeAnswer.plan_type,
      answer,
      initialValues:
        typeAnswer.plan_type === "SECURITY_TEST_PLAN"
          ? { environment: {}, evidence: [], residual_risk: [] }
          : {
              workload_model: {},
              baseline: {},
              load: {},
              stress: {},
              spike: {},
              soak: {},
              concurrency: "",
              duration_minutes: "",
              response_time_target: "",
              data: {},
              environment: {},
            },
    });
  };
  const edit = async () => {
    setPlanEditorError("");
    const answer = await ask({
      title: "Cập nhật kế hoạch kiểm thử phi chức năng",
      confirmLabel: "Lưu",
      fields: [
        { name: "name", label: "Tên", required: true, initialValue: selected.name },
        {
          name: "objective",
          label: "Mục tiêu",
          required: true,
          multiline: true,
          initialValue: selected.objective,
        },
        {
          name: "scope",
          label: "Phạm vi mỗi dòng một mục",
          required: true,
          multiline: true,
          initialValue: selected.scope?.join("\n"),
        },
        {
          name: "approach",
          label: "Cách tiếp cận",
          required: true,
          multiline: true,
          initialValue: selected.approach,
        },
        {
          name: "entry_criteria",
          label: "Điều kiện bắt đầu mỗi dòng một mục",
          multiline: true,
          initialValue: selected.entry_criteria?.join("\n"),
        },
        {
          name: "exit_criteria",
          label: "Điều kiện kết thúc mỗi dòng một mục",
          multiline: true,
          initialValue: selected.exit_criteria?.join("\n"),
        },
        {
          name: "tool_refs",
          label: "Tham chiếu công cụ mỗi dòng một mục",
          multiline: true,
          initialValue: selected.tool_refs?.join("\n"),
        },
        ...(selected.plan_type === "SECURITY_TEST_PLAN"
          ? [
              {
                name: "risk_refs",
                label: "Tham chiếu rủi ro mỗi dòng một mục",
                multiline: true,
                initialValue: selected.risk_refs?.join("\n"),
              },
              {
                name: "categories",
                label: "Nhóm kiểm thử mỗi dòng một mục",
                multiline: true,
                initialValue: selected.categories?.join("\n"),
              },
            ]
          : [
              {
                name: "throughput_target",
                label: "Mục tiêu thông lượng",
                type: "number",
                initialValue: selected.throughput_target ?? "",
              },
              {
                name: "error_rate_target",
                label: "Mục tiêu tỷ lệ lỗi phần trăm",
                type: "number",
                initialValue: selected.error_rate_target ?? "",
              },
              {
                name: "external_tool_ref",
                label: "Tham chiếu công cụ bên ngoài",
                initialValue: selected.external_tool_ref || "",
              },
            ]),
      ],
    });
    if (!answer) return;
    setPlanEditor({
      mode: "edit",
      planType: selected.plan_type,
      answer,
      initialValues: Object.fromEntries(
        (selected.plan_type === "SECURITY_TEST_PLAN"
          ? ["environment", "evidence", "residual_risk"]
          : [
              "workload_model",
              "baseline",
              "load",
              "stress",
              "spike",
              "soak",
              "concurrency",
              "duration_minutes",
              "response_time_target",
              "data",
              "environment",
            ]
        ).map((key) => [
          key,
          selected[key] ??
            (key === "evidence" || key === "residual_risk"
              ? []
              : key === "concurrency" ||
                  key === "duration_minutes" ||
                  key === "response_time_target"
                ? ""
                : {}),
        ]),
      ),
    });
  };
  const savePlanEditor = async (dataValues, modes) => {
    if (!planEditor) return;
    const { answer, mode, planType } = planEditor;
    const security = planType === "SECURITY_TEST_PLAN";
    const readIds = (value) =>
      String(value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    const numberOrNull = (value) => (value === "" || value == null ? null : Number(value));
    const common = {
      name: answer.name,
      objective: answer.objective,
      scope: splitLines(answer.scope),
      approach: answer.approach,
      entry_criteria: splitLines(answer.entry_criteria),
      exit_criteria: splitLines(answer.exit_criteria),
      tool_refs: splitLines(answer.tool_refs),
      environment: dataValues.environment,
    };
    const typeSpecific = security
      ? {
          risk_refs: splitLines(answer.risk_refs),
          categories: splitLines(answer.categories),
          evidence: dataValues.evidence,
          residual_risk: dataValues.residual_risk,
        }
      : {
          workload_model: dataValues.workload_model,
          baseline: dataValues.baseline,
          load: dataValues.load,
          stress: dataValues.stress,
          spike: dataValues.spike,
          soak: dataValues.soak,
          concurrency:
            modes.concurrencyType === "object"
              ? dataValues.concurrency
              : numberOrNull(dataValues.concurrency),
          duration_minutes: numberOrNull(dataValues.duration_minutes),
          throughput_target: numberOrNull(answer.throughput_target),
          response_time_target:
            modes.responseTargetType === "object"
              ? dataValues.response_time_target
              : numberOrNull(dataValues.response_time_target),
          error_rate_target: numberOrNull(answer.error_rate_target),
          data: dataValues.data,
          external_tool_ref: answer.external_tool_ref || null,
        };
    if (
      security &&
      [dataValues.evidence, dataValues.residual_risk].some(
        (items) =>
          !Array.isArray(items) ||
          items.some(
            (item) =>
              typeof item !== "string" &&
              (!item || typeof item !== "object" || Array.isArray(item)),
          ),
      )
    ) {
      setPlanEditorError(
        "Bằng chứng và rủi ro tồn dư chỉ nhận danh sách văn bản hoặc nhóm thuộc tính.",
      );
      return;
    }
    setSavingPlan(true);
    setPlanEditorError("");
    try {
      if (mode === "create") {
        const value = await testingApi.createNonFunctionalTestPlan(project._id, {
          idempotency_key: planEditor.idempotencyKey,
          plan_type: planType,
          ...common,
          test_conditions: readIds(answer.condition_ids),
          test_cases: readIds(answer.case_ids),
          requirement_refs: readIds(answer.requirement_refs),
          source_ai_result_ids: [],
          ...typeSpecific,
        });
        setSelected(await testingApi.getNonFunctionalTestPlan(value._id));
        await load();
      } else {
        const updated = await testingApi.updateNonFunctionalTestPlan(selected._id, {
          expected_revision: selected.revision,
          ...common,
          ...(security
            ? typeSpecific
            : {
                ...typeSpecific,
                throughput_target: numberOrNull(answer.throughput_target),
                error_rate_target: numberOrNull(answer.error_rate_target),
              }),
        });
        setSelected(updated);
      }
      setPlanEditor(null);
      setError("");
    } catch (reason) {
      setPlanEditorError(messageOf(reason));
    } finally {
      setSavingPlan(false);
    }
  };
  const importEvidence = async (answer) => {
    if (!selected || savingEvidence) return;
    setSavingEvidence(true);
    setEvidenceError("");
    try {
      await testingApi.importNonFunctionalEvidence(selected._id, {
        idempotency_key: crypto.randomUUID(),
        provider: answer.provider,
        external_run_ref: answer.externalRunRef.trim(),
        executed_at: new Date(answer.executedAt).toISOString(),
        evidence_refs: splitLines(answer.evidenceRefs),
        result_summary: answer.resultSummary,
        raw_result_hash: answer.rawResultHash.trim(),
      });
      setSelected(await testingApi.getNonFunctionalTestPlan(selected._id));
      await load();
      setEvidenceEditor(false);
    } catch (reason) {
      setEvidenceError(messageOf(reason));
    } finally {
      setSavingEvidence(false);
    }
  };
  const transition = async (approve) => {
    try {
      setSelected(
        await testingApi.transitionNonFunctionalTestPlan(
          selected._id,
          {
            expected_revision: selected.revision,
            note: approve ? "Phê duyệt kế hoạch" : "Gửi rà soát",
          },
          approve,
        ),
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Kiểm thử phi chức năng"
      actions={
        can("nfrtest.manage") ? (
          <button className="apple-button" type="button" onClick={create}>
            Tạo kế hoạch kiểm thử phi chức năng
          </button>
        ) : null
      }
    >
      {dialog}
      {planEditor && (
        <StructuredPlanFieldsModal
          planType={planEditor.planType}
          initialValues={planEditor.initialValues}
          saving={savingPlan}
          error={planEditorError}
          onClose={() => {
            if (savingPlan) return;
            setPlanEditor(null);
            setPlanEditorError("");
          }}
          onSave={savePlanEditor}
        />
      )}
      {evidenceEditor && (
        <ExternalEvidenceModal
          saving={savingEvidence}
          error={evidenceError}
          onClose={() => {
            if (!savingEvidence) setEvidenceEditor(false);
          }}
          onSave={importEvidence}
        />
      )}
      {error && (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      )}
      <DataTable
        items={items}
        empty="Chưa có kế hoạch kiểm thử phi chức năng"
        columns={[
          { key: "plan_type", label: "Loại" },
          { key: "name", label: "Tên" },
          {
            key: "test_conditions",
            label: "Điều kiện kiểm thử",
            render: (item) => item.test_conditions?.length || 0,
          },
          {
            key: "test_cases",
            label: "Ca kiểm thử",
            render: (item) => item.test_cases?.length || 0,
          },
          {
            key: "external_evidence_ids",
            label: "Bằng chứng",
            render: (item) => item.external_evidence_ids?.length || 0,
          },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (item) => (
              <button
                className="secondary-button"
                type="button"
                onClick={async () => {
                  try {
                    setSelected(await testingApi.getNonFunctionalTestPlan(item._id));
                  } catch (reason) {
                    setError(messageOf(reason));
                  }
                }}
              >
                Mở
              </button>
            ),
          },
        ]}
      />
      {selected && (
        <div className="space-y-4 border-t border-border p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold">{selected.name}</p>
              <p className="mt-1 max-w-3xl whitespace-pre-wrap text-sm text-ink-muted">
                {selected.objective}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {["DRAFT", "IN_REVIEW"].includes(selected.status) && can("nfrtest.manage") && (
                <button className="secondary-button" type="button" onClick={edit}>
                  Chỉnh sửa
                </button>
              )}
              {selected.status === "DRAFT" && can("nfrtest.review") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => transition(false)}
                >
                  Gửi rà soát
                </button>
              )}
              {selected.status === "IN_REVIEW" && can("nfrtest.approve") && (
                <button className="apple-button" type="button" onClick={() => transition(true)}>
                  Phê duyệt
                </button>
              )}
              {can("nfrtest.evidence.import") && (
                <button
                  className="apple-button"
                  type="button"
                  onClick={() => {
                    setEvidenceError("");
                    setEvidenceEditor(true);
                  }}
                >
                  Nhập bằng chứng
                </button>
              )}
            </div>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-3">
            <div>
              <p className="field-label">Phạm vi</p>
              <p>{selected.scope?.join(", ")}</p>
            </div>
            <div>
              <p className="field-label">Công cụ</p>
              <p>{selected.tool_refs?.join(", ") || "Chưa khai báo"}</p>
            </div>
            <div>
              <p className="field-label">Kết quả gần nhất</p>
              <StructuredValueView value={selected.result_summary || {}} />
            </div>
          </div>
          <DataTable
            items={selected.external_evidence || []}
            empty="Chưa nhập bằng chứng bên ngoài"
            columns={[
              { key: "provider", label: "Công cụ" },
              { key: "external_run_ref", label: "Lần chạy" },
              { key: "executed_at", label: "Thời điểm" },
              { key: "raw_result_hash", label: "Hash" },
            ]}
          />
        </div>
      )}
    </Panel>
  );
}
