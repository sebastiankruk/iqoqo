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

import Link from "next/link";
import type { ReactNode } from "react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** Props for the DiscoveryPivot component. */
interface DiscoveryPivotProps {
  /** The filter type to apply on the collection page. */
  type: "tags" | "genres" | "publishers" | "q";
  /** The value to filter by. */
  value: string;
  /** Optional display label, defaults to value if not provided. */
  label?: string;
  /** Whether to render as a Badge or a simple Link. */
  variant?: "badge" | "link";
  /** If variant is 'badge', the shadcn badge variant. */
  badgeVariant?: BadgeProps["variant"];
  /** Additional CSS classes. */
  className?: string;
  /** Optional children to override label/value display. */
  children?: ReactNode;
}

/**
 * A shared component for "pivotal" discovery links (tags, genres, authors, etc.)
 * that point back to the main collection view with a filter applied.
 *
 * @param props - Component props
 * @param props.type - The filter type to apply on the collection page.
 * @param props.value - The value to filter by.
 * @param props.label - Optional display label, defaults to value if not provided.
 * @param props.variant - Whether to render as a Badge or a simple Link.
 * @param props.badgeVariant - If variant is 'badge', the shadcn badge variant.
 * @param props.className - Additional CSS classes.
 * @param props.children - Optional children to override label/value display.
 * @returns {JSX.Element} The rendered component
 */
export function DiscoveryPivot({
  type,
  value,
  label,
  variant = "badge",
  badgeVariant = "secondary",
  className,
  children,
}: DiscoveryPivotProps) {
  const href = `/collection?${type}=${encodeURIComponent(value)}`;
  const content = children || label || value;

  if (variant === "link") {
    return (
      <Link
        href={href}
        className={cn("hover:text-primary hover:underline transition-colors cursor-pointer font-medium", className)}
      >
        {content}
      </Link>
    );
  }

  return (
    <Link href={href} className="transition-transform hover:scale-105 active:scale-95 inline-block">
      <Badge
        variant={badgeVariant}
        className={cn("hover:bg-muted hover:text-primary transition-colors cursor-pointer", className)}
      >
        {content}
      </Badge>
    </Link>
  );
}
