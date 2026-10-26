import assert from "node:assert/strict";
import test from "node:test";
import { authReturnPath, isSafeAuthReturnPath } from "./authReturnPath.mjs";

test("authentication redirects only to safe local destinations", () => {
  assert.equal(authReturnPath("/du-an/PRJ-1/yeu-cau"), "/du-an/PRJ-1/yeu-cau");
  assert.equal(authReturnPath("//attacker.example/path"), "/du-an");
  assert.equal(authReturnPath("/\\attacker.example/path"), "/du-an");
  assert.equal(authReturnPath("https://attacker.example/path"), "/du-an");
  assert.equal(authReturnPath("/dang-nhap?next=/admin"), "/du-an");
  assert.equal(authReturnPath("/dang-nhap/google/chuyen-huong"), "/du-an");
  assert.equal(authReturnPath(""), "/du-an");
  assert.equal(isSafeAuthReturnPath("/du-an"), true);
  assert.equal(isSafeAuthReturnPath("/dang-nhap?next=/admin"), false);
});
