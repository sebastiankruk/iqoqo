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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TotpSetup } from "@/components/profile/totp-setup";
import { PatManagement } from "@/components/profile/pat-management";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("TotpSetup Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders disabled state and handles full enrollment flow", async () => {
    const onStatusChanged = vi.fn();

    vi.mocked(apiClient.post).mockImplementation(async (url: string) => {
      if (url === "/auth/2fa/enroll") {
        return {
          data: {
            secret: "JBSWY3DPEHPK3PXP",
            provisioning_uri: "otpauth://totp/iqoqo:test@test.local?secret=JBSWY3DPEHPK3PXP",
            recovery_codes: ["A1B2C3D4", "E5F6G7H8"],
            qr_code: "data:image/png;base64,mockqr",
          },
        } as any;
      }
      if (url === "/auth/2fa/verify") {
        return { data: { success: true, enabled: true } } as any;
      }
      throw new Error(`Unhandled post to ${url}`);
    });

    render(<TotpSetup totpEnabled={false} onStatusChanged={onStatusChanged} />);

    expect(screen.getByText("Disabled")).toBeDefined();
    const enableBtn = screen.getByTestId("enable-2fa-button");
    fireEvent.click(enableBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/2fa/enroll");
      expect(screen.getByTestId("totp-enroll-dialog")).toBeDefined();
      expect(screen.getByText("JBSWY3DPEHPK3PXP")).toBeDefined();
      expect(screen.getByText("A1B2C3D4")).toBeDefined();
    });

    const input = screen.getByTestId("totp-verification-input");
    fireEvent.change(input, { target: { value: "123456" } });

    const verifyBtn = screen.getByTestId("verify-and-enable-button");
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/2fa/verify", { code: "123456" });
      expect(onStatusChanged).toHaveBeenCalled();
    });
  });

  it("renders enabled state and handles disabling 2FA", async () => {
    const onStatusChanged = vi.fn();
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { success: true, enabled: false } });

    render(<TotpSetup totpEnabled={true} onStatusChanged={onStatusChanged} />);

    expect(screen.getByText("Enabled")).toBeDefined();
    const disableBtn = screen.getByTestId("disable-2fa-button");
    fireEvent.click(disableBtn);

    expect(screen.getByTestId("disable-2fa-dialog")).toBeDefined();
    const passInput = screen.getByTestId("disable-password-input");
    fireEvent.change(passInput, { target: { value: "mypassword" } });

    const confirmBtn = screen.getByTestId("confirm-disable-2fa-button");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/2fa/disable", {
        password: "mypassword",
        code: undefined,
      });
      expect(onStatusChanged).toHaveBeenCalled();
    });
  });
});

describe("PatManagement Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and displays tokens list, generates a token, and revokes", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 1,
            name: "Home Assistant",
            token_prefix: "iqo_abc123",
            scopes: ["read:catalog"],
            expires_at: null,
            last_used_at: null,
            revoked_at: null,
            created_at: "2026-10-24T00:00:00Z",
            is_active: true,
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      },
    });

    render(<PatManagement />);

    await waitFor(() => {
      expect(screen.getByText("Home Assistant")).toBeDefined();
      expect(screen.getByText("iqo_abc123...")).toBeDefined();
    });

    // Generate new token
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        token: "iqo_newsecrettoken1234567890",
        data: {
          id: 2,
          name: "CLI Tool",
          token_prefix: "iqo_newsec",
          scopes: ["read:catalog"],
          expires_at: null,
          last_used_at: null,
          revoked_at: null,
          created_at: "2026-10-24T01:00:00Z",
          is_active: true,
        },
      },
    });
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 1,
            name: "Home Assistant",
            token_prefix: "iqo_abc123",
            scopes: ["read:catalog"],
            expires_at: null,
            last_used_at: null,
            revoked_at: null,
            created_at: "2026-10-24T00:00:00Z",
            is_active: true,
          },
          {
            id: 2,
            name: "CLI Tool",
            token_prefix: "iqo_newsec",
            scopes: ["read:catalog"],
            expires_at: null,
            last_used_at: null,
            revoked_at: null,
            created_at: "2026-10-24T01:00:00Z",
            is_active: true,
          },
        ],
        total: 2,
        limit: 50,
        offset: 0,
      },
    });

    fireEvent.click(screen.getByTestId("generate-pat-button"));
    expect(screen.getByTestId("generate-pat-dialog")).toBeDefined();

    fireEvent.change(screen.getByTestId("pat-name-input"), { target: { value: "CLI Tool" } });
    fireEvent.click(screen.getByTestId("confirm-generate-pat-button"));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/auth/tokens", {
        name: "CLI Tool",
        scopes: ["read:catalog"],
        expires_in_days: 30,
      });
      expect(screen.getByTestId("new-pat-banner")).toBeDefined();
      expect(screen.getByText("iqo_newsecrettoken1234567890")).toBeDefined();
    });

    // Revoke token 1
    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { success: true } });
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
    });

    const revokeBtn = screen.getByTestId("revoke-pat-1");
    fireEvent.click(revokeBtn);

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/auth/tokens/1");
    });
  });
});
