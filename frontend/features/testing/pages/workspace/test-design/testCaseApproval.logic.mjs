export function requiresAiComparison(draft) {
  return draft?.origin === "ai_generated" || Boolean(draft?.ai_proposal_snapshot);
}

export function isAiComparisonCurrent(draft, comparedRevisions = {}) {
  return !requiresAiComparison(draft) || comparedRevisions[draft?._id] === draft?.revision;
}

export function isGroupApprovalComparisonCurrent(draft, comparison, comparedRevisions = {}) {
  if (!draft?._id || comparison?.draft?._id !== draft._id) return false;
  if (comparison.draft.revision !== draft.revision) return false;
  if (!comparison.comparison_token || comparison.stale_reasons?.length) return false;
  return !requiresAiComparison(draft) || comparedRevisions[draft._id] === comparison.draft.revision;
}

export function unreviewedAiDrafts(drafts = [], comparedRevisions = {}) {
  return drafts.filter(
    (draft) => requiresAiComparison(draft) && !isAiComparisonCurrent(draft, comparedRevisions),
  );
}

export function recordAiComparison(comparedRevisions, draft, isCurrent) {
  const next = { ...comparedRevisions };
  if (!isCurrent) delete next[draft._id];
  else next[draft._id] = draft.revision;
  return next;
}
