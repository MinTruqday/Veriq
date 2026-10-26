export function eligibleRetestResults(defect, results) {
  const linkedResult = defect?.linked_test_result_id
    ? results.find((result) => result._id === defect.linked_test_result_id)
    : null;
  if (defect?.linked_test_result_id && !linkedResult) return [];

  const linkedVersionId =
    defect?.linked_test_case_version_id || linkedResult?.test_case_version_id || null;
  return results.filter(
    (result) =>
      result._id !== defect?.linked_test_result_id &&
      (!linkedVersionId || result.test_case_version_id === linkedVersionId),
  );
}
