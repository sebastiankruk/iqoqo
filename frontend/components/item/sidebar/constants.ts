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
