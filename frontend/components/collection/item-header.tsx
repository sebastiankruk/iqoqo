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

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { queryKeys, useManifestationWithPolling, useRegenerateCover } from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";
import { useQueryClient } from "@tanstack/react-query";

/** Props for ItemHeader component */
interface ItemHeaderProps {
  initialItem: Item;
}

/**
 * Header for an item detail page.
 *
 * @param root0 - The props object
 * @param root0.initialItem - The initial item data
 * @returns {JSX.Element} The component
 */
export function ItemHeader({ initialItem }: ItemHeaderProps) {
  // Use our hook to handle the real-time update via polling
  const { item, } = useManifestationWithPolling(initialItem);
  const qc = useQueryClient(); // Add this to access the React Query cache!
  const regenerateCover = useRegenerateCover();
  const [isRequesting, setIsRequesting] = useState(false);

  const isPending = item?.cover_status === 'pending';

  const handleRegenerate = async () => {
    if (!item.manifestation_id) return;

    setIsRequesting(true);
    try {
      await regenerateCover.mutateAsync(item.manifestation_id);
      // Tell React Query to update the cache for this specific item
      qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          cover_status: 'pending'
        };
      });
    } catch (error) {
      console.error("Failed to schedule regeneration:", error);
    } finally {
      setIsRequesting(false);
    }
  };

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRegenerate}
          disabled={isPending || isRequesting}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isPending ? 'animate-spin' : ''}`} />
          {isPending ? "Generating..." : "Regenerate Cover"}
        </Button>
      </div>
    </div>
  );
}
