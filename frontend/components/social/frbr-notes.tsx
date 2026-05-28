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
import { useSocialNotes, useSubmitNote, useUpdateNote, useDeleteNote } from "@/lib/api/social";
import { useProfile } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Loader2, MessageSquare, Trash2, Edit3, User, Send, X, Check } from "lucide-react";
import { toast } from "sonner";
import Image from "next/image";

interface FRBRNotesProps {
  level: "work" | "expression" | "manifestation" | "item";
  targetId: number;
  title: string;
}

/**
 * Component for personal and community notes on a specific FRBR level.
 * Allows users to add, update, and delete text notes chronologically.
 *
 * @param props - Component props.
 * @param props.level - The target FRBR level.
 * @param props.targetId - The database ID of the target resource.
 * @param props.title - The user-friendly title of the level.
 * @returns The notes section view.
 */
export function FRBRNotes({ level, targetId, title }: FRBRNotesProps) {
  const { data: profile } = useProfile();
  const { data: notes, isLoading, isError, refetch } = useSocialNotes(level, targetId);
  const submitMutation = useSubmitNote();
  const updateMutation = useUpdateNote();
  const deleteMutation = useDeleteNote();

  const [newNote, setNewNote] = useState<string>("");
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const noteText = newNote.trim();
    if (!noteText) {
      toast.error("Note content cannot be empty");
      return;
    }

    try {
      await submitMutation.mutateAsync({
        level,
        targetId,
        note: noteText,
      });
      toast.success("Note added!");
      setNewNote("");
      await refetch();
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to add note");
    }
  };

  const handleUpdate = async (noteId: number) => {
    const noteText = editingText.trim();
    if (!noteText) {
      toast.error("Note content cannot be empty");
      return;
    }

    try {
      await updateMutation.mutateAsync({
        noteId,
        note: noteText,
      });
      toast.success("Note updated!");
      setEditingNoteId(null);
      await refetch();
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to update note");
    }
  };

  const handleDelete = async (noteId: number) => {
    if (!confirm("Are you sure you want to delete this note?")) {
      return;
    }

    try {
      await deleteMutation.mutateAsync({ noteId, level, targetId });
      toast.success("Note deleted");
      await refetch();
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to delete note");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-36 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !notes) {
    return <div className="py-6 text-center text-sm text-muted-foreground">Failed to load notes.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Input area */}
      {profile && (
        <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-border/80 bg-card p-4 shadow-sm">
          <h4 className="font-serif text-sm font-bold text-foreground">Add Note / Remarks</h4>
          <div className="flex items-start gap-3">
            <textarea
              placeholder={`Write a personal note, comment, or tracking remark on this ${title} level...`}
              value={newNote}
              onChange={e => setNewNote(e.target.value)}
              className="min-h-[72px] w-full resize-y rounded-xl border border-border/85 bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={submitMutation.isPending} className="h-8 gap-1.5">
              {submitMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              Add Note
            </Button>
          </div>
        </form>
      )}

      {/* List of notes */}
      <div className="space-y-4">
        <h4 className="font-serif text-sm font-bold text-foreground">Notes & Remarks ({notes.length})</h4>

        {notes.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center">
            <MessageSquare className="h-7 w-7 text-muted-foreground/45" />
            <span className="mt-2 text-xs font-medium text-muted-foreground">No notes recorded yet</span>
            <span className="text-[10px] text-muted-foreground/80 mt-0.5">Use the field above to save notes.</span>
          </div>
        ) : (
          <div className="relative border-l border-border pl-6 ml-3 space-y-6 py-1">
            {notes.map(note => {
              const isOwn = profile && strEquals(note.user_id, profile.id);
              const isEditing = editingNoteId === note.id;

              return (
                <div key={note.id} className="relative group">
                  {/* Timeline bullet */}
                  <span className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full border border-border bg-background text-muted-foreground shadow-sm">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  </span>

                  <div className="rounded-xl border bg-card p-4 shadow-sm hover:border-border/100 transition-colors duration-150">
                    <div className="flex items-center justify-between gap-4 mb-2">
                      <div className="flex items-center gap-2">
                        <div className="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary border text-muted-foreground overflow-hidden">
                          {note.user_avatar_url ? (
                            <Image
                              src={note.user_avatar_url}
                              alt={note.user_display_name}
                              fill
                              className="object-cover"
                              unoptimized
                            />
                          ) : (
                            <User className="h-3 w-3" />
                          )}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-foreground leading-none">{note.user_display_name}</div>
                          <div className="text-[9px] text-muted-foreground font-medium mt-0.5">
                            @{note.user_username || "anonymous"} &bull; {new Date(note.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>

                      {isOwn && !isEditing && (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => {
                              setEditingNoteId(note.id);
                              setEditingText(note.note);
                            }}
                          >
                            <Edit3 className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-destructive/80 hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDelete(note.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </div>

                    {isEditing ? (
                      <div className="space-y-2 mt-1">
                        <textarea
                          value={editingText}
                          onChange={e => setEditingText(e.target.value)}
                          className="min-h-[56px] w-full resize-y rounded-lg border border-border/90 bg-background px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-0"
                        />
                        <div className="flex gap-2 justify-end">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2.5 text-xs gap-1"
                            onClick={() => setEditingNoteId(null)}
                          >
                            <X className="h-3 w-3" /> Cancel
                          </Button>
                          <Button
                            size="sm"
                            className="h-7 px-2.5 text-xs gap-1"
                            onClick={() => handleUpdate(note.id)}
                            disabled={updateMutation.isPending}
                          >
                            <Check className="h-3 w-3" /> Save
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap pl-0.5">
                        {note.note}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Helper to compare two strings case-insensitively, handling null or undefined values.
 *
 * @param a - First string.
 * @param b - Second string.
 * @returns True if strings are equal, false otherwise.
 */
function strEquals(a: string | undefined | null, b: string | undefined | null): boolean {
  if (!a || !b) return false;
  return String(a).toLowerCase() === String(b).toLowerCase();
}
