import assert from "node:assert/strict";
import test from "node:test";
import { runReleaseQualityAction } from "./releaseQualityActions.mjs";

test("release quality actions return API failures for visible error handling", async () => {
  const failure = new Error("REVISION_CONFLICT");
  const result = await runReleaseQualityAction(async () => {
    throw failure;
  });

  assert.deepEqual(result, { ok: false, error: failure });
});

test("release quality actions preserve successful API values", async () => {
  const response = { _id: "QEV-1", revision: 2 };
  const result = await runReleaseQualityAction(async () => response);

  assert.deepEqual(result, { ok: true, value: response });
});
