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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccountVerification } from "@/components/account/account-verification";
import { AccountDeletion } from "@/components/account/account-deletion";
import {
  confirmAccountDeletion,
  confirmEmailVerification,
  fetchCsrfToken,
  getDeletionConfirmationState,
  getEmailVerificationState,
} from "@/lib/api/account";

/**
 * The two emailed confirmation screens.
 *
 * These stand where the deleted backend appearance tests did. The screens moved
 * out of Flask precisely because a hand-styled page arriving by email is
 * indistinguishable from a phishing page, so the properties worth pinning are the
 * ones a user depends on: that the account is named, that the consequence is
 * spelled out, and that nothing happens until the button is pressed.
 *
 * All imports are at module scope. Vitest hoists `vi.mock`, so a factory closing
 * over an identifier declared inside a test body reads it as undefined at
 * registration time.
 */
vi.mock("@/lib/api/account", () => ({
  fetchCsrfToken: vi.fn(),
  getEmailVerificationState: vi.fn(),
  confirmEmailVerification: vi.fn(),
  getDeletionConfirmationState: vi.fn(),
  confirmAccountDeletion: vi.fn(),
  requestEmailVerification: vi.fn(),
  changeAccountEmail: vi.fn(),
  requestAccountDeletion: vi.fn(),
  getDeletionStatus: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

/** Mutable token backing the `useSearchParams` mock below. */
const searchState = { token: "" };

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(searchState.token ? `token=${searchState.token}` : ""),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const user = userEvent.setup();

describe("AccountVerification", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchState.token = "abc123";
    vi.mocked(fetchCsrfToken).mockResolvedValue("tok");
  });

  it("confirms nothing on load", async () => {
    // The property the whole screen exists for: this URL is fetched by scanners
    // and previewers within seconds of the mail landing.
    vi.mocked(getEmailVerificationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountVerification />);

    await waitFor(() => expect(screen.getByTestId("verify-ready")).toBeInTheDocument());
    expect(confirmEmailVerification).not.toHaveBeenCalled();
  });

  it("names the address being confirmed", async () => {
    vi.mocked(getEmailVerificationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountVerification />);

    await waitFor(() => expect(screen.getByTestId("verify-target-email")).toHaveTextContent("me@example.com"));
  });

  it("confirms only when the button is pressed", async () => {
    vi.mocked(getEmailVerificationState).mockResolvedValue({ usable: true, email: "me@example.com" });
    vi.mocked(confirmEmailVerification).mockResolvedValue({ email: "me@example.com", verified: true });

    render(<AccountVerification />);
    await waitFor(() => expect(screen.getByTestId("verify-ready")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Confirm this address" }));

    await waitFor(() => expect(confirmEmailVerification).toHaveBeenCalledWith("abc123"));
    expect(await screen.findByTestId("verify-confirmed")).toBeInTheDocument();
  });

  it("explains that verification is not a sign-in", async () => {
    vi.mocked(getEmailVerificationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountVerification />);

    await waitFor(() => expect(screen.getByTestId("verify-ready")).toBeInTheDocument());
    expect(screen.getByText(/does not sign you in/i)).toBeInTheDocument();
  });

  it("offers sign-in when the session is not the right account", async () => {
    vi.mocked(getEmailVerificationState).mockRejectedValue({ response: { status: 401 } });

    render(<AccountVerification />);

    expect(await screen.findByTestId("verify-unauthenticated")).toBeInTheDocument();
    expect(confirmEmailVerification).not.toHaveBeenCalled();
  });

  it("distinguishes an already-verified address from a dead link", async () => {
    vi.mocked(getEmailVerificationState).mockResolvedValue({ usable: false, already_verified: true });

    render(<AccountVerification />);

    expect(await screen.findByTestId("verify-already")).toBeInTheDocument();
    // Not framed as a failure: the user's address is fine.
    expect(screen.queryByTestId("verify-unusable")).not.toBeInTheDocument();
  });

  it("refuses to act when the token is missing entirely", async () => {
    searchState.token = "";
    render(<AccountVerification />);

    expect(await screen.findByTestId("verify-unusable")).toBeInTheDocument();
    expect(getEmailVerificationState).not.toHaveBeenCalled();
  });
});

describe("AccountDeletion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchState.token = "del123";
    vi.mocked(fetchCsrfToken).mockResolvedValue("tok");
  });

  it("deletes nothing on load", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountDeletion />);

    await waitFor(() => expect(screen.getByTestId("delete-ready")).toBeInTheDocument());
    expect(confirmAccountDeletion).not.toHaveBeenCalled();
  });

  it("states that the deletion cannot be undone", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountDeletion />);

    await waitFor(() => expect(screen.getByTestId("delete-ready")).toBeInTheDocument());
    expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument();
    expect(screen.getByText(/no grace period and no recovery/i)).toBeInTheDocument();
  });

  it("names the account about to be deleted", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });

    render(<AccountDeletion />);

    await waitFor(() => expect(screen.getByTestId("delete-target-email")).toHaveTextContent("me@example.com"));
  });

  it("deletes only when the button is pressed", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });
    vi.mocked(confirmAccountDeletion).mockResolvedValue({ deleted: true });

    render(<AccountDeletion />);
    await waitFor(() => expect(screen.getByTestId("delete-ready")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /permanently delete my account/i }));

    await waitFor(() => expect(confirmAccountDeletion).toHaveBeenCalledWith("del123"));
    expect(await screen.findByTestId("delete-done")).toBeInTheDocument();
  });

  it("says nothing was deleted when the link is spent", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: false });

    render(<AccountDeletion />);

    expect(await screen.findByTestId("delete-unusable")).toBeInTheDocument();
    // The reassurance has to be unmissable: a user arriving here worried they
    // deleted their account by clicking a preview.
    expect(screen.getByText(/Nothing has been deleted/i)).toBeInTheDocument();
  });

  it("offers sign-in for a token belonging to another account", async () => {
    vi.mocked(getDeletionConfirmationState).mockRejectedValue({ response: { status: 401 } });

    render(<AccountDeletion />);

    expect(await screen.findByTestId("delete-unauthenticated")).toBeInTheDocument();
    expect(screen.getByText(/different account is not enough/i)).toBeInTheDocument();
  });

  it("reports a failed deletion without claiming success", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });
    vi.mocked(confirmAccountDeletion).mockRejectedValue(new Error("boom"));

    render(<AccountDeletion />);
    await waitFor(() => expect(screen.getByTestId("delete-ready")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /permanently delete my account/i }));

    expect(await screen.findByTestId("delete-failed")).toBeInTheDocument();
    expect(screen.queryByTestId("delete-done")).not.toBeInTheDocument();
  });

  it("treats a rejected token as unusable rather than failed", async () => {
    vi.mocked(getDeletionConfirmationState).mockResolvedValue({ usable: true, email: "me@example.com" });
    vi.mocked(confirmAccountDeletion).mockRejectedValue({ response: { status: 400 } });

    render(<AccountDeletion />);
    await waitFor(() => expect(screen.getByTestId("delete-ready")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /permanently delete my account/i }));

    expect(await screen.findByTestId("delete-unusable")).toBeInTheDocument();
  });
});
