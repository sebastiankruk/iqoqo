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
import * as React from "react";
import { cn } from "@/lib/utils";

/** Badge variant type */
type BadgeVariant = "default" | "secondary" | "outline" | "destructive";

/** Props for Badge component */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:
    "bg-primary text-primary-foreground",
  secondary:
    "bg-secondary text-secondary-foreground",
  outline:
    "border border-input bg-background text-foreground",
  destructive:
    "bg-destructive text-destructive-foreground",
};

/**
 * Badge component.
 *
 * @param props - The component props
 * @param props.className - Additional CSS classes to apply.
 * @param props.variant - The visual style variant of the badge.
 * @returns {JSX.Element} The component
 */
export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
