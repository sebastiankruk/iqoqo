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

"use client";

import { useState } from "react";
import { Star } from "lucide-react";

interface StarRatingProps {
  rating: number;
  maxStars?: number;
  readOnly?: boolean;
  onChange?: (rating: number) => void;
  size?: "sm" | "md" | "lg";
}

/**
 * Polished, interactive StarRating component supporting click, hover micro-animations, and read-only views.
 *
 * @param props - Component props.
 * @param props.rating - The current star rating value.
 * @param props.maxStars - The maximum number of stars to display (default 5).
 * @param props.readOnly - Whether the rating is read-only or interactive (default false).
 * @param props.onChange - Optional callback triggered when a star is clicked.
 * @param props.size - Size of the stars: 'sm', 'md', or 'lg' (default 'md').
 * @returns The rendered star rating component.
 */
export function StarRating({ rating, maxStars = 5, readOnly = false, onChange, size = "md" }: StarRatingProps) {
  const [hoverRating, setHoverRating] = useState<number | null>(null);

  const starSizes = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-7 w-7",
  };

  const handleMouseEnter = (index: number) => {
    if (!readOnly) {
      setHoverRating(index);
    }
  };

  const handleMouseLeave = () => {
    if (!readOnly) {
      setHoverRating(null);
    }
  };

  const handleClick = (index: number) => {
    if (!readOnly && onChange) {
      onChange(index);
    }
  };

  return (
    <div className="flex items-center gap-1" onMouseLeave={handleMouseLeave}>
      {Array.from({ length: maxStars }).map((_, index) => {
        const starValue = index + 1;
        const isFilled = hoverRating !== null ? starValue <= hoverRating : starValue <= rating;

        return (
          <button
            key={index}
            type="button"
            disabled={readOnly}
            onClick={() => handleClick(starValue)}
            onMouseEnter={() => handleMouseEnter(starValue)}
            className={`transition-all duration-150 focus:outline-none ${
              readOnly ? "cursor-default" : "cursor-pointer hover:scale-115 active:scale-95"
            }`}
          >
            <Star
              className={`${starSizes[size]} ${
                isFilled ? "fill-amber-400 text-amber-400 drop-shadow-sm" : "text-muted-foreground/35 fill-none"
              } transition-colors duration-150`}
            />
          </button>
        );
      })}
    </div>
  );
}
