export function clearImportMappings(mappings, importId) {
  const prefix = `${importId}:`;
  return Object.fromEntries(Object.entries(mappings).filter(([key]) => !key.startsWith(prefix)));
}
