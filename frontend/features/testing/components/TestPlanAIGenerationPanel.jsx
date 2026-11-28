import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { Panel, ErrorState } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { isApprovedCurrentRequirement, messageOf } from "../lib/testing";

const fields = [
  ["objective", "Mục tiêu"],
  ["scope_out", "Ngoài phạm vi"],
  ["entry_criteria", "Điều kiện bắt đầu"],
  ["exit_criteria", "Tiêu chí hoàn thành"],
  ["test_types", "Loại kiểm thử"],
  ["test_level", "Cấp độ kiểm thử"],
  ["risks", "Rủi ro"],
];

function fieldLines(key, value) {
  if (!value) return [];
  if (key === "risks") {
    return value.map((risk) => [risk.title, risk.response].filter(Boolean).join(" — "));
  }
  return Array.isArray(value) ? value.map(String) : [String(value)];
}

export default function TestPlanAIGenerationPanel({
  projectId,
  requirements,
  canGenerate = false,
  onApply,
}) {
  const [requirementVersionIds, setRequirementVersionIds] = useState([]);
  const [instruction, setInstruction] = useState("");
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setPreview(null);
    setSelected(new Set());
  }, [requirements]);

  const approvedRequirements = requirements.filter(isApprovedCurrentRequirement);
  const suggestedFields = fields.map(([key, label]) => {
    const value = preview?.suggestion?.[key];
    const lines = fieldLines(key, value);
    return { key, label, lines, available: lines.length > 0 };
  });
  const generate = async () => {
    if (busy || !requirementVersionIds.length || !canGenerate) return;
    setBusy(true);
    setError("");
    setPreview(null);
    setSelected(new Set());
    try {
      const result = await testingApi.suggestTestPlan(projectId, {
        requirement_version_ids: requirementVersionIds,
        instruction,
      });
      setPreview(result);
      setSelected(
        new Set(
          fields
            .map(([key]) => key)
            .filter((key) => fieldLines(key, result?.suggestion?.[key]).length > 0),
        ),
      );
    } catch (reason) {
      setError(messageOf(reason) || "Không thể tạo gợi ý kế hoạch kiểm thử");
    } finally {
      setBusy(false);
    }
  };

  const apply = () => {
    if (!preview?.suggestion || !selected.size) return;
    const suggestion = preview.suggestion;
    const values = { requirement_version_ids: requirementVersionIds };
    for (const key of selected) {
      if (key === "risks") {
        values.risk_register = (suggestion.risks || []).map((risk) => ({
          risk_id: crypto.randomUUID(),
          category: risk.category || "PRODUCT",
          title: risk.title || "",
          description: risk.description || "",
          probability: risk.probability ?? null,
          impact: risk.impact ?? null,
          exposure: risk.exposure ?? null,
          response: risk.response || "",
          owner_id: risk.owner_id || null,
          status: "OPEN",
          due_at: risk.due_at || null,
        }));
      } else {
        values[key] = suggestion[key];
      }
    }
    onApply(values);
  };

  return (
    <Panel title="Tạo kế hoạch kiểm thử bằng AI">
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <MultiSelect
            compact
            label={
              <span>
                Yêu cầu đã duyệt <span className="text-danger">*</span>
              </span>
            }
            options={approvedRequirements.map((item) => ({
              value: item.current_version_id,
              label: `${item.requirement_key} ${item.current_version?.title || item.title || ""}`,
            }))}
            searchPlaceholder="Tìm yêu cầu đã duyệt"
            value={requirementVersionIds}
            onChange={(next) => {
              setRequirementVersionIds(next);
              setPreview(null);
              setSelected(new Set());
            }}
            disabled={busy}
          />
          <button
            className="apple-button"
            type="button"
            onClick={generate}
            disabled={!canGenerate || busy || !requirementVersionIds.length}
            aria-busy={busy}
          >
            {busy ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
            ) : (
              <Sparkles aria-hidden="true" size={17} />
            )}
            {busy ? "Đang tạo bản xem trước…" : "Tạo bản xem trước bằng AI"}
          </button>
        </div>
        {!approvedRequirements.length && (
          <p className="text-sm text-ink-muted">Chưa có yêu cầu đã duyệt để tạo kế hoạch</p>
        )}
        {!canGenerate && (
          <p className="text-sm text-warning" role="status">
            Bạn chưa được cấp quyền sử dụng AI trong dự án này
          </p>
        )}
        <label className="field-label block">
          Yêu cầu bổ sung cho AI
          <textarea
            className="apple-input mt-2 min-h-20"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            disabled={busy}
            placeholder="Ví dụ: ưu tiên luồng đăng nhập và phân quyền"
          />
        </label>
        {preview && (
          <div className="space-y-3 border-t border-border pt-4">
            <p className="text-sm text-ink-muted" role="status">
              AI có căn cứ cho {suggestedFields.filter((item) => item.available).length}/
              {fields.length} mục. Mục chưa có căn cứ sẽ không được điền
            </p>
            {suggestedFields.map(({ key, label, lines, available }) => (
              <label
                key={key}
                className="flex min-w-0 gap-3 border-b border-border pb-3 last:border-0"
              >
                <input
                  className="mt-1 shrink-0"
                  type="checkbox"
                  disabled={!available}
                  checked={available && selected.has(key)}
                  onChange={() =>
                    setSelected((current) => {
                      const next = new Set(current);
                      if (next.has(key)) next.delete(key);
                      else next.add(key);
                      return next;
                    })
                  }
                />
                <span className="min-w-0 text-sm">
                  <strong>{label}</strong>
                  <span className="mt-1 block whitespace-pre-line text-ink-muted">
                    {available ? lines.join("\n") : "Chưa có căn cứ phù hợp trong yêu cầu đã chọn"}
                  </span>
                </span>
              </label>
            ))}
            {preview.suggestion?.unresolved_questions?.length > 0 && (
              <div className="rounded-control bg-surface-quiet p-3 text-sm">
                <strong>Cần xác nhận</strong>
                <ul className="mt-1 list-disc pl-5 text-ink-muted">
                  {preview.suggestion.unresolved_questions.map((question, index) => (
                    <li key={`${index}:${question}`}>{question}</li>
                  ))}
                </ul>
              </div>
            )}
            {preview.suggestion?.field_evidence?.length > 0 && (
              <details className="text-sm">
                <summary className="cursor-pointer font-medium">Căn cứ theo yêu cầu</summary>
                <ul className="mt-2 space-y-2 text-ink-muted">
                  {preview.suggestion.field_evidence.slice(0, 12).map((item, index) => (
                    <li key={`${item.field}:${index}`}>
                      <strong>
                        {fields.find(([field]) => field === item.field)?.[1] || item.field}:
                      </strong>{" "}
                      {item.evidence_quotes?.map((quote) => `“${quote.quote}”`).join(" · ") ||
                        "Có trích dẫn từ yêu cầu đã chọn"}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <div className="flex justify-end border-t border-border pt-3">
              <button
                className="apple-button"
                type="button"
                onClick={apply}
                disabled={!selected.size}
              >
                {selected.size
                  ? `Dùng ${selected.size} mục trong kế hoạch`
                  : "Chọn mục để tiếp tục"}
              </button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
