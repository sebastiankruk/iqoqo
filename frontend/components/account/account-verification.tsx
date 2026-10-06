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

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { fetchCsrfToken, confirmEmailVerification, getEmailVerificationState } from "@/lib/api/account";

type Phase = "loading" | "ready" | "unusable" | "already" | "unauthenticated" | "confirmed";

/**
 * Confirmation screen for an emailed email-verification link.
 *
 * Renders nothing on load beyond the token's usability, because this URL is
 * fetched automatically by mail clients and link scanners within seconds of the
 * mail landing. Only the button mutates anything.
 *
 * The signed-out branch matters as much as the happy one: a verification token
 * proves mailbox control, not identity, so it cannot verify an address on its own.
 * The user has to be signed in as the account it was sent to.
 *
 * @returns {JSX.Element} The confirmation UI
 */
export function AccountVerification() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  // No token in the URL is a render-time fact, not something to fetch. Deriving it
  // here keeps the effect free of a synchronous setState, and means a mistyped
  // link renders the right thing without a round trip.
  const [phase, setPhase] = useState<Phase>(token ? "loading" : "unusable");
  const [email, setEmail] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;

    // A promise chain rather than `await` in the effect body: the setState lands in
    // a callback, which is where a response belongs, and `cancelled` stops a slow
    // response from updating a component the user has already navigated away from.
    let cancelled = false;
    fetchCsrfToken()
      .then(() => getEmailVerificationState(token))
      .then(state => {
        if (cancelled) return;
        if (!state.usable) {
          setPhase(state.already_verified ? "already" : "unusable");
          return;
        }
        setEmail(state.email ?? null);
        setPhase("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // A 401 here means the token may be fine but this session is not the right
        // account, so offer sign-in rather than calling the link invalid.
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
      await confirmEmailVerification(token);
      setPhase("confirmed");
      toast.success("Email address confirmed.");
    } catch {
      setPhase("unusable");
      toast.error("That confirmation link could not be used. Request a new one from your profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (phase === "loading") {
    return <div className="p-8 text-center text-muted-foreground">Checking your confirmation link...</div>;
  }

  if (phase === "confirmed") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="verify-confirmed">
        <h1 className="text-xl font-semibold">Email address confirmed</h1>
        <p className="text-sm text-muted-foreground">
          {email ? `${email} can now receive mail for your account.` : "Your account address is now confirmed."}
        </p>
        <Button asChild>
          <Link href="/profile">Back to your profile</Link>
        </Button>
      </section>
    );
  }

  if (phase === "already") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="verify-already">
        <h1 className="text-xl font-semibold">Already confirmed</h1>
        <p className="text-sm text-muted-foreground">This address is already verified. Nothing more to do.</p>
        <Button asChild>
          <Link href="/profile">Back to your profile</Link>
        </Button>
      </section>
    );
  }

  if (phase === "unauthenticated") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="verify-unauthenticated">
        <h1 className="text-xl font-semibold">Sign in to continue</h1>
        <p className="text-sm text-muted-foreground">
          This link works only for the account it was sent to. Sign in as that account, then open the link again.
        </p>
        <Button asChild>
          <Link href="/login">Go to sign in</Link>
        </Button>
      </section>
    );
  }

  if (phase === "unusable") {
    return (
      <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="verify-unusable">
        <h1 className="text-xl font-semibold">This confirmation link is no longer valid</h1>
        <p className="text-sm text-muted-foreground">
          It may have expired, already been used, or been replaced by a newer request. Request a new one from your
          profile under <strong>Email Address</strong>.
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
    <section className="p-6 border rounded-lg bg-card space-y-4" data-testid="verify-ready">
      <h1 className="text-xl font-semibold">Confirm your email address</h1>
      <p className="text-sm text-muted-foreground">
        You are confirming <strong data-testid="verify-target-email">{email}</strong> as the address for your iQoQo
        account.
      </p>
      <p className="text-xs text-muted-foreground">
        Confirming shows that you can receive mail at this address. It does not sign you in and does not change anything
        else.
      </p>
      <div className="flex gap-2">
        <Button variant="destructive" onClick={handleConfirm} disabled={isSubmitting}>
          {isSubmitting ? "Confirming..." : "Confirm this address"}
        </Button>
        <Button variant="outline" asChild>
          <Link href="/profile">Cancel</Link>
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">This link can be used once, and expires in 24 hours.</p>
    </section>
  );
}
