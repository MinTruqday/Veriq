import assert from "node:assert/strict";
import test from "node:test";
import { getOAuthCallbackAttempt } from "./oauthCallbackAttempt.mjs";

test("repeated callback effects share one complete authentication attempt", async () => {
  const attemptRef = { current: null };
  let calls = 0;
  const operation = async () => {
    calls += 1;
    return { access_token: "access" };
  };

  const first = getOAuthCallbackAttempt(attemptRef, "code\u0000state", operation);
  const second = getOAuthCallbackAttempt(attemptRef, "code\u0000state", operation);

  assert.equal(first, second);
  assert.deepEqual(await second, { access_token: "access" });
  assert.equal(calls, 1);
});

test("a different callback state starts a separate authentication attempt", async () => {
  const attemptRef = { current: null };
  let calls = 0;

  await getOAuthCallbackAttempt(attemptRef, "code-a\u0000state-a", async () => ++calls);
  await getOAuthCallbackAttempt(attemptRef, "code-b\u0000state-b", async () => ++calls);

  assert.equal(calls, 2);
});
