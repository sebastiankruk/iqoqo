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
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { InstanceSettings } from "@/components/admin/instance-settings";
import * as adminApi from "@/lib/api/admin";
import * as fedApi from "@/lib/api/federation";

vi.mock("@/lib/api/admin");
vi.mock("@/lib/api/federation");

vi.mock("@/components/ui/alert-dialog", () => ({
  AlertDialog: ({ open, children }: any) => (open ? <div data-testid="alert-dialog">{children}</div> : null),
  AlertDialogContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  AlertDialogHeader: ({ children }: any) => <div>{children}</div>,
  AlertDialogTitle: ({ children }: any) => <h2>{children}</h2>,
  AlertDialogDescription: ({ children }: any) => <p>{children}</p>,
  AlertDialogFooter: ({ children }: any) => <div>{children}</div>,
  AlertDialogAction: ({ children, onClick }: any) => (
    <button data-testid="alert-dialog-action" onClick={onClick}>
      {children}
    </button>
  ),
  AlertDialogCancel: ({ children, onClick }: any) => (
    <button data-testid="alert-dialog-cancel" onClick={onClick}>
      {children}
    </button>
  ),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      noFingerprint: "Not configured",
      copyFingerprint: "Copy key fingerprint",
      copiedFingerprint: "Fingerprint copied to clipboard",
      rotateKey: "Rotate Key",
      generateKey: "Generate Instance Key",
      keyFingerprintDesc: "Public key fingerprint",
      keyProvisioned: "Instance key generated",
      keyRotated: "Instance key rotated",
    };
    return translations[key] || key;
  },
}));

describe("InstanceSettings - Federation Key Fingerprint", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminApi.getInstanceSettings).mockResolvedValue({
      FEDERATION_ENABLED: { value: "true", source: "db" },
      FEDERATION_BASE_URL: { value: "https://library.example", source: "db" },
      FEDERATION_DEFAULT_TRUST: { value: "untrusted", source: "db" },
      FEDERATION_AUTO_ACCEPT_FOLLOWS: { value: "false", source: "db" },
    });
  });

  it("handles unconfigured instance key by hiding copy and calling provision with rotate=false", async () => {
    vi.mocked(fedApi.getFederationKeyFingerprint).mockResolvedValue("Not configured");
    vi.mocked(fedApi.provisionFederationInstanceKey).mockResolvedValue("SHA256:11:22:33:44");

    render(<InstanceSettings category="federation" />);

    await waitFor(() => {
      expect(screen.getByText("Not configured")).toBeDefined();
    });

    // Copy button must NOT be present
    expect(screen.queryByText(/Copy/i)).toBeNull();

    // Action button must say Generate Instance Key
    const generateBtn = screen.getByRole("button", { name: /generatekey|generate instance key/i });
    expect(generateBtn).toBeDefined();

    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(fedApi.provisionFederationInstanceKey).toHaveBeenCalledWith(false);
    });
  });

  it("handles configured instance key by showing copy and prompting confirmation before rotate", async () => {
    const validFingerprint = "SHA256:aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99";
    vi.mocked(fedApi.getFederationKeyFingerprint).mockResolvedValue(validFingerprint);
    vi.mocked(fedApi.provisionFederationInstanceKey).mockResolvedValue("SHA256:99:88:77:66");

    render(<InstanceSettings category="federation" />);

    await waitFor(() => {
      expect(screen.getByText(validFingerprint)).toBeDefined();
    });

    // Copy button must be present
    expect(screen.getByRole("button", { name: /copy/i })).toBeDefined();

    // Action button must say Rotate Key
    const rotateBtn = screen.getByRole("button", { name: /rotatekey|rotate key/i });
    expect(rotateBtn).toBeDefined();

    // Clicking rotate opens confirmation dialog
    fireEvent.click(rotateBtn);

    // Dialog confirm action
    await waitFor(() => {
      expect(screen.getByTestId("alert-dialog")).toBeDefined();
    });

    const confirmBtn = screen.getByTestId("alert-dialog-action");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(fedApi.provisionFederationInstanceKey).toHaveBeenCalledWith(true);
    });
  });
});
