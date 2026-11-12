export function b64urlToBuffer(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const encoded = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(encoded);
  const bytes = Uint8Array.from(raw, (character) => character.charCodeAt(0));
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}
export function bufferToB64url(value) {
  const bytes = new Uint8Array(value);
  let raw = "";
  bytes.forEach((byte) => {
    raw += String.fromCharCode(byte);
  });
  return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}
