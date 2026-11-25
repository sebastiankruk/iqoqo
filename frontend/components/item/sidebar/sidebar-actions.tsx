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
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Pencil,
  QrCode,
  Eye,
  EyeOff,
  Folder,
  X,
  Plus,
  Loader2,
  ImagePlus,
  ArrowRightLeft,
  ChevronDown,
  ChevronUp,
  MoreHorizontal,
} from "lucide-react";
import type { Item, MediaFormat } from "@/types/frbr";
import { PermissionName } from "@/lib/permissions";
import { CoverUploadPicker, type CoverUploadResult } from "@/components/scanner/cover-upload-picker";
import { MultiImageUploader } from "@/components/scanner/multi-image-uploader";
import { TaxonomyEditor } from "@/components/item/taxonomy-editor";
import { PrintQrCodeDialog } from "@/components/item/qrcode-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { STATUS_LABELS } from "./constants";

/** Props for SidebarActions component */
export interface SidebarActionsProps {
  item: Item;
  canModifyItem?: boolean;
  isOwner?: boolean;
  profile?: { id?: string; roles?: string[]; permissions?: string[] } | null;
  onEdit?: () => void;
  format?: string;
  isAudio?: boolean;
  isVideo?: boolean;
  isGame?: boolean;
  isBook?: boolean;
  collectionStatusInfo?: { label: string; class: string };
  progressStatusInfo?: { label: string; class: string };
  hasUploadPermission?: boolean;
  hasEditPermission?: boolean;
  updateItem?: { isPending: boolean };
  handleCollectionStatusChange?: (e: ChangeEvent<HTMLSelectElement>) => void;
  handleStatusChange?: (e: ChangeEvent<HTMLSelectElement>) => void;
  loanStatus?: { status?: string } | null;
  requestLoan?: { isPending: boolean };
  handleRequestLoan?: () => void;
  handleToggleVisibility?: () => void;
  isQrOpen?: boolean;
  setIsQrOpen?: (open: boolean) => void;
  handleUploadComplete?: (result?: CoverUploadResult) => void;
  itemCollections?: Array<{ id: number; name: string }> | null;
  collectionsLoading?: boolean;
  removeFromCollection?: { isPending: boolean };
  handleRemoveFromCollection?: (id: number) => void;
  showCollectionDropdown?: boolean;
  setShowCollectionDropdown?: React.Dispatch<React.SetStateAction<boolean>>;
  collectionDropdownRef?: React.RefObject<HTMLDivElement | null>;
  userCollections?: Array<{ id: number; name: string }> | null;
  addToCollection?: { isPending: boolean };
  handleAddToCollection?: (id: number) => void;
  linkedOpenDataNode?: React.ReactNode;
  adminActionsNode?: React.ReactNode;
  adminAccordionLabel?: string;
}

/**
 * Action buttons and status selects region of ItemSidebar.
 *
 * @param props - Props object
 * @returns {JSX.Element} Rendered action buttons and controls
 */
