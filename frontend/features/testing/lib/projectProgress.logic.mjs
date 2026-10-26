export function taskProgressPresentation(summary) {
  if (!summary || typeof summary !== "object") {
    return {
      label: "Chưa tải được số liệu công việc",
      completionPercent: null,
      completed: null,
      total: null,
      blocked: null,
    };
  }

  const completed = Number.isFinite(summary.completed) ? summary.completed : null;
  const total = Number.isFinite(summary.total) ? summary.total : null;
  const blocked = Number.isFinite(summary.blocked) ? summary.blocked : null;
  if (Number.isFinite(summary.completion_percent)) {
    return { label: "", completionPercent: summary.completion_percent, completed, total, blocked };
  }

  if (summary.total === 0) {
    return { label: "Chưa có công việc", completionPercent: null, completed: 0, total: 0, blocked };
  }

  if (summary.applicable_total === 0 && summary.cancelled > 0) {
    return {
      label: "Tất cả công việc đã hủy",
      completionPercent: null,
      completed,
      total,
      blocked,
    };
  }

  return {
    label: "Chưa tính được tiến độ công việc",
    completionPercent: null,
    completed,
    total,
    blocked,
  };
}
