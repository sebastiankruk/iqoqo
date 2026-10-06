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

interface DeletionPendingNoticeProps {
  /** ISO 8601 expiry of the pending request, when known. */
  expiresAt: string | null;
}

/**
 * Banner shown while a deletion request is awaiting confirmation.
 *
 * Leads with the reassuring fact — the account is intact — before saying what is
 * pending and how to stop it. A user who opened their profile later and saw a
 * deletion notice without that framing would reasonably assume the worst.
 *
 * @param root0 - Component props
 * @param root0.expiresAt - ISO 8601 expiry of the pending request, when known
 * @returns The banner, or null when nothing is pending
 */
export function DeletionPendingNotice({ expiresAt }: DeletionPendingNoticeProps) {
  if (!expiresAt) return null;

  const expiresLabel = new Date(expiresAt).toLocaleString();

  return (
    <div
      role="status"
      data-testid="deletion-pending-notice"
      className="p-4 border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 rounded-lg space-y-2"
    >
      <div className="space-y-1">
        <p className="font-semibold text-amber-900 dark:text-amber-200">Account deletion is waiting for you</p>
        <p className="text-sm text-amber-900 dark:text-amber-200">
          Your account and all your data are still here and nothing has been deleted. We emailed a confirmation link to
          your verified address.
        </p>
        <p className="text-xs text-amber-800 dark:text-amber-300">
          The link can be used once and expires at {expiresLabel}. If you did not request this, or have changed your
          mind, simply do nothing — the request becomes unusable on its own and your account is unaffected. You can also
          change your email address or request a fresh link, which cancels this one.
        </p>
      </div>
    </div>
  );
}
