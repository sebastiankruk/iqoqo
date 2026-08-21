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

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { useProfile } from "@/lib/api/hooks";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { FeedbackModal } from "@/components/feedback/feedback-modal";
import { FeedbackDetailModal, type FeedbackItemDetail } from "@/components/feedback/feedback-detail-modal";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import {
  Bug,
  Lightbulb,
  Plus,
  Search,
  SlidersHorizontal,
  Clock,
  User as UserIcon,
  Paperclip,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
} from "lucide-react";

type PaginationData = {
  page: number;
  per_page: number;
  total: number;
  pages: number;
};

const statusStyles: Record<string, { bg: string; text: string; border: string; label: string }> = {
  new: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", border: "border-blue-500/20", label: "New" },
  accepted: {
    bg: "bg-purple-500/10",
    text: "text-purple-600 dark:text-purple-400",
    border: "border-purple-500/20",
    label: "Accepted",
  },
  in_progress: {
    bg: "bg-amber-500/10",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-500/20",
    label: "In Progress",
  },
  in_validation: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-500/20",
    label: "In Validation",
  },
  closed: { bg: "bg-muted", text: "text-muted-foreground", border: "border-border", label: "Closed" },
};

/**
 * Dedicated feedback and ticket management page.
 *
 * @returns {JSX.Element} The FeedbackPage component.
 */
