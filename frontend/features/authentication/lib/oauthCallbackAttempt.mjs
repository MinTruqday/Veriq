export function getOAuthCallbackAttempt(attemptRef, key, operation) {
  if (attemptRef.current?.key === key) return attemptRef.current.promise;
  const promise = Promise.resolve().then(operation);
  attemptRef.current = { key, promise };
  return promise;
}
