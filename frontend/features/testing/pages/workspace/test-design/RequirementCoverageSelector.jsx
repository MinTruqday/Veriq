import { useEffect, useRef, useState } from "react";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { testingApi } from "../../../services/testing.service";

function businessRuleLabel(item) {
  const match = /business_rule:(\d+)/i.exec(item.source_ref || "");
  return match ? `BR-${String(match[1]).padStart(2, "0")}` : "Quy tắc nghiệp vụ";
}

export default function RequirementCoverageSelector({
  requirements,
  requirementVersionIds,
  value,
  onChange,
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const versionKey = [...new Set(requirementVersionIds || [])].sort().join("|");
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    valueRef.current = value;
    onChangeRef.current = onChange;
  }, [onChange, value]);

  useEffect(() => {
    const versionIds = versionKey ? versionKey.split("|") : [];
    if (!versionIds.length) {
      setItems([]);
      setError("");
      setLoading(false);
      if (valueRef.current.length) onChangeRef.current([]);
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError("");
    Promise.all(versionIds.map((id) => testingApi.listRequirementCoverageItems(id)))
      .then((sources) => {
        if (!active) return;
        const nextItems = sources.flat().filter((item) => item.source_type === "business_rule");
        setItems(nextItems);
        const available = new Set(nextItems.map((item) => item.coverage_item_id));
        const currentValue = valueRef.current;
        const nextValue = currentValue.filter((id) => available.has(id));
        if (nextValue.length !== currentValue.length) onChangeRef.current(nextValue);
      })
      .catch(() => {
        if (active) {
          setItems([]);
          setError("Không thể tải quy tắc nghiệp vụ của yêu cầu đã chọn.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [versionKey]);

  const requirementByVersion = new Map(requirements.map((item) => [item.current_version_id, item]));
  const options = items.map((item) => {
    const requirement = requirementByVersion.get(item.requirement_version_id);
    return {
      value: item.coverage_item_id,
      label: `${requirement?.requirement_key || "Yêu cầu"} · ${businessRuleLabel(item)}`,
      description: item.source_quote,
    };
  });
  const currentOptions = new Set(options.map((item) => item.value));
  const missing = value
    .filter((id) => !currentOptions.has(id))
    .map((id) => ({
      value: id,
      label: "Quy tắc đã liên kết",
      description: "Nguồn không còn khả dụng.",
    }));

  return (
    <div className="space-y-1">
      <MultiSelect
        label="Quy tắc nghiệp vụ cần bao phủ"
        searchPlaceholder="Tìm quy tắc nghiệp vụ"
        emptyMessage={loading ? "Đang tải quy tắc nghiệp vụ…" : "Yêu cầu đã chọn chưa có BR"}
        options={[...options, ...missing]}
        value={value}
        onChange={onChange}
      />
      {error && (
        <p role="status" className="text-sm text-danger">
          {error}
        </p>
      )}
      {!error && !loading && requirementVersionIds.length > 0 && items.length === 0 && (
        <p className="text-sm text-ink-muted">Không có BR trong các yêu cầu đã chọn.</p>
      )}
    </div>
  );
}
