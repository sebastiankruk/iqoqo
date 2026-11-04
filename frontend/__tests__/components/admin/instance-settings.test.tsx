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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { InstanceSettings } from "@/components/admin/instance-settings";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("InstanceSettings - Google OAuth Admin Settings UI", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders Google OAuth fields, handles mask/reveal, and persists keys on save", async () => {
    const user = userEvent.setup();

    vi.mocked(adminApi.getInstanceSettings).mockResolvedValue({
      GOOGLE_CLIENT_ID: { value: "***client123", source: "db" },
      GOOGLE_CLIENT_SECRET: { value: "***secret456", source: "db" },
      GOOGLE_BOOKS_API_KEY: { value: "***books789", source: "db" },
    });

    vi.mocked(adminApi.revealSettingValue).mockImplementation(async (key: string) => {
      if (key === "GOOGLE_CLIENT_ID") {
        return { success: true, key, value: "123456789-test.apps.googleusercontent.com" };
      }
      if (key === "GOOGLE_CLIENT_SECRET") {
        return { success: true, key, value: "GOCSPX-super-secret-oauth-key" };
      }
      return { success: true, key, value: "revealed-secret" };
    });

    vi.mocked(adminApi.updateInstanceSettings).mockResolvedValue({
      GOOGLE_CLIENT_ID: "new-client-id.apps.googleusercontent.com",
      GOOGLE_CLIENT_SECRET: "new-client-secret",
    });

    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Enter Google OAuth Client ID")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Enter Google OAuth Client Secret")).toBeInTheDocument();
    });

    const clientIdInput = screen.getByPlaceholderText("Enter Google OAuth Client ID") as HTMLInputElement;
    const clientSecretInput = screen.getByPlaceholderText("Enter Google OAuth Client Secret") as HTMLInputElement;

    expect(clientIdInput.value).toBe("***client123");
    expect(clientSecretInput.value).toBe("***secret456");

    // Reveal Google OAuth Client ID
    const clientIdContainer = clientIdInput.closest(".relative");
    const clientIdRevealBtn = clientIdContainer?.querySelector('button[title="Reveal stored value"]');
    expect(clientIdRevealBtn).not.toBeNull();
    await user.click(clientIdRevealBtn!);

    await waitFor(() => {
      expect(adminApi.revealSettingValue).toHaveBeenCalledWith("GOOGLE_CLIENT_ID");
      expect(clientIdInput.value).toBe("123456789-test.apps.googleusercontent.com");
    });

    // Reveal Google OAuth Client Secret
    const clientSecretContainer = clientSecretInput.closest(".relative");
    const clientSecretRevealBtn = clientSecretContainer?.querySelector('button[title="Reveal stored value"]');
    expect(clientSecretRevealBtn).not.toBeNull();
    await user.click(clientSecretRevealBtn!);

    await waitFor(() => {
      expect(adminApi.revealSettingValue).toHaveBeenCalledWith("GOOGLE_CLIENT_SECRET");
      expect(clientSecretInput.value).toBe("GOCSPX-super-secret-oauth-key");
    });

    // Hide Google OAuth Client Secret again
    const clientSecretHideBtn = clientSecretContainer?.querySelector('button[title="Hide value"]');
    expect(clientSecretHideBtn).not.toBeNull();
    await user.click(clientSecretHideBtn!);

    await waitFor(() => {
      expect(clientSecretInput.value).toBe("***secret456");
    });

    // Edit Google OAuth Client ID and save
    await user.clear(clientIdInput);
    await user.type(clientIdInput, "new-client-id.apps.googleusercontent.com");

    const saveButtons = screen.getAllByRole("button", { name: /save/i });
    expect(saveButtons.length).toBeGreaterThan(0);
    await user.click(saveButtons[0]);

    await waitFor(() => {
      expect(adminApi.updateInstanceSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          GOOGLE_CLIENT_ID: "new-client-id.apps.googleusercontent.com",
        }),
        "external_apis"
      );
    });
  });
});
