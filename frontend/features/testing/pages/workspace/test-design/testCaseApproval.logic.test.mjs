import assert from "node:assert/strict";
import test from "node:test";
import {
  isAiComparisonCurrent,
  isGroupApprovalComparisonCurrent,
  recordAiComparison,
  requiresAiComparison,
  unreviewedAiDrafts,
} from "./testCaseApproval.logic.mjs";

test("chỉ ca có nguồn AI mới bắt buộc mở đối chiếu trước khi duyệt nhóm", () => {
  assert.equal(requiresAiComparison({ origin: "ai_generated" }), true);
  assert.equal(requiresAiComparison({ ai_proposal_snapshot: { title: "AI" } }), true);
  assert.equal(requiresAiComparison({ origin: "manual" }), false);
});

test("đối chiếu chỉ hợp lệ với đúng revision hiện tại", () => {
  const draft = { _id: "draft-1", revision: 4, origin: "ai_generated" };
  assert.equal(isAiComparisonCurrent(draft, { "draft-1": 4 }), true);
  assert.equal(isAiComparisonCurrent(draft, { "draft-1": 3 }), false);
  assert.equal(isAiComparisonCurrent(draft, {}), false);
});

test("không dùng bản đối chiếu mới hơn để duyệt revision AI người dùng chưa xem", () => {
  const draft = { _id: "draft-1", revision: 4, origin: "ai_generated" };
  const comparison = {
    draft: { _id: "draft-1", revision: 5 },
    comparison_token: "fresh-token",
    stale_reasons: [],
  };

  assert.equal(isGroupApprovalComparisonCurrent(draft, comparison, { "draft-1": 4 }), false);
  assert.equal(
    isGroupApprovalComparisonCurrent({ ...draft, revision: 5 }, comparison, { "draft-1": 5 }),
    true,
  );
});

test("duyệt nhóm từ chối kết quả so sánh thiếu token, đã cũ hoặc thuộc ca khác", () => {
  const draft = { _id: "draft-1", revision: 4, origin: "ai_generated" };
  const comparison = {
    draft: { _id: "draft-1", revision: 4 },
    comparison_token: "fresh-token",
    stale_reasons: [],
  };

  assert.equal(
    isGroupApprovalComparisonCurrent(
      draft,
      { ...comparison, comparison_token: "" },
      { "draft-1": 4 },
    ),
    false,
  );
  assert.equal(
    isGroupApprovalComparisonCurrent(
      draft,
      { ...comparison, stale_reasons: ["SOURCE_CHANGED"] },
      { "draft-1": 4 },
    ),
    false,
  );
  assert.equal(
    isGroupApprovalComparisonCurrent(
      draft,
      { ...comparison, draft: { ...comparison.draft, _id: "draft-2" } },
      { "draft-1": 4 },
    ),
    false,
  );
});

test("lọc đúng các ca AI chưa được đối chiếu hoặc đã đổi revision", () => {
  const drafts = [
    { _id: "ai-1", revision: 2, origin: "ai_generated" },
    { _id: "ai-2", revision: 5, origin: "ai_generated" },
    { _id: "manual-1", revision: 1, origin: "manual" },
  ];
  assert.deepEqual(unreviewedAiDrafts(drafts, { "ai-1": 2, "ai-2": 4 }), [drafts[1]]);
});

test("đối chiếu nguồn cũ xóa dấu đã xem, nguồn hiện hành lưu revision đã xem", () => {
  const draft = { _id: "ai-1", revision: 3, origin: "ai_generated" };
  assert.deepEqual(recordAiComparison({ "ai-1": 2 }, draft, false), {});
  assert.deepEqual(recordAiComparison({}, draft, true), { "ai-1": 3 });
});
