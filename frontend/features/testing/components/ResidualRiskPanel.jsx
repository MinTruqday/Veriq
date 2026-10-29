"use client";

import { valueLabel } from "../lib/testing";

const severityValues = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function ResidualRiskPanel({
  items = [],
  members = [],
  editable = false,
  allowAdd = true,
  allowRemove = true,
  onChange,
  onDecide,
}) {
  const update = (index, field, value) => {
    const next = items.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: value } : item,
    );
    onChange?.(next);
  };
  const remove = (index) => onChange?.(items.filter((_, itemIndex) => itemIndex !== index));
  const add = () =>
    onChange?.([
      ...items,
      {
        risk_id: `RISK-${crypto.randomUUID()}`,
        title: "",
        description: "",
        severity: "MEDIUM",
        owner_id: members[0]?.user_id || "",
        acceptance: "PENDING",
        acceptance_reason: "",
        accepted_by: null,
      },
    ]);
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-ink">Rủi ro còn lại</h3>
        {editable && allowAdd && (
          <button className="secondary-button" type="button" onClick={add}>
            Thêm rủi ro
          </button>
        )}
      </div>
      {!items.length && <p className="text-sm text-ink-muted">Không có rủi ro còn lại</p>}
      {items.map((item, index) => (
        <article
          className="space-y-3 rounded-xl border border-border bg-surface-raised p-4"
          key={item.risk_id || index}
        >
          {editable ? (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="field-label">
                  Tên rủi ro
                  <input
                    className="apple-input mt-2"
                    required
                    value={item.title || ""}
                    onChange={(event) => update(index, "title", event.target.value)}
                  />
                </label>
                <label className="field-label">
                  Mức độ
                  <select
                    className="apple-input mt-2"
                    value={item.severity || "MEDIUM"}
                    onChange={(event) => update(index, "severity", event.target.value)}
                  >
                    {severityValues.map((value) => (
                      <option key={value} value={value}>
                        {valueLabel(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field-label">
                  Người phụ trách
                  <select
                    className="apple-input mt-2"
                    required
                    value={item.owner_id || ""}
                    onChange={(event) => update(index, "owner_id", event.target.value)}
                  >
                    <option value="">Chọn người phụ trách</option>
                    {members.map((member) => (
                      <option key={member.user_id} value={member.user_id}>
                        {member.user_label || member.user?.email || "Thành viên"}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="text-sm">
                  <span className="field-label">Xử lý</span>
                  <br />
                  {valueLabel(item.acceptance || "PENDING")}
                </p>
              </div>
              <label className="field-label block">
                Mô tả
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={item.description || ""}
                  onChange={(event) => update(index, "description", event.target.value)}
                />
              </label>
              {allowRemove && (
                <button className="danger-button" type="button" onClick={() => remove(index)}>
                  Xóa rủi ro
                </button>
              )}
            </>
          ) : (
            <div className="grid gap-2 text-sm md:grid-cols-2">
              <p>
                <span className="field-label">Rủi ro</span>
                <br />
                {item.title}
              </p>
              <p>
                <span className="field-label">Mức độ</span>
                <br />
                {valueLabel(item.severity)}
              </p>
              <p>
                <span className="field-label">Người phụ trách</span>
                <br />
                {members.find((member) => member.user_id === item.owner_id)?.user_label ||
                  members.find((member) => member.user_id === item.owner_id)?.user?.email ||
                  (item.owner_id ? "Người phụ trách không còn trong danh sách" : "Chưa phân công")}
              </p>
              <p>
                <span className="field-label">Xử lý</span>
                <br />
                {valueLabel(item.acceptance)}
              </p>
              {item.description && <p className="md:col-span-2">{item.description}</p>}
              {item.acceptance_reason && (
                <p className="md:col-span-2">
                  <span className="field-label">Lý do</span>
                  <br />
                  {item.acceptance_reason}
                </p>
              )}
              {item.acceptance === "PENDING" && onDecide && (
                <button
                  className="secondary-button justify-self-start md:col-span-2"
                  type="button"
                  onClick={() => onDecide(item)}
                >
                  Ghi nhận xử lý rủi ro
                </button>
              )}
            </div>
          )}
        </article>
      ))}
    </section>
  );
}
