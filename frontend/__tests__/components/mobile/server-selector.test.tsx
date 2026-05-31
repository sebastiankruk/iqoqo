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
/**
 * Tests for the ServerSelector component.
 *
 * The server's /api/health endpoint is hit via the global fetch mock so that
 * the verification flow can be exercised without a real network.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServerSelector } from "@/components/mobile/server-selector";

// Mock Next.js router.
const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

// Mock Capacitor storage.
vi.mock("@/lib/capacitor/storage", () => ({
  setInstanceUrl: vi.fn().mockResolvedValue(undefined),
  setInstanceName: vi.fn().mockResolvedValue(undefined),
}));

describe("ServerSelector", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders the URL input and Verify button", () => {
    render(<ServerSelector />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /verify connection/i })).toBeInTheDocument();
  });

  it("shows a success state when the server responds with 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ instance_name: "My Library" }),
      })
    );

    render(<ServerSelector />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "https://library.example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify connection/i }));

    await waitFor(() =>
      expect(screen.getByText(/connected: my library/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /continue to login/i })).toBeInTheDocument();
  });

  it("shows an error state when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("Network failure")));

    render(<ServerSelector />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "https://unreachable.example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify connection/i }));

    await waitFor(() =>
      expect(screen.getByText(/network failure/i)).toBeInTheDocument()
    );
  });

  it("navigates to /login after connecting", async () => {
    const { setInstanceUrl, setInstanceName } = await import("@/lib/capacitor/storage");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ instance_name: "Test Instance" }),
      })
    );

    render(<ServerSelector />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "https://library.example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify connection/i }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /continue to login/i })).toBeInTheDocument()
    );
    fireEvent.click(screen.getByRole("button", { name: /continue to login/i }));

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/login"));
    expect(setInstanceUrl).toHaveBeenCalledWith("https://library.example.com");
    expect(setInstanceName).toHaveBeenCalledWith("Test Instance");
  });
});
