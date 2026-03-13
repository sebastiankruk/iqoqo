"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

export interface AvatarProps {
  src?: string | null;
  alt?: string;
  size?: number;
  className?: string;
  fallback?: string;
}

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
