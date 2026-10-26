import assert from "node:assert/strict";
import test from "node:test";
import { toggleNotificationSelection } from "./notificationSelection.mjs";

test("notification rule selection adds and removes one channel without duplicates", () => {
  assert.deepEqual(toggleNotificationSelection(["in_app"], "email", true), ["in_app", "email"]);
  assert.deepEqual(toggleNotificationSelection(["in_app", "email"], "email", false), ["in_app"]);
  assert.deepEqual(toggleNotificationSelection(["in_app", "email"], "email", true), [
    "in_app",
    "email",
  ]);
});
