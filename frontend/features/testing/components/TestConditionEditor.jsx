import { useEffect, useState } from "react";
import TestBasisPanel from "./TestBasisPanel";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { messageOf, textDoc, valueLabel } from "../lib/testing";

const defaults = {
  title: "",
  category: "",
  description: "",
  basis_refs: [],
  coverage_item: "",
  test_level: "",
  test_type: "",
  risk: "",
  priority: "",
  technique_candidates: [],
  testability_status: "TESTABLE",
  analysis_findings: [],
};

export default function TestConditionEditor({
  initialValue,
  requirements,
  strategies = [],
  riskLevels = [],
  priorityLevels = [],
  projectId,
  onSave,
  onCancel,
}) {
  const [value, setValue] = useState(defaults);
  const [error, setError] = useState("");
  useEffect(
    () =>
      setValue(
        initialValue
          ? {
              ...defaults,
              ...initialValue,
              description:
                initialValue.description || initialValue.coverage_item || initialValue.title || "",
            }
          : defaults,
      ),
    [initialValue],
  );
  useEffect(() => {
    if (initialValue) return;
    const strategy = strategies.find((item) => item.active_approved);
    if (!strategy) return;
    setValue((current) => ({
      ...current,
      test_level: current.test_level || strategy.test_levels?.[0] || "",
      test_type: current.test_type || strategy.test_types?.[0] || "",
    }));
  }, [initialValue, strategies]);
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));
  const levels = [
    ...new Set(
      [...strategies.flatMap((item) => item.test_levels || []), value.test_level].filter(Boolean),
    ),
  ];
  const types = [
    ...new Set(
      [...strategies.flatMap((item) => item.test_types || []), value.test_type].filter(Boolean),
    ),
  ];
  const configuredRiskLevels = [
    ...new Set(
      [...riskLevels, value.risk].map((item) => String(item || "").trim()).filter(Boolean),
    ),
  ];
  const configuredPriorityLevels = [
    ...new Set(
      [...priorityLevels, value.priority].map((item) => String(item || "").trim()).filter(Boolean),
    ),
  ];
  return (
    <form
      className="space-y-4 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          const payload = {
            title: value.title,
            category: value.category || null,
            description_doc: textDoc(value.description || value.title),
            basis_refs: value.basis_refs,
            coverage_item: value.coverage_item,
            test_level: value.test_level,
            test_type: value.test_type,
            risk: value.risk,
            priority: value.priority,
            technique_candidates: value.technique_candidates,
            testability_status: value.testability_status,
            analysis_findings: value.analysis_findings,
            origin: value.origin || "MANUAL",
            ai_result_id: value.ai_result_id || null,
          };
          await onSave(payload);
        } catch (reason) {
          setError(messageOf(reason) || "Không thể lưu điều kiện kiểm thử");
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      <div>
        <ContentOriginBadge origin={value.origin || "manual"} />
      </div>
      <TestBasisPanel
        refs={value.basis_refs}
        onChange={(refs) => setField("basis_refs", refs)}
        requirements={requirements}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <label className="field-label">
          Tên điều kiện
          <input
            className="apple-input mt-2"
            value={value.title}
            onChange={(event) => setField("title", event.target.value)}
            required
          />
        </label>
        <label className="field-label">
          Hạng mục độ phủ
          <input
            className="apple-input mt-2"
            value={value.coverage_item}
            onChange={(event) => setField("coverage_item", event.target.value)}
            required
          />
        </label>
        <label className="field-label md:col-span-2">
          Mô tả
          <textarea
            className="apple-input mt-2 min-h-24"
            value={value.description}
            onChange={(event) => setField("description", event.target.value)}
          />
        </label>
        <label className="field-label">
          Nhóm điều kiện
          <input
            className="apple-input mt-2"
            value={value.category}
            onChange={(event) => setField("category", event.target.value)}
            maxLength={100}
            placeholder="Nhập nhóm điều kiện"
          />
        </label>
        <label className="field-label">
          Cấp kiểm thử
          <select
            aria-label="Cấp kiểm thử"
            className="apple-input mt-2"
            value={value.test_level}
            onChange={(event) => setField("test_level", event.target.value)}
            required
            disabled={!levels.length}
          >
            <option value="">Chọn cấp kiểm thử</option>
            {levels.map((item) => (
              <option key={item} value={item}>
                {valueLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Loại kiểm thử
          <select
            aria-label="Loại kiểm thử"
            className="apple-input mt-2"
            value={value.test_type}
            onChange={(event) => setField("test_type", event.target.value)}
            required
            disabled={!types.length}
          >
            <option value="">Chọn loại kiểm thử</option>
            {types.map((item) => (
              <option key={item} value={item}>
                {valueLabel(item)}
              </option>
            ))}
          </select>
        </label>
        {(!levels.length || !types.length) && (
          <p className="text-sm text-ink-muted md:col-span-2">
            {!levels.length && !types.length
              ? "Chiến lược đã duyệt chưa có cấp và loại kiểm thử."
              : !levels.length
                ? "Chiến lược đã duyệt chưa có cấp kiểm thử."
                : "Chiến lược đã duyệt chưa có loại kiểm thử."}{" "}
            {projectId && (
              <a
                className="font-medium text-brand underline"
                href={`/du-an/${projectId}/quan-tri-kiem-thu`}
              >
                Mở chiến lược kiểm thử
              </a>
            )}
          </p>
        )}
        <label className="field-label">
          Mức rủi ro
          {configuredRiskLevels.length ? (
            <select
              aria-label="Mức rủi ro điều kiện kiểm thử"
              className="apple-input mt-2"
              value={value.risk}
              onChange={(event) => setField("risk", event.target.value)}
              required
            >
              <option value="">Chọn mức rủi ro theo chiến lược dự án</option>
              {configuredRiskLevels.map((item) => (
                <option key={item} value={item}>
                  {valueLabel(item)}
                </option>
              ))}
            </select>
          ) : (
            <input
              className="apple-input mt-2"
              value={value.risk}
              onChange={(event) => setField("risk", event.target.value)}
              maxLength={100}
              placeholder="Nhập theo quy ước dự án"
              required
            />
          )}
        </label>
        <label className="field-label">
          Mức ưu tiên
          {configuredPriorityLevels.length ? (
            <select
              aria-label="Mức ưu tiên điều kiện kiểm thử"
              className="apple-input mt-2"
              value={value.priority}
              onChange={(event) => setField("priority", event.target.value)}
              required
            >
              <option value="">Chọn mức ưu tiên theo chiến lược dự án</option>
              {configuredPriorityLevels.map((item) => (
                <option key={item} value={item}>
                  {valueLabel(item)}
                </option>
              ))}
            </select>
          ) : (
            <input
              className="apple-input mt-2"
              value={value.priority}
              onChange={(event) => setField("priority", event.target.value)}
              maxLength={100}
              placeholder="Nhập theo quy ước dự án"
              required
            />
          )}
        </label>
        <label className="field-label">
          Khả năng kiểm thử
          <select
            className="apple-input mt-2"
            value={value.testability_status}
            onChange={(event) => setField("testability_status", event.target.value)}
          >
            {["TESTABLE", "TESTABLE_WITH_RISK", "NOT_TESTABLE", "NEEDS_CLARIFICATION"].map(
              (item) => (
                <option key={item} value={item}>
                  {valueLabel(item)}
                </option>
              ),
            )}
          </select>
        </label>
        <label className="field-label">
          Kỹ thuật đề xuất
          <input
            className="apple-input mt-2"
            value={value.technique_candidates.join(", ")}
            onChange={(event) =>
              setField(
                "technique_candidates",
                event.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              )
            }
          />
        </label>
      </div>
      <div className="flex justify-end gap-3">
        <button className="secondary-button" type="button" onClick={onCancel}>
          Hủy
        </button>
        <button className="apple-button" type="submit">
          Lưu điều kiện
        </button>
      </div>
    </form>
  );
}
