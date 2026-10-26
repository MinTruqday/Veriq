import assert from "node:assert/strict";
import test from "node:test";
import {
  chooseFields,
  chooseStep,
  comparedStepIds,
  chooseStepSource,
  fieldDifference,
  moveStep,
  removeStep,
} from "./testCaseMerge.logic.mjs";

test("chọn toàn bộ nguồn cũng xóa trường bị nguồn đó lược bỏ", () => {
  const result = { title: "Ca cũ", test_kind: "security", custom_values: { old: true } };
  const proposal = { title: "Ca AI", custom_values: { new: true } };
  const merged = chooseFields(result, proposal, ["title", "test_kind", "custom_values"]);
  assert.deepEqual(merged, { title: "Ca AI", custom_values: { new: true } });
  assert.deepEqual(result, { title: "Ca cũ", test_kind: "security", custom_values: { old: true } });
});

test("ghép bước theo ID, không theo vị trí", () => {
  const result = {
    steps: [
      { id: "b", order: 1, expected: "B" },
      { id: "a", order: 2, expected: "A" },
    ],
  };
  const merged = chooseStep(result, { id: "a", order: 1, expected: "AI" });
  assert.equal(merged.steps[0].id, "b");
  assert.equal(merged.steps[1].expected, "AI");
  assert.equal(result.steps[1].expected, "A");
});

test("sắp xếp và bỏ bước giữ ID, cập nhật thứ tự liên tục", () => {
  const result = {
    steps: [
      { id: "a", order: 1 },
      { id: "b", order: 2 },
      { id: "c", order: 3 },
    ],
  };
  assert.deepEqual(
    moveStep(result, "c", -1).steps.map((step) => step.id),
    ["a", "c", "b"],
  );
  assert.deepEqual(removeStep(result, "b").steps, [
    { id: "a", order: 1 },
    { id: "c", order: 2 },
  ]);
  assert.equal(moveStep(result, "a", -1), result);
});

test("bước chỉ có trong bản gốc vẫn được hiển thị để QA chọn lại", () => {
  assert.deepEqual(
    comparedStepIds(
      { steps: [{ id: "old" }] },
      { steps: [{ id: "new" }] },
      { steps: [{ id: "new" }] },
    ),
    ["new", "old"],
  );
  assert.equal(fieldDifference(undefined, "mới"), "AI bổ sung");
  assert.equal(fieldDifference("cũ", undefined), "AI lược bỏ");
});

test("chọn nguồn không có bước sẽ bỏ đúng bước đó khỏi bản ghép", () => {
  const result = {
    steps: [
      { id: "keep", order: 1, action: "giữ" },
      { id: "remove", order: 2, action: "bỏ" },
    ],
  };
  const merged = chooseStepSource(result, "remove", undefined);
  assert.deepEqual(merged.steps, [{ id: "keep", order: 1, action: "giữ" }]);
  assert.equal(result.steps.length, 2);
});
