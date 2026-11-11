export function isSupportedLocale(value) {
  if (typeof value !== "string" || !value.trim()) return false;
  try {
    new Intl.DateTimeFormat(value).format(new Date(0));
    return true;
  } catch {
    return false;
  }
}

export function safeLocale(value) {
  return isSupportedLocale(value) ? value : undefined;
}

export function formatNumber(value, locale, options = {}) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return "—";
  return new Intl.NumberFormat(safeLocale(locale), options).format(numericValue);
}