export default function FeedbackPage() {
  const { data: profile } = useProfile();
  const isAdmin = Boolean(profile?.roles?.includes("admin") || profile?.permissions?.includes("tickets:admin"));

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<FeedbackItemDetail | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const {
    data: feedbackData,
    isLoading: loading,
    refetch: fetchTickets,
  } = useQuery({
    queryKey: ["feedback", statusFilter, typeFilter, currentPage],
    queryFn: async () => {
      const response = await apiClient.get<{
        data: FeedbackItemDetail[];
        pagination?: PaginationData;
      }>("/feedback", {
        params: {
          status: statusFilter || undefined,
          type: typeFilter || undefined,
          page: currentPage,
          per_page: 15,
        },
      });
      return response.data;
    },
  });

  const items = useMemo(() => feedbackData?.data ?? [], [feedbackData]);
  const pagination: PaginationData = useMemo(() => {
    if (feedbackData?.pagination) return feedbackData.pagination;
    return {
      page: 1,
      per_page: 15,
      total: feedbackData?.data?.length ?? 0,
      pages: 1,
    };
  }, [feedbackData]);

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      item =>
        item.description.toLowerCase().includes(q) ||
        item.user_display_name.toLowerCase().includes(q) ||
        (item.user_email && item.user_email.toLowerCase().includes(q))
    );
  }, [items, searchQuery]);

  const handleCardClick = (item: FeedbackItemDetail) => {
    setSelectedTicket(item);
    setDetailModalOpen(true);
  };

  const handleClearFilters = () => {
    setStatusFilter("");
    setTypeFilter("");
    setSearchQuery("");
    setCurrentPage(1);
  };

  const hasActiveFilters = Boolean(statusFilter || typeFilter || searchQuery);

  const renderFilterControls = (isMobile = false) => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-serif text-sm font-bold uppercase tracking-wider text-muted-foreground">
          <SlidersHorizontal className="h-4 w-4" />
          Filters
        </h2>
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleClearFilters}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </button>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Filter by keyword..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {/* Type filter */}
      <div className="space-y-2 border-t border-border pt-4">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Request Type</label>
        <div className="space-y-1">
          {[
            { value: "", label: "All Types" },
            { value: "bug", label: "Bugs", icon: Bug },
            { value: "feature_request", label: "Feature Requests", icon: Lightbulb },
          ].map(opt => {
            const active = typeFilter === opt.value;
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setTypeFilter(opt.value);
                  setCurrentPage(1);
                  if (isMobile) setMobileFiltersOpen(false);
                }}
                className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                  active
                    ? "bg-primary/10 text-primary font-semibold"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                {Icon && <Icon className="h-3.5 w-3.5" />}
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Status filter */}
      <div className="space-y-2 border-t border-border pt-4">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</label>
        <div className="space-y-1">
          {[
            { value: "", label: "All Statuses" },
            { value: "new", label: "New" },
            { value: "accepted", label: "Accepted" },
            { value: "in_progress", label: "In Progress" },
            { value: "in_validation", label: "In Validation" },
            { value: "closed", label: "Closed" },
          ].map(opt => {
            const active = statusFilter === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setStatusFilter(opt.value);
                  setCurrentPage(1);
                  if (isMobile) setMobileFiltersOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                  active
                    ? "bg-primary/10 text-primary font-semibold"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <span>{opt.label}</span>
                {opt.value && (
                  <span
                    className={`h-2 w-2 rounded-full ${
                      opt.value === "new"
                        ? "bg-blue-500"
                        : opt.value === "accepted"
                          ? "bg-purple-500"
                          : opt.value === "in_progress"
                            ? "bg-amber-500"
                            : opt.value === "in_validation"
                              ? "bg-emerald-500"
                              : "bg-muted-foreground"
                    }`}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {isMobile && (
        <div className="pt-2 border-t border-border">
          <button
            type="button"
            onClick={() => setMobileFiltersOpen(false)}
            className="w-full rounded-lg bg-primary py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
          >
            Apply Filters
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
          <div>
            <h1 className="font-serif text-3xl font-bold tracking-tight">Help & Feedback</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Submit feature ideas, report bugs, and track the status of support tickets.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCreateModalOpen(true)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-90 transition-opacity self-start sm:self-auto"
          >
            <Plus className="h-4 w-4" />
            <span>New Request</span>
          </button>
        </div>

        {/* Mobile Filter Drawer Trigger */}
        <div className="md:hidden flex items-center justify-between">
          <Sheet open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                data-testid="mobile-filters-trigger"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground shadow-xs hover:bg-muted transition-colors"
              >
                <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
                <span>Filters</span>
                {hasActiveFilters && <span className="h-2 w-2 rounded-full bg-primary" />}
              </button>
            </SheetTrigger>
            <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto rounded-t-2xl p-6">
              <SheetHeader className="pb-2">
                <SheetTitle className="sr-only">Filters</SheetTitle>
                <SheetDescription className="sr-only">Filter feedback tickets</SheetDescription>
              </SheetHeader>
              {renderFilterControls(true)}
            </SheetContent>
          </Sheet>
        </div>

        {/* Layout Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Desktop Left Sidebar Filters */}
          <aside className="hidden md:block md:col-span-1 space-y-6">
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-6">
              {renderFilterControls(false)}
            </div>
          </aside>

          {/* Right Ticket List Area */}
          <section className="md:col-span-3 space-y-4">
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>
                Showing {filteredItems.length} {filteredItems.length === 1 ? "ticket" : "tickets"}
                {pagination.total > 0 && ` of ${pagination.total}`}
              </span>
              {isAdmin && <span className="font-semibold text-primary">Admin View Enabled</span>}
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, idx) => (
                  <div key={idx} className="h-28 rounded-xl border border-border bg-card p-5 animate-pulse" />
                ))}
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center bg-card/40 space-y-3">
                <div className="rounded-full bg-muted p-3 text-muted-foreground">
                  <Lightbulb className="h-6 w-6" />
                </div>
                <h3 className="text-base font-semibold">No feedback tickets found</h3>
                <p className="text-xs text-muted-foreground max-w-sm">
                  {hasActiveFilters
                    ? "No tickets match your current filters. Try resetting the filters."
                    : "No feedback or bug reports have been submitted yet."}
                </p>
                {hasActiveFilters ? (
                  <button
                    type="button"
                    onClick={handleClearFilters}
                    className="rounded-md border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-muted"
                  >
                    Clear Filters
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setCreateModalOpen(true)}
                    className="rounded-md bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
                  >
                    Submit First Request
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredItems.map(item => {
                  const statusInfo = statusStyles[item.status] || {
                    bg: "bg-muted",
                    text: "text-foreground",
                    border: "border-border",
                    label: item.status,
                  };

                  return (
                    <article
                      key={item.id}
                      onClick={() => handleCardClick(item)}
                      className="group cursor-pointer rounded-xl border border-border bg-card p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
                          >
                            {statusInfo.label}
                          </span>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            {item.feedback_type === "bug" ? (
                              <Bug className="h-3.5 w-3.5 text-rose-500" />
                            ) : (
                              <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                            )}
                            <span className="capitalize">{item.feedback_type.replace("_", " ")}</span>
                          </div>
                        </div>

                        <span className="text-[11px] text-muted-foreground">#{item.id}</span>
                      </div>

                      {/* Description truncated safely */}
                      <p className="mt-3 text-sm text-foreground line-clamp-2 leading-relaxed">{item.description}</p>

                      {/* Footer metadata */}
                      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-3 text-xs text-muted-foreground">
                        <div className="flex items-center gap-4">
                          <span className="flex items-center gap-1.5 font-medium text-foreground/80">
                            <UserIcon className="h-3 w-3" />
                            {item.user_display_name}
                            {isAdmin && item.user_email && (
                              <span className="text-muted-foreground font-normal">({item.user_email})</span>
                            )}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(item.created_at).toLocaleDateString()}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          {item.attachments && item.attachments.length > 0 && (
                            <span className="flex items-center gap-1 text-muted-foreground">
                              <Paperclip className="h-3.5 w-3.5" />
                              {item.attachments.length}
                            </span>
                          )}
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <MessageSquare className="h-3.5 w-3.5" />
                            {item.comments_count ?? item.comments?.length ?? 0}
                          </span>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}

            {/* Pagination Controls */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-between border-t border-border pt-4 text-xs">
                <button
                  type="button"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-3 py-1.5 font-semibold text-foreground hover:bg-muted disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </button>
                <span className="text-muted-foreground">
                  Page {currentPage} of {pagination.pages}
                </span>
                <button
                  type="button"
                  disabled={currentPage >= pagination.pages}
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, pagination.pages))}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-3 py-1.5 font-semibold text-foreground hover:bg-muted disabled:opacity-40"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </section>
        </div>
      </main>

      <Footer />

      {/* Creation Modal */}
      <FeedbackModal open={createModalOpen} onOpenChange={setCreateModalOpen} onSuccess={() => void fetchTickets()} />

      {/* Detail & Action Modal */}
      <FeedbackDetailModal
        item={selectedTicket}
        open={detailModalOpen}
        onOpenChange={open => {
          setDetailModalOpen(open);
          if (!open) setSelectedTicket(null);
        }}
        isAdmin={isAdmin}
        currentUserId={profile?.id}
        onUpdated={() => {
          void fetchTickets();
          if (selectedTicket) {
            void apiClient
              .get<{ data: FeedbackItemDetail }>(`/feedback/${selectedTicket.id}`)
              .then(res => setSelectedTicket(res.data.data))
              .catch(() => {});
          }
        }}
      />
    </div>
  );
}
