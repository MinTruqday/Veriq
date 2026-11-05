export function normalizeSummaryLocale(locale) {
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

export function summaryLanguageOptions(locale) {
  const preferred = normalizeSummaryLocale(locale);
  const options = [];
  if (preferred) {
    let label = preferred;
    try {
      label = new Intl.DisplayNames([preferred], { type: "language" }).of(preferred) || preferred;
    } catch {}
    options.push({ value: preferred, label });
  } else {
    options.push({ value: "auto", label: "Tự nhận diện theo tài liệu" });
  }

  if (!preferred?.toLowerCase().startsWith("vi")) {
    options.push({ value: "vi", label: "Tiếng Việt" });
  }
  if (!preferred?.toLowerCase().startsWith("en")) {
    options.push({ value: "en", label: "English" });
  }
  return options;
}
