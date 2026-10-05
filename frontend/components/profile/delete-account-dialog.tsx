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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { requestAccountDeletion } from "@/lib/api/account";

interface DeleteAccountDialogProps {
  /** Whether the account currently has a verified address. */
  emailVerified: boolean;
  /** Whether a deletion request is already awaiting confirmation. */
  pending: boolean;
  /** Called after a request is accepted, so the parent can show pending state. */
  onRequested: () => void | Promise<void>;
}

/**
 * Initiate account deletion.
 *
 * This button never deletes anything. It creates a pending request and sends a
 * confirmation link to the verified address; the account and its data are
 * untouched until that link is opened and the confirmation submitted. The copy
 * states that plainly, because a control that looks destructive but quietly only
 * sends a mail is the kind of mismatch that erodes trust in every other
 * destructive control in the product.
 *
 * The two ways the request cannot proceed are handled distinctly rather than as
 * one generic failure: an unverified address is fixed by verifying it, and an
 * instance that cannot send mail is fixed by an administrator. Collapsing both
 * into "something went wrong" would send the user looking in the wrong place.
 *
 * @param root0 - Component props
 * @param root0.emailVerified - Whether the account currently has a verified address
 * @param root0.pending - Whether a deletion request is already awaiting confirmation
 * @param root0.onRequested - Called after a request is accepted, so the parent can show pending state
 * @returns The dialog trigger
 */
export function DeleteAccountDialog({ emailVerified, pending, onRequested }: DeleteAccountDialogProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRequest = async () => {
    setIsSubmitting(true);
    try {
      await requestAccountDeletion();
      setOpen(false);
      toast.success("Check your verified email address for a confirmation link. Nothing has been deleted yet.");
      await onRequested();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not start the deletion request";
      if (message.toLowerCase().includes("verify")) {
        toast.error(message);
        setOpen(false);
      } else {
        // Kept open so the warning is read in context rather than flashed and
        // dismissed alongside a toast the user is already looking away from.
        toast.error(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <Button variant="destructive" onClick={() => setOpen(true)} disabled={pending}>
        Delete Account
      </Button>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Permanently delete your account?</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3 text-sm">
              <p>
                This is permanent. Your profile, library, notes, collections and lending history will be removed and
                cannot be recovered. There is no grace period once you confirm.
              </p>
              {!emailVerified && (
                <p className="font-medium text-amber-600 dark:text-amber-500">
                  Your email address is not verified yet. Verify it first — there is no way to delete an account without
                  a verified address, because the confirmation link would go to an address we cannot prove belongs to
                  you.
                </p>
              )}
              <p>
                Nothing is deleted now. We will email a confirmation link, and the account is only removed after you
                open it and confirm. You can do nothing and your account will be exactly as it is.
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>Keep my account</AlertDialogCancel>
          <AlertDialogAction
            onClick={event => {
              // Keep the dialog mounted while the request is in flight, otherwise
              // it unmounts on click and the user sees no pending state at all.
              event.preventDefault();
              void handleRequest();
            }}
            disabled={isSubmitting || !emailVerified}
          >
            {isSubmitting ? "Sending..." : "Email me a confirmation link"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
