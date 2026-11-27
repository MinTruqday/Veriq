import Link from "next/link";
import Image from "next/image";

export default function AuthFrame({ title, description, children, footer, width = "sm" }) {
  return (
    <main className="min-h-[100dvh] bg-canvas px-4 py-4 text-ink sm:px-6 sm:py-6">
      <div className="mx-auto flex min-w-0 w-full max-w-[1180px] items-center justify-between border-b border-border pb-4">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2.5 rounded-control text-[17px] font-semibold tracking-[-0.025em] text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        >
          <Image
            src="/brand/veriq-logo.png"
            alt="Veriq"
            width={32}
            height={32}
            className="h-8 w-8 rounded-control object-cover"
            priority
            unoptimized
          />
          <span>Veriq</span>
        </Link>
        <Link
          href="/"
          className="rounded-control px-3 py-2 text-[13px] font-medium text-ink-muted transition hover:bg-surface-quiet hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        >
          Về trang chủ
        </Link>
      </div>
      <div className="mx-auto flex min-h-[calc(100dvh-88px)] min-w-0 w-full max-w-[1180px] items-center justify-center py-8 sm:py-10">
        <section
          className={`min-w-0 w-full max-w-full ${width === "md" ? "sm:max-w-[520px]" : "sm:max-w-[440px]"} rounded-panel border border-border bg-surface p-5 sm:p-8`}
        >
          <header className="mb-6 border-b border-border pb-5">
            <h1 className="text-[23px] font-semibold leading-tight tracking-[-0.025em] text-ink sm:text-[24px]">
              {title}
            </h1>
            {description && (
              <p className="mt-2 break-words text-[13px] leading-5 text-ink-muted">{description}</p>
            )}
          </header>
          {children}
          {footer && (
            <div className="mt-6 border-t border-border pt-4 text-[13px] leading-5 text-ink-muted">
              {footer}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
