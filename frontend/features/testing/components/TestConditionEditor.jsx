import { useEffect, useState } from "react";
import TestBasisPanel from "./TestBasisPanel";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { messageOf, textDoc, valueLabel } from "../lib/testing";

const defaults = {
  title: "",
  category: "",
  description: "",
  basis_refs: [],
  test_level: "",
  test_type: "",
  risk: "",
  priority: "",
  technique_candidates: [],
  testability_status: "TESTABLE",
  analysis_findings: [],
};

const levels = [
  ["COMPONENT", "Thành phần"],
  ["COMPONENT_INTEGRATION", "Tích hợp thành phần"],
  ["SYSTEM", "Hệ thống"],
  ["SYSTEM_INTEGRATION", "Tích hợp hệ thống"],
  ["ACCEPTANCE", "Chấp nhận"],
];

const types = [
  ["functional", "Chức năng"],
  ["non_functional", "Phi chức năng"],
  ["confirmation", "Xác nhận"],
  ["regression", "Hồi quy"],
];

const techniques = [
  ["EQUIVALENCE_PARTITIONING", "Phân vùng tương đương"],
  ["BOUNDARY_VALUE", "Giá trị biên"],
  ["DECISION_TABLE", "Bảng quyết định"],
  ["STATE_TRANSITION", "Chuyển trạng thái"],
  ["ERROR_GUESSING", "Dự đoán lỗi"],
];

const assessments = [
  ["HIGH", "Cao"],
  ["MEDIUM", "Trung bình"],
  ["LOW", "Thấp"],
];

export default function TestConditionEditor({ initialValue, requirements, onSave, onCancel }) {
  const [value, setValue] = useState(defaults);
  const [error, setError] = useState("");

  useEffect(() => {
    setValue(
      initialValue
        ? {
            ...defaults,
            ...initialValue,
            description:
              initialValue.description || initialValue.coverage_item || initialValue.title || "",
          }
        : defaults,
    );
  }, [initialValue]);

  const setField = (key, next) => setValue((current) => ({ ...current, [key]: next }));
  const selectOptions = (items, current) =>
    current && !items.some(([id]) => id === current)
      ? [[current, valueLabel(current)], ...items]
      : items;

  return (
    <form
      className="test-design-form space-y-4 p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          await onSave({
            title: value.title,
            category: value.category || null,
            description_doc: textDoc(value.description),
            basis_refs: value.basis_refs,
            coverage_item: value.title,
            test_level: value.test_level,
            test_type: value.test_type,
            risk: value.risk,
            priority: value.priority,
            technique_candidates: value.technique_candidates,
            testability_status: value.testability_status,
            analysis_findings: value.analysis_findings,
            origin: value.origin || "MANUAL",
            ai_result_id: value.ai_result_id || null,
          });
        } catch (reason) {
          setError(messageOf(reason) || "Không thể lưu điều kiện kiểm thử");
        }
      }}
    >
      {error && <p className="text-sm text-danger">{error}</p>}
      <ContentOriginBadge origin={value.origin || "manual"} />
      <label className="field-label block">
        Tên điều kiện <span className="text-danger">*</span>
        <input
          className="apple-input mt-2 w-full"
          value={value.title}
          onChange={(event) => setField("title", event.target.value)}
          minLength={2}
          maxLength={300}
          required
        />
      </label>
      <label className="field-label block">
        Mô tả
        <textarea
          className="apple-input mt-2 min-h-24 w-full"
          value={value.description}
          onChange={(event) => setField("description", event.target.value)}
          maxLength={5000}
        />
      </label>
      <TestBasisPanel
        refs={value.basis_refs}
        onChange={(refs) => setField("basis_refs", refs)}
        requirements={requirements}
      />
      <details className="rounded-control border border-border p-4">
        <summary className="cursor-pointer font-medium">Tùy chọn</summary>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="field-label">
            Nhóm điều kiện
            <input
              className="apple-input mt-2"
              value={value.category || ""}
              onChange={(event) => setField("category", event.target.value)}
              maxLength={100}
            />
          </label>
          <label className="field-label">
            Cấp kiểm thử
            <select
              className="apple-input mt-2"
              value={value.test_level || ""}
              onChange={(event) => setField("test_level", event.target.value)}
            >
              <option value="">-</option>
              {selectOptions(levels, value.test_level).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Loại kiểm thử
            <select
              className="apple-input mt-2"
              value={value.test_type || ""}
              onChange={(event) => setField("test_type", event.target.value)}
            >
              <option value="">-</option>
              {selectOptions(types, value.test_type).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {[
            ["risk", "Rủi ro"],
            ["priority", "Ưu tiên"],
          ].map(([field, label]) => (
            <label className="field-label" key={field}>
              {label}
              <select
                className="apple-input mt-2"
                value={value[field] || ""}
                onChange={(event) => setField(field, event.target.value)}
              >
                <option value="">-</option>
                {selectOptions(assessments, value[field]).map(([id, text]) => (
                  <option key={id} value={id}>
                    {text}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <label className="field-label">
            Khả năng kiểm thử
            <select
              className="apple-input mt-2"
              value={value.testability_status || "TESTABLE"}
              onChange={(event) => setField("testability_status", event.target.value)}
            >
              {[
                ["TESTABLE", "Có thể kiểm thử"],
                ["TESTABLE_WITH_RISK", "Có thể kiểm thử, có rủi ro"],
                ["NOT_TESTABLE", "Chưa thể kiểm thử"],
                ["NEEDS_CLARIFICATION", "Cần làm rõ"],
              ].map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="space-y-2 md:col-span-2">
            <legend className="field-label">Kỹ thuật kiểm thử</legend>
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {techniques.map(([id, label]) => (
                <label className="flex items-center gap-2 text-sm" key={id}>
                  <input
                    type="checkbox"
                    checked={value.technique_candidates.includes(id)}
                    onChange={(event) =>
                      setField(
                        "technique_candidates",
                        event.target.checked
                          ? [...new Set([...value.technique_candidates, id])]
                          : value.technique_candidates.filter((item) => item !== id),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </details>
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
