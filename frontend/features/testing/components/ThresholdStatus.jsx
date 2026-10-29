const THRESHOLD_LABELS = {
  CRITICAL: "Vượt ngưỡng nghiêm trọng",
  NORMAL: "Trong ngưỡng",
  TARGET_MET: "Đạt mục tiêu",
  WARNING: "Cần theo dõi",
};

const LOWER_IS_BETTER = new Set([
  "BLOCKED_RATE",
  "DEFECT_REOPEN_RATE",
  "CRITICAL_DEFECT_AGING",
  "MEAN_TIME_TO_RETEST",
  "STALE_TEST_RATIO",
  "REQUIREMENT_VOLATILITY",
  "ESCAPED_DEFECT_RATE",
]);

export default function ThresholdStatus({ metricKey, value, target, warning, critical }) {
  let status = "NORMAL";
  if (LOWER_IS_BETTER.has(metricKey)) {
    if (critical !== null && critical !== undefined && value >= critical) status = "CRITICAL";
    else if (warning !== null && warning !== undefined && value >= warning) status = "WARNING";
    else if (target !== null && target !== undefined && value <= target) status = "TARGET_MET";
  } else {
    if (critical !== null && critical !== undefined && value <= critical) status = "CRITICAL";
    else if (warning !== null && warning !== undefined && value <= warning) status = "WARNING";
    else if (target !== null && target !== undefined && value >= target) status = "TARGET_MET";
  }
  return (
    <span
      className={`inline-flex max-w-full rounded-full px-2.5 py-1 text-center text-[11px] font-semibold leading-4 ${status === "CRITICAL" ? "bg-danger-soft text-danger" : status === "WARNING" ? "bg-amber-100 text-amber-900" : "bg-brand-soft text-brand"}`}
    >
      {THRESHOLD_LABELS[status]}
    </span>
  );
}
