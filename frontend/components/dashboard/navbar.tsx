"use client";

import Link from "next/link";
import { Search, Bell, ScanLine, Library } from "lucide-react";

/** Sticky top navigation bar – "Modern Athenaeum" style. */
export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-primary text-primary-foreground">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-6">
        {/* Brand */}
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="text-accent-foreground"
            >
              <path
                d="M2 3h4v10H2V3zm8 0h4v10h-4V3z"
                fill="currentColor"
                opacity="0.9"
              />
              <path d="M6 5h4v6H6V5z" fill="currentColor" opacity="0.5" />
            </svg>
          </div>
          <span className="font-serif text-xl font-bold tracking-tight">
            iqoqo
          </span>
        </Link>

        {/* Search */}
        <div className="relative mx-auto w-full max-w-md">
          <div className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center">
            <Search className="h-4 w-4 text-primary-foreground/50" />
          </div>
          <input
            type="text"
            placeholder="Search your collection..."
            className="h-9 w-full rounded-full border border-primary-foreground/15 bg-primary-foreground/10 pl-10 pr-4 text-sm text-primary-foreground placeholder-primary-foreground/40 outline-none transition-colors focus:border-accent focus:bg-primary-foreground/15"
          />
        </div>

        {/* Right section */}
        <div className="flex shrink-0 items-center gap-4">
          <Link
            href="/collection"
            className="hidden items-center gap-1.5 rounded-full border border-primary-foreground/20 px-3.5 py-1.5 text-xs font-medium text-primary-foreground/80 transition-colors hover:border-primary-foreground/40 hover:text-primary-foreground sm:flex"
          >
            <Library className="h-3.5 w-3.5" />
            Collection
          </Link>
          <Link
            href="/scan"
            className="flex h-9 items-center gap-1.5 rounded-full bg-accent px-3.5 text-xs font-semibold text-accent-foreground transition-opacity hover:opacity-90"
          >
            <ScanLine className="h-4 w-4" />
            <span className="hidden sm:inline">Scan</span>
          </Link>
          <button
            className="relative rounded-full p-2 transition-colors hover:bg-primary-foreground/10"
            aria-label="Notifications"
          >
            <Bell className="h-4.5 w-4.5" />
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent" />
          </button>
          <button
            className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground transition-opacity hover:opacity-90"
            aria-label="User profile"
          >
            iq
          </button>
        </div>
      </div>
    </nav>
  );
}
