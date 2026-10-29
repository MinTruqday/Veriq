export function taskProgressPresentation(summary) {
  if (!summary || typeof summary !== "object") {
    return {
      label: "Chưa tải được số liệu công việc",
      completionPercent: null,
      completed: null,
      total: null,
      applicableTotal: null,
      blocked: null,
    };
  }

  const completed = Number.isFinite(summary.completed) ? summary.completed : null;
  const total = Number.isFinite(summary.total) ? summary.total : null;
  const applicableTotal = Number.isFinite(summary.applicable_total)
    ? summary.applicable_total
    : total;
  const blocked = Number.isFinite(summary.blocked) ? summary.blocked : null;
  if (Number.isFinite(summary.completion_percent)) {
    return {
      label: "",
      completionPercent: summary.completion_percent,
      completed,
      total,
      applicableTotal,
      blocked,
    };
  }

  if (applicableTotal === 0) {
    return {
      label: "Chưa có công việc",
      completionPercent: null,
      completed,
      total,
      applicableTotal,
      blocked,
    };
  }

  return {
    label: "Chưa tính được tiến độ công việc",
    completionPercent: null,
    completed,
    total,
    applicableTotal,
    blocked,
  };
}
