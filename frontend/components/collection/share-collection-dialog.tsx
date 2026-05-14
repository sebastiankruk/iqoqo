"use client";

import * as React from "react";
import { Share2, Loader2, Copy, Check } from "lucide-react";
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
import { resolveApiUrl } from "@/lib/utils";
import { ShareButton } from "@/components/ui/share-button";
import { apiClient } from "@/lib/api/client";

interface ShareCollectionDialogProps {
  activeFilters: ActiveFilter[];
  appliedQuery: string;
}

export function ShareCollectionDialog({ activeFilters, appliedQuery }: ShareCollectionDialogProps) {
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [shareUrl, setShareUrl] = React.useState("");

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      // Reset state on close
      setTimeout(() => {
        setName("");
        setDescription("");
        setShareUrl("");
      }, 300);
    } else {
      // Auto-generate a name based on filters
      const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
      const categories = activeFilters.filter(f => f.type === "category").map(f => f.value);
      let defaultName = "My Shared Collection";
      if (statuses.length === 1) defaultName = `My ${statuses[0].replace(/_/g, " ")} Items`;
      if (categories.length === 1) defaultName = `My ${categories[0]} Collection`;
      if (appliedQuery) defaultName = `Search results for "${appliedQuery}"`;
      setName(defaultName);
    }
  };

  const handleGenerate = async () => {
    if (!name.trim()) {
      toast.error("Please enter a name for the collection.");
      return;
    }

    setLoading(true);

    try {
      // Build filters payload
      const filtersPayload: Record<string, any> = {};
      const statuses = activeFilters.filter(f => f.type === "status").map(f => f.value);
      const categories = activeFilters.filter(f => f.type === "category").map(f => f.value);

      if (statuses.length > 0) filtersPayload.status = statuses[0]; // assuming single status for now
      if (categories.length > 0) filtersPayload.tags = categories;
      if (appliedQuery) filtersPayload.query = appliedQuery;

      const response = await apiClient.post("/sharing/", {
        name: name.trim(),
        description: description.trim(),
        filters: filtersPayload,
      });

      const data = response.data;
      if (data.success && data.data && data.data.share_token) {
        const url = `${window.location.origin}/share/${data.data.share_token}`;
        setShareUrl(url);
        toast.success("Sharing link generated!");
      }
    } catch (error) {
      console.error(error);
      toast.error("Failed to generate sharing link.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="flex items-center gap-2 transition-all shrink-0">
          <Share2 className="w-4 h-4" />
          <span>Share View</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Share Collection View</DialogTitle>
          <DialogDescription>
            Create a public sharing link for your current filtered view. Hidden items will remain private.
          </DialogDescription>
        </DialogHeader>

        {!shareUrl ? (
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label
                htmlFor="name"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Collection Name
              </label>
              <input
                id="name"
                value={name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                placeholder="e.g. My Birthday Wishlist"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div className="grid gap-2">
              <label
                htmlFor="description"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Description (Optional)
              </label>
              <input
                id="description"
                value={description}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDescription(e.target.value)}
                placeholder="A short description for visitors"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          </div>
        ) : (
          <div className="py-6 flex flex-col items-center space-y-4">
            <div className="p-3 bg-green-100 text-green-700 rounded-full dark:bg-green-900/30 dark:text-green-400">
              <Check className="w-8 h-8" />
            </div>
            <p className="text-center font-medium">Your link is ready!</p>
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
              Generate Link
            </Button>
          ) : (
            <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="outline" onClick={() => setOpen(false)} className="flex-1 sm:flex-none">
                Done
              </Button>
              <ShareButton url={shareUrl} title={name} text={description} />
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
