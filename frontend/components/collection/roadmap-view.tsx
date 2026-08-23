// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

"use client";

import { useState } from "react";
import { Plus, MoveUp, MoveDown, Search, BookOpen, FileText } from "lucide-react";
import {
  useRoadmaps,
  useCreateRoadmap,
  useAddRoadmapItem,
  useReorderRoadmapItem,
  useManifestations,
} from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import type { CatalogEntry } from "@/types/frbr";

/**
 * RoadmapView component provides reading roadmap CRUD administration,
 * allowing users to sequentialize reading tracking lists and perform reordering.
 *
 * @returns {React.JSX.Element} The roadmap view element.
 */
export function RoadmapView() {
  const { data: roadmaps = [], isLoading: isLoadingRoadmaps } = useRoadmaps();
  const createRoadmapMutation = useCreateRoadmap();
  const addRoadmapItemMutation = useAddRoadmapItem();
  const reorderRoadmapItemMutation = useReorderRoadmapItem();

  const [activeRoadmapId, setActiveRoadmapId] = useState<number | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // Create Roadmap form states
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  // Add Item form states
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedResult, setSelectedResult] = useState<CatalogEntry | null>(null);
  const [notes, setNotes] = useState("");

  // Manifestation search hook
  const { data: searchResults } = useManifestations(1, 5, searchQuery, searchQuery.trim().length >= 2);

  const activeRoadmap = roadmaps.find(r => r.id === (activeRoadmapId ?? roadmaps[0]?.id));
  const sortedItems = activeRoadmap?.items ? [...activeRoadmap.items].sort((a, b) => a.position - b.position) : [];

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
    }
  };

  const handleAddItem = async () => {
    if (!activeRoadmap || !selectedResult) return;

    try {
      await addRoadmapItemMutation.mutateAsync({
        roadmapId: activeRoadmap.id,
        manifestationId: selectedResult.id,
        workId: selectedResult.work_id || undefined,
        notes: notes || undefined,
      });
      setSearchQuery("");
      setSelectedResult(null);
      setNotes("");
      setAddDialogOpen(false);
    } catch (err) {
      console.error("Failed to add item to roadmap:", err);
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
      console.error("Failed to reorder item:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-serif text-2xl font-bold text-foreground">Reading Roadmaps</h1>
          <p className="mt-1 text-sm text-muted-foreground max-w-prose">
            Plan and sequence your learning tracks and reading pipelines.
          </p>
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="create-roadmap-btn" className="flex items-center gap-1">
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
      ) : roadmaps.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-16 text-center">
          <BookOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="font-serif text-lg font-bold text-foreground">No Reading Roadmaps Yet</h3>
          <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-6">
            Get started by creating your first roadmap to organize and prioritize your books into sequential reading
            tracks.
          </p>
          <Button onClick={() => setCreateDialogOpen(true)}>Create First Roadmap</Button>
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
                        <DialogTitle>Add Book to Roadmap</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto pr-1">
                        {/* Search Input */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-foreground">Search Manifestations</label>
                          <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <input
                              type="text"
                              data-testid="item-search-input"
                              value={searchQuery}
                              onChange={e => setSearchQuery(e.target.value)}
                              placeholder="Type title or author to search..."
                              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>
                        </div>

                        {/* Search Results Dropdown/List */}
                        {searchQuery.trim().length >= 2 && (
                          <div className="rounded-lg border border-border bg-card divide-y divide-border/40 max-h-60 overflow-y-auto">
                            {searchResults?.data && searchResults.data.length > 0 ? (
                              searchResults.data.map((result, idx) => (
                                <div
                                  key={result.id}
                                  className={`p-3 flex items-center justify-between text-sm transition-colors ${
                                    selectedResult?.id === result.id ? "bg-accent/40" : "hover:bg-secondary/40"
                                  }`}
                                >
                                  <div className="min-w-0 flex-1">
                                    <p className="font-medium text-foreground truncate">{result.title}</p>
                                    <p className="text-xs text-muted-foreground truncate">
                                      {result.authors?.join(", ") || "Unknown Author"}
                                    </p>
                                  </div>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={selectedResult?.id === result.id ? "secondary" : "outline"}
                                    data-testid={`select-item-${idx}`}
                                    onClick={() => setSelectedResult(result)}
                                  >
                                    {selectedResult?.id === result.id ? "Selected" : "Select"}
                                  </Button>
                                </div>
                              ))
                            ) : (
                              <div className="p-4 text-center text-sm text-muted-foreground">No results found.</div>
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
                          disabled={!selectedResult}
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
                        Add works or manifestations using the Add Item button above.
                      </p>
                    </div>
                  ) : (
                    <div className="relative border-l border-border/80 pl-6 ml-4 space-y-6">
                      {sortedItems.map((item, idx) => (
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
                            <h4 className="font-serif font-bold text-base text-foreground leading-snug">
                              {item.title}
                            </h4>
                            <p className="text-xs text-primary font-medium mt-0.5">{item.creator}</p>
                            {item.notes && (
                              <p className="text-xs text-muted-foreground bg-secondary/30 rounded-lg p-2 mt-2 border border-border/30">
                                {item.notes}
                              </p>
                            )}
                          </div>

                          {/* Reordering and Actions Controls */}
                          <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
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
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
