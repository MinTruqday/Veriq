"use client";

import { valueLabel } from "../lib/testing";
import { StructuredValueView } from "./StructuredValueEditor";

export default function LessonsLearnedPanel({
  lessons = [],
  actions = [],
  members = [],
  editable = false,
  editableLessons = editable,
  editableActions = editable,
  onLessonsChange,
  onActionsChange,
}) {
  const addLesson = () =>
    onLessonsChange?.([
      ...lessons,
      {
        observation: "",
        category: "WORKED",
        impact: "",
        recommendation: "",
        evidence_refs: [],
        owner_id: null,
        convert_to_improvement: false,
      },
    ]);
  const updateLesson = (index, field, value) =>
    onLessonsChange?.(
      lessons.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)),
    );
  const addAction = () =>
    onActionsChange?.([
      ...actions,
      {
        action_id: `ACTION-${crypto.randomUUID()}`,
        title: "",
        owner_id: members[0]?.user_id || "",
        due_at: null,
        status: "OPEN",
        evidence_refs: [],
      },
    ]);
  const updateAction = (index, field, value) =>
    onActionsChange?.(
      actions.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)),
    );
  const memberName = (userId) => {
    if (!userId) return "Chưa phân công";
    const member = members.find((item) => item.user_id === userId);
    return member?.user_label || member?.user?.email || "Thành viên không còn trong danh sách";
  };
  return (
    <section className="space-y-5">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold text-ink">Bài học kinh nghiệm</h3>
          {editableLessons && (
            <button className="secondary-button" type="button" onClick={addLesson}>
              Thêm bài học
            </button>
          )}
        </div>
        {!lessons.length && (
          <p className="text-sm text-ink-muted">Chưa ghi nhận bài học kinh nghiệm</p>
        )}
        {lessons.map((item, index) =>
          editableLessons ? (
            <div
              className="grid min-w-0 gap-3 rounded-xl border border-border p-3 md:grid-cols-[180px_minmax(0,1fr)_auto]"
              key={`lesson-${index}`}
            >
              <select
                aria-label={`Loại bài học ${index + 1}`}
                className="apple-input"
                value={item.category || "WORKED"}
                onChange={(event) => updateLesson(index, "category", event.target.value)}
              >
                {["WORKED", "FAILED", "BLOCKER", "IMPROVEMENT", "OTHER"].map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <textarea
                aria-label={`Bài học ${index + 1}`}
                className="apple-input min-h-16 w-full min-w-0"
                required
                value={item.observation || item.text || ""}
                onChange={(event) => updateLesson(index, "observation", event.target.value)}
              />
              <button
                className="danger-button"
                type="button"
                onClick={() =>
                  onLessonsChange?.(lessons.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                Xóa
              </button>
            </div>
          ) : (
            <article
              className="rounded-xl border border-border p-3 text-sm"
              key={`lesson-${index}`}
            >
              <p className="field-label">{valueLabel(item.category || "LESSON")}</p>
              <p className="mt-1">
                {item.observation || item.text || item.lesson || (
                  <StructuredValueView value={item} />
                )}
              </p>
              {item.impact && (
                <p className="mt-2">
                  <span className="field-label">Tác động</span>
                  <br />
                  {item.impact}
                </p>
              )}
              {item.recommendation && (
                <p className="mt-2">
                  <span className="field-label">Khuyến nghị</span>
                  <br />
                  {item.recommendation}
                </p>
              )}
            </article>
          ),
        )}
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold text-ink">Hành động cải tiến</h3>
          {editableActions && (
            <button className="secondary-button" type="button" onClick={addAction}>
              Thêm hành động
            </button>
          )}
        </div>
        {!actions.length && <p className="text-sm text-ink-muted">Chưa có hành động cải tiến</p>}
        {actions.map((item, index) =>
          editableActions ? (
            <div
              className="grid gap-3 rounded-xl border border-border p-3 md:grid-cols-2"
              key={item.action_id || index}
            >
              <label className="field-label">
                Hành động
                <input
                  className="apple-input mt-2 w-full min-w-0"
                  required
                  value={item.title || ""}
                  onChange={(event) => updateAction(index, "title", event.target.value)}
                />
              </label>
              <label className="field-label">
                Người phụ trách
                <select
                  className="apple-input mt-2"
                  required
                  value={item.owner_id || ""}
                  onChange={(event) => updateAction(index, "owner_id", event.target.value)}
                >
                  <option value="">Chọn người phụ trách</option>
                  {members.map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {member.user_label || member.user?.email || "Thành viên"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Hạn hoàn tất
                <input
                  className="apple-input mt-2"
                  type="datetime-local"
                  value={item.due_at ? String(item.due_at).slice(0, 16) : ""}
                  onChange={(event) => updateAction(index, "due_at", event.target.value || null)}
                />
              </label>
              <label className="field-label">
                Trạng thái
                <select
                  className="apple-input mt-2"
                  value={item.status || "OPEN"}
                  onChange={(event) => updateAction(index, "status", event.target.value)}
                >
                  {["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"].map((value) => (
                    <option key={value} value={value}>
                      {valueLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="danger-button md:col-span-2 md:justify-self-start"
                type="button"
                onClick={() =>
                  onActionsChange?.(actions.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                Xóa hành động
              </button>
            </div>
          ) : (
            <article
              className="grid gap-2 rounded-xl border border-border p-3 text-sm md:grid-cols-3"
              key={item.action_id || index}
            >
              <p>
                <span className="field-label">Hành động</span>
                <br />
                {item.title}
              </p>
              <p>
                <span className="field-label">Người phụ trách</span>
                <br />
                {memberName(item.owner_id)}
              </p>
              <p>
                <span className="field-label">Trạng thái</span>
                <br />
                {valueLabel(item.status)}
              </p>
            </article>
          ),
        )}
      </div>
    </section>
  );
}
