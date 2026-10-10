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
import type { Item } from "@/types/frbr";
import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import { isAudioMedia, getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { isBoardGameFormat, isVideoFormat } from "@/lib/media-classification";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useItemSidebarActions } from "./sidebar/use-item-sidebar-actions";
import { SidebarCover } from "./sidebar/sidebar-cover";
import { SidebarStatusBadges } from "./sidebar/sidebar-status-badges";
import { SidebarLendingInfo } from "./sidebar/sidebar-lending-info";
import { SidebarIdentifiers } from "./sidebar/sidebar-identifiers";
import { SidebarActions } from "./sidebar/sidebar-actions";
import { SidebarFrbrInfo } from "./sidebar/sidebar-frbr-info";

export const STATUS_LABELS: Record<string, { label: string; class: string }> = {
  // Collection (Physical)
  available: { label: "On Shelf", class: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  lent: { label: "Lent Out", class: "bg-orange-50 text-orange-700 ring-orange-200" },
  lost: { label: "Lost", class: "bg-red-50 text-red-700 ring-red-200" },
  wish_list: { label: "On Wish List", class: "bg-primary/10 text-primary ring-primary/20" },
  ordered: { label: "Ordered", class: "bg-amber-50 text-amber-700 ring-amber-200" },
  damaged: { label: "Damaged", class: "bg-orange-100 text-orange-800 ring-orange-300" },
  // Progress
  reading: { label: "Reading...", class: "bg-accent/10 text-accent ring-accent/20" },
  read: { label: "Read", class: "bg-blue-50 text-blue-700 ring-blue-200" },
  unread: { label: "Unread", class: "bg-zinc-50 text-zinc-700 ring-zinc-200" },
  want_to_read: { label: "Want to Read", class: "bg-primary/10 text-primary ring-primary/20" },
  listening: { label: "Listening...", class: "bg-teal-50 text-teal-700 ring-teal-200" },
  listened: { label: "Listened", class: "bg-cyan-50 text-cyan-700 ring-cyan-200" },
  want_to_listen: { label: "Want to Listen", class: "bg-sky-50 text-sky-700 ring-sky-200" },
  watching: { label: "Watching...", class: "bg-indigo-50 text-indigo-700 ring-indigo-200" },
  watched: { label: "Watched", class: "bg-violet-50 text-violet-700 ring-violet-200" },
  want_to_watch: { label: "Want to Watch", class: "bg-indigo-50/50 text-indigo-600 ring-indigo-200" },
  want_to_play: { label: "Want to Play", class: "bg-rose-50/50 text-rose-600 ring-rose-200" },
  played: { label: "Played", class: "bg-rose-50 text-rose-700 ring-rose-200" },
  playing: { label: "Playing...", class: "bg-pink-50 text-pink-700 ring-pink-200" },
};

/** Props for ItemSidebar component */
interface ItemSidebarProps {
  item: Item;
  onEdit?: () => void;
}

/**
 * Left sidebar of the item detail page – cover, status, actions, quick stats.
 *
 * @param root0 - The props object
 * @param root0.item - The item
 * @param root0.onEdit - Callback when edit is clicked
 * @returns {JSX.Element} The component
 */
export function ItemSidebar({ item, onEdit }: ItemSidebarProps) {
  const timestamp = getCoverTimestamp(item.manifestation_meta, item.meta);

  const coverUrl =
    getCoverUrl(item.cover_url || undefined, timestamp) ??
    getCoverUrl(item.manifestation_meta?.["cover_url"] as string | undefined, timestamp) ??
    getCoverUrl(item.meta?.["cover_url"] as string | undefined, timestamp);

  const { data: profile } = useProfile();
  const permissions = profile?.permissions ?? [];
  const hasUploadPermission = permissions.includes(PermissionName.UPLOAD_COVER);
  const hasEditPermission = permissions.includes(PermissionName.WRITE_METADATA);

  const isOwner = !!item.is_owner || (!!profile && item.owner_id === profile.id);
  const isAdmin = !!profile?.roles?.includes("admin");
  const canModifyItem = isOwner || isAdmin;
  // Media type detection
  const format =
    (item.manifestation_meta?.["format"] as string | undefined) ??
    (item.meta?.["format"] as string | undefined) ??
    "book";
  const isAudio = isAudioMedia(format);
  const isVideo = isVideoFormat(format);
  const isGame = isBoardGameFormat(format);
  const isBook = !isAudio && !isVideo && !isGame;

  const progressStatusInfo = STATUS_LABELS[item.status] ?? {
    label: item.status,
    class: "bg-secondary text-foreground ring-border",
  };
  const collectionStatusInfo = item.is_borrowed
    ? { label: "Borrowed", class: "bg-blue-50 text-blue-700 ring-blue-200" }
    : (STATUS_LABELS[item.collection_status] ?? {
        label: item.collection_status,
        class: "bg-secondary text-foreground ring-border",
      });
  const {
    updateItem,
    handleUploadComplete,
    isLentDialogOpen,
    setIsLentDialogOpen,
    isQrOpen,
    setIsQrOpen,
    borrowerName,
    setBorrowerName,
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
  } = useItemSidebarActions(item, { isOwner, canModifyItem });

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Book/Audio cover */}
      <SidebarCover
        item={item}
        coverUrl={coverUrl}
        format={format}
        isAudio={isAudio}
        isVideo={isVideo}
        isGame={isGame}
        isBook={isBook}
      />

      {/* Status badges */}
      <SidebarStatusBadges
        collectionStatusInfo={collectionStatusInfo}
        progressStatusInfo={progressStatusInfo}
        isHidden={item.is_hidden}
      />

      {/* Lending info */}
      <SidebarLendingInfo item={item} handleRequestLoan={handleRequestLoan} handleLentSubmit={handleLentSubmit} />

      {/* ISBN */}
      <SidebarIdentifiers item={item} />

      {/* Action buttons & Status Selects */}
      <SidebarActions
        item={item}
        canModifyItem={canModifyItem}
        isOwner={isOwner}
        profile={profile}
        onEdit={onEdit}
        format={format}
        isAudio={isAudio}
        isVideo={isVideo}
        isGame={isGame}
        isBook={isBook}
        collectionStatusInfo={collectionStatusInfo}
        progressStatusInfo={progressStatusInfo}
        hasUploadPermission={hasUploadPermission}
        hasEditPermission={hasEditPermission}
        updateItem={updateItem}
        handleCollectionStatusChange={handleCollectionStatusChange}
        handleStatusChange={handleStatusChange}
        loanStatus={loanStatus}
        requestLoan={requestLoan}
        handleRequestLoan={handleRequestLoan}
        handleToggleVisibility={handleToggleVisibility}
        isQrOpen={isQrOpen}
        setIsQrOpen={setIsQrOpen}
        handleUploadComplete={handleUploadComplete}
        itemCollections={itemCollections}
        collectionsLoading={collectionsLoading}
        removeFromCollection={removeFromCollection}
        handleRemoveFromCollection={handleRemoveFromCollection}
        showCollectionDropdown={showCollectionDropdown}
        setShowCollectionDropdown={setShowCollectionDropdown}
        collectionDropdownRef={collectionDropdownRef}
        userCollections={userCollections}
        addToCollection={addToCollection}
        handleAddToCollection={handleAddToCollection}
      />

      {/* FRBR quick info */}
      <SidebarFrbrInfo item={item} />

      <Dialog open={isLentDialogOpen} onOpenChange={setIsLentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lent Out Item</DialogTitle>
            <DialogDescription>
              Who are you lending this item to? This helps you keep track of your physical collection.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label
              htmlFor="borrower-name"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Borrower Name
            </label>
            <div className="relative">
              <input
                id="borrower-name"
                className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Search user or enter name..."
                value={borrowerName}
                onChange={e => {
                  setBorrowerName(e.target.value);
                  setBorrowerId(undefined); // Reset ID if user types something new
                }}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
                onKeyDown={e => e.key === "Enter" && handleLentSubmit()}
                autoFocus
                autoComplete="off"
              />
              {searchFocused && borrowerName.trim().length >= 2 && (
                <div className="absolute z-50 w-full mt-1 bg-popover text-popover-foreground rounded-md border shadow-md outline-none">
                  <ul className="max-h-48 overflow-y-auto py-1">
                    {isSearching ? (
                      <li className="px-3 py-2 text-sm text-muted-foreground">Searching...</li>
                    ) : searchResults && searchResults.length > 0 ? (
                      searchResults.map(user => (
                        <li
                          key={user.id}
                          className="px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground cursor-pointer flex items-center justify-between"
                          onMouseDown={e => {
                            e.preventDefault(); // Prevent blur
                            setBorrowerName(user.display_name || user.email);
                            setBorrowerId(user.id);
                            setSearchFocused(false);
                          }}
                        >
                          <span className="font-medium">{user.display_name || user.email}</span>
                          <span className="text-xs text-muted-foreground ml-2 truncate max-w-[120px]">
                            {user.email}
                          </span>
                        </li>
                      ))
                    ) : (
                      <li className="px-3 py-2 text-sm text-muted-foreground">
                        No users found. Will save as plain name.
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLentDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleLentSubmit} disabled={updateItem.isPending}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
