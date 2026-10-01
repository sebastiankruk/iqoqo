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

import { cn } from "@/lib/utils";

/**
 * A neutral loading placeholder block.
 *
 * Prefer this to returning `null` for a component that occupies layout space.
 * A component that renders nothing while loading and then appears pushes
 * everything below it down, which the browser scores as Cumulative Layout
 * Shift — most visible on a landing page above the fold, where a stats strip
 * appearing after its fetch shifts the sections beneath it.
 *
 * Sizing is the caller's job: pass the same box the real content will occupy,
 * so the placeholder reserves exactly that space and the swap is invisible.
 *
 * @param props - Component properties.
 * @param props.className - Tailwind classes for the placeholder box.
 * @returns A pulsing, screen-reader-hidden placeholder block.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div aria-hidden="true" data-testid="skeleton" className={cn("animate-pulse rounded-md bg-muted", className)} />
  );
}
