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
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { changeAccountEmail, requestEmailVerification } from "@/lib/api/account";

interface EmailVerificationCardProps {
  /** The account's current address. */
  email: string;
  /** Whether the backend considers the current address verified. */
  verified: boolean;
  /** Called after a change or verification request so the parent can refetch. */
  onChanged: () => void | Promise<void>;
}

/**
 * Email verification state and address change.
 *
 * The copy is careful about what verification is and is not: it confirms
 * mailbox control, and it says so. Calling it "verification of your identity"
 * would overstate it, because possession of the mailbox is not proof of who is
 * reading this page — the account owner may have handed over a password. The
 * deletion flow leans on this distinction, and the UI should not contradict it.
 *
 * @param root0 - Component props
 * @param root0.email - The account's current address
 * @param root0.verified - Whether the backend considers the current address verified
 * @param root0.onChanged - Called after a change or verification request so the parent can refetch
 * @returns The card
 */
export function EmailVerificationCard({ email, verified, onChanged }: EmailVerificationCardProps) {
  const [draftEmail, setDraftEmail] = useState(email);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);

  const handleRequestVerification = async () => {
    setIsRequesting(true);
    try {
      await requestEmailVerification();
      toast.success("If the address needs verification, a link is on its way.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not send the verification email";
      // A misconfigured instance cannot send mail at all. That is an operator
      // problem, so the message says so instead of implying the user did
      // something wrong.
      toast.error(message);
    } finally {
      setIsRequesting(false);
    }
  };

  const handleChangeEmail = async () => {
    const candidate = draftEmail.trim();
    if (!candidate || candidate === email.trim()) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    try {
      const result = await changeAccountEmail(candidate);
      setIsEditing(false);
      if (result.verification_email_sent) {
        toast.success("Email address updated. Check it for a confirmation link.");
      } else {
        // The address did change. Saying otherwise would send the user back to
        // re-enter it and might lead them to cancel a change that was applied.
        toast.warning(
          "Email address updated, but the confirmation email could not be sent. Ask your administrator to configure mail."
        );
      }
      await onChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not change the email address");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setDraftEmail(email);
    setIsEditing(false);
  };

  return (
    <div className="p-4 border rounded-lg bg-card space-y-4" data-testid="email-verification-card">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Email Address</h2>
        <p className="text-sm text-muted-foreground">
          Your account needs a verified email address before you can delete it.
        </p>
      </div>

      {isEditing ? (
        <div className="space-y-3">
          <div>
            <label htmlFor="change-email" className="block text-sm font-medium text-foreground">
              New email address
            </label>
            <input
              id="change-email"
              type="email"
              value={draftEmail}
              onChange={e => setDraftEmail(e.target.value)}
              autoComplete="email"
              className="mt-1 flex h-10 w-full max-w-sm rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Changing your address clears its verification and cancels any deletion request already waiting for
            confirmation.
          </p>
          <div className="flex gap-2">
            <Button onClick={handleChangeEmail} disabled={isSaving || !draftEmail.trim()}>
              {isSaving ? "Saving..." : "Save address"}
            </Button>
            <Button variant="outline" onClick={handleCancelEdit} disabled={isSaving}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <p className="font-medium" data-testid="account-email">
              {email}
            </p>
            {verified ? (
              <p className="text-xs text-muted-foreground" data-testid="email-verified-state">
                Verified — this address can receive mail for your account.
              </p>
            ) : (
              <>
                <p
                  className="text-xs font-medium text-amber-600 dark:text-amber-500"
                  data-testid="email-unverified-state"
                >
                  Not verified. We have not confirmed you can receive mail here.
                </p>
                <p className="text-xs text-muted-foreground">
                  Confirming shows we can reach this mailbox. It is not a second sign-in, and it is not treated as one.
                </p>
              </>
            )}
          </div>
          <div className="flex gap-2">
            {!verified && (
              <Button variant="outline" onClick={handleRequestVerification} disabled={isRequesting}>
                {isRequesting ? "Sending..." : "Send verification link"}
              </Button>
            )}
            <Button variant="ghost" onClick={() => setIsEditing(true)}>
              Change address
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
