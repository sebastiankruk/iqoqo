import Link from "next/link";
import { ArrowLeft, Zap } from "lucide-react";

/** Scanner page top overlay bar. */
export function TopBar() {
  return (
    <div className="absolute inset-x-0 top-0 z-20">
      <div className="flex items-center justify-between bg-black/40 px-4 py-4 backdrop-blur-sm">
        <Link
          href="/"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
          aria-label="Go back to library"
        >
          <ArrowLeft className="h-5 w-5 text-white" />
        </Link>

        <div className="flex flex-col items-center">
          <span className="font-serif text-base font-bold tracking-tight text-white">
            Scan ISBN or Cover
          </span>
          <span className="mt-0.5 text-[11px] text-white/50">
            Position item within the frame
          </span>
        </div>

        <button
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
          aria-label="Toggle flash"
        >
          <Zap className="h-5 w-5 text-white" />
        </button>
      </div>
    </div>
  );
}
