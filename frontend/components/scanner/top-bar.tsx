// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import Link from "next/link";
import { ArrowLeft, Zap } from "lucide-react";

/**
 * Scanner page top overlay bar.
 *
 * @returns {JSX.Element} The component
 */
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
          <span className="font-serif text-base font-bold tracking-tight text-white">Scan ISBN or Cover</span>
          <span className="mt-0.5 text-[11px] text-white/50">Position item within the frame</span>
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
