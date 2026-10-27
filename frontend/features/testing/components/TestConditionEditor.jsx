import { useEffect, useState } from "react";
import TestBasisPanel from "./TestBasisPanel";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { textDoc, valueLabel } from "../lib/testing";

const defaults = {
  title: "",
  category: "",
  description: "",
  basis_refs: [],
  coverage_item: "",
  test_level: "SYSTEM",
  test_type: "FUNCTIONAL",
  risk: "MEDIUM",
  priority: "MEDIUM",
  technique_candidates: [],
  testability_status: "TESTABLE",
  analysis_findings: [],
};

export default function TestConditionEditor({ initialValue, requirements, onSave, onCancel }) {
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
  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));
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
          setError(reason.message || "Không thể lưu điều kiện kiểm thử");
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
          <select
            className="apple-input mt-2"
            value={value.category}
            onChange={(event) => setField("category", event.target.value)}
            required
          >
            <option value="">Chọn nhóm điều kiện</option>
            <option value="POSITIVE">Dương</option>
            <option value="NEGATIVE">Âm</option>
            <option value="BOUNDARY">Biên</option>
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
          Loại kiểm thử
          <input
            className="apple-input mt-2"
            value={value.test_type}
            onChange={(event) => setField("test_type", event.target.value)}
            required
          />
        </label>
        <label className="field-label">
          Rủi ro
          <select
            className="apple-input mt-2"
            value={value.risk}
            onChange={(event) => setField("risk", event.target.value)}
          >
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((item) => (
              <option key={item} value={item}>
                {valueLabel(item.toLowerCase())}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Ưu tiên
          <select
            className="apple-input mt-2"
            value={value.priority}
            onChange={(event) => setField("priority", event.target.value)}
          >
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((item) => (
              <option key={item} value={item}>
                {valueLabel(item.toLowerCase())}
              </option>
            ))}
          </select>
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
