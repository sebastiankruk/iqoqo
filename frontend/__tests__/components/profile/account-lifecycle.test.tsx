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
import { EmailVerificationCard } from "@/components/profile/email-verification-card";
import { DeleteAccountDialog } from "@/components/profile/delete-account-dialog";
import { DeletionPendingNotice } from "@/components/profile/deletion-pending-notice";
import { changeAccountEmail, requestEmailVerification, requestAccountDeletion } from "@/lib/api/account";
import { toast } from "sonner";

// Declared at module scope, not inside a test body. Vitest hoists `vi.mock`, so
// a factory that closes over an import declared later reads it as undefined at
// mock-registration time -- the classic hoisting race.
vi.mock("@/lib/api/account", () => ({
  requestEmailVerification: vi.fn(),
  changeAccountEmail: vi.fn(),
  requestAccountDeletion: vi.fn(),
  getDeletionStatus: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

/** Helper to render with user-event already typed. */
const user = userEvent.setup();

describe("EmailVerificationCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("tells the user their address is unverified and offers a link", () => {
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={vi.fn()} />);

    expect(screen.getByTestId("email-unverified-state")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send verification link" })).toBeInTheDocument();
    // The destructive control must not read as available while unverified.
    expect(screen.queryByTestId("email-verified-state")).not.toBeInTheDocument();
  });

  it("does not offer a verification link when already verified", () => {
    render(<EmailVerificationCard email="me@iqoqo.local" verified onChanged={vi.fn()} />);

    expect(screen.getByTestId("email-verified-state")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send verification link" })).not.toBeInTheDocument();
  });

  it("does not tell a verified user that verification is still required", () => {
    // Regression. A static subtitle read "Your account needs a verified email
    // address before you can delete it" directly above "Verified". The card
    // exists to answer whether the account can be deleted, and it answered both
    // ways at once.
    render(<EmailVerificationCard email="me@iqoqo.local" verified onChanged={vi.fn()} />);

    expect(screen.getByTestId("email-card-subtitle")).not.toHaveTextContent(/needs a verified email address/i);
    expect(screen.getByTestId("email-card-subtitle")).toHaveTextContent(/confirmation link/i);
  });

  it("tells an unverified user that verification is required", () => {
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={vi.fn()} />);

    expect(screen.getByTestId("email-card-subtitle")).toHaveTextContent(/needs a verified email address/i);
  });

  it("calls the API when requesting a verification link", async () => {
    vi.mocked(requestEmailVerification).mockResolvedValue(undefined);
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Send verification link" }));

    await waitFor(() => expect(requestEmailVerification).toHaveBeenCalledTimes(1));
    expect(toast.success).toHaveBeenCalled();
  });

  it("warns rather than failing when the address changed but the mail did not send", async () => {
    // The server applied the change and then failed to send. Reporting this as a
    // plain error would send the user back to re-enter an address that is
    // already changed.
    vi.mocked(changeAccountEmail).mockResolvedValue({
      email: "new@iqoqo.local",
      email_verified: false,
      verification_email_sent: false,
    });
    const onChanged = vi.fn();
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={onChanged} />);

    await user.click(screen.getByRole("button", { name: "Change address" }));
    const input = screen.getByLabelText("New email address");
    await user.clear(input);
    await user.type(input, "new@iqoqo.local");
    await user.click(screen.getByRole("button", { name: "Save address" }));

    await waitFor(() => expect(changeAccountEmail).toHaveBeenCalledWith("new@iqoqo.local"));
    expect(toast.warning).toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
    expect(onChanged).toHaveBeenCalled();
  });

  it("warns that changing the address clears verification", async () => {
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Change address" }));

    expect(screen.getByText(/clears its verification/i)).toBeInTheDocument();
  });

  it("returns to the previous address when an edit is cancelled", async () => {
    render(<EmailVerificationCard email="me@iqoqo.local" verified={false} onChanged={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Change address" }));
    const input = screen.getByLabelText("New email address");
    await user.clear(input);
    await user.type(input, "typed@iqoqo.local");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    await user.click(screen.getByRole("button", { name: "Change address" }));
    expect(screen.getByLabelText("New email address")).toHaveValue("me@iqoqo.local");
  });
});

describe("DeleteAccountDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("states that nothing is deleted at request time", async () => {
    render(<DeleteAccountDialog emailVerified pending={false} onRequested={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Delete Account" }));

    expect(screen.getByText(/nothing is deleted now/i)).toBeInTheDocument();
    expect(screen.getByText(/no grace period/i)).toBeInTheDocument();
  });

  it("blocks confirmation when the address is unverified, and says why", async () => {
    render(<DeleteAccountDialog emailVerified={false} pending={false} onRequested={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Delete Account" }));

    const confirm = screen.getByRole("button", { name: /email me a confirmation link/i });
    expect(confirm).toBeDisabled();
    expect(screen.getByText(/no way to delete an account without a verified address/i)).toBeInTheDocument();
  });

  it("sends a confirmation link rather than deleting, and reports it", async () => {
    vi.mocked(requestAccountDeletion).mockResolvedValue(undefined);
    const onRequested = vi.fn();
    render(<DeleteAccountDialog emailVerified pending={false} onRequested={onRequested} />);

    await user.click(screen.getByRole("button", { name: "Delete Account" }));
    await user.click(screen.getByRole("button", { name: /email me a confirmation link/i }));

    await waitFor(() => expect(requestAccountDeletion).toHaveBeenCalledTimes(1));
    expect(toast.success).toHaveBeenCalledWith(expect.stringMatching(/nothing has been deleted yet/i));
    expect(onRequested).toHaveBeenCalled();
  });

  it("keeps the dialog open and explains a mail failure", async () => {
    // A misconfigured instance is an operator problem, so the message has to say
    // so rather than reading as the user's own failure.
    vi.mocked(requestAccountDeletion).mockRejectedValue(
      new Error("The confirmation email could not be sent. This instance is not configured to send mail.")
    );
    render(<DeleteAccountDialog emailVerified pending={false} onRequested={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Delete Account" }));
    await user.click(screen.getByRole("button", { name: /email me a confirmation link/i }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/not configured to send mail/i))
    );
    // Still open, so the warning is read in context.
    expect(screen.getByRole("button", { name: /email me a confirmation link/i })).toBeInTheDocument();
  });

  it("closes and points at verification when the address is unverified server-side", async () => {
    vi.mocked(requestAccountDeletion).mockRejectedValue(
      new Error("Verify your email address before deleting your account.")
    );
    render(<DeleteAccountDialog emailVerified pending={false} onRequested={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Delete Account" }));
    await user.click(screen.getByRole("button", { name: /email me a confirmation link/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/verify your email/i)));
  });

  it("disables the trigger while a request is already pending", () => {
    render(<DeleteAccountDialog emailVerified pending onRequested={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Delete Account" })).toBeDisabled();
  });
});

describe("DeletionPendingNotice", () => {
  it("renders nothing when no request is pending", () => {
    const { container } = render(<DeletionPendingNotice expiresAt={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("leads with the reassurance that the account is intact", () => {
    render(<DeletionPendingNotice expiresAt="2026-02-01T12:00:00Z" />);

    const notice = screen.getByTestId("deletion-pending-notice");
    // The intact-account sentence must appear before the pending description.
    expect(notice.textContent).toMatch(/still here and nothing has been deleted/i);
  });

  it("tells the user that doing nothing is a valid way out", () => {
    render(<DeletionPendingNotice expiresAt="2026-02-01T12:00:00Z" />);
    expect(screen.getByTestId("deletion-pending-notice")).toHaveTextContent(/simply do nothing/i);
  });
});
