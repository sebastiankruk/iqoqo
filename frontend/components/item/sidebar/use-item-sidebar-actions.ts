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
import { ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { Item } from "@/types/frbr";
import {
  useUpdateItem,
  useUserSearch,
  useLoanStatus,
  useRequestLoan,
  useItemCollections,
  useAddItemToCollection,
  useRemoveItemFromCollection,
  useUserCollections,
} from "@/lib/api/hooks";
import { STATUS_LABELS } from "../item-sidebar";

/** Options for useItemSidebarActions hook */
export interface UseItemSidebarActionsOptions {
  isOwner?: boolean;
  canModifyItem?: boolean;
}

/**
 * Custom hook containing action handlers and related state for ItemSidebar.
 *
 * @param item - The current item
 * @param options - Optional flags for ownership and modification rights
 * @returns Named object containing handlers, mutations, and local state
 */
export function useItemSidebarActions(item: Item, options?: UseItemSidebarActionsOptions) {
  const router = useRouter();
  const updateItem = useUpdateItem(item.id);

  const isOwner = options?.isOwner ?? !!item.is_owner;
  const canModifyItem = options?.canModifyItem ?? isOwner;

  const handleUploadComplete = () => {
    toast.success("Cover uploaded and processing started!");
    // Refresh to show 'processing' status
    router.refresh();
  };

  const [isLentDialogOpen, setIsLentDialogOpen] = React.useState(false);
  const [isQrOpen, setIsQrOpen] = React.useState(false);
  const [borrowerName, setBorrowerName] = React.useState(item.lent_to_name || "");
  const [borrowerId, setBorrowerId] = React.useState<string | undefined>(item.lent_to_user_id || undefined);

  // Hook for user search, enabled when borrowerName is typed and doesn't exactly match the selected ID
  const [searchFocused, setSearchFocused] = React.useState(false);
  const { data: searchResults, isLoading: isSearching } = useUserSearch(borrowerName, searchFocused);

  const { data: loanStatus } = useLoanStatus(isOwner ? null : item.id);
  const requestLoan = useRequestLoan();

  const { data: itemCollections, isLoading: collectionsLoading } = useItemCollections(canModifyItem ? item.id : null);
  const addToCollection = useAddItemToCollection();
  const removeFromCollection = useRemoveItemFromCollection();
  const { data: userCollections } = useUserCollections();
  const [showCollectionDropdown, setShowCollectionDropdown] = React.useState(false);
  const collectionDropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    /**
     * Handles clicking outside the collection dropdown.
     *
     * @param event - The mouse event
     */
    function handleClickOutside(event: MouseEvent) {
      if (collectionDropdownRef.current && !collectionDropdownRef.current.contains(event.target as Node)) {
        setShowCollectionDropdown(false);
      }
    }
    if (showCollectionDropdown) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showCollectionDropdown]);

  const handleAddToCollection = (collectionId: number) => {
    addToCollection.mutate(
      { itemId: item.id, collectionId },
      {
        onSuccess: () => {
          toast.success("Added to collection");
          setShowCollectionDropdown(false);
        },
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleRemoveFromCollection = (collectionId: number) => {
    removeFromCollection.mutate(
      { itemId: item.id, collectionId },
      {
        onSuccess: () => toast.success("Removed from collection"),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleRequestLoan = () => {
    requestLoan.mutate(
      { itemId: item.id },
      {
        onSuccess: () => {
          toast.success("Loan request submitted");
        },
        onError: e => {
          toast.error((e as Error).message);
        },
      }
    );
  };

  const handleStatusChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as Item["status"];
    updateItem.mutate(
      { status: newStatus },
      {
        onSuccess: () => toast.success(`Progress status updated to ${STATUS_LABELS[newStatus]?.label || newStatus}`),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleCollectionStatusChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as Item["collection_status"];

    if (newStatus === "lent") {
      setIsLentDialogOpen(true);
      return;
    }

    // If moving away from 'lent', we should clear the borrower info
    const updatePayload: Partial<Item> = { collection_status: newStatus };
    if (item.collection_status === "lent") {
      updatePayload.lent_to_name = null;
      updatePayload.lent_to_user_id = null;
    }

    updateItem.mutate(updatePayload, {
      onSuccess: res => {
        toast.success(`Collection status updated to ${STATUS_LABELS[newStatus]?.label || newStatus}`);
        if (res?.data?.id && res.data.id !== item.id) {
          router.replace(`/item/${res.data.id}`);
        }
      },
      onError: e => toast.error((e as Error).message),
    });
  };

  const handleLentSubmit = () => {
    if (!borrowerName.trim()) {
      toast.error("Please enter a borrower name");
      return;
    }

    updateItem.mutate(
      {
        collection_status: "lent",
        lent_to_name: borrowerName.trim(),
        lent_to_user_id: borrowerId || null,
      },
      {
        onSuccess: res => {
          toast.success(`Item marked as lent to ${borrowerName}`);
          setIsLentDialogOpen(false);
          if (res?.data?.id && res.data.id !== item.id) {
            router.replace(`/item/${res.data.id}`);
          }
        },
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleToggleVisibility = () => {
    const newHidden = !item.is_hidden;
    updateItem.mutate(
      { is_hidden: newHidden },
      {
        onSuccess: () => toast.success(`Item is now ${newHidden ? "hidden" : "public"}`),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  return {
    updateItem,
    handleUploadComplete,
    isLentDialogOpen,
    setIsLentDialogOpen,
    isQrOpen,
    setIsQrOpen,
    borrowerName,
    setBorrowerName,
    borrowerId,
    setBorrowerId,
    searchFocused,
    setSearchFocused,
    searchResults,
    isSearching,
    loanStatus,
    requestLoan,
    itemCollections,
    collectionsLoading,
    addToCollection,
    removeFromCollection,
    userCollections,
    showCollectionDropdown,
    setShowCollectionDropdown,
    collectionDropdownRef,
    handleAddToCollection,
    handleRemoveFromCollection,
    handleRequestLoan,
    handleStatusChange,
    handleCollectionStatusChange,
    handleLentSubmit,
    handleToggleVisibility,
  };
}
