function normalizeSummaryLocale(locale) {
  if (typeof locale !== "string" || !locale.trim()) return "";
  try {
    return Intl.getCanonicalLocales(locale.trim())[0] || "";
  } catch {
    return "";
  }
}

export function preferredSummaryLocale(...locales) {
  for (const locale of locales) {
    const normalized = normalizeSummaryLocale(locale);
    if (normalized) return normalized;
  }
  return "auto";
}
