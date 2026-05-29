// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

"use client";

import { useProfile, useLoanRequests, useResolveLoan } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, X, Shield, Clock, User, BookOpen } from "lucide-react";

/**
 * AdminLendingPage component renders the custodian lending dashboard
 * where owners can coordinate and approve/reject book loan requests.
 *
 * @returns {React.JSX.Element} The admin lending dashboard element.
 */
export default function AdminLendingPage() {
  const { data: profile, isLoading: isProfileLoading } = useProfile();
  const { data: requests = [], isLoading: isLoadingRequests } = useLoanRequests();
  const resolveLoanMutation = useResolveLoan();
  const router = useRouter();

  // Protect page
  useEffect(() => {
    if (!isProfileLoading && !profile) {
      router.push("/login");
    }
  }, [profile, isProfileLoading, router]);

  const handleResolve = async (requestId: number, action: "approve" | "reject") => {
    try {
      await resolveLoanMutation.mutateAsync({ requestId, action });
    } catch (err) {
      console.error("Failed to resolve loan request:", err);
    }
  };

  if (isProfileLoading || !profile) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground animate-pulse">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight font-serif text-foreground">
              Lending Administration
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Approve and coordinate loan requests from other users borrowing from your collection.
            </p>
          </div>
          <div className="flex items-center gap-2 bg-secondary/40 border border-border px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Shield className="h-3.5 w-3.5" /> Custodian Mode
          </div>
        </div>

        {isLoadingRequests ? (
          <div className="flex items-center justify-center py-20">
            <p className="text-muted-foreground animate-pulse">Loading requests...</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-16 text-center">
            <BookOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="font-serif text-lg font-bold text-foreground">No Loan Requests</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              When other users browse your catalog and request to loan your public items, they will appear here.
            </p>
          </div>
        ) : (
          <Card className="border border-border/80 shadow-md">
            <CardHeader className="border-b border-border/40 pb-6">
              <CardTitle className="font-serif text-xl font-bold text-foreground">Active Loan Requests</CardTitle>
              <CardDescription>Coordinate and approve/reject pending peer-to-peer book loans.</CardDescription>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-border/40">
              {requests.map(req => {
                const isPending = req.status === "pending";
                const isApproved = req.status === "approved";

                return (
                  <div
                    key={req.id}
                    data-testid={`request-row-${req.item_id}`}
                    className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-muted/10 transition-colors"
                  >
                    <div className="space-y-2 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-serif font-bold text-base text-foreground leading-snug truncate">
                          {req.item_title}
                        </h4>
                        <span
                          data-testid="status-cell"
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold leading-none ${
                            isApproved
                              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                              : isPending
                                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                                : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                          }`}
                        >
                          {isApproved ? "Lent" : isPending ? "Pending" : "Rejected"}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <User className="h-3.5 w-3.5" /> Requester:{" "}
                          <strong className="text-foreground">{req.requester_name}</strong>
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" /> Requested:{" "}
                          <strong>
                            {new Intl.DateTimeFormat("en-US", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            }).format(new Date(req.created_at))}
                          </strong>
                        </span>
                      </div>

                      {req.notes && (
                        <p className="text-xs text-muted-foreground bg-secondary/40 border border-border/30 rounded-lg p-2.5 max-w-xl mt-2">
                          <strong>Note:</strong> &ldquo;{req.notes}&rdquo;
                        </p>
                      )}
                    </div>

                    {isPending && (
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          aria-label="Approve Loan"
                          size="sm"
                          onClick={() => handleResolve(req.id, "approve")}
                          disabled={resolveLoanMutation.isPending}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1.5"
                        >
                          <Check className="h-4 w-4" /> Approve
                        </Button>
                        <Button
                          aria-label="Reject Loan"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleResolve(req.id, "reject")}
                          disabled={resolveLoanMutation.isPending}
                          className="text-rose-600 hover:text-rose-700 hover:bg-rose-500/10 font-semibold flex items-center gap-1.5"
                        >
                          <X className="h-4 w-4" /> Reject
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}
      </main>

      <Footer />
    </div>
  );
}
