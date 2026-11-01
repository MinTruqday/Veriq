export default function nextConfig() {
  const apiUpstream =
    process.env.NODE_ENV === "development"
      ? process.env.NEXT_PUBLIC_API_URL
      : process.env.INTERNAL_API_URL;
  if (!apiUpstream) throw new Error("API upstream configuration is required");

  return {
    output: "standalone",
    distDir: ".next",
    async rewrites() {
      return [{ source: "/api/:path*", destination: `${apiUpstream}/:path*` }];
    },
  };
}
