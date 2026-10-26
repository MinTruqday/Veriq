export function toggleNotificationSelection(current, value, checked) {
  const selected = new Set(current || []);
  if (checked) selected.add(value);
  else selected.delete(value);
  return [...selected];
}
