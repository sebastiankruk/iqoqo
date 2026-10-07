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

"use client";

import { useState } from "react";
import { Plus, MoveUp, MoveDown, Search, BookOpen, FileText, AlertCircle, Trash2, Pencil } from "lucide-react";
import {
  useRoadmaps,
  useCreateRoadmap,
  useAddRoadmapItem,
  useUpdateRoadmapItemTarget,
  useDeleteRoadmapItem,
  useReorderRoadmapItem,
  useManifestations,
  useWorksShelf,
  useExpressionsShelf,
  useItems,
  type RoadmapItemData,
} from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";

type TargetLevel = "work" | "expression" | "manifestation" | "item";

interface CandidateOption {
  id: number;
  title: string;
  subtitle?: string;
  badge?: string;
}

/**
 * RoadmapView component provides reading roadmap CRUD administration,
 * allowing users to sequentialize reading tracking lists across all four FRBR levels.
 *
 * @returns {React.JSX.Element} The roadmap view element.
 */
export function RoadmapView() {
  const {
    data: roadmaps = [],
    isLoading: isLoadingRoadmaps,
    isError: roadmapsFailed,
    refetch: refetchRoadmaps,
  } = useRoadmaps();
  const createRoadmapMutation = useCreateRoadmap();
  const addRoadmapItemMutation = useAddRoadmapItem();
  const updateTargetMutation = useUpdateRoadmapItemTarget();
  const deleteRoadmapItemMutation = useDeleteRoadmapItem();
  const reorderRoadmapItemMutation = useReorderRoadmapItem();

  const [activeRoadmapId, setActiveRoadmapId] = useState<number | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<RoadmapItemData | null>(null);

  // Create Roadmap form states
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  // Add Item form states
  const [targetLevel, setTargetLevel] = useState<TargetLevel>("manifestation");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateOption | null>(null);
  const [notes, setNotes] = useState("");

  // Replace Target form states
  const [replaceLevel, setReplaceLevel] = useState<TargetLevel>("manifestation");
  const [replaceQuery, setReplaceQuery] = useState("");
  const [replaceCandidate, setReplaceCandidate] = useState<CandidateOption | null>(null);
  const [replaceNotes, setReplaceNotes] = useState("");

  // Active queries for Add dialog
  const isSearchActive = searchQuery.trim().length >= 2;
  const manifestationsQuery = useManifestations(
    1,
    10,
    searchQuery,
    addDialogOpen && targetLevel === "manifestation" && isSearchActive
  );
  const worksQuery = useWorksShelf(addDialogOpen && targetLevel === "work" && isSearchActive, searchQuery);
  const expressionsQuery = useExpressionsShelf(
    addDialogOpen && targetLevel === "expression" && isSearchActive,
    searchQuery
  );
  const itemsQuery = useItems(
    1,
    10,
    undefined,
    searchQuery,
    undefined,
    addDialogOpen && targetLevel === "item",
    undefined,
    undefined,
    false,
    false,
    false,
    true
  );

  // Active queries for Replace dialog
  const isReplaceSearchActive = replaceQuery.trim().length >= 2;
  const replaceManifestationsQuery = useManifestations(
    1,
    10,
    replaceQuery,
    replaceDialogOpen && replaceLevel === "manifestation" && isReplaceSearchActive
  );
  const replaceWorksQuery = useWorksShelf(
    replaceDialogOpen && replaceLevel === "work" && isReplaceSearchActive,
    replaceQuery
  );
  const replaceExpressionsQuery = useExpressionsShelf(
    replaceDialogOpen && replaceLevel === "expression" && isReplaceSearchActive,
    replaceQuery
  );
  const replaceItemsQuery = useItems(
    1,
    10,
    undefined,
    replaceQuery,
    undefined,
    replaceDialogOpen && replaceLevel === "item",
    undefined,
    undefined,
    false,
    false,
    false,
    true
  );

  const activeRoadmap = roadmaps.find(r => r.id === (activeRoadmapId ?? roadmaps[0]?.id));
  const sortedItems = activeRoadmap?.items ? [...activeRoadmap.items].sort((a, b) => a.position - b.position) : [];

  const getCandidates = (level: TargetLevel, isReplace = false): CandidateOption[] => {
    if (isReplace) {
      if (level === "manifestation") {
        return (replaceManifestationsQuery.data?.data ?? []).map(m => ({
          id: m.id,
          title: m.title,
          subtitle: m.authors?.join(", ") || m.publisher || "Unknown author",
          badge: m.format,
        }));
      }
      if (level === "work") {
        return (replaceWorksQuery.data?.data ?? []).map(w => ({
          id: w.work_id,
          title: w.title,
          subtitle: w.creators?.join(", ") || "Unknown creator",
          badge: "Work",
        }));
      }
      if (level === "expression") {
        return (replaceExpressionsQuery.data?.data ?? []).map(e => ({
          id: e.expression_id,
          title: e.work_title,
          subtitle: `${e.language || "Unknown lang"} (${e.content_type || "text"}) • ${e.creators?.join(", ") || ""}`,
          badge: "Expression",
        }));
      }
      if (level === "item") {
        return (replaceItemsQuery.data?.data ?? []).map(i => ({
          id: i.id,
          title: i.title || "Untitled Copy",
          subtitle: `${i.publisher || ""} • Copy #${i.id} • ${i.collection_status || "owned"}`,
          badge: "Physical Copy",
        }));
      }
      return [];
    }

    if (level === "manifestation") {
      return (manifestationsQuery.data?.data ?? []).map(m => ({
        id: m.id,
        title: m.title,
        subtitle: m.authors?.join(", ") || m.publisher || "Unknown author",
        badge: m.format,
      }));
    }
    if (level === "work") {
      return (worksQuery.data?.data ?? []).map(w => ({
        id: w.work_id,
        title: w.title,
        subtitle: w.creators?.join(", ") || "Unknown creator",
        badge: "Work",
      }));
    }
    if (level === "expression") {
      return (expressionsQuery.data?.data ?? []).map(e => ({
        id: e.expression_id,
        title: e.work_title,
        subtitle: `${e.language || "Unknown lang"} (${e.content_type || "text"}) • ${e.creators?.join(", ") || ""}`,
        badge: "Expression",
      }));
    }
    if (level === "item") {
      return (itemsQuery.data?.data ?? []).map(i => ({
        id: i.id,
        title: i.title || "Untitled Copy",
        subtitle: `${i.publisher || ""} • Copy #${i.id} • ${i.collection_status || "owned"}`,
        badge: "Physical Copy",
      }));
    }
    return [];
  };

  const handleCreateRoadmap = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      const created = await createRoadmapMutation.mutateAsync({
        title: newTitle,
        description: newDescription || undefined,
      });
      setActiveRoadmapId(created.id);
      setNewTitle("");
      setNewDescription("");
      setCreateDialogOpen(false);
    } catch (err) {
      console.error("Failed to create roadmap:", err);
      toast.error("Could not create the roadmap. Please try again.");
    }
  };

  const handleAddItem = async () => {
    if (!activeRoadmap || !selectedCandidate) return;

    try {
      await addRoadmapItemMutation.mutateAsync({
        roadmapId: activeRoadmap.id,
        workId: targetLevel === "work" ? selectedCandidate.id : undefined,
        expressionId: targetLevel === "expression" ? selectedCandidate.id : undefined,
        manifestationId: targetLevel === "manifestation" ? selectedCandidate.id : undefined,
        itemId: targetLevel === "item" ? selectedCandidate.id : undefined,
        notes: notes || undefined,
      });
      setSearchQuery("");
      setSelectedCandidate(null);
      setNotes("");
      setAddDialogOpen(false);
      toast.success("Target added to roadmap.");
    } catch (err) {
      console.error("Failed to add target to roadmap:", err);
      toast.error("Could not add the item to the roadmap. Please try again.");
    }
  };

  const handleOpenReplace = (item: RoadmapItemData) => {
    setEditingItem(item);
    const initialLevel: TargetLevel =
      item.target_type ??
      (item.work_id ? "work" : item.expression_id ? "expression" : item.item_id ? "item" : "manifestation");
    setReplaceLevel(initialLevel);
    setReplaceQuery("");
    setReplaceCandidate(null);
    setReplaceNotes(item.notes || "");
    setReplaceDialogOpen(true);
  };

  const handleReplaceTarget = async () => {
    if (!editingItem) return;

    try {
      await updateTargetMutation.mutateAsync({
        itemId: editingItem.id,
        workId: replaceCandidate && replaceLevel === "work" ? replaceCandidate.id : undefined,
        expressionId: replaceCandidate && replaceLevel === "expression" ? replaceCandidate.id : undefined,
        manifestationId: replaceCandidate && replaceLevel === "manifestation" ? replaceCandidate.id : undefined,
        targetItemId: replaceCandidate && replaceLevel === "item" ? replaceCandidate.id : undefined,
        notes: replaceNotes,
      });
      setReplaceDialogOpen(false);
      setEditingItem(null);
      setReplaceCandidate(null);
      toast.success("Roadmap entry updated.");
    } catch (err) {
      console.error("Failed to update roadmap target:", err);
      toast.error("Could not update roadmap target. Please try again.");
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    try {
      await deleteRoadmapItemMutation.mutateAsync(itemId);
      toast.success("Item removed from roadmap.");
    } catch (err) {
      console.error("Failed to delete roadmap item:", err);
      toast.error("Could not remove item from roadmap. Please try again.");
    }
  };

  const handleReorder = async (itemId: number, currentPosition: number, direction: "up" | "down") => {
    const newPosition = direction === "up" ? currentPosition - 1 : currentPosition + 1;
    try {
      await reorderRoadmapItemMutation.mutateAsync({
        itemId,
        position: newPosition,
      });
    } catch (err) {
      console.error("Failed to reorder roadmap:", err);
      toast.error("Could not reorder the item. Please try again.");
    }
  };

  const resolveTargetType = (item: RoadmapItemData): TargetLevel => {
    if (item.target_type) return item.target_type;
    if (item.work_id) return "work";
    if (item.expression_id) return "expression";
    if (item.item_id) return "item";
    return "manifestation";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-serif text-2xl font-bold text-foreground">Reading Roadmaps</h1>
          <p className="mt-1 text-sm text-muted-foreground max-w-prose">
            Plan and sequence your learning tracks and reading pipelines across FRBR levels.
          </p>
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button
              data-testid="create-roadmap-btn"
              className="flex items-center gap-1"
              onClick={() => setCreateDialogOpen(true)}
            >
              <Plus className="h-4 w-4" /> Create Roadmap
            </Button>
          </DialogTrigger>
          <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>New Reading Roadmap</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateRoadmap} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Title</label>
                <input
                  type="text"
                  name="title"
                  required
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  placeholder="e.g. Distributed Systems Mastery 2026"
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Description</label>
                <textarea
                  name="description"
                  rows={3}
                  value={newDescription}
                  onChange={e => setNewDescription(e.target.value)}
                  placeholder="A rigorous track mapping out foundations of decentralized computing..."
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <DialogFooter>
                <Button type="submit">Create</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoadingRoadmaps ? (
        <div className="flex items-center justify-center py-20">
          <p className="text-muted-foreground animate-pulse">Loading roadmaps...</p>
        </div>
      ) : roadmapsFailed ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-16 text-center">
          <AlertCircle className="h-12 w-12 text-destructive/60 mb-4" />
          <h3 className="font-serif text-lg font-bold text-foreground">Could not load your roadmaps</h3>
          <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-6">
            The request failed, so this list may be incomplete. Check your connection and try again.
          </p>
          <Button variant="outline" onClick={() => void refetchRoadmaps()}>
            Try again
          </Button>
        </div>
      ) : roadmaps.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-16 text-center">
          <BookOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="font-serif text-lg font-bold text-foreground">No Reading Roadmaps Yet</h3>
          <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-6">
            Get started by creating your first roadmap to organize and prioritize your books into sequential reading
            tracks.
          </p>
          <Button data-testid="create-first-roadmap-btn" onClick={() => setCreateDialogOpen(true)}>
            Create First Roadmap
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
          {/* Side Roadmap List */}
          <div className="lg:col-span-1 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">My Tracks</h3>
            <div className="space-y-1">
              {roadmaps.map(r => (
                <button
                  key={r.id}
                  onClick={() => setActiveRoadmapId(r.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    activeRoadmap?.id === r.id
                      ? "bg-primary text-primary-foreground shadow"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  {r.title}
                </button>
              ))}
            </div>
          </div>

          {/* Active Roadmap Panel */}
          <div className="lg:col-span-3">
            {activeRoadmap && (
              <Card className="border border-border/80 shadow-md">
                <CardHeader className="flex flex-row items-start justify-between pb-6 border-b border-border/40">
                  <div className="space-y-1">
                    <CardTitle className="font-serif text-xl font-bold text-foreground">
                      <h2>{activeRoadmap.title}</h2>
                    </CardTitle>
                    {activeRoadmap.description && (
                      <CardDescription className="text-sm text-muted-foreground max-w-2xl">
                        {activeRoadmap.description}
                      </CardDescription>
                    )}
                  </div>

                  <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="add-to-roadmap-btn" variant="outline" className="flex items-center gap-1.5">
                        <Plus className="h-4 w-4" /> Add Item
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-md">
                      <DialogHeader>
                        <DialogTitle>Add Target to Roadmap</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto pr-1">
                        {/* 4-level Target Selector */}
                        <div className="space-y-1.5">
                          <label className="text-sm font-medium text-foreground">FRBR Target Level</label>
                          <div className="grid grid-cols-4 gap-1 p-1 bg-secondary/50 rounded-lg text-xs font-medium">
                            {(["work", "expression", "manifestation", "item"] as const).map(lvl => (
                              <button
                                key={lvl}
                                type="button"
                                data-testid={`target-level-${lvl}`}
                                onClick={() => {
                                  setTargetLevel(lvl);
                                  setSelectedCandidate(null);
                                }}
                                className={`py-1.5 px-2 rounded-md transition-all text-center capitalize ${
                                  targetLevel === lvl
                                    ? "bg-background text-foreground shadow-sm font-semibold"
                                    : "text-muted-foreground hover:text-foreground"
                                }`}
                              >
                                {lvl === "item" ? "Copy" : lvl}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Search Input */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-foreground">
                            {targetLevel === "item"
                              ? "Search Your Physical Copies"
                              : `Search ${targetLevel.charAt(0).toUpperCase() + targetLevel.slice(1)}s`}
                          </label>
                          <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <input
                              type="text"
                              data-testid="item-search-input"
                              value={searchQuery}
                              onChange={e => setSearchQuery(e.target.value)}
                              placeholder={
                                targetLevel === "item"
                                  ? "Search your owned physical copies..."
                                  : `Search ${targetLevel} by title or creator...`
                              }
                              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>
                        </div>

                        {/* Search Results Dropdown/List */}
                        {(targetLevel === "item" || searchQuery.trim().length >= 2) && (
                          <div className="rounded-lg border border-border bg-card divide-y divide-border/40 max-h-60 overflow-y-auto">
                            {getCandidates(targetLevel).length > 0 ? (
                              getCandidates(targetLevel).map((result, idx) => (
                                <div
                                  key={result.id}
                                  className={`p-3 flex items-center justify-between text-sm transition-colors ${
                                    selectedCandidate?.id === result.id ? "bg-accent/40" : "hover:bg-secondary/40"
                                  }`}
                                >
                                  <div className="min-w-0 flex-1 pr-2">
                                    <div className="flex items-center gap-1.5">
                                      <p className="font-medium text-foreground truncate">{result.title}</p>
                                      {result.badge && (
                                        <Badge variant="outline" className="text-[10px] py-0 px-1 shrink-0">
                                          {result.badge}
                                        </Badge>
                                      )}
                                    </div>
                                    <p className="text-xs text-muted-foreground truncate">{result.subtitle}</p>
                                  </div>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={selectedCandidate?.id === result.id ? "secondary" : "outline"}
                                    data-testid={`select-item-${idx}`}
                                    onClick={() => setSelectedCandidate(result)}
                                  >
                                    {selectedCandidate?.id === result.id ? "Selected" : "Select"}
                                  </Button>
                                </div>
                              ))
                            ) : (
                              <div className="p-4 text-center text-sm text-muted-foreground">
                                {targetLevel === "item" ? "No owned copies found." : "No results found."}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Notes Input */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-foreground">Notes (Optional)</label>
                          <textarea
                            rows={2}
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            placeholder="Add study objectives or goals..."
                            className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button
                          data-testid="confirm-add-item"
                          onClick={handleAddItem}
                          disabled={!selectedCandidate}
                          className="w-full sm:w-auto"
                        >
                          Confirm Add
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </CardHeader>

                <CardContent className="pt-6">
                  {sortedItems.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <FileText className="h-10 w-10 text-muted-foreground/30 mb-3" />
                      <p className="text-sm font-medium text-foreground">This roadmap is empty.</p>
                      <p className="text-xs text-muted-foreground max-w-xs mt-0.5 mb-4">
                        Add works, expressions, editions, or copies using the Add Item button above.
                      </p>
                    </div>
                  ) : (
                    <div className="relative border-l border-border/80 pl-6 ml-4 space-y-6">
                      {sortedItems.map((item, idx) => {
                        const targetType = resolveTargetType(item);
                        return (
                          <div
                            key={item.id}
                            data-testid="roadmap-item-card"
                            className="relative group bg-card border border-border/60 hover:border-primary/20 rounded-xl p-4 shadow-sm hover:shadow-md transition-all flex items-start justify-between gap-4"
                          >
                            {/* Timeline Dot Marker */}
                            <div className="absolute -left-[31px] top-1/2 -translate-y-1/2 flex items-center justify-center h-6.5 w-6.5 rounded-full bg-background border-2 border-primary text-[10px] font-bold text-primary">
                              {idx + 1}
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2 mb-1">
                                <h4 className="font-serif font-bold text-base text-foreground leading-snug">
                                  {item.title}
                                </h4>
                                <Badge
                                  variant="secondary"
                                  data-testid="target-level-badge"
                                  className={
                                    targetType === "item"
                                      ? "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                                      : targetType === "manifestation"
                                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                                        : targetType === "expression"
                                          ? "bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-300"
                                          : "bg-purple-100 text-purple-800 dark:bg-purple-950/40 dark:text-purple-300"
                                  }
                                >
                                  {targetType === "item" ? "Physical Copy" : targetType.toUpperCase()}
                                </Badge>
                                {targetType === "item" && item.summary?.condition && (
                                  <Badge variant="outline" className="text-xs">
                                    Condition: {item.summary.condition}
                                  </Badge>
                                )}
                                {targetType === "manifestation" && item.summary?.edition && (
                                  <Badge variant="outline" className="text-xs">
                                    {item.summary.edition}
                                  </Badge>
                                )}
                              </div>
                              <p className="text-xs text-primary font-medium mt-0.5">{item.creator}</p>
                              {item.notes && (
                                <p className="text-xs text-muted-foreground bg-secondary/30 rounded-lg p-2 mt-2 border border-border/30">
                                  {item.notes}
                                </p>
                              )}
                            </div>

                            {/* Reordering, Replace and Delete Controls */}
                            <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                              <Button
                                variant="ghost"
                                size="icon"
                                data-testid="replace-target-btn"
                                onClick={() => handleOpenReplace(item)}
                                title="Replace Target"
                                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                data-testid="delete-item-btn"
                                onClick={() => handleDeleteItem(item.id)}
                                title="Remove from Roadmap"
                                className="h-8 w-8 text-destructive/70 hover:text-destructive"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                data-testid="move-up-btn"
                                disabled={idx === 0}
                                onClick={() => handleReorder(item.id, item.position, "up")}
                                title="Move Up"
                                className="h-8 w-8"
                              >
                                <MoveUp className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                data-testid="move-down-btn"
                                disabled={idx === sortedItems.length - 1}
                                onClick={() => handleReorder(item.id, item.position, "down")}
                                title="Move Down"
                                className="h-8 w-8"
                              >
                                <MoveDown className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Replace Target Dialog */}
      <Dialog open={replaceDialogOpen} onOpenChange={setReplaceDialogOpen}>
        <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Replace Target</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto pr-1">
            <p className="text-xs text-muted-foreground">
              Current target: <span className="font-medium text-foreground">{editingItem?.title}</span>
            </p>
            {/* Level Selector */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">New FRBR Level</label>
              <div className="grid grid-cols-4 gap-1 p-1 bg-secondary/50 rounded-lg text-xs font-medium">
                {(["work", "expression", "manifestation", "item"] as const).map(lvl => (
                  <button
                    key={lvl}
                    type="button"
                    data-testid={`replace-level-${lvl}`}
                    onClick={() => {
                      setReplaceLevel(lvl);
                      setReplaceCandidate(null);
                    }}
                    className={`py-1.5 px-2 rounded-md transition-all text-center capitalize ${
                      replaceLevel === lvl
                        ? "bg-background text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {lvl === "item" ? "Copy" : lvl}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Input */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                {replaceLevel === "item"
                  ? "Search Your Physical Copies"
                  : `Search ${replaceLevel.charAt(0).toUpperCase() + replaceLevel.slice(1)}s`}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  data-testid="replace-search-input"
                  value={replaceQuery}
                  onChange={e => setReplaceQuery(e.target.value)}
                  placeholder={`Search ${replaceLevel}...`}
                  className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            {/* Candidate Results */}
            {(replaceLevel === "item" || replaceQuery.trim().length >= 2) && (
              <div className="rounded-lg border border-border bg-card divide-y divide-border/40 max-h-60 overflow-y-auto">
                {getCandidates(replaceLevel, true).length > 0 ? (
                  getCandidates(replaceLevel, true).map((result, idx) => (
                    <div
                      key={result.id}
                      className={`p-3 flex items-center justify-between text-sm transition-colors ${
                        replaceCandidate?.id === result.id ? "bg-accent/40" : "hover:bg-secondary/40"
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center gap-1.5">
                          <p className="font-medium text-foreground truncate">{result.title}</p>
                          {result.badge && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1 shrink-0">
                              {result.badge}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{result.subtitle}</p>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant={replaceCandidate?.id === result.id ? "secondary" : "outline"}
                        data-testid={`select-replace-item-${idx}`}
                        onClick={() => setReplaceCandidate(result)}
                      >
                        {replaceCandidate?.id === result.id ? "Selected" : "Select"}
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-sm text-muted-foreground">No candidates found.</div>
                )}
              </div>
            )}

            {/* Notes */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Notes</label>
              <textarea
                rows={2}
                value={replaceNotes}
                onChange={e => setReplaceNotes(e.target.value)}
                placeholder="Updated notes..."
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
          <DialogFooter>
            <Button data-testid="confirm-replace-target" onClick={handleReplaceTarget} className="w-full sm:w-auto">
              Update Target
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
