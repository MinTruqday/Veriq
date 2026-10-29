import Link from "next/link";
import Image from "next/image";

export default function AuthFrame({ title, description, children, footer, width = "sm" }) {
  return (
    <main className="min-h-[100dvh] bg-[#eef3ef] px-4 py-5 sm:px-6 md:px-10 md:py-8">
      <div className="mx-auto flex min-w-0 w-full max-w-[1180px] items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-3 text-[19px] font-semibold tracking-[-0.035em] text-ink"
        >
          <Image
            src="/brand/veriq-logo.png"
            alt="Veriq"
            width={36}
            height={36}
            className="h-9 w-9 rounded-xl object-cover"
            priority
            unoptimized
          />
          <span>Veriq</span>
        </Link>
        <Link
          href="/"
          className="rounded-control px-3 py-2 text-[14px] font-semibold text-ink-muted hover:bg-surface-quiet hover:text-ink"
        >
          Về trang chủ
        </Link>
      </div>
      <div className="mx-auto flex min-h-[calc(100dvh-104px)] min-w-0 w-full max-w-[1180px] items-center justify-center py-6 sm:py-8">
        <section
          className={`min-w-0 w-full max-w-full ${width === "md" ? "sm:max-w-[520px]" : "sm:max-w-[500px]"} rounded-3xl bg-surface p-6 shadow-[0_24px_70px_rgba(48,47,42,0.12)] sm:p-9`}
        >
          <header className="mb-6">
            <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.035em] text-ink">
              {title}
            </h1>
            {description && (
              <p className="mt-2 break-words text-[14px] leading-relaxed text-ink-muted">
                {description}
              </p>
            )}
          </header>
          {children}
          {footer && (
            <div className="mt-7 border-t border-border pt-5 text-[14px] text-ink-muted">
              {footer}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
