export default function nextConfig() {
  const apiUpstream =
    process.env.NODE_ENV === "development"
      ? process.env.NEXT_PUBLIC_API_URL
      : process.env.INTERNAL_API_URL;
  if (!apiUpstream) throw new Error("API upstream configuration is required");
  const configuredProxyTimeout = Number.parseInt(process.env.NEXT_PROXY_TIMEOUT_MS || "", 10);
  const proxyTimeout =
    Number.isSafeInteger(configuredProxyTimeout) && configuredProxyTimeout > 0
      ? configuredProxyTimeout
      : 180_000;

  return {
    output: "standalone",
    experimental: { proxyTimeout },
    distDir: ".next",
    async rewrites() {
      return [{ source: "/api/:path*", destination: `${apiUpstream}/:path*` }];
    },
  };
}
