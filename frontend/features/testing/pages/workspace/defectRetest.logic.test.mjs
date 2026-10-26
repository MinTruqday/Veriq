import assert from "node:assert/strict";
import test from "node:test";
import { eligibleRetestResults } from "./defectRetest.logic.mjs";

const results = [
  { _id: "failure-1", test_case_version_id: "case-1" },
  { _id: "retest-1", test_case_version_id: "case-1" },
  { _id: "other-case", test_case_version_id: "case-2" },
];

test("retest không đề xuất lại kết quả lỗi ban đầu hoặc kết quả của ca khác", () => {
  assert.deepEqual(
    eligibleRetestResults(
      { linked_test_result_id: "failure-1", linked_test_case_version_id: "case-1" },
      results,
    ),
    [results[1]],
  );
});

test("lấy đúng phiên bản ca từ kết quả ban đầu khi lỗi chưa lưu liên kết phiên bản riêng", () => {
  assert.deepEqual(eligibleRetestResults({ linked_test_result_id: "failure-1" }, results), [
    results[1],
  ]);
});

test("không mở rộng lựa chọn khi kết quả ban đầu đã liên kết nhưng không đọc được", () => {
  assert.deepEqual(eligibleRetestResults({ linked_test_result_id: "missing" }, results), []);
});

test("giữ các kết quả trong dự án cho lỗi chưa liên kết với test case", () => {
  assert.deepEqual(eligibleRetestResults({}, results), results);
});
