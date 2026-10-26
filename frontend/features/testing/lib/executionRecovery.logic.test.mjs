import assert from "node:assert/strict";
import test from "node:test";
import {
  operationForRetry,
  shouldReloadAfterAmbiguousMutation,
} from "./executionRecovery.logic.mjs";

test("thực thi đồng bộ lại snapshot sau xung đột, lỗi máy chủ hoặc lỗi mạng không rõ kết quả", () => {
  assert.equal(shouldReloadAfterAmbiguousMutation({ status: 409 }), true);
  assert.equal(shouldReloadAfterAmbiguousMutation({ status: 503 }), true);
  assert.equal(shouldReloadAfterAmbiguousMutation(new TypeError("Network error")), true);
});

test("lỗi xác thực hoặc dữ liệu không tự tải lại snapshot thực thi", () => {
  assert.equal(shouldReloadAfterAmbiguousMutation({ status: 401 }), false);
  assert.equal(shouldReloadAfterAmbiguousMutation({ status: 403 }), false);
  assert.equal(shouldReloadAfterAmbiguousMutation({ status: 422 }), false);
});

test("thử lại cùng nội dung dùng lại mã idempotency, nội dung đổi tạo mã mới", () => {
  const first = operationForRetry(null, "same-payload", "operation-1");
  assert.equal(operationForRetry(first, "same-payload", "operation-2"), first);
  assert.deepEqual(operationForRetry(first, "changed-payload", "operation-3"), {
    signature: "changed-payload",
    idempotencyKey: "operation-3",
  });
});
