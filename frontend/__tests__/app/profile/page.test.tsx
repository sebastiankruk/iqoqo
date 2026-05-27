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

// Mock the API client BEFORE importing the component
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  apiFetch: vi.fn(),
}));

// Mock dashboard components
vi.mock("@/components/dashboard/navbar", () => ({
  /** @returns {JSX.Element} Navbar mock */
  Navbar: () => <div data-testid="navbar">Navbar</div>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  /** @returns {JSX.Element} Footer mock */
  Footer: () => <div data-testid="footer">Footer</div>,
}));

// Mock useAppConfig so it doesn't compete with apiFetch mocks via useQuery
vi.mock("@/lib/api/hooks", () => ({
  useAppConfig: vi.fn(),
}));

import ProfilePage from "@/app/profile/page";
import { apiClient, apiFetch } from "@/lib/api/client";
import { useAppConfig } from "@/lib/api/hooks";

describe("ProfilePage", () => {
  const mockProfileData = {
    id: "test-user-id",
    email: "user@iqoqo.local",
    display_name: "Test User",
    avatar_url: null,
    visibility: "private" as const,
    created_at: "2026-01-01T00:00:00Z",
    consents: {
      consent_type: "all",
      is_granted: true,
      policy_version: "1.0",
      timestamp: "2026-01-01T00:00:00Z",
      telemetry: true,
      federation: false,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Default: federation disabled (federation button won't render)
    vi.mocked(useAppConfig).mockReturnValue({ data: { federation_enabled: false, version: "0.0.7" } } as never);

    // Mock the apiFetch function to return the profile data
    vi.mocked(apiFetch).mockResolvedValueOnce(mockProfileData);
  });

  it("renders loading state initially, then profile data", async () => {
    render(<ProfilePage />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
      expect(screen.getByText("user@iqoqo.local")).toBeInTheDocument();
    });

    // Verify apiFetch was called with the correct path
    expect(apiFetch).toHaveBeenCalledWith("/profile/");
  });

  it("toggles GDPR consents", async () => {
    // Enable federation so the federation consent button renders
    vi.mocked(useAppConfig).mockReturnValue({ data: { federation_enabled: true, version: "0.0.7" } } as never);

    // Extra apiFetch mock for this test's profile load
    vi.mocked(apiFetch).mockResolvedValueOnce(mockProfileData);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    // Mock the POST request for the consent toggle
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        success: true,
        data: {},
        error: null,
      },
    } as never);

    // With federation_enabled: true, the federation button appears before telemetry
    const federationButtons = screen.getAllByRole("button", { name: /Opted/i });

    // Click the first "Opted" button — the federation one
    fireEvent.click(federationButtons[0]);

    // Assert the API was called with federation consent
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/profile/consent",
        expect.objectContaining({
          consent_type: "federation",
          is_granted: true,
        })
      );
    });
  });

  it("toggles telemetry consent specifically", async () => {
    vi.mocked(useAppConfig).mockReturnValue({ data: { federation_enabled: false, version: "0.0.7" } } as never);
    vi.mocked(apiFetch).mockResolvedValueOnce(mockProfileData);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        success: true,
        data: {},
        error: null,
      },
    } as never);

    // Get telemetry opt-in button
    const telemetryButton = screen.getByRole("button", { name: "Opted In" });
    fireEvent.click(telemetryButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/profile/consent",
        expect.objectContaining({
          consent_type: "telemetry",
          is_granted: false,
        })
      );
    });
  });
});
