const supportedTimeZones =
  typeof Intl.supportedValuesOf === "function"
    ? new Set(["UTC", ...Intl.supportedValuesOf("timeZone")])
    : null;

export function isSupportedTimeZone(value) {
  const timeZone = String(value || "");
  if (!timeZone || /^[+-]\d{1,2}(?::?\d{2})?$/.test(timeZone)) return false;
  try {
    new Intl.DateTimeFormat("en", { timeZone });
    return true;
  } catch {
    return false;
  }
}

export function timeZoneOptions(currentValue = "") {
  const values = new Set(supportedTimeZones || ["UTC"]);
  const current = String(currentValue || "");
  if (current) values.add(current);
  return [...values]
    .sort((left, right) => left.localeCompare(right))
    .map((value) => {
      const valid = isSupportedTimeZone(value);
      return {
        value,
        valid,
        label: valid ? value : `${value} · Không phải múi giờ hợp lệ`,
      };
    });
}
