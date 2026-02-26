"use client";

import Link from "next/link";

/** Blurred-cover hero banner with breadcrumb navigation. */
export function HeroBanner({
  coverUrl,
  title,
}: {
  coverUrl?: string;
  title?: string;
}) {
  return (
    <div className="relative h-[200px] w-full overflow-hidden bg-primary">
      {coverUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={coverUrl}
          alt=""
          className="absolute inset-0 h-full w-full scale-110 object-cover opacity-40 blur-xl"
        />
      )}
      {/* Dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/60 via-primary/70 to-primary/90" />

      {/* Breadcrumb */}
      <div className="relative z-10 mx-auto flex h-full max-w-6xl flex-col justify-end px-6 pb-16">
        <nav
          className="flex items-center gap-2 text-xs text-primary-foreground/60"
          aria-label="Breadcrumb"
        >
          <Link
            href="/"
            className="transition-colors hover:text-primary-foreground"
          >
            Library
          </Link>
          <span>/</span>
          <Link
            href="/collection"
            className="transition-colors hover:text-primary-foreground"
          >
            Collection
          </Link>
          <span>/</span>
          <span className="text-primary-foreground/90">{title ?? "Item"}</span>
        </nav>
      </div>
    </div>
  );
}
