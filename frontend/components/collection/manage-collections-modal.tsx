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
import { Folder, Trash2, Edit2, Loader2, AlertCircle, Plus } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface UserCollection {
  id: number;
  name: string;
  parent_id: number | null;
  description?: string;
}

export interface ManageCollectionsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * A dedicated modal to fully manage (create, rename, delete, list) the user's
 * hierarchy of custom collections.
 *
 * @param root0 - Component props
 * @param root0.isOpen - Whether the modal is open
 * @param root0.onClose - Callback to close the modal
 * @returns {JSX.Element | null} The component or null if not open
 */
export function ManageCollectionsModal({ isOpen, onClose }: ManageCollectionsModalProps) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [collectionToDelete, setCollectionToDelete] = useState<UserCollection | null>(null);

  const { data: collections, isLoading } = useQuery<UserCollection[]>({
    queryKey: ["user-collections"],
    queryFn: async () => {
      const res = await apiClient.get("/collections");
      return res.data.collections;
    },
    enabled: isOpen,
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => {
      const res = await apiClient.put(`/collections/${id}`, { name });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-collections"] });
      queryClient.invalidateQueries({ queryKey: ["taxonomies"] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await apiClient.delete(`/collections/${id}`);
      return res.data;
    },
    onSuccess: (_data, deletedCollectionId) => {
      queryClient.invalidateQueries({ queryKey: ["user-collections"] });
      queryClient.invalidateQueries({ queryKey: ["taxonomies"] });
      toast.success("Collection removed");
      setCollectionToDelete(current => (current?.id === deletedCollectionId ? null : current));
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const [createName, setCreateName] = useState("");

  const createMutation = useMutation({
    mutationFn: async (name: string) => {
      const res = await apiClient.post("/collections", { name });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-collections"] });
      queryClient.invalidateQueries({ queryKey: ["taxonomies"] });
      setCreateName("");
      toast.success("Collection created");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={open => !open && onClose()}>
      <DialogContent className="flex w-[calc(100%-2rem)] max-h-[calc(100dvh-2rem)] max-w-md flex-col gap-0 overflow-hidden rounded-lg border border-border bg-background p-0 shadow-xl">
        <DialogHeader className="relative flex-row items-center border-b border-border bg-muted/20 px-4 py-3 pr-12 text-left space-y-0">
          <div className="flex items-center gap-2">
            <Folder className="h-5 w-5 text-primary" />
            <DialogTitle className="text-lg font-semibold">Manage Collections</DialogTitle>
          </div>
          <DialogDescription className="sr-only">Create, rename, and delete your custom collections.</DialogDescription>
        </DialogHeader>

        {/* Content */}
        <div className="p-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto custom-scrollbar">
          {/* Create new collection */}
          <form
            className="flex items-center gap-2"
            onSubmit={e => {
              e.preventDefault();
              if (createName.trim()) {
                createMutation.mutate(createName.trim());
              }
            }}
          >
            <label htmlFor="new-collection-name" className="sr-only">
              New collection name
            </label>
            <input
              id="new-collection-name"
              type="text"
              placeholder="New collection name"
              value={createName}
              onChange={e => setCreateName(e.target.value)}
              className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              disabled={createMutation.isPending}
            />
            <button
              type="submit"
              disabled={!createName.trim() || createMutation.isPending}
              className="flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Add
            </button>
          </form>

          {isLoading ? (
            <div className="flex flex-1 items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : collections?.length === 0 ? (
            <div className="flex flex-col flex-1 items-center justify-center text-muted-foreground gap-3 py-12">
              <AlertCircle className="h-10 w-10 opacity-20" />
              <p className="text-sm font-medium">No collections found.</p>
              <p className="text-xs">Create your first collection from the items view.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {collections?.map(col => (
                <div
                  key={col.id}
                  className="flex items-center justify-between p-2.5 rounded-md border border-border bg-card hover:border-primary/30 transition-all shadow-sm"
                >
                  {editingId === col.id ? (
                    <form
                      className="flex-1 flex items-center gap-2"
                      onSubmit={e => {
                        e.preventDefault();
                        updateMutation.mutate({ id: col.id, name: editName });
                      }}
                    >
                      <label htmlFor={`rename-collection-${col.id}`} className="sr-only">
                        Rename collection {col.name}
                      </label>
                      <input
                        id={`rename-collection-${col.id}`}
                        autoFocus
                        className="flex-1 h-8 rounded-md border border-input bg-background px-3 text-sm text-foreground focus-visible:ring-1 focus-visible:ring-ring outline-none"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                      />
                      <button
                        type="submit"
                        disabled={updateMutation.isPending}
                        className="text-xs font-bold text-primary hover:text-primary/80 px-2 uppercase tracking-tight"
                      >
                        {updateMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="text-xs font-bold text-muted-foreground hover:text-foreground px-2 uppercase tracking-tight"
                      >
                        Cancel
                      </button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-center gap-3 overflow-hidden">
                        <Folder className="h-4 w-4 text-primary shrink-0" />
                        <span className="font-medium text-sm truncate text-foreground">{col.name}</span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => {
                            setEditingId(col.id);
                            setEditName(col.name);
                          }}
                          className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors"
                          aria-label={`Edit collection ${col.name}`}
                          title="Edit Name"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setCollectionToDelete(col)}
                          disabled={deleteMutation.isPending}
                          aria-label={`Delete collection ${col.name}`}
                          className="p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-md transition-colors"
                          title="Delete Collection"
                        >
                          {deleteMutation.isPending && deleteMutation.variables === col.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="border-t border-border bg-muted/20 px-4 py-3 sm:space-x-0">
          <DialogClose asChild>
            <button
              type="button"
              className="px-4 py-1.5 text-sm font-medium rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
            >
              Close
            </button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
      <AlertDialog
        open={collectionToDelete !== null}
        onOpenChange={open => {
          if (!open && !deleteMutation.isPending) setCollectionToDelete(null);
        }}
      >
        <AlertDialogContent className="w-[calc(100%-2rem)] max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete collection?</AlertDialogTitle>
            <AlertDialogDescription>
              Delete collection &quot;{collectionToDelete?.name}&quot;? This action cannot be undone.
            </AlertDialogDescription>
            {deleteMutation.isError && deleteMutation.variables === collectionToDelete?.id && (
              <p role="alert" className="text-sm text-destructive">
                {deleteMutation.error instanceof Error ? deleteMutation.error.message : "Collection deletion failed."}
                {" You can retry."}
              </p>
            )}
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <button
              type="button"
              onClick={() => {
                if (collectionToDelete) deleteMutation.mutate(collectionToDelete.id);
              }}
              disabled={deleteMutation.isPending || collectionToDelete === null}
              aria-label="Confirm collection deletion"
              className="inline-flex h-9 items-center justify-center rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground shadow transition-colors hover:bg-destructive/90 disabled:pointer-events-none disabled:opacity-50"
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  );
}
