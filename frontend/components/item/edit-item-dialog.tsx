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
import { toast } from "sonner";
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
  const [localBarcode, setLocalBarcode] = useState<string>(item.local_barcode ?? "");
  const [condition, setCondition] = useState<string>(item.condition ?? "");
  const updateItem = useUpdateItem(item.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateItem.mutateAsync({
        local_barcode: localBarcode.trim() ? localBarcode.trim() : null,
        condition: condition.trim() ? condition.trim() : null,
      });
      toast.success("Item details updated successfully");
      onOpenChange(false);
      onSuccess?.();
    } catch {
      toast.error("Failed to update item details");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 py-2">
      <div className="space-y-2">
        <label
          htmlFor="item-local-barcode"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          Local Barcode / Inventory Tag
        </label>
        <input
          id="item-local-barcode"
          name="local_barcode"
          value={localBarcode}
          onChange={e => setLocalBarcode(e.target.value)}
          placeholder="e.g. SHELF-01-A, INV-12345"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
        <p className="text-[11px] text-muted-foreground">
          Physical shelf sticker or exemplar barcode, separate from Manifestation ISBN.
        </p>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="item-condition"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          Condition
        </label>
        <input
          id="item-condition"
          name="condition"
          value={condition}
          onChange={e => setCondition(e.target.value)}
          placeholder="e.g. Like New, Good, Fair"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>

      <DialogFooter className="pt-2">
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={updateItem.isPending}>
          Cancel
        </Button>
        <Button type="submit" disabled={updateItem.isPending}>
          {updateItem.isPending ? "Saving..." : "Save Changes"}
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
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Edit Item Details</DialogTitle>
          <DialogDescription>Update physical exemplar details, local shelf barcode, and condition.</DialogDescription>
        </DialogHeader>

        {isOpen && <EditItemForm item={item} onOpenChange={onOpenChange} onSuccess={onSuccess} />}
      </DialogContent>
    </Dialog>
  );
}
