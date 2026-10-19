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
import { FederationConsentSettings } from "@/components/settings/federation-consent";
import { getFederationConsent, updateFederationConsent } from "@/lib/api/federation";
import type { FederationConsent } from "@/types/federation";

vi.mock("@/lib/api/federation", () => ({
  getFederationConsent: vi.fn(),
  updateFederationConsent: vi.fn(),
}));

const mockConsent: FederationConsent = {
  user_id: "test-user-id-123",
  federated_profile: false,
  federated_collection: false,
  updated_at: "2026-10-16T12:00:00Z",
};

describe("FederationConsentSettings", () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading indicator while fetching initial consent", () => {
    vi.mocked(getFederationConsent).mockReturnValue(new Promise(() => {}));
    render(<FederationConsentSettings />);
    expect(screen.getByTestId("federation-consent-loading")).toBeInTheDocument();
  });

  it("renders toggles unchecked when consent is false", async () => {
    vi.mocked(getFederationConsent).mockResolvedValue(mockConsent);
    render(<FederationConsentSettings />);

    await waitFor(() => {
      expect(screen.getByText("Federation Privacy")).toBeInTheDocument();
    });

    const profileCheckbox = screen.getByRole("checkbox", { name: /make profile discoverable/i });
    const collectionCheckbox = screen.getByRole("checkbox", { name: /share collection updates/i });

    expect(profileCheckbox).not.toBeChecked();
    expect(collectionCheckbox).not.toBeChecked();
  });

  it("renders toggles checked when consent is true", async () => {
    vi.mocked(getFederationConsent).mockResolvedValue({
      ...mockConsent,
      federated_profile: true,
      federated_collection: true,
    });
    render(<FederationConsentSettings />);

    await waitFor(() => {
      expect(screen.getByText("Federation Privacy")).toBeInTheDocument();
    });

    const profileCheckbox = screen.getByRole("checkbox", { name: /make profile discoverable/i });
    const collectionCheckbox = screen.getByRole("checkbox", { name: /share collection updates/i });

    expect(profileCheckbox).toBeChecked();
    expect(collectionCheckbox).toBeChecked();
  });

  it("calls updateFederationConsent when profile toggle is clicked", async () => {
    vi.mocked(getFederationConsent).mockResolvedValue(mockConsent);
    vi.mocked(updateFederationConsent).mockResolvedValue({
      ...mockConsent,
      federated_profile: true,
    });

    render(<FederationConsentSettings />);

    await waitFor(() => {
      expect(screen.getByText("Federation Privacy")).toBeInTheDocument();
    });

    const profileCheckbox = screen.getByRole("checkbox", { name: /make profile discoverable/i });
    await user.click(profileCheckbox);

    expect(updateFederationConsent).toHaveBeenCalledWith({ federated_profile: true });

    await waitFor(() => {
      expect(screen.getByText("Saved")).toBeInTheDocument();
    });
  });

  it("calls updateFederationConsent when collection toggle is clicked", async () => {
    vi.mocked(getFederationConsent).mockResolvedValue(mockConsent);
    vi.mocked(updateFederationConsent).mockResolvedValue({
      ...mockConsent,
      federated_collection: true,
    });

    render(<FederationConsentSettings />);

    await waitFor(() => {
      expect(screen.getByText("Federation Privacy")).toBeInTheDocument();
    });

    const collectionCheckbox = screen.getByRole("checkbox", { name: /share collection updates/i });
    await user.click(collectionCheckbox);

    expect(updateFederationConsent).toHaveBeenCalledWith({ federated_collection: true });

    await waitFor(() => {
      expect(screen.getByText("Saved")).toBeInTheDocument();
    });
  });

  it("handles update failure gracefully without crashing", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.mocked(getFederationConsent).mockResolvedValue(mockConsent);
    vi.mocked(updateFederationConsent).mockRejectedValue(new Error("Network error"));

    render(<FederationConsentSettings />);

    await waitFor(() => {
      expect(screen.getByText("Federation Privacy")).toBeInTheDocument();
    });

    const profileCheckbox = screen.getByRole("checkbox", { name: /make profile discoverable/i });
    await user.click(profileCheckbox);

    expect(updateFederationConsent).toHaveBeenCalledWith({ federated_profile: true });
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
