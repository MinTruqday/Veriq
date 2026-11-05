export function reportDateInput(date = new Date(), timeZone) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function reportDateTime(value, timeZone) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) throw new Error("Ngày giờ không hợp lệ.");
  const [, year, month, day, hour, minute, second = "0"] = match;
  const expected = [year, month, day, hour, minute, second].map(Number);
  const wall = Date.UTC(expected[0], expected[1] - 1, ...expected.slice(2));
  const formatter = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  let instant = wall;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = Object.fromEntries(
      formatter.formatToParts(new Date(instant)).map(({ type, value: part }) => [type, part]),
    );
    const actual = [parts.year, parts.month, parts.day, parts.hour, parts.minute, parts.second].map(
      Number,
    );
    if (actual.every((part, index) => part === expected[index]))
      return new Date(instant).toISOString();
    instant += wall - Date.UTC(actual[0], actual[1] - 1, ...actual.slice(2));
  }
  throw new Error("Giờ đã chọn không tồn tại trong múi giờ dự án. Hãy chọn giờ khác.");
}
