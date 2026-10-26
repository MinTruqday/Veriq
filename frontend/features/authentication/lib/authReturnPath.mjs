export function isSafeAuthReturnPath(requested) {
  if (
    typeof requested !== "string" ||
    !requested.startsWith("/") ||
    requested.startsWith("//") ||
    requested.includes("\\")
  ) {
    return false;
  }

  try {
    const target = new URL(requested, "https://veriq.invalid");
    return (
      target.origin === "https://veriq.invalid" &&
      target.pathname !== "/dang-nhap" &&
      !target.pathname.startsWith("/dang-nhap/")
    );
  } catch {
    return false;
  }
}

export function authReturnPath(requested) {
  return isSafeAuthReturnPath(requested) ? requested : "/du-an";
}
