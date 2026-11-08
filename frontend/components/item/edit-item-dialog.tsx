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
import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { isLegoFormat } from "@/lib/media-classification";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useUpdateItem } from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

export interface EditItemDialogProps {
  item: Item;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface EditItemFormProps {
  item: Item;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * Inner form component for editing Item details.
 *
 * @param props - Component props
 * @returns {React.JSX.Element} The rendered form
 */
function EditItemForm({ item, onOpenChange, onSuccess }: EditItemFormProps) {
  const t = useTranslations("EditItemDialog");
  const [localBarcode, setLocalBarcode] = useState<string>(item.local_barcode ?? "");
  const [condition, setCondition] = useState<string>(item.condition ?? "");
  const [visibility, setVisibility] = useState<"private" | "friends_only" | "public">(
    (item as { visibility?: "private" | "friends_only" | "public" }).visibility ??
      (item.is_hidden ? "private" : "public")
  );

  const isLego =
    item.expression?.content_type === "lego" ||
    item.content_type === "lego" ||
    item.meta?.category === "lego" ||
    item.meta?.build_status !== undefined ||
    (Boolean(item.manifestation_meta?.category) && item.manifestation_meta?.category === "lego") ||
    (Boolean(item.manifestation_meta?.format) && isLegoFormat(item.manifestation_meta?.format as string));

  const [buildStatus, setBuildStatus] = useState<string>((item.meta?.build_status as string) ?? "built");
  const [missingPiecesCount, setMissingPiecesCount] = useState<string>(
    item.meta?.missing_pieces_count !== undefined ? String(item.meta.missing_pieces_count) : "0"
  );
  const [instructionsIncluded, setInstructionsIncluded] = useState<boolean>(
    item.meta?.instructions_included !== undefined ? Boolean(item.meta.instructions_included) : true
  );

  const hasMapAttachment =
    Boolean(item.manifestation_meta?.has_map) ||
    Boolean(item.display?.fields?.has_map) ||
    (Array.isArray(item.manifestation_meta?.map_attachments) &&
      (item.manifestation_meta?.map_attachments as unknown[]).length > 0) ||
    item.manifestation_meta?.format === "cartographic_map" ||
    item.manifestation_meta?.format === "atlas" ||
    item.map_insert_present !== undefined ||
    item.meta?.map_insert_present !== undefined;

  const [mapInsertPresent, setMapInsertPresent] = useState<boolean>(
    item.map_insert_present !== undefined
      ? Boolean(item.map_insert_present)
      : item.meta?.map_insert_present !== undefined
        ? Boolean(item.meta.map_insert_present)
        : true
  );

  const updateItem = useUpdateItem(item.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: Record<string, unknown> = {
        local_barcode: localBarcode.trim() ? localBarcode.trim() : null,
        condition: condition.trim() ? condition.trim() : null,
        visibility,
      };

      if (isLego) {
        payload.build_status = buildStatus;
        payload.missing_pieces_count = parseInt(missingPiecesCount, 10) || 0;
        payload.instructions_included = instructionsIncluded;
      }

      if (hasMapAttachment) {
        payload.map_insert_present = mapInsertPresent;
      }

      await updateItem.mutateAsync(payload as Partial<Item>);
      toast.success(t("success"));
      onOpenChange(false);
      onSuccess?.();
    } catch {
      toast.error(t("error"));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 py-2">
      <div className="space-y-2">
        <label
          htmlFor="item-local-barcode"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          {t("localBarcode")}
        </label>
        <input
          id="item-local-barcode"
          name="local_barcode"
          value={localBarcode}
          onChange={e => setLocalBarcode(e.target.value)}
          placeholder={t("localBarcodePlaceholder")}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
        <p className="text-[11px] text-muted-foreground">{t("localBarcodeHint")}</p>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="item-condition"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          {t("condition")}
        </label>
        <input
          id="item-condition"
          name="condition"
          value={condition}
          onChange={e => setCondition(e.target.value)}
          placeholder={t("conditionPlaceholder")}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>

      <div className="space-y-2">
        <label
          htmlFor="item-visibility"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          {t("visibility") || "Visibility Tier"}
        </label>
        <select
          id="item-visibility"
          name="visibility"
          value={visibility}
          onChange={e => setVisibility(e.target.value as "private" | "friends_only" | "public")}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <option value="private">{t("visibilityPrivate") || "Private"}</option>
          <option value="friends_only">{t("visibilityFriendsOnly") || "Friends Only"}</option>
          <option value="public">{t("visibilityPublic") || "Public"}</option>
        </select>
        <p className="text-[11px] text-muted-foreground">
          {t("visibilityHint") || "Controls who can see this physical item in your library."}
        </p>
      </div>

      {isLego && (
        <div className="space-y-4 pt-2 border-t border-border/40">
          <div className="space-y-2">
            <label
              htmlFor="item-build-status"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              {t("buildStatus") || "Build Status"}
            </label>
            <select
              id="item-build-status"
              name="build_status"
              value={buildStatus}
              onChange={e => setBuildStatus(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="sealed">{t("buildStatusSealed") || "Sealed (In Box)"}</option>
              <option value="built">{t("buildStatusBuilt") || "Built"}</option>
              <option value="incomplete">{t("buildStatusIncomplete") || "Incomplete"}</option>
              <option value="parted_out">{t("buildStatusPartedOut") || "Parted Out"}</option>
            </select>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="item-missing-pieces"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              {t("missingPieces") || "Missing Pieces Count"}
            </label>
            <input
              id="item-missing-pieces"
              name="missing_pieces_count"
              type="number"
              min="0"
              value={missingPiecesCount}
              onChange={e => setMissingPiecesCount(e.target.value)}
              placeholder="0"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            ></input>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="item-instructions-included"
              name="instructions_included"
              type="checkbox"
              checked={instructionsIncluded}
              onChange={e => setInstructionsIncluded(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <label htmlFor="item-instructions-included" className="text-sm font-medium leading-none cursor-pointer">
              {t("instructionsIncluded") || "Instructions Included"}
            </label>
          </div>
        </div>
      )}

      {hasMapAttachment && (
        <div className="flex items-center gap-2 pt-2 border-t border-border/40">
          <input
            id="item-map-insert-present"
            name="map_insert_present"
            type="checkbox"
            checked={mapInsertPresent}
            onChange={e => setMapInsertPresent(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
          />
          <label htmlFor="item-map-insert-present" className="text-sm font-medium leading-none cursor-pointer">
            {t("mapInsertPresent") || "Map Insert Present"}
          </label>
        </div>
      )}

      <DialogFooter className="pt-2">
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={updateItem.isPending}>
          {t("cancel")}
        </Button>
        <Button type="submit" disabled={updateItem.isPending}>
          {updateItem.isPending ? t("saving") : t("saveChanges")}
        </Button>
      </DialogFooter>
    </form>
  );
}

/**
 * Dialog for editing physical Item exemplar details, including local barcode and condition.
 *
 * @param props - Component props
 * @returns {React.JSX.Element} Edit item dialog component
 */
export function EditItemDialog({ item, isOpen, onOpenChange, onSuccess }: EditItemDialogProps) {
  const t = useTranslations("EditItemDialog");
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        {isOpen && <EditItemForm item={item} onOpenChange={onOpenChange} onSuccess={onSuccess} />}
      </DialogContent>
    </Dialog>
  );
}
