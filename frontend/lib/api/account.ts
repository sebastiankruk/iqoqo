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

import { apiClient } from "@/lib/api/client";

/**
 * Name of the double-submit CSRF cookie the backend sets on
 * `GET /api/account/csrf`.
 *
 * Read from `document.cookie` rather than kept in React state, because the
 * protection only works if the value the client sends is the one the *browser*
 * holds. Holding it in state would make the two drift the moment the cookie
 * expired or was rotated, and the request would be refused for no visible
 * reason.
 */
const CSRF_COOKIE_NAME = "iqoqo_csrf";

/** Matches the backend's `CSRF_FIELD_NAME`. */
const CSRF_FIELD_NAME = "csrf_token";

/** The header the backend reads when a request carries a cookie credential. */
const CSRF_HEADER = "X-CSRF-Token";

/**
 * Read a cookie value from `document.cookie`.
 *
 * @param name - Cookie name to read
 * @returns The decoded value, or an empty string when the cookie is absent
 */
function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie
    .split(";")
    .map(part => part.trim())
    .find(part => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : "";
}

/**
 * Fetch a CSRF token and return it.
 *
 * The response also sets the `iqoqo_csrf` cookie; the returned value is the same
 * string, which is what the mutation helpers below echo back in the header.
 *
 * @returns {Promise<string>} A signed, unexpired CSRF token
 */
export async function fetchCsrfToken(): Promise<string> {
  const res = await apiClient.get<{ success: boolean; data: { csrf_token: string } }>("/account/csrf");
  return res.data.data.csrf_token;
}

/**
 * Perform a state-changing request with CSRF proof attached.
 *
 * The header is only sent when a CSRF cookie is actually present. A bearer-token
 * client has no cookie to prove anything about and the backend does not require
 * proof for it, so sending a header with an empty value would only produce a
 * confusing 403 in a context where none was asked for.
 *
 * @param method - HTTP verb to use
 * @param path - API path
 * @param body - Optional JSON body
 * @returns The parsed response
 */
async function csrfMutation<T>(method: "post" | "put", path: string, body?: unknown): Promise<T> {
  const csrf = readCookie(CSRF_COOKIE_NAME);
  const res = await apiClient.request<T>({
    method: method.toUpperCase(),
    url: path,
    data: body,
    ...(csrf ? { headers: { [CSRF_HEADER]: csrf } } : {}),
  });
  return res.data;
}

/**
 * Request an email-verification link for the current address.
 *
 * The response is deliberately identical whether or not the address was already
 * verified, so it discloses nothing about the account to the caller.
 *
 * @returns {Promise<void>} Resolves when the request has been accepted
 */
export async function requestEmailVerification(): Promise<void> {
  await csrfMutation("post", "/account/email/verification-request");
}

/**
 * Change the account's email address.
 *
 * Clears verification and invalidates outstanding tokens server-side, then sends
 * a verification link to the new address. `verification_email_sent` reports
 * whether that link could actually go out — an address change still applies when
 * it could not, so the caller must surface that rather than implying failure.
 *
 * @param email - The new address
 * @returns The updated owner-facing profile fragment
 */
export async function changeAccountEmail(
  email: string
): Promise<{ email: string; email_verified: boolean; verification_email_sent: boolean }> {
  const res = await csrfMutation<{
    success: boolean;
    data: { email: string; email_verified: boolean; verification_email_sent: boolean };
  }>("put", "/account/email", { email });
  return res.data;
}

/**
 * Begin account deletion.
 *
 * Changes nothing. A confirmation link is sent to the verified address and the
 * user must open it and submit the confirmation while signed in.
 *
 * @returns {Promise<void>} Resolves once the request is recorded
 */
export async function requestAccountDeletion(): Promise<void> {
  await csrfMutation("post", "/account/deletion/request");
}

/**
 * Read whether a deletion request is awaiting confirmation.
 *
 * @returns {Promise<{ pending: boolean; expires_at: string | null }>} The pending state
 */
export async function getDeletionStatus(): Promise<{ pending: boolean; expires_at: string | null }> {
  const res = await apiClient.get<{ success: boolean; data: { pending: boolean; expires_at: string | null } }>(
    "/account/deletion/status"
  );
  return res.data.data;
}

export { CSRF_FIELD_NAME };

/** Shape returned by the verification-state endpoint. */
export interface EmailVerificationState {
  usable: boolean;
  /** Present when `usable`, so the screen can name the address being confirmed. */
  email?: string | null;
  /** True when the address is already verified, which is not a failure. */
  already_verified?: boolean;
}

/**
 * Ask whether a verification token can be spent.
 *
 * Read-only by contract: this is called with the URL that arrives by email, and
 * mail clients and scanners fetch it automatically.
 *
 * @param token - The raw token from the link
 * @returns Whether the link is usable, and for which address
 */
export async function getEmailVerificationState(token: string): Promise<EmailVerificationState> {
  await fetchCsrfToken();
  const res = await apiClient.get<{ success: boolean; data: EmailVerificationState }>("/account/email/verify", {
    params: { token },
  });
  return res.data.data;
}

/**
 * Consume a verification token.
 *
 * @param token - The raw token from the link
 * @returns The confirmed address
 */
export async function confirmEmailVerification(token: string): Promise<{ email: string; verified: boolean }> {
  const res = await csrfMutation<{ success: boolean; data: { email: string; verified: boolean } }>(
    "post",
    "/account/email/verify",
    { token }
  );
  return res.data;
}

/** Shape returned by the deletion-confirmation endpoint. */
export interface DeletionConfirmationState {
  usable: boolean;
  email?: string | null;
}

/**
 * Ask whether a deletion token can be spent, without spending it.
 *
 * @param token - The raw token from the link
 * @returns Whether the link is usable, and for which account
 */
export async function getDeletionConfirmationState(token: string): Promise<DeletionConfirmationState> {
  await fetchCsrfToken();
  const res = await apiClient.get<{ success: boolean; data: DeletionConfirmationState }>("/account/deletion/confirm", {
    params: { token },
  });
  return res.data.data;
}

/**
 * Consume a deletion token and delete the account.
 *
 * The response clears the session cookie, so the caller should navigate away
 * rather than assume it is still authenticated.
 *
 * @param token - The raw token from the link
 * @returns Confirmation that the account was removed
 */
export async function confirmAccountDeletion(token: string): Promise<{ deleted: boolean }> {
  const res = await csrfMutation<{ success: boolean; data: { deleted: boolean } }>(
    "post",
    "/account/deletion/confirm",
    {
      token,
    }
  );
  return res.data;
}
