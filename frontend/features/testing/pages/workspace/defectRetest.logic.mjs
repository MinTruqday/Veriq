export function eligibleRetestResults(defect, results) {
  const linkedResult = defect?.linked_test_result_id
    ? results.find((result) => result._id === defect.linked_test_result_id)
    : null;
  if (defect?.linked_test_result_id && !linkedResult) return [];

  const linkedVersionId =
    defect?.linked_test_case_version_id || linkedResult?.test_case_version_id || null;
  const readyAfter = Date.parse(defect?.updated_at || "");
  if (!linkedVersionId || Number.isNaN(readyAfter)) return [];
  return results.filter(
    (result) =>
      result._id !== defect?.linked_test_result_id &&
      result.test_case_version_id === linkedVersionId &&
      ["PASS", "FAIL"].includes(result.status) &&
      Date.parse(result.completed_at || "") > readyAfter &&
      !(result.retested_defect_ids || []).includes(defect?._id),
  );
}
