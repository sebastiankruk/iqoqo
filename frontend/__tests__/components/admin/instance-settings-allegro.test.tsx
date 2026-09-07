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
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { InstanceSettings } from "@/components/admin/instance-settings";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("InstanceSettings - Allegro Device Flow", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.stubGlobal("fetch", vi.fn());
    vi.spyOn(window, "open").mockImplementation(vi.fn());

    vi.mocked(adminApi.getInstanceSettings).mockResolvedValue({
      ALLEGRO_CLIENT_ID: { value: "test-client-id", source: "db" },
      ALLEGRO_CLIENT_SECRET: { value: "test-client-secret", source: "db" },
    });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("handles successful Allegro device flow", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    // Mock initial device flow response
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        device_code: "test-device-code",
        user_code: "ABC-123",
        verification_uri_complete: "https://allegro.pl/auth/device?user_code=ABC-123",
        interval: 1, // 1 second interval
        expires_in: 600,
      }),
    } as Response);

    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    // Wait for initial render of settings
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Authorize Allegro Account/i })).toBeDefined();
    });

    const authorizeBtn = screen.getByRole("button", { name: /Authorize Allegro Account/i });
    await user.click(authorizeBtn);

    // Verify fetch was called with right args
    expect(fetch).toHaveBeenCalledWith("/api/auth/allegro/device-flow", expect.any(Object));

    // Verify UI shows pending status
    await waitFor(() => {
      expect(screen.getByText(/Authorize code: ABC-123. Waiting for confirmation/i)).toBeDefined();
    });

    expect(window.open).toHaveBeenCalledWith("https://allegro.pl/auth/device?user_code=ABC-123", "_blank");

    // Mock pending response first (202)
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 202,
    } as Response);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    // Mock success response next (200)
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 200,
    } as Response);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    await waitFor(() => {
      expect(screen.getByText(/Allegro authorized successfully!/i)).toBeDefined();
    });
  });

  it("handles timeout/expiration in Allegro device flow", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        device_code: "test-device-code",
        user_code: "XYZ-789",
        verification_uri_complete: "https://allegro.pl/auth/device",
        interval: 1,
        expires_in: 1, // Expire after 1 tick
      }),
    } as Response);

    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Authorize Allegro Account/i })).toBeDefined();
    });

    const authorizeBtn = screen.getByRole("button", { name: /Authorize Allegro Account/i });
    await user.click(authorizeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Authorize code: XYZ-789/i)).toBeDefined();
    });

    // Mock pending response first
    vi.mocked(fetch).mockResolvedValue({
      status: 202,
    } as Response);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    // 1 second elapsed, interval triggers but expires_in is now 0
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    await waitFor(() => {
      expect(screen.getByText(/Authorization expired. Please try again./i)).toBeDefined();
    });
  });

  it("handles failure in Allegro device flow", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        device_code: "test-device-code",
        user_code: "FAIL-400",
        verification_uri_complete: "https://allegro.pl/auth/device",
        interval: 1,
        expires_in: 600,
      }),
    } as Response);

    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Authorize Allegro Account/i })).toBeDefined();
    });

    const authorizeBtn = screen.getByRole("button", { name: /Authorize Allegro Account/i });
    await user.click(authorizeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Authorize code: FAIL-400/i)).toBeDefined();
    });

    // Mock denied response (400 or other non-200/202)
    vi.mocked(fetch).mockResolvedValueOnce({
      status: 400,
    } as Response);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    await waitFor(() => {
      expect(screen.getByText(/Authorization failed or denied./i)).toBeDefined();
    });
  });

  it("renders Authorize Allegro button inside Allegro credential group", async () => {
    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    await waitFor(() => {
      expect(screen.getByText("Allegro Integration")).toBeDefined();
    });

    const allegroHeading = screen.getByText("Allegro Integration");
    const allegroSection = allegroHeading.closest("div.space-y-4");
    expect(allegroSection).not.toBeNull();

    const authorizeBtn = screen.getByRole("button", { name: /Authorize Allegro Account/i });
    expect(allegroSection?.contains(authorizeBtn)).toBe(true);
  });
});
