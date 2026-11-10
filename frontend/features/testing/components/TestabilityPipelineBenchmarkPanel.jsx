"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";

const stages = [
  { id: "TEST_PLAN", label: "Lập kế hoạch kiểm thử" },
  { id: "TEST_SCENARIO", label: "Sinh kịch bản kiểm thử" },
  { id: "TEST_CASE", label: "Sinh ca kiểm thử" },
];

function candidateItems(stage, result) {
  if (stage === "TEST_PLAN") {
    const suggestion = result?.suggestion || {};
    return Object.entries(suggestion)
      .filter(([key, value]) => key !== "evidence_quotes" && key !== "field_evidence" && value)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join("; ") : value}`);
  }
  return (result?.items || []).map(({ draft = {} }) => {
    const steps = (draft.steps || []).map((step) =>
      [step.action, step.expected_result].filter(Boolean).join(" → "),
    );
    return [draft.title, draft.objective, draft.description, draft.preconditions, ...steps]
      .filter(Boolean)
      .join("\n");
  }).filter(Boolean);
}

export default function TestabilityPipelineBenchmarkPanel({ project, requirements }) {
  const { user } = useAuth();
  const canManage = user?.system_role === "ADMIN";
  const [versionId, setVersionId] = useState("");
  const [stage, setStage] = useState("TEST_PLAN");
  const [mode, setMode] = useState("INDEPENDENT");
  const [goldText, setGoldText] = useState("");
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRuns = useCallback(async () => {
    if (!canManage) return;
    try {
      const result = await testingApi.listTestabilityPipelineStageRuns(project._id, 30);
      setRuns(Array.isArray(result) ? result : []);
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canManage, project._id]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  const runStage = async () => {
    const source = requirements.find((item) => item.current_version_id === versionId);
    if (!source || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const parsedGold = JSON.parse(goldText);
      const selectedStages = mode === "END_TO_END" ? stages : stages.filter((item) => item.id === stage);
      if (mode === "END_TO_END" && (!parsedGold || Array.isArray(parsedGold))) {
        throw new Error("Chế độ xuyên suốt cần JSON là đối tượng có đáp án riêng cho TEST_PLAN, TEST_SCENARIO và TEST_CASE.");
      }
      const goldFor = (id) => mode === "END_TO_END" ? parsedGold[id] : parsedGold;
      for (const current of selectedStages) {
        if (!Array.isArray(goldFor(current.id)) || !goldFor(current.id).length) {
          throw new Error(`Thiếu danh sách đáp án chuẩn cho ${current.label}.`);
        }
      }
      const upstreamContext = {};
      const reports = [];
      for (const current of selectedStages) {
        const stageStartedAt = performance.now();
        let latestResult;
        if (current.id === "TEST_PLAN") {
          latestResult = await testingApi.suggestTestPlanDraft(project._id, {
            requirement_version_ids: [versionId],
            instruction: "Đánh giá benchmark; chỉ tạo đề xuất, không lưu kế hoạch.",
          });
          upstreamContext.test_plan = latestResult.suggestion;
        } else if (current.id === "TEST_SCENARIO") {
          latestResult = await testingApi.generateScenarios(versionId, {
            preview_only: true,
            max_cases: 20,
            instruction: mode === "END_TO_END"
              ? `Dùng kế hoạch kiểm thử sau làm ngữ cảnh; chỉ xem trước kịch bản, không lưu.\n${JSON.stringify(upstreamContext.test_plan).slice(0, 12000)}`
              : "Tạo kịch bản kiểm thử độc lập từ yêu cầu và tiêu chí chấp nhận đã duyệt; chỉ xem trước, không lưu.",
          });
          upstreamContext.test_scenarios = candidateItems("TEST_SCENARIO", latestResult);
        } else if (current.id === "TEST_CASE") {
          latestResult = await testingApi.generateTestCases(versionId, {
            preview_only: true,
            max_cases: 20,
            instruction: mode === "END_TO_END"
              ? `Dùng kế hoạch và kịch bản AI tạo sau làm ngữ cảnh.\nKế hoạch: ${JSON.stringify(upstreamContext.test_plan).slice(0, 6000)}\nKịch bản: ${JSON.stringify(upstreamContext.test_scenarios).slice(0, 6000)}\nChỉ xem trước ca kiểm thử, không lưu.`
              : "Tạo ca kiểm thử độc lập từ yêu cầu và tiêu chí chấp nhận đã duyệt; chỉ xem trước, không lưu.",
          });
        }
        const currentGold = goldFor(current.id);
        const output = candidateItems(current.id, latestResult);
        if (!output.length) throw new Error(`${current.label}: AI không trả về đầu ra có thể chấm.`);
        reports.push(await testingApi.saveTestabilityPipelineStageRun({
          project_id: project._id,
          requirement_version_id: versionId,
          stage: current.id,
          mode,
          upstream_context: current.id === "TEST_PLAN" ? {} : upstreamContext,
          gold_items: currentGold,
          candidate_items: output,
          generation_metadata: {
            capability: latestResult.capability || current.id,
            provider: latestResult.provider || latestResult.model?.provider,
            model: latestResult.model || {},
            prompt_version: latestResult.prompt_version || "unknown",
            created_at: latestResult.created_at || new Date().toISOString(),
            duration_ms: Math.round(performance.now() - stageStartedAt),
          },
        }));
      }
      setNotice(`Đã chạy AI thật và lưu ${reports.length} kết quả. Không tạo tài sản kiểm thử trong dự án.`);
      await loadRuns();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  if (!canManage) {
    return <Panel title="Benchmark xuyên suốt quy trình"><p className="p-4 text-sm text-ink-muted">Chỉ quản trị viên hệ thống được tạo và chạy benchmark.</p></Panel>;
  }

  return (
    <div className="space-y-4">
      {error && <ErrorState message={error} />}
      {notice && <p className="rounded-lg border border-success/30 bg-success-soft p-3 text-sm text-success">{notice}</p>}
      <Panel title="Benchmark xuyên suốt quy trình kiểm thử">
        <div className="space-y-4 p-4 text-sm">
          <p className="leading-6 text-ink-muted">Chạy AI qua Test Plan → Scenario → Test Case ở chế độ xuyên suốt, hoặc chạy riêng từng giai đoạn. Scenario và Test Case luôn gọi chế độ xem trước; không tạo bản nháp hay thay đổi dữ liệu nghiệp vụ. Điểm hiện tại đối chiếu các tiêu chí và từ khóa do người đánh giá nhập, không dùng LLM tự chấm.</p>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="field-label">Yêu cầu đã duyệt<select className="apple-input mt-2 w-full" value={versionId} onChange={(event) => setVersionId(event.target.value)}><option value="">Chọn yêu cầu</option>{requirements.filter((item) => item.current_version_id).map((item) => <option key={item.current_version_id} value={item.current_version_id}>{item.requirement_key} · {item.current_version?.title || "Yêu cầu"}</option>)}</select></label>
            <label className="field-label">Chế độ<select className="apple-input mt-2 w-full" value={mode} onChange={(event) => setMode(event.target.value)}><option value="INDEPENDENT">Độc lập — một giai đoạn</option><option value="END_TO_END">Xuyên suốt — truyền ngữ cảnh AI</option></select></label>
            {mode === "INDEPENDENT" && <label className="field-label">Giai đoạn<select className="apple-input mt-2 w-full" value={stage} onChange={(event) => setStage(event.target.value)}>{stages.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>}
          </div>
          <label className="field-label block">Đáp án chuẩn đã được người đánh giá chuẩn bị · JSON<textarea className="apple-input mt-2 min-h-32 w-full font-mono text-xs" value={goldText} onChange={(event) => setGoldText(event.target.value)} placeholder={'[{"label":"Khóa tài khoản sau 5 lần sai","keywords":["5 lần", "khóa tài khoản"]}]'} /></label>
          <p className="text-xs text-ink-faint">Mỗi tiêu chí có nhãn và cụm từ thể hiện điều kiện cần được bao phủ. Lưu ý: điểm khớp từ khóa là baseline từ vựng, cần QA rà soát ngữ nghĩa trước khi kết luận học thuật.</p>
          <button className="apple-button" type="button" disabled={busy || !versionId || !goldText.trim()} onClick={() => void runStage()}>{busy ? "Đang gọi AI và chấm…" : mode === "END_TO_END" ? "Chạy xuyên suốt 3 giai đoạn" : "Chạy giai đoạn đã chọn"}</button>
        </div>
      </Panel>
      <Panel title="Lịch sử benchmark các giai đoạn">
        <div className="space-y-4 p-4"><DataTable items={runs.map((item) => ({ ...item, _id: item.run_id }))} onSelect={(item) => void testingApi.getTestabilityPipelineStageRun(project._id, item.run_id).then(setSelectedRun).catch((reason) => setError(messageOf(reason)))} empty="Chưa có kết quả benchmark cho các giai đoạn." columns={[
          { key: "created_at", label: "Thời điểm", render: (item) => formatDate(item.created_at) },
          { key: "stage", label: "Giai đoạn", render: (item) => stages.find((value) => value.id === item.stage)?.label || valueLabel(item.stage) },
          { key: "mode", label: "Chế độ", render: (item) => item.mode === "END_TO_END" ? "Xuyên suốt" : "Độc lập" },
          { key: "precision", label: "Precision", render: (item) => `${((item.scores?.precision || 0) * 100).toFixed(1)}%` },
          { key: "recall", label: "Recall", render: (item) => `${((item.scores?.recall || 0) * 100).toFixed(1)}%` },
          { key: "f1", label: "F1", render: (item) => `${((item.scores?.f1 || 0) * 100).toFixed(1)}%` },
          { key: "duplicates", label: "Trùng lặp", render: (item) => `${((item.scores?.duplicate_rate || 0) * 100).toFixed(1)}%` },
          { key: "matched_gold_items", label: "Đạt / chuẩn", render: (item) => `${item.scores?.matched_gold_items?.length || 0}/${item.scores?.gold_count || 0}` },
        ]} />{selectedRun && <div className="space-y-3 rounded-xl border border-border bg-surface-quiet p-4"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold text-ink">Chi tiết lượt chạy · {stages.find((item) => item.id === selectedRun.stage)?.label || selectedRun.stage}</h3><button className="apple-button-secondary" type="button" onClick={() => setSelectedRun(null)}>Đóng</button></div><p className="text-sm text-ink-muted">Đáp án đã nhập · {selectedRun.gold_items?.length || 0} tiêu chí</p><pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface p-3 text-xs">{JSON.stringify(selectedRun.gold_items, null, 2)}</pre><p className="text-sm text-ink-muted">Đầu ra AI · {selectedRun.candidate_items?.length || 0} mục</p><pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface p-3 text-xs">{JSON.stringify(selectedRun.candidate_items, null, 2)}</pre><p className="text-xs text-ink-faint">{selectedRun.scoring_method} · Thời gian: {selectedRun.generation_metadata?.duration_ms ?? "—"} ms</p></div>}</div>
      </Panel>
    </div>
  );
}
