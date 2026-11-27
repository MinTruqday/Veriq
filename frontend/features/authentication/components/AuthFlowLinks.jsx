import Link from "next/link";

export default function AuthFlowLinks({ links }) {
  if (!links?.length) return null;

  return (
    <nav aria-label="Điều hướng xác thực" className="flex flex-wrap gap-x-4 gap-y-2">
      {links.map(({ href, label, tone = "brand" }) => (
        <Link
          className={`font-semibold ${tone === "ink" ? "text-ink hover:text-brand" : "text-brand hover:text-brand-hover"}`}
          href={href}
          key={`${href}:${label}`}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
