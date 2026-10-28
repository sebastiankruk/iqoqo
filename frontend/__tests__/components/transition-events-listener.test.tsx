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

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useProfile } from "@/lib/api/hooks";
import { TransitionEventsListener } from "@/components/providers";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

const mockUsePathname = vi.mocked(usePathname);
const mockUseProfile = vi.mocked(useProfile);

describe("TransitionEventsListener", () => {
  let mockEventSourceInstances: any[] = [];

  beforeEach(() => {
    mockEventSourceInstances = [];
    mockUsePathname.mockReturnValue("/collection");
    mockUseProfile.mockReturnValue({
      data: { id: "user-123", username: "collector" },
    } as any);

    // Mock global EventSource
    class MockEventSource {
      url: string;
      options: any;
      onmessage: ((ev: any) => void) | null = null;
      onerror: ((ev: any) => void) | null = null;
      close = vi.fn();

      constructor(url: string, options: any) {
        this.url = url;
        this.options = options;
        mockEventSourceInstances.push(this);
      }
    }

    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("subscribes to /api/v1/events/stream on mount and closes on unmount", () => {
    const queryClient = new QueryClient();

    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(mockEventSourceInstances).toHaveLength(1);
    const instance = mockEventSourceInstances[0];
    expect(instance.url).toBe("/api/v1/events/stream");
    expect(instance.options).toEqual({ withCredentials: true });

    unmount();
    expect(instance.close).toHaveBeenCalledTimes(1);
  });

  it("invalidates queries when transition event is received", () => {
    const mockInvalidate = vi.fn();
    vi.mocked(useQueryClient).mockReturnValue({
      invalidateQueries: mockInvalidate,
    } as any);

    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    const instance = mockEventSourceInstances[mockEventSourceInstances.length - 1];
    expect(instance.onmessage).toBeDefined();

    instance.onmessage({
      data: JSON.stringify({
        event: "fts_reindexed",
        data: { entities: ["item:10"] },
      }),
    });

    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["stats"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["items"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["manifestations"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["facetStats"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["globalStats"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["collectionGrid"] });
  });

  it("does not connect EventSource when user is unauthenticated", () => {
    mockUseProfile.mockReturnValue({ data: null } as any);
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(mockEventSourceInstances).toHaveLength(0);
  });

  it("does not connect EventSource when on public routes", () => {
    mockUsePathname.mockReturnValue("/login");
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(mockEventSourceInstances).toHaveLength(0);
  });

  it("connects when user becomes authenticated and closes on logout", () => {
    mockUseProfile.mockReturnValue({ data: null } as any);
    const queryClient = new QueryClient();

    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(mockEventSourceInstances).toHaveLength(0);

    // User logs in
    mockUseProfile.mockReturnValue({
      data: { id: "user-123", username: "collector" },
    } as any);

    rerender(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(mockEventSourceInstances).toHaveLength(1);
    const instance = mockEventSourceInstances[0];
    expect(instance.close).not.toHaveBeenCalled();

    // User logs out
    mockUseProfile.mockReturnValue({ data: null } as any);

    rerender(
      <QueryClientProvider client={queryClient}>
        <TransitionEventsListener />
      </QueryClientProvider>
    );

    expect(instance.close).toHaveBeenCalledTimes(1);
  });
});
