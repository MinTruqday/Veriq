"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";

const splitLines = (value) =>
  String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

const parseJson = (value, fallback) => (String(value || "").trim() ? JSON.parse(value) : fallback);

export default function NonFunctionalTestPanel({ project }) {
  const [items, setItems] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
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
              {
                name: "environment",
                label: "Môi trường dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "evidence",
                label: "Bằng chứng dạng JSON",
                multiline: true,
                initialValue: "[]",
              },
              {
                name: "residual_risk",
                label: "Rủi ro tồn dư dạng JSON",
                multiline: true,
                initialValue: "[]",
              },
            ]
          : [
              {
                name: "workload_model",
                label: "Mô hình tải dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "baseline",
                label: "Đường cơ sở dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "load",
                label: "Tải thông thường dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "stress",
                label: "Tải cực hạn dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "spike",
                label: "Tải tăng đột biến dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              {
                name: "soak",
                label: "Tải kéo dài dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              { name: "concurrency", label: "Số người dùng đồng thời", type: "number" },
              { name: "throughput_target", label: "Mục tiêu thông lượng", type: "number" },
              {
                name: "response_time_target",
                label: "Mục tiêu thời gian phản hồi dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              { name: "error_rate_target", label: "Mục tiêu tỷ lệ lỗi phần trăm", type: "number" },
              {
                name: "environment",
                label: "Môi trường dạng JSON",
                multiline: true,
                initialValue: "{}",
              },
              { name: "data", label: "Dữ liệu tải dạng JSON", multiline: true, initialValue: "{}" },
              { name: "external_tool_ref", label: "Tham chiếu công cụ bên ngoài" },
            ]),
      ],
    });
    if (!answer) return;
    try {
      const value = await testingApi.createNonFunctionalTestPlan(project._id, {
        idempotency_key: crypto.randomUUID(),
        plan_type: typeAnswer.plan_type,
        name: answer.name,
        objective: answer.objective,
        scope: splitLines(answer.scope),
        approach: answer.approach,
        entry_criteria: splitLines(answer.entry_criteria),
        exit_criteria: splitLines(answer.exit_criteria),
        test_conditions: String(answer.condition_ids || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        test_cases: String(answer.case_ids || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        requirement_refs: String(answer.requirement_refs || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        source_ai_result_ids: [],
        tool_refs: splitLines(answer.tool_refs),
        environment: parseJson(answer.environment, {}),
        ...(security
          ? {
              risk_refs: splitLines(answer.risk_refs),
              categories: splitLines(answer.categories),
              evidence: parseJson(answer.evidence, []),
              residual_risk: parseJson(answer.residual_risk, []),
            }
          : {
              workload_model: parseJson(answer.workload_model, {}),
              baseline: parseJson(answer.baseline, {}),
              load: parseJson(answer.load, {}),
              stress: parseJson(answer.stress, {}),
              spike: parseJson(answer.spike, {}),
              soak: parseJson(answer.soak, {}),
              concurrency: answer.concurrency === "" ? null : Number(answer.concurrency),
              throughput_target:
                answer.throughput_target === "" ? null : Number(answer.throughput_target),
              response_time_target: parseJson(answer.response_time_target, {}),
              error_rate_target:
                answer.error_rate_target === "" ? null : Number(answer.error_rate_target),
              data: parseJson(answer.data, {}),
              external_tool_ref: answer.external_tool_ref || null,
            }),
      });
      setSelected(await testingApi.getNonFunctionalTestPlan(value._id));
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const edit = async () => {
    const answer = await ask({
      title: "Cập nhật kế hoạch NFR",
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
        {
          name: "environment",
          label: "Môi trường dạng JSON",
          multiline: true,
          initialValue: JSON.stringify(selected.environment || {}, null, 2),
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
              {
                name: "evidence",
                label: "Bằng chứng dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.evidence || [], null, 2),
              },
              {
                name: "residual_risk",
                label: "Rủi ro tồn dư dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.residual_risk || [], null, 2),
              },
            ]
          : [
              {
                name: "workload_model",
                label: "Mô hình tải dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.workload_model || {}, null, 2),
              },
              {
                name: "baseline",
                label: "Đường cơ sở dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.baseline || {}, null, 2),
              },
              {
                name: "load",
                label: "Tải thông thường dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.load || {}, null, 2),
              },
              {
                name: "stress",
                label: "Tải cực hạn dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.stress || {}, null, 2),
              },
              {
                name: "spike",
                label: "Tải tăng đột biến dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.spike || {}, null, 2),
              },
              {
                name: "soak",
                label: "Tải kéo dài dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.soak || {}, null, 2),
              },
              {
                name: "concurrency",
                label: "Số người dùng đồng thời",
                type: "number",
                initialValue: selected.concurrency ?? "",
              },
              {
                name: "throughput_target",
                label: "Mục tiêu thông lượng",
                type: "number",
                initialValue: selected.throughput_target ?? "",
              },
              {
                name: "response_time_target",
                label: "Mục tiêu thời gian phản hồi dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.response_time_target || {}, null, 2),
              },
              {
                name: "error_rate_target",
                label: "Mục tiêu tỷ lệ lỗi phần trăm",
                type: "number",
                initialValue: selected.error_rate_target ?? "",
              },
              {
                name: "data",
                label: "Dữ liệu tải dạng JSON",
                multiline: true,
                initialValue: JSON.stringify(selected.data || {}, null, 2),
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
    try {
      setSelected(
        await testingApi.updateNonFunctionalTestPlan(selected._id, {
          expected_revision: selected.revision,
          name: answer.name,
          objective: answer.objective,
          scope: splitLines(answer.scope),
          approach: answer.approach,
          entry_criteria: splitLines(answer.entry_criteria),
          exit_criteria: splitLines(answer.exit_criteria),
          tool_refs: splitLines(answer.tool_refs),
          environment: parseJson(answer.environment, {}),
          ...(selected.plan_type === "SECURITY_TEST_PLAN"
            ? {
                risk_refs: splitLines(answer.risk_refs),
                categories: splitLines(answer.categories),
                evidence: parseJson(answer.evidence, []),
                residual_risk: parseJson(answer.residual_risk, []),
              }
            : {
                workload_model: parseJson(answer.workload_model, {}),
                baseline: parseJson(answer.baseline, {}),
                load: parseJson(answer.load, {}),
                stress: parseJson(answer.stress, {}),
                spike: parseJson(answer.spike, {}),
                soak: parseJson(answer.soak, {}),
                concurrency: answer.concurrency === "" ? null : Number(answer.concurrency),
                throughput_target:
                  answer.throughput_target === "" ? null : Number(answer.throughput_target),
                response_time_target: parseJson(answer.response_time_target, {}),
                error_rate_target:
                  answer.error_rate_target === "" ? null : Number(answer.error_rate_target),
                data: parseJson(answer.data, {}),
                external_tool_ref: answer.external_tool_ref || null,
              }),
        }),
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const importEvidence = async () => {
    const answer = await ask({
      title: "Nhập bằng chứng thực thi bên ngoài",
      confirmLabel: "Nhập",
      fields: [
        {
          name: "provider",
          label: "Công cụ",
          options: ["GENERIC", "K6", "JMETER", "OWASP_ZAP", "PLAYWRIGHT"].map((value) => ({
            value,
            label: value,
          })),
        },
        { name: "external_run_ref", label: "Mã lần chạy", required: true },
        { name: "executed_at", label: "Thời điểm chạy", required: true, type: "datetime-local" },
        {
          name: "evidence_refs",
          label: "Tham chiếu bằng chứng mỗi dòng một mục",
          required: true,
          multiline: true,
        },
        {
          name: "result_summary",
          label: "Tóm tắt kết quả JSON",
          required: true,
          multiline: true,
          initialValue: "{}",
        },
        { name: "raw_result_hash", label: "SHA256 kết quả gốc", required: true },
      ],
    });
    if (!answer) return;
    try {
      const resultSummary = JSON.parse(answer.result_summary);
      await testingApi.importNonFunctionalEvidence(selected._id, {
        idempotency_key: crypto.randomUUID(),
        provider: answer.provider,
        external_run_ref: answer.external_run_ref,
        executed_at: new Date(answer.executed_at).toISOString(),
        evidence_refs: splitLines(answer.evidence_refs),
        result_summary: resultSummary,
        raw_result_hash: answer.raw_result_hash.trim(),
      });
      setSelected(await testingApi.getNonFunctionalTestPlan(selected._id));
      await load();
    } catch (reason) {
      setError(
        reason instanceof SyntaxError ? "Tóm tắt kết quả phải là JSON hợp lệ" : messageOf(reason),
      );
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
            Tạo kế hoạch NFR
          </button>
        ) : null
      }
    >
      {dialog}
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
                <button className="apple-button" type="button" onClick={importEvidence}>
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
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(selected.result_summary || {}, null, 2)}
              </pre>
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
