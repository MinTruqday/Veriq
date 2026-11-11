import { isSupportedTimeZone } from "./timeZone.mjs";
import { safeLocale } from "./locale.mjs";

function optionsWithTimeZone(options, timeZone) {
  return {
    ...options,
    ...(isSupportedTimeZone(timeZone) ? { timeZone } : {}),
  };
}

export function formatDateTime(value, { locale, timeZone, options = {} } = {}) {
  if (!value) return "Chưa có";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có";
  const usesStyle = options.dateStyle || options.timeStyle;
  return new Intl.DateTimeFormat(
    safeLocale(locale),
    optionsWithTimeZone(
      {
        ...(!usesStyle && {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
        ...options,
      },
      timeZone,
    ),
  ).format(date);
}

export function formatDateOnly(value, { locale, timeZone, options = {} } = {}) {
  if (!value) return "Chưa có";
  const dateOnly = typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
  const date = new Date(dateOnly ? `${value}T00:00:00.000Z` : value);
  if (Number.isNaN(date.getTime())) return "Chưa có";
  return new Intl.DateTimeFormat(
    safeLocale(locale),
    optionsWithTimeZone(
      {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        ...options,
      },
      dateOnly ? "UTC" : timeZone,
    ),
  ).format(date);
}
