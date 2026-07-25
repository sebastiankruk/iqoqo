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

import { ArrowLeft, Zap } from "lucide-react";
import Link from "next/link";
import { ScanFormat, SCAN_FORMATS } from "@/types/frbr";
import { MEDIA_REGISTRY } from "@/lib/media";

interface TopBarProps {
  currentFormat?: ScanFormat;
  setFormat?: (format: ScanFormat) => void;
  currentPolicy?: "inventory" | "wishlist" | "catalog";
  setPolicy?: (policy: "inventory" | "wishlist" | "catalog") => void;
  onCancel?: () => void;
  hasFlash?: boolean;
  isFlashOn?: boolean;
  onToggleFlash?: () => void;
}

const POLICY_OPTIONS = [
  { value: "inventory", label: "Inventory" },
  { value: "wishlist", label: "Wishlist" },
  { value: "catalog", label: "Catalog" },
] as const;

/**
 * Scanner page top overlay bar with format and policy selector.
 *
 * @param {TopBarProps} props - The component props
 * @returns {JSX.Element} The component
 */
export function TopBar({
  currentFormat,
  setFormat,
  currentPolicy,
  setPolicy,
  onCancel,
  hasFlash,
  isFlashOn,
  onToggleFlash,
}: TopBarProps) {
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

        {hasFlash ? (
          <button
            onClick={onToggleFlash}
            className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors ${
              isFlashOn ? "bg-primary text-primary-foreground" : "bg-white/10 text-white hover:bg-white/20"
            }`}
            aria-label="Toggle flash"
          >
            <Zap className={`h-5 w-5 ${isFlashOn ? "fill-current" : ""}`} />
          </button>
        ) : (
          <div className="h-10 w-10" />
        )}
      </div>

      {(setFormat || setPolicy) && (
        <div className="flex flex-col bg-black/20 px-4 py-3 backdrop-blur-sm border-b border-white/5 gap-3">
          {setFormat && (
            <div className="flex justify-center gap-2 overflow-x-auto no-scrollbar">
              {SCAN_FORMATS.map(f => {
                const meta = MEDIA_REGISTRY[f];
                const Icon = meta.icon;
                return (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    title={meta.label}
                    aria-label={meta.label}
                    className={`flex items-center justify-center p-3 sm:px-3 sm:py-1.5 sm:gap-2 rounded-full border transition-all ${
                      currentFormat === f
                        ? "bg-primary text-primary-foreground border-primary shadow-lg"
                        : "bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <Icon className="h-5 w-5 sm:h-3.5 sm:w-3.5" />
                    <span className="hidden sm:inline text-xs font-bold uppercase tracking-wider">{meta.label}</span>
                  </button>
                );
              })}
            </div>
          )}

          {setPolicy && (
            <div className="flex justify-center items-center gap-1.5 border-t border-white/10 pt-2">
              {POLICY_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPolicy(opt.value)}
                  className={`px-3 py-1 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider rounded-full border transition-all ${
                    currentPolicy === opt.value
                      ? "bg-white text-black border-white shadow-md"
                      : "bg-white/10 text-white/70 border-white/10 hover:bg-white/20 hover:text-white"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
