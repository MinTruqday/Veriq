import assert from "node:assert/strict";
import test from "node:test";
import { clearImportMappings } from "./junitImport.logic.mjs";

test("xóa lựa chọn JUnit của receipt sau khi chỉ số hàng chưa liên kết có thể dịch chuyển", () => {
  const mappings = {
    "receipt-1:0": "version-a",
    "receipt-1:1": "version-b",
    "receipt-2:0": "version-c",
  };

  assert.deepEqual(clearImportMappings(mappings, "receipt-1"), {
    "receipt-2:0": "version-c",
  });
});
