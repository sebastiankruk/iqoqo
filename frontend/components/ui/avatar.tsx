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
"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

/** Props for Avatar component */
export interface AvatarProps {
  src?: string | null;
  alt?: string;
  size?: number;
  className?: string;
  fallback?: string;
}

/**
 * Avatar component.
 *
 * @param props - The component props
 * @returns {JSX.Element} The component
 */
export function Avatar({ src, alt, size = 40, className, fallback }: AvatarProps) {
  const initials = fallback;
  return (
    <div
      style={{ width: size, height: size }}
      className={cn("inline-flex items-center justify-center rounded-full overflow-hidden", className)}
      aria-hidden={src && !alt ? true : undefined}
      role={!src ? "img" : undefined}
      aria-label={!src ? (alt || initials || "avatar") : undefined}
    >
      {src ? (
        <Image src={src} alt={alt || "avatar"} width={size} height={size} className="object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-muted text-muted-foreground select-none font-medium">
          {initials ?? "?"}
        </div>
      )}
    </div>
  );
}