export function SidebarActions({
  item,
  canModifyItem = false,
  isOwner = false,
  profile,
  onEdit,
  format = "book",
  isAudio = false,
  isVideo = false,
  isGame = false,
  isBook = true,
  collectionStatusInfo = { label: "Unknown", class: "bg-secondary text-foreground ring-border" },
  progressStatusInfo = { label: "Unknown", class: "bg-secondary text-foreground ring-border" },
  hasUploadPermission = false,
  hasEditPermission = false,
  updateItem = { isPending: false },
  handleCollectionStatusChange,
  handleStatusChange,
  loanStatus,
  requestLoan = { isPending: false },
  handleRequestLoan,
  handleToggleVisibility,
  isQrOpen = false,
  setIsQrOpen,
  handleUploadComplete = () => {},
  itemCollections,
  collectionsLoading = false,
  removeFromCollection = { isPending: false },
  handleRemoveFromCollection = () => {},
  showCollectionDropdown = false,
  setShowCollectionDropdown = () => {},
  collectionDropdownRef,
  userCollections,
  addToCollection = { isPending: false },
  handleAddToCollection = () => {},
  linkedOpenDataNode,
  adminActionsNode,
  adminAccordionLabel,
}: SidebarActionsProps) {
  const t = useTranslations("ItemDetail");
  const tSidebar = useTranslations("ItemDetail.sidebar");
  const [coverPickerOpen, setCoverPickerOpen] = React.useState(false);
  const [showCollectionsEditor, setShowCollectionsEditor] = React.useState(false);
  const [showScansEditor, setShowScansEditor] = React.useState(false);
  const [showTaxonomyEditor, setShowTaxonomyEditor] = React.useState(false);
  const [showLinkedOpenData, setShowLinkedOpenData] = React.useState(false);
  const [showAdminActions, setShowAdminActions] = React.useState(false);

  const hasCover = Boolean(item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]);
  const canReplaceCover = canModifyItem && hasUploadPermission && Boolean(item.manifestation_id);
  const canTransferOwnership = Boolean(
    profile &&
    (profile.roles?.includes("admin") ||
      profile.roles?.includes("custodian") ||
      profile.permissions?.includes(PermissionName.TRANSFER_ITEM))
  );
  const mediumLabel = isBook
    ? tSidebar("mediumBook")
    : isAudio
      ? tSidebar("mediumAudio")
      : isVideo
        ? tSidebar("mediumVideo")
        : isGame
          ? tSidebar("mediumGame")
          : tSidebar("mediumDefault");

  return (
    <>
      <div className="flex w-full flex-col gap-3 px-1">
        {canModifyItem ? (
          <div className="flex flex-col gap-2.5">
            {/* Collection Select */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                {tSidebar("availabilityLabel")}
              </span>
              <select
                aria-label="Collection status"
                value={item.collection_status}
                onChange={handleCollectionStatusChange}
                disabled={updateItem.isPending}
                className="w-full rounded-lg bg-secondary/80 px-3 py-2 text-sm font-medium text-foreground outline-none ring-1 ring-border transition-all hover:bg-secondary focus:ring-primary/50 disabled:opacity-60 cursor-pointer appearance-none"
              >
                <optgroup label="Availability & Condition">
                  {["available", "lent", "damaged", "lost"].map(key => (
                    <option key={key} value={key} className="bg-card py-2">
                      {STATUS_LABELS[key]?.label || key}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Acquisition">
                  {["wish_list", "ordered"].map(key => (
                    <option key={key} value={key} className="bg-card py-2">
                      {STATUS_LABELS[key]?.label || key}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>

            {/* Progress Select */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                {tSidebar("progressLabel", { medium: mediumLabel })}
              </span>
              <select
                aria-label="Item status"
                value={item.status}
                onChange={handleStatusChange}
                disabled={updateItem.isPending}
                className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground outline-none shadow-sm transition-all hover:opacity-90 focus:ring-2 focus:ring-primary/20 disabled:opacity-60 cursor-pointer appearance-none text-center"
              >
                {isBook && (
                  <optgroup label="Reading Progress">
                    {["unread", "reading", "read", "want_to_read"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isAudio && (
                  <optgroup label="Listening Progress">
                    {["want_to_listen", "listening", "listened"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isVideo && (
                  <optgroup label="Watching Progress">
                    {["want_to_watch", "watching", "watched"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isGame && (
                  <optgroup label="Gaming Progress">
                    {["want_to_play", "playing", "played"].map(s => (
                      <option key={s} value={s} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[s]?.label || s}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>
          </div>
        ) : item.is_borrowed ? (
          <div className="flex flex-col gap-2.5">
            {/* Collection Status (Read-only for borrower) */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                Availability & Condition
              </span>
              <div className="w-full rounded-lg bg-secondary/50 px-4 py-2 text-xs font-semibold text-center text-secondary-foreground border border-border/50">
                {collectionStatusInfo.label || "Unknown"}
              </div>
            </div>

            {/* Progress Select (Editable for borrower) */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                {isBook ? "Reading" : isAudio ? "Listening" : isVideo ? "Watching" : isGame ? "Gaming" : "Item"}{" "}
                Progress
              </span>
              <select
                aria-label="Item status"
                value={item.status}
                onChange={handleStatusChange}
                disabled={updateItem.isPending}
                className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground outline-none shadow-sm transition-all hover:opacity-90 focus:ring-2 focus:ring-primary/20 disabled:opacity-60 cursor-pointer appearance-none text-center"
              >
                {isBook && (
                  <optgroup label="Reading Progress">
                    {["unread", "reading", "read", "want_to_read"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isAudio && (
                  <optgroup label="Listening Progress">
                    {["want_to_listen", "listening", "listened"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isVideo && (
                  <optgroup label="Watching Progress">
                    {["want_to_watch", "watching", "watched"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isGame && (
                  <optgroup label="Gaming Progress">
                    {["want_to_play", "playing", "played"].map(s => (
                      <option key={s} value={s} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[s]?.label || s}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>

            {/* Lending actions for borrower */}
            <div className="mt-4 border-t border-border/40 pt-4 flex flex-col gap-2">
              {item.collection_status === "lent" && item.lent_to_user_id === profile?.id ? (
                <span
                  data-testid="loan-status-badge"
                  className="w-full rounded-lg bg-blue-50 text-blue-700 ring-blue-200 px-4 py-2 text-xs font-semibold text-center border border-blue-100"
                >
                  On Loan
                </span>
              ) : loanStatus?.status === "approved" ? (
                <span
                  data-testid="loan-status-badge"
                  className="w-full rounded-lg bg-blue-50 text-blue-700 ring-blue-200 px-4 py-2 text-xs font-semibold text-center border border-blue-100"
                >
                  On Loan
                </span>
              ) : loanStatus?.status === "pending" ? (
                <span
                  data-testid="loan-status-badge"
                  className="w-full rounded-lg bg-amber-50 text-amber-700 ring-amber-200 px-4 py-2 text-xs font-semibold text-center border border-amber-100"
                >
                  Pending Approval
                </span>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {!(item.collection_status === "wish_list" && !isOwner) && (
              <>
                <div className="w-full rounded-lg bg-secondary/50 px-4 py-2 text-xs font-semibold text-center text-secondary-foreground border border-border/50">
                  {collectionStatusInfo.label || "Unknown"}
                </div>
                <div className="w-full rounded-lg bg-primary/10 px-4 py-2 text-xs font-semibold text-center text-primary border border-primary/20">
                  {progressStatusInfo.label || "Unknown"}
                </div>
              </>
            )}

            {/* Lending Actions for borrower/public user */}
            {!isOwner && profile && item.collection_status !== "wish_list" && (
              <div className="mt-4 border-t border-border/40 pt-4 flex flex-col gap-2">
                {item.collection_status === "lent" && item.lent_to_user_id === profile?.id ? (
                  <span
                    data-testid="loan-status-badge"
                    className="w-full rounded-lg bg-blue-50 text-blue-700 ring-blue-200 px-4 py-2 text-xs font-semibold text-center border border-blue-100"
                  >
                    On Loan
                  </span>
                ) : loanStatus ? (
                  loanStatus.status === "pending" ? (
                    <span
                      data-testid="loan-status-badge"
                      className="w-full rounded-lg bg-amber-50 text-amber-700 ring-amber-200 px-4 py-2 text-xs font-semibold text-center border border-amber-100"
                    >
                      Pending Approval
                    </span>
                  ) : loanStatus.status === "approved" ? (
                    <span
                      data-testid="loan-status-badge"
                      className="w-full rounded-lg bg-blue-50 text-blue-700 ring-blue-200 px-4 py-2 text-xs font-semibold text-center border border-blue-100"
                    >
                      On Loan
                    </span>
                  ) : (
                    <button
                      onClick={handleRequestLoan}
                      disabled={requestLoan.isPending}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
                    >
                      {requestLoan.isPending ? "Requesting..." : "Request Loan"}
                    </button>
                  )
                ) : (
                  <button
                    onClick={handleRequestLoan}
                    disabled={requestLoan.isPending}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50"
                  >
                    {requestLoan.isPending ? "Requesting..." : "Request Loan"}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Compact Owner Action Row (<= 2 visible buttons: Edit Metadata + Manage menu) */}
        {(canModifyItem || canTransferOwnership) && (
          <div className="flex items-center gap-2">
            {canModifyItem && onEdit && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={onEdit}
                className="flex-1 justify-center gap-2"
              >
                <Pencil className="h-3.5 w-3.5" />
                <span>{tSidebar("editMetadata")}</span>
              </Button>
            )}

            {(canModifyItem || canTransferOwnership) && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    data-testid="sidebar-manage-menu"
                    className={`gap-1.5 ${canModifyItem && onEdit ? "" : "w-full justify-center"}`}
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" />
                    <span>{tSidebar("manageMenu")}</span>
                    <ChevronDown className="h-3 w-3 opacity-70" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {canModifyItem && (
                    <DropdownMenuItem
                      onSelect={() => handleToggleVisibility?.()}
                      disabled={updateItem.isPending}
                      className="cursor-pointer gap-2"
                    >
                      {item.is_hidden ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                      <span>{item.is_hidden ? tSidebar("makePublic") : tSidebar("hideFromPublic")}</span>
                    </DropdownMenuItem>
                  )}
                  {canModifyItem && item.manifestation_id && (
                    <DropdownMenuItem
                      data-testid="qrcode-btn"
                      onSelect={() => setIsQrOpen?.(true)}
                      className="cursor-pointer gap-2"
                    >
                      <QrCode className="h-4 w-4" />
                      <span>{tSidebar("printQrCode")}</span>
                    </DropdownMenuItem>
                  )}
                  {canReplaceCover && (
                    <DropdownMenuItem
                      data-testid="replace-cover-menu-item"
                      onSelect={() => setCoverPickerOpen(true)}
                      className="cursor-pointer gap-2"
                    >
                      <ImagePlus className="h-4 w-4" />
                      <span>{hasCover ? tSidebar("replaceCover") : tSidebar("contributeCover")}</span>
                    </DropdownMenuItem>
                  )}
                  {canTransferOwnership && (
                    <>
                      {canModifyItem && <DropdownMenuSeparator />}
                      <DropdownMenuItem asChild className="cursor-pointer gap-2">
                        <Link
                          href={`/admin/ownership?sourceUserId=${encodeURIComponent(item.owner_id || "")}&itemId=${item.id}`}
                        >
                          <ArrowRightLeft className="h-4 w-4" />
                          <span>{t("reassignOwner")}</span>
                        </Link>
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        )}

        {/* Single hoisted CoverUploadPicker outside DropdownMenuContent so Radix menu close never unmounts AlertDialog/inputs */}
        {canReplaceCover && (
          <CoverUploadPicker
            manifestation_id={item.manifestation_id}
            format={format as MediaFormat}
            onUploadComplete={handleUploadComplete}
            label={hasCover ? tSidebar("replaceCover") : tSidebar("contributeCover")}
            icon={<ImagePlus className="h-3.5 w-3.5" />}
            confirmTitle={hasCover ? tSidebar("replaceCoverConfirmTitle") : undefined}
            confirmMessage={hasCover ? tSidebar("replaceCoverConfirmMessage") : undefined}
            open={coverPickerOpen}
            onOpenChange={setCoverPickerOpen}
            hideTrigger
          />
        )}

        {/* Collapsible cataloging disclosures */}
        {canModifyItem && hasEditPermission && (
          <div className="border-t border-border/40 pt-2">
            <button
              type="button"
              onClick={() => setShowScansEditor(prev => !prev)}
              className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <span>{tSidebar("additionalScans")}</span>
              {showScansEditor ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showScansEditor && (
              <div className="mt-2">
                <MultiImageUploader
                  manifestationId={item.manifestation_id}
                  currentItemFormat={format}
                  onUploadComplete={handleUploadComplete}
                />
              </div>
            )}
          </div>
        )}

        {canModifyItem && (
          <div className="border-t border-border/40 pt-2">
            <button
              type="button"
              onClick={() => setShowCollectionsEditor(prev => !prev)}
              className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <span>
                {tSidebar("namedCollections")}
                {(itemCollections?.length ?? 0) > 0 ? ` (${itemCollections?.length})` : ""}
              </span>
              {showCollectionsEditor ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showCollectionsEditor && (
              <div className="mt-2 flex flex-col gap-2">
                {(itemCollections ?? []).length === 0 && !collectionsLoading ? (
                  <p className="text-[10px] text-muted-foreground italic px-1">Not in any named collections yet.</p>
                ) : collectionsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mx-auto" />
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {(itemCollections ?? []).map(col => (
                      <span
                        key={col.id}
                        className="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-500 px-2.5 py-0.5 text-[10px] font-semibold ring-1 ring-green-200 dark:ring-green-500/20"
                      >
                        <Folder className="h-2.5 w-2.5" />
                        {col.name}
                        <button
                          type="button"
                          onClick={() => handleRemoveFromCollection(col.id)}
                          disabled={removeFromCollection.isPending}
                          className="ml-0.5 p-0.5 rounded-full hover:bg-green-200 dark:hover:bg-green-500/20 transition-colors"
                        >
                          <X className="h-2.5 w-2.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="relative" ref={collectionDropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowCollectionDropdown(prev => !prev)}
                    disabled={addToCollection.isPending}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-[10px] font-semibold text-muted-foreground transition-colors hover:bg-secondary disabled:opacity-60"
                  >
                    <Plus className="h-3 w-3" />
                    Add to named collection
                  </button>
                  {showCollectionDropdown && (userCollections?.length ?? 0) > 0 && (
                    <div className="absolute left-0 top-full mt-1 w-full rounded-md border border-border bg-card shadow-lg overflow-hidden z-50 max-h-40 overflow-y-auto">
                      {userCollections!
                        .filter(uc => !(itemCollections ?? []).some(ic => ic.id === uc.id))
                        .map(uc => (
                          <button
                            type="button"
                            key={uc.id}
                            onClick={() => handleAddToCollection(uc.id)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-foreground hover:bg-secondary transition-colors"
                          >
                            <Folder className="h-3 w-3 text-primary" />
                            <span className="truncate">{uc.name}</span>
                          </button>
                        ))}
                      {(userCollections ?? []).filter(uc => !(itemCollections ?? []).some(ic => ic.id === uc.id))
                        .length === 0 && (
                        <p className="px-3 py-2 text-[10px] text-muted-foreground italic">
                          Already in all your named collections.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {canModifyItem && (
          <div className="border-t border-border/40 pt-2">
            <button
              type="button"
              onClick={() => setShowTaxonomyEditor(prev => !prev)}
              className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <span>{tSidebar("taxonomy")}</span>
              {showTaxonomyEditor ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showTaxonomyEditor && (
              <div className="mt-2">
                <TaxonomyEditor item={item} />
              </div>
            )}
          </div>
        )}

        {linkedOpenDataNode && (
          <div className="border-t border-border/40 pt-2">
            <button
              type="button"
              data-testid="lod-accordion-toggle"
              onClick={() => setShowLinkedOpenData(prev => !prev)}
              className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <span>{tSidebar("linkedOpenData")}</span>
              {showLinkedOpenData ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showLinkedOpenData && <div className="mt-2">{linkedOpenDataNode}</div>}
          </div>
        )}

        {adminActionsNode && (
          <div className="border-t border-border/40 pt-2">
            <button
              type="button"
              data-testid="admin-actions-accordion-toggle"
              onClick={() => setShowAdminActions(prev => !prev)}
              className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <span>{adminAccordionLabel ?? tSidebar("adminActions")}</span>
              {showAdminActions ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showAdminActions && <div className="mt-2">{adminActionsNode}</div>}
          </div>
        )}
      </div>
      <PrintQrCodeDialog isOpen={isQrOpen} onOpenChange={setIsQrOpen ?? (() => {})} item={item} />
    </>
  );
}
