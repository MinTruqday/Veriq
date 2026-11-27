import Image from "next/image";
import Link from "next/link";

export default function SystemStatusPage({
  code,
  eyebrow,
  title,
  description,
  primaryHref,
  primaryLabel,
  onRetry,
  secondaryHref,
  secondaryLabel,
}) {
  return (
    <main className="min-h-[100dvh] bg-canvas px-5 py-6 text-ink sm:px-8 sm:py-8">
      <div className="mx-auto flex min-h-[calc(100dvh-3rem)] w-full max-w-5xl flex-col sm:min-h-[calc(100dvh-4rem)]">
        <header className="flex items-center justify-between border-b border-border pb-4">
          <Link className="flex items-center gap-2.5 font-semibold" href="/">
            <Image
              src="/brand/veriq-logo.png"
              alt=""
              width={32}
              height={32}
              className="size-8 rounded-control object-cover"
              priority
              unoptimized
            />
            <span>Veriq</span>
          </Link>
          <span className="text-xs text-ink-muted">Trạng thái hệ thống</span>
        </header>

        <section className="grid flex-1 content-center gap-5 py-12 md:grid-cols-[minmax(10rem,0.55fr)_minmax(0,1.45fr)] md:gap-10">
          <p
            aria-hidden="true"
            className="font-mono text-5xl font-semibold tracking-tight text-ink-faint sm:text-6xl"
          >
            {code}
          </p>
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-brand">{eyebrow}</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
            <p className="mt-3 max-w-[60ch] text-sm leading-6 text-ink-muted">{description}</p>
            <div className="mt-6 flex flex-wrap gap-2">
              {onRetry && (
                <button className="apple-button" type="button" onClick={onRetry}>
                  {primaryLabel}
                </button>
              )}
              {!onRetry && primaryHref && (
                <Link className="apple-button" href={primaryHref}>
                  {primaryLabel}
                </Link>
              )}
              {secondaryHref && (
                <Link className="secondary-button" href={secondaryHref}>
                  {secondaryLabel}
                </Link>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
