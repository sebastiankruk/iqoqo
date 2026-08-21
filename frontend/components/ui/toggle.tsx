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

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const toggleVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-muted hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-[state=on]:bg-accent data-[state=on]:text-accent-foreground",
  {
    variants: {
      variant: {
        default: "bg-transparent",
        outline: "border border-input bg-transparent shadow-xs hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-9 px-3 min-w-9",
        sm: "h-8 px-2 min-w-8",
        lg: "h-10 px-3 min-w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ToggleProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof toggleVariants> {
  pressed?: boolean;
  onPressedChange?: (pressed: boolean) => void;
}

const Toggle = React.forwardRef<HTMLButtonElement, ToggleProps>(
  ({ className, variant, size, pressed, onPressedChange, onClick, ...props }, ref) => {
    const isControlled = pressed !== undefined;
    const [isPressed, setIsPressed] = React.useState(false);
    const state = isControlled ? pressed : isPressed;

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      onClick?.(e);
      if (!isControlled) {
        setIsPressed(!isPressed);
      }
      onPressedChange?.(!state);
    };

    return (
      <button
        ref={ref}
        type="button"
        aria-pressed={state}
        data-state={state ? "on" : "off"}
        className={cn(toggleVariants({ variant, size, className }))}
        onClick={handleClick}
        {...props}
      />
    );
  }
);

Toggle.displayName = "Toggle";

export { Toggle, toggleVariants };
