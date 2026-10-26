export function minimumProjectEndDate(startDate) {
  if (!startDate) return undefined;
  const date = new Date(`${startDate}T00:00:00.000Z`);
  if (Number.isNaN(date.getTime())) return undefined;
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
}

export function invalidProjectDateRange(startDate, endDate) {
  return Boolean(startDate && endDate && endDate <= startDate);
}

export function invalidTimelineRange(startDate, endDate, allowSameDay = false) {
  if (!(startDate instanceof Date) || !(endDate instanceof Date)) return false;
  const startTime = startDate.getTime();
  const endTime = endDate.getTime();
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) return false;
  return allowSameDay ? endTime < startTime : endTime <= startTime;
}

export function formatProjectDate(value) {
  if (!value) return "Chưa đặt";
  const datePart = String(value).slice(0, 10);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(datePart);
  if (!match) return "Ngày không hợp lệ";
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (
    date.getUTCFullYear() !== Number(match[1]) ||
    date.getUTCMonth() + 1 !== Number(match[2]) ||
    date.getUTCDate() !== Number(match[3])
  ) {
    return "Ngày không hợp lệ";
  }
  return date.toLocaleDateString("vi-VN", {
    timeZone: "UTC",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function projectPlannedDurationDays(startValue, endValue) {
  if (!startValue || !endValue || invalidProjectDateRange(startValue, endValue)) return null;
  const start = new Date(`${String(startValue).slice(0, 10)}T00:00:00.000Z`);
  const end = new Date(`${String(endValue).slice(0, 10)}T00:00:00.000Z`);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) return null;
  if (
    formatProjectDate(startValue) === "Ngày không hợp lệ" ||
    formatProjectDate(endValue) === "Ngày không hợp lệ"
  ) {
    return null;
  }
  return Math.floor((end.getTime() - start.getTime()) / 86400000) + 1;
}
