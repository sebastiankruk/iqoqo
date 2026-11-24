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

import { ArrowLeft, Check, ChevronDown, Zap } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  /** Optional inline accessory placed on the same single line as Format and Policy pills. */
  rightAccessory?: React.ReactNode;
  children?: React.ReactNode;
}

const POLICY_KEYS: Record<"inventory" | "wishlist" | "catalog", { labelKey: string; hintKey: string }> = {
  inventory: { labelKey: "topBar.policyShelf", hintKey: "topBar.policyShelfHint" },
  wishlist: { labelKey: "topBar.policyWishlist", hintKey: "topBar.policyWishlistHint" },
  catalog: { labelKey: "topBar.policyCatalog", hintKey: "topBar.policyCatalogHint" },
};

const POLICY_ORDER: readonly ("inventory" | "wishlist" | "catalog")[] = ["inventory", "wishlist", "catalog"];

/**
 * Compact scanner top overlay bar with a single-line [Format | Policy | Batch] strip
 * and full-width search bar slot.
 *
 * @param {TopBarProps} props - The component props
 * @returns {JSX.Element} The component
 */
export function TopBar({
  currentFormat = "book",
  setFormat,
  currentPolicy = "inventory",
  setPolicy,
  onCancel,
  hasFlash,
  isFlashOn,
  onToggleFlash,
  rightAccessory,
  children,
}: TopBarProps) {
  const t = useTranslations("scanner");
  const activePolicyConfig = POLICY_KEYS[currentPolicy] || POLICY_KEYS.inventory;
  const activeFormatMeta = MEDIA_REGISTRY[currentFormat] ?? MEDIA_REGISTRY.book;
  const ActiveFormatIcon = activeFormatMeta?.icon;
  const activeFormatLabel =
    currentFormat && t.has?.(`formats.${currentFormat}`)
      ? t(`formats.${currentFormat}`)
      : activeFormatMeta?.label || currentFormat;

  const hasControlRow = Boolean(setFormat || currentPolicy || setPolicy || rightAccessory);

  return (
    <div className="absolute inset-x-0 top-0 z-20 flex flex-col pt-[env(safe-area-inset-top,0px)]">
      <div className="flex items-center justify-between bg-black/40 px-4 py-3 backdrop-blur-sm">
        <Link
          href="/"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20"
          aria-label={t("topBar.backAria")}
          onClick={onCancel}
        >
          <ArrowLeft className="h-5 w-5 text-white" />
        </Link>

        <div className="flex flex-col items-center text-center">
          <h1 className="text-base font-bold tracking-tight text-white sm:text-lg">{t("topBar.title")}</h1>
          <span className="mt-0.5 text-[11px] text-white/50">{t("topBar.subtitle")}</span>
        </div>

        {hasFlash ? (
          <button
            type="button"
            onClick={onToggleFlash}
            className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors ${
              isFlashOn ? "bg-primary text-primary-foreground" : "bg-white/10 text-white hover:bg-white/20"
            }`}
            aria-label={t("topBar.flashToggleAria")}
          >
            <Zap className={`h-5 w-5 ${isFlashOn ? "fill-current" : ""}`} />
          </button>
        ) : (
          <div className="h-10 w-10" />
        )}
      </div>

      {hasControlRow && (
        <div className="flex items-center justify-between gap-1.5 bg-black/25 px-4 py-2 backdrop-blur-sm border-b border-white/5">
          <div className="flex items-center gap-1.5 min-w-0">
            {setFormat && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    data-testid="format-selector-trigger"
                    aria-label={`${t("topBar.formatLabel")}: ${activeFormatLabel}`}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-white/20 min-w-0"
                  >
                    {ActiveFormatIcon && <ActiveFormatIcon className="h-3.5 w-3.5 shrink-0" />}
                    <span className="truncate max-w-[84px]">{activeFormatLabel}</span>
                    <ChevronDown className="h-3.5 w-3.5 opacity-75 shrink-0" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuLabel className="text-xs">{t("topBar.formatLabel")}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {SCAN_FORMATS.map(f => {
                    const meta = MEDIA_REGISTRY[f];
                    if (!meta) return null;
                    const Icon = meta.icon;
                    const formatLabel = t.has?.(`formats.${f}`) ? t(`formats.${f}`) : meta.label;
                    const selected = currentFormat === f;
                    return (
                      <DropdownMenuItem
                        key={f}
                        data-testid={`format-option-${f}`}
                        onClick={() => setFormat(f)}
                        className="flex items-center justify-between gap-2 cursor-pointer"
                      >
                        <span className="flex items-center gap-2">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <span>{formatLabel}</span>
                        </span>
                        {selected && <Check className="h-4 w-4 text-primary" />}
                      </DropdownMenuItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {(currentPolicy || setPolicy) && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    data-testid="policy-selector-trigger"
                    title={t(activePolicyConfig.hintKey)}
                    aria-label={`${t("topBar.policyLabel")}: ${t(activePolicyConfig.labelKey)}`}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-white/20 min-w-0"
                  >
                    <span className="truncate max-w-[84px]">{t(activePolicyConfig.labelKey)}</span>
                    <ChevronDown className="h-3.5 w-3.5 opacity-75 shrink-0" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-64">
                  <DropdownMenuLabel className="text-xs">{t("topBar.policyLabel")}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {POLICY_ORDER.map(policyValue => {
                    const conf = POLICY_KEYS[policyValue];
                    const selected = currentPolicy === policyValue;
                    return (
                      <DropdownMenuItem
                        key={policyValue}
                        data-testid={`policy-option-${policyValue}`}
                        onClick={() => setPolicy?.(policyValue)}
                        className="flex items-start justify-between gap-2 py-2 cursor-pointer"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs font-semibold">{t(conf.labelKey)}</span>
                          <span className="text-[11px] text-muted-foreground">{t(conf.hintKey)}</span>
                        </div>
                        {selected && <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />}
                      </DropdownMenuItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {rightAccessory && <div className="shrink-0">{rightAccessory}</div>}
        </div>
      )}

      {children && (
        <div className="flex w-full flex-col px-4 py-2 bg-black/20 backdrop-blur-sm border-b border-white/5">
          {children}
        </div>
      )}
    </div>
  );
}
