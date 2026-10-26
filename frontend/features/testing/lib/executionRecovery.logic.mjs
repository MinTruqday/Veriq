export function shouldReloadAfterAmbiguousMutation(error) {
  const status = Number(error?.status);
  return !Number.isFinite(status) || status === 409 || status >= 500;
}

export function operationForRetry(current, signature, nextIdempotencyKey) {
  return current?.signature === signature
    ? current
    : { signature, idempotencyKey: nextIdempotencyKey };
}
