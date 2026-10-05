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

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { confirmAccountDeletion, fetchCsrfToken, getDeletionConfirmationState } from "@/lib/api/account";

type Phase = "loading" | "ready" | "unusable" | "unauthenticated" | "deleted" | "failed";

/**
 * Confirmation screen for an emailed account-deletion link.
 *
 * Loads read-only. The account is removed only on an explicit button press, which
 * requires an authenticated session for that account and CSRF proof. This URL is
 * fetched automatically by mail clients and security scanners within seconds of
 * the message arriving, so a GET must be indistinguishable from a human merely
 * reading the page.
 *
 * The button is styled destructive and the consequence is spelled out in full,
 * because this is the one action in the product that cannot be undone or
 * recovered by the owner.
 *
 * @returns {JSX.Element} The confirmation UI
 */
export function AccountDeletion() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") ?? "";

  // No token in the URL is a render-time fact, not something to fetch. Deriving it
  // here keeps the effect free of a synchronous setState, and means a mistyped
  // link renders the right thing without a round trip.
  const [phase, setPhase] = useState<Phase>(token ? "loading" : "unusable");
  const [email, setEmail] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      await fetchCsrfToken();
      const state = await getDeletionConfirmationState(token);
      if (!state.usable) {
        setPhase("unusable");
        return;
      }
      setEmail(state.email ?? null);
      setPhase("ready");
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setPhase(status === 401 ? "unauthenticated" : "unusable");
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    // A promise chain rather than `await` in the effect body: the setState lands in
    // a callback, which is where a response belongs, and `cancelled` stops a slow
    // response from updating a component the user has already navigated away from.
    let cancelled = false;
    fetchCsrfToken()
      .then(() => getDeletionConfirmationState(token))
      .then(state => {
        if (cancelled) return;
        if (!state.usable) {
          setPhase("unusable");
          return;
        }
        setEmail(state.email ?? null);
        setPhase("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const status = (err as { response?: { status?: number } })?.response?.status;
        setPhase(status === 401 ? "unauthenticated" : "unusable");
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await confirmAccountDeletion(token);
      setPhase("deleted");
      toast.success("Your account has been deleted.");
      // The session cookie is cleared by the API response; push the user home so
      // no cached view of the profile lingers.
      router.push("/");
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 400) {
        setPhase("unusable");
        return;
      }
      setPhase("failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (phase === "loading") {
    return <div className="p-8 text-center text-muted-foreground">Checking your confirmation link...</div>;
  }

  if (phase === "deleted") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="delete-done">
        <h1 className="text-xl font-semibold">Your account has been deleted</h1>
        <p className="text-sm text-muted-foreground">
          Everything associated with it has been removed, and you are signed out everywhere. This cannot be undone.
        </p>
        <Button asChild>
          <Link href="/">Go to the home page</Link>
        </Button>
      </section>
    );
  }

  if (phase === "failed") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="delete-failed">
        <h1 className="text-xl font-semibold">Deletion could not be completed</h1>
        <p className="text-sm text-muted-foreground">
          Nothing has been changed and your account is intact. Please try again.
        </p>
        <Button onClick={() => void load()}>Try again</Button>
      </section>
    );
  }

  if (phase === "unauthenticated") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="delete-unauthenticated">
        <h1 className="text-xl font-semibold">Sign in to continue</h1>
        <p className="text-sm text-muted-foreground">
          This link works only for the account it was sent to. Sign in as that account, then open the link again. Your
          session on a different account is not enough.
        </p>
        <Button asChild>
          <Link href="/login">Go to sign in</Link>
        </Button>
      </section>
    );
  }

  if (phase === "unusable") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="delete-unusable">
        <h1 className="text-xl font-semibold">This deletion link is no longer valid</h1>
        <p className="text-sm text-muted-foreground">
          It may have expired, already been used, or been replaced by a newer request.{" "}
          <strong>Nothing has been deleted.</strong> You can request a new link from your profile, or close this page.
        </p>
        <p className="text-xs text-muted-foreground">
          If you did not request this, no action is needed and nothing has changed on your account.
        </p>
        <Button asChild>
          <Link href="/profile">Back to your profile</Link>
        </Button>
      </section>
    );
  }

  return (
    <section className="p-6 border border-destructive/50 rounded-lg bg-card space-y-4" data-testid="delete-ready">
      <h1 className="text-xl font-semibold">Permanently delete your account</h1>
      <div className="p-3 border border-destructive/50 bg-destructive/5 rounded-md text-sm space-y-1">
        <p className="font-semibold">This cannot be undone.</p>
        <p>
          Deleting <strong data-testid="delete-target-email">{email}</strong> permanently removes your profile, your
          library, your notes, your collections and your lending history. There is no grace period and no recovery.
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        To confirm, you will be signed out everywhere and this link will stop working.
      </p>
      <div className="flex gap-2">
        <Button variant="destructive" onClick={handleConfirm} disabled={isSubmitting}>
          {isSubmitting ? "Deleting..." : "Yes, permanently delete my account"}
        </Button>
        <Button variant="outline" asChild>
          <Link href="/profile">Cancel</Link>
        </Button>
      </div>
      <hr className="my-2" />
      <p className="text-xs text-muted-foreground">
        This link expires in 30 minutes and works only once. If you did not request this, close this page — nothing has
        happened.
      </p>
      <p className="text-xs text-muted-foreground">
        Email confirmation proves you can receive mail at this address. It is not a second sign-in, and it is not
        treated as one.
      </p>
    </section>
  );
}
