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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ServerSelector } from "@/components/mobile/server-selector";
import * as storage from "@/lib/capacitor/storage";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    const messages: Record<string, string> = {
      serverSelectorTitle: "Connect to your library",
      serverSelectorDescription: "Enter the URL of your self-hosted iqoqo instance to begin.",
      serverUrlLabel: "Server URL",
      serverUrlPlaceholder: "https://library.example.com",
      verifyConnection: "Verify connection",
      verifying: "Verifying...",
      connectionSuccess: `Connected to ${values?.name || "library"}`,
      connectionFailed: "Unable to connect to this server.",
      invalidUrl: "Please enter a valid HTTP or HTTPS URL.",
      cancel: "Cancel",
      version: `Version: ${values?.version || ""}`,
    };
    return messages[key] || key;
  },
}));

describe("ServerSelector Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(storage, "getInstanceUrl").mockResolvedValue(null);
    vi.spyOn(storage, "setInstanceUrl").mockResolvedValue();
    vi.spyOn(storage, "setInstanceName").mockResolvedValue();
  });

  it("renders server URL input and verify button", () => {
    render(<ServerSelector />);

    expect(screen.getByText("Connect to your library")).toBeDefined();
    expect(screen.getByPlaceholderText("https://library.example.com")).toBeDefined();
    expect(screen.getByRole("button", { name: "Verify connection" })).toBeDefined();
  });

  it("validates empty or invalid URLs without calling fetch", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    render(<ServerSelector />);

    const input = screen.getByPlaceholderText("https://library.example.com");
    fireEvent.change(input, { target: { value: "invalid url with spaces" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify connection" }));

    await waitFor(() => {
      expect(screen.getByText("Please enter a valid HTTP or HTTPS URL.")).toBeDefined();
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("probes /api/health and calls onConnected on successful verification", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.endsWith("/api/health")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ status: "ok", service: "iqoqo-api", version: "1.0.0" }),
        } as Response;
      }
      if (urlStr.endsWith("/api/config")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ data: { instance_name: "Kruk Library", version: "1.0.0" } }),
        } as Response;
      }
      return { ok: false, status: 404 } as Response;
    });

    const onConnected = vi.fn();
    render(<ServerSelector onConnected={onConnected} />);

    const input = screen.getByPlaceholderText("https://library.example.com");
    fireEvent.change(input, { target: { value: "https://iqoqo.kruk.cc" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify connection" }));

    await waitFor(() => {
      expect(storage.setInstanceUrl).toHaveBeenCalledWith("https://iqoqo.kruk.cc");
      expect(storage.setInstanceName).toHaveBeenCalledWith("Kruk Library");
      expect(onConnected).toHaveBeenCalledWith("https://iqoqo.kruk.cc", "Kruk Library");
    });
  });

  it("displays error message when /api/health probe fails", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("Connection refused"));

    render(<ServerSelector />);

    const input = screen.getByPlaceholderText("https://library.example.com");
    fireEvent.change(input, { target: { value: "https://offline.iqoqo.local" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify connection" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to connect to this server.")).toBeDefined();
    });
  });
});
