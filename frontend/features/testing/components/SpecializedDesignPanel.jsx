"use client";
import { useCallback, useEffect, useState } from "react";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";

export default function SpecializedDesignPanel({ project, requirements }) {
  const [securityResults, setSecurityResults] = useState([]);
  const [performancePlans, setPerformancePlans] = useState([]);
  const [requirementVersionIds, setRequirementVersionIds] = useState([]);
  const [securityCategories, setSecurityCategories] = useState([
    "authorization",
    "input_validation",
    "session",
  ]);
  const [performance, setPerformance] = useState({
    name: "",
    objective: "",
    targetVirtualUsers: "",
    targetRequestsPerSecond: "",
    durationMinutes: "",
    responseTimeP95Ms: "",
    maximumErrorRate: "",
  });
  const [error, setError] = useState("");
  const [aiAction, setAiAction] = useState("");
  const canGenerateSecurity = project.current_permissions?.includes("ai.generate_security_tests");
  const canGeneratePerformance = project.current_permissions?.includes(
    "ai.generate_performance_plan",
  );
  const load = useCallback(async () => {
    try {
      const [securityValues, performanceValues] = await Promise.all([
        canGenerateSecurity
          ? testingApi.listSecurityTestSuggestions(project._id)
          : Promise.resolve([]),
        canGeneratePerformance
          ? testingApi.listPerformancePlanDrafts(project._id)
          : Promise.resolve([]),
      ]);
      setSecurityResults(securityValues);
      setPerformancePlans(performanceValues);
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canGeneratePerformance, canGenerateSecurity, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const toggleCategory = (category) => {
    setSecurityCategories((current) =>
      current.includes(category)
        ? current.filter((value) => value !== category)
        : [...current, category],
    );
  };
  const generateSecurity = async () => {
    if (securityCategories.length === 0) {
      setError("Phải chọn ít nhất một nhóm kiểm thử bảo mật");
      return;
    }
    setAiAction("security");
    try {
      await testingApi.generateSecurityTestSuggestions(project._id, {
        requirement_version_ids: requirementVersionIds,
        categories: securityCategories,
        context: "",
        idempotency_key: crypto.randomUUID(),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  const generatePerformance = async (event) => {
    event.preventDefault();
    setAiAction("performance");
    try {
      await testingApi.generatePerformancePlanDraft(project._id, {
        name: performance.name,
        objective: performance.objective,
        requirement_version_ids: requirementVersionIds,
        workload_types: ["baseline", "load", "stress", "spike", "soak"],
        target_virtual_users: Number(performance.targetVirtualUsers),
        target_requests_per_second: performance.targetRequestsPerSecond
          ? Number(performance.targetRequestsPerSecond)
          : null,
        duration_minutes: Number(performance.durationMinutes),
        response_time_p95_ms: performance.responseTimeP95Ms
          ? Number(performance.responseTimeP95Ms)
          : null,
        maximum_error_rate: performance.maximumErrorRate
          ? Number(performance.maximumErrorRate)
          : null,
        context: "",
        idempotency_key: crypto.randomUUID(),
      });
      setPerformance({
        name: "",
        objective: "",
        targetVirtualUsers: "",
        targetRequestsPerSecond: "",
        durationMinutes: "",
        responseTimeP95Ms: "",
        maximumErrorRate: "",
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAiAction("");
    }
  };
  if (!canGenerateSecurity && !canGeneratePerformance) return null;
  return (
    <Panel title="Thiết kế kiểm thử chuyên sâu">
      {error && <ErrorState message={error} />}
      <div className="space-y-4 border-b border-border p-5">
        <label className="field-label block">
          Phiên bản yêu cầu làm bằng chứng
          <select
            aria-label="Phiên bản yêu cầu cho thiết kế chuyên sâu"
            className="apple-input mt-2 min-h-28"
            multiple
            value={requirementVersionIds}
            onChange={(event) =>
              setRequirementVersionIds(
                Array.from(event.target.selectedOptions, (option) => option.value),
              )
            }
          >
            {requirements
              .filter((item) => item.current_version_id)
              .map((item) => (
                <option key={item.current_version_id} value={item.current_version_id}>
                  {item.requirement_key} {item.current_version?.title || item.title}
                </option>
              ))}
          </select>
        </label>
        <p className="text-xs text-ink-muted">
          Kết quả chỉ là bản nháp cần con người rà soát và không thực hiện quét lỗ hổng hoặc phát
          tải
        </p>
      </div>
      <div className="grid gap-5 p-5 xl:grid-cols-2">
        {canGenerateSecurity && (
          <div className="space-y-3">
            <h3 className="font-medium text-ink">Gợi ý kiểm thử bảo mật</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ["authorization", "Phân quyền"],
                ["authentication", "Xác thực"],
                ["input_validation", "Kiểm tra đầu vào"],
                ["session", "Phiên đăng nhập"],
                ["data_protection", "Bảo vệ dữ liệu"],
              ].map(([value, label]) => (
                <label className="flex items-center gap-2 text-sm" key={value}>
                  <input
                    type="checkbox"
                    checked={securityCategories.includes(value)}
                    onChange={() => toggleCategory(value)}
                  />
                  {label}
                </label>
              ))}
            </div>
            <button
              aria-busy={aiAction === "security"}
              className="apple-button"
              disabled={Boolean(aiAction)}
              type="button"
              onClick={generateSecurity}
            >
              {aiAction === "security" ? "AI đang tạo bản nháp bảo mật" : "Tạo bản nháp bảo mật"}
            </button>
            <div className="space-y-3">
              {securityResults.map((result) => (
                <div className="rounded-xl border border-border p-3" key={result._id}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-ink">{result.candidates.length} gợi ý</p>
                    <StatusPill value={result.generation_status} />
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-ink-muted">
                    {result.candidates.map((candidate) => (
                      <li className="rounded-lg bg-surface-subtle p-3" key={candidate.candidate_id}>
                        <p className="font-medium text-ink">{candidate.title}</p>
                        <p className="mt-1">{valueLabel(candidate.category)}</p>
                        <p className="mt-1">Thao tác {candidate.action}</p>
                        <p className="mt-1">Kết quả {candidate.expected}</p>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-ink-muted">
                    {result.model?.model} · Độ tin cậy {result.confidence}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
        {canGeneratePerformance && (
          <div className="space-y-3">
            <h3 className="font-medium text-ink">Bản nháp kế hoạch hiệu năng</h3>
            <form className="space-y-3" onSubmit={generatePerformance}>
              <input
                aria-label="Tên kế hoạch hiệu năng"
                className="apple-input"
                required
                placeholder="Tên kế hoạch"
                value={performance.name}
                onChange={(event) => setPerformance({ ...performance, name: event.target.value })}
              />
              <textarea
                aria-label="Mục tiêu kế hoạch hiệu năng"
                className="apple-input min-h-20"
                placeholder="Mục tiêu"
                value={performance.objective}
                onChange={(event) =>
                  setPerformance({ ...performance, objective: event.target.value })
                }
              />
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  aria-label="Số người dùng ảo mục tiêu"
                  className="apple-input"
                  min="1"
                  required
                  type="number"
                  value={performance.targetVirtualUsers}
                  onChange={(event) =>
                    setPerformance({ ...performance, targetVirtualUsers: event.target.value })
                  }
                />
                <input
                  aria-label="Số yêu cầu mỗi giây"
                  className="apple-input"
                  min="0.01"
                  step="0.01"
                  type="number"
                  value={performance.targetRequestsPerSecond}
                  onChange={(event) =>
                    setPerformance({
                      ...performance,
                      targetRequestsPerSecond: event.target.value,
                    })
                  }
                />
                <input
                  aria-label="Thời lượng kiểm thử phút"
                  className="apple-input"
                  min="1"
                  required
                  type="number"
                  value={performance.durationMinutes}
                  onChange={(event) =>
                    setPerformance({ ...performance, durationMinutes: event.target.value })
                  }
                />
                <input
                  aria-label="Ngưỡng phản hồi P95 mili giây"
                  className="apple-input"
                  min="1"
                  type="number"
                  value={performance.responseTimeP95Ms}
                  onChange={(event) =>
                    setPerformance({ ...performance, responseTimeP95Ms: event.target.value })
                  }
                />
              </div>
              <label className="field-label block">
                Tỷ lệ lỗi tối đa
                <input
                  aria-label="Tỷ lệ lỗi tối đa"
                  className="apple-input mt-2"
                  max="1"
                  min="0"
                  step="0.001"
                  type="number"
                  value={performance.maximumErrorRate}
                  onChange={(event) =>
                    setPerformance({ ...performance, maximumErrorRate: event.target.value })
                  }
                />
              </label>
              <button
                aria-busy={aiAction === "performance"}
                className="apple-button"
                disabled={Boolean(aiAction)}
                type="submit"
              >
                {aiAction === "performance"
                  ? "AI đang tạo bản nháp hiệu năng"
                  : "Tạo bản nháp hiệu năng"}
              </button>
            </form>
            <div className="space-y-3">
              {performancePlans.map((plan) => (
                <div className="rounded-xl border border-border p-3" key={plan._id}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-ink">{plan.name}</p>
                    <StatusPill value={plan.generation_status} />
                  </div>
                  <p className="mt-1 text-sm text-ink-muted">
                    {plan.scenarios.length} kịch bản tải và chưa thực thi phát tải
                  </p>
                  <div className="mt-2 space-y-2">
                    {plan.scenarios.map((scenario) => (
                      <div
                        className="rounded-lg bg-surface-subtle p-3 text-sm"
                        key={scenario.scenario_id}
                      >
                        <p className="font-medium text-ink">{scenario.title}</p>
                        <p className="mt-1 text-ink-muted">
                          {scenario.virtual_users} người dùng · {scenario.duration_minutes} phút
                        </p>
                        <p className="mt-1 text-ink-muted">{scenario.expected}</p>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-ink-muted">
                    {plan.model?.model} · Độ tin cậy {plan.confidence}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
