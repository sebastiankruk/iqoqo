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
import { Share2, Loader2, Check, AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { toast } from "sonner";
import { ShareButton } from "@/components/ui/share-button";
import { apiClient } from "@/lib/api/client";
import { resolvePublicUrl } from "@/lib/utils";
import { type ActiveFilter } from "./filter-bar";

export type ShareVisibilityScope = "public_only" | "friends_and_public" | "all";

interface ShareCollectionDialogProps {
  activeFilters: ActiveFilter[];
  appliedQuery: string;
}

const SCOPE_OPTIONS: ReadonlyArray<{
  value: ShareVisibilityScope;
  labelKey: "scopePublicOnly" | "scopeFriendsAndPublic" | "scopeAll";
  hintKey: "scopePublicOnlyHint" | "scopeFriendsAndPublicHint" | "scopeAllHint";
}> = [
  { value: "public_only", labelKey: "scopePublicOnly", hintKey: "scopePublicOnlyHint" },
  { value: "friends_and_public", labelKey: "scopeFriendsAndPublic", hintKey: "scopeFriendsAndPublicHint" },
  { value: "all", labelKey: "scopeAll", hintKey: "scopeAllHint" },
];

/**
 * Dialog component for sharing a filtered collection view.
 * @param props - Component props.
 * @param props.activeFilters - Currently active filters to be shared.
 * @param props.appliedQuery - Current search query to be shared.
 * @returns React component.
 */
export function ShareCollectionDialog({ activeFilters, appliedQuery }: ShareCollectionDialogProps) {
  const t = useTranslations("ShareCollection");
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [visibilityScope, setVisibilityScope] = React.useState<ShareVisibilityScope>("public_only");
  const [shareUrl, setShareUrl] = React.useState("");

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      // Reset state on close
      setTimeout(() => {
        setName("");
        setDescription("");
        setVisibilityScope("public_only");
        setShareUrl("");
      }, 300);
    } else {
      // Auto-generate a name based on filters
      const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
      const categories = activeFilters.filter(f => f.type === "category").map(f => f.value);
      let defaultName = t("defaultNameAll");
      if (statuses.length === 1) defaultName = t("defaultNameStatus", { status: statuses[0].replace(/_/g, " ") });
      if (categories.length === 1) defaultName = t("defaultNameCategory", { category: categories[0] });
      if (appliedQuery) defaultName = t("defaultNameSearch", { query: appliedQuery });
      setName(defaultName);
    }
  };

  const handleGenerate = async () => {
    if (!name.trim()) {
      toast.error(t("nameRequiredError"));
      return;
    }

    setLoading(true);

    try {
      // Build filters payload
      const filtersPayload: Record<string, string | string[]> = {
        visibility_scope: visibilityScope,
      };
      const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
      const categories = activeFilters.filter(f => f.type === "category").map(f => f.value);

      // Send every selected status, not just the first. The collection page
      // allows multi-select, so passing statuses[0] published a link covering
      // a subset of what the sharer had on screen.
      if (statuses.length === 1) filtersPayload.status = statuses[0];
      else if (statuses.length > 1) filtersPayload.status = statuses;
      if (categories.length > 0) filtersPayload.tags = categories;
      if (appliedQuery) filtersPayload.query = appliedQuery;

      const response = await apiClient.post("/sharing/", {
        name: name.trim(),
        description: description.trim(),
        visibility_scope: visibilityScope,
        filters: filtersPayload,
      });

      const data = response.data;
      if (data.success && data.data && data.data.share_token) {
        const url = resolvePublicUrl(`/share/${data.data.share_token}`);
        setShareUrl(url);
        toast.success(t("generateSuccess"));
      }
    } catch (error) {
      console.error(error);
      toast.error(t("generateError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="flex items-center gap-2 transition-all shrink-0">
          <Share2 className="w-4 h-4" />
          <span>{t("triggerLabel")}</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle>{t("dialogTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>

        {!shareUrl ? (
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label
                htmlFor="name"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {t("nameLabel")}
              </label>
              <input
                id="name"
                value={name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                placeholder={t("namePlaceholder")}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div className="grid gap-2">
              <label
                htmlFor="description"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {t("descriptionLabel")}
              </label>
              <input
                id="description"
                value={description}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDescription(e.target.value)}
                placeholder={t("descriptionPlaceholder")}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <fieldset className="grid gap-2">
              <legend className="text-sm font-medium leading-none mb-1">{t("scopeLabel")}</legend>
              <div className="grid gap-2">
                {SCOPE_OPTIONS.map(opt => {
                  const selected = visibilityScope === opt.value;
                  return (
                    <label
                      key={opt.value}
                      className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                        selected ? "border-primary bg-primary/5" : "border-input hover:bg-muted/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="visibility_scope"
                        value={opt.value}
                        checked={selected}
                        onChange={() => setVisibilityScope(opt.value)}
                        className="mt-1 h-4 w-4 accent-primary"
                      />
                      <span className="grid gap-0.5 text-sm">
                        <span className="font-medium leading-none">{t(opt.labelKey)}</span>
                        <span className="text-xs text-muted-foreground">{t(opt.hintKey)}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            {visibilityScope !== "public_only" && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                <span>{visibilityScope === "all" ? t("warningAll") : t("warningFriends")}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="py-6 flex flex-col items-center space-y-4">
            <div className="p-3 bg-green-100 text-green-700 rounded-full dark:bg-green-900/30 dark:text-green-400">
              <Check className="w-8 h-8" />
            </div>
            <p className="text-center font-medium">{t("linkReady")}</p>
            <div className="w-full flex space-x-2 mt-4">
              <input
                value={shareUrl}
                readOnly
                className="flex-1 flex h-9 w-full rounded-md border border-input bg-muted/50 px-3 py-1 text-sm shadow-sm transition-colors"
              />
            </div>
          </div>
        )}

        <DialogFooter>
          {!shareUrl ? (
            <Button onClick={handleGenerate} disabled={loading} className="w-full sm:w-auto">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("generateButton")}
            </Button>
          ) : (
            <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="outline" onClick={() => setOpen(false)} className="flex-1 sm:flex-none">
                {t("doneButton")}
              </Button>
              <ShareButton url={shareUrl} title={name} text={description} />
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
