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

import { ArrowLeft, Zap, Book, Disc, Film, Dices, Puzzle } from "lucide-react";
import Link from "next/link";

interface TopBarProps {
  currentFormat?: string;
  setFormat?: (format: string) => void;
  onCancel?: () => void;
}

/**
 * Scanner page top overlay bar with format selector.
 *
 * @param {TopBarProps} props - The component props
 * @returns {JSX.Element} The component
 */
export function TopBar({ currentFormat, setFormat, onCancel }: TopBarProps) {
  const formats = [
    { id: "book", icon: Book, label: "Book" },
    { id: "audio", icon: Disc, label: "Audio" },
    { id: "video", icon: Film, label: "Video" },
    { id: "boardgame", icon: Dices, label: "Game" },
    { id: "puzzle", icon: Puzzle, label: "Puzzle" },
  ];

  return (
    <div className="absolute inset-x-0 top-0 z-20 flex flex-col">
      <div className="flex items-center justify-between bg-black/40 px-4 py-4 backdrop-blur-sm">
        <Link
          href="/"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
          aria-label="Go back to library"
          onClick={onCancel}
        >
          <ArrowLeft className="h-5 w-5 text-white" />
        </Link>

        <div className="flex flex-col items-center text-center">
          <h1 className="text-base font-bold tracking-tight text-white sm:text-lg">Scan New Item</h1>
          <span className="mt-0.5 text-[11px] text-white/50">Position barcode or cover within the frame</span>
        </div>

        <button
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
          aria-label="Toggle flash"
        >
          <Zap className="h-5 w-5 text-white" />
        </button>
      </div>

      {setFormat && (
        <div className="flex justify-center bg-black/20 px-4 py-3 backdrop-blur-sm border-b border-white/5">
          <div className="flex gap-2 overflow-x-auto no-scrollbar">
            {formats.map(f => (
              <button
                key={f.id}
                onClick={() => setFormat(f.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all ${
                  currentFormat === f.id
                    ? "bg-primary text-primary-foreground border-primary shadow-lg"
                    : "bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white"
                }`}
              >
                <f.icon className="h-3.5 w-3.5" />
                <span className="text-xs font-bold uppercase tracking-wider">{f.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
