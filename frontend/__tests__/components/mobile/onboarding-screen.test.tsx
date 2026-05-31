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
 * Tests for the OnboardingGuard component.
 *
 * Exercises the native-only first-launch flow:
 *  - On web  → renders children directly.
 *  - Native, URL set     → renders children.
 *  - Native, URL missing → renders ServerSelector.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Control mock values at module scope so they can be changed per-test.
let mockIsNative = false;
let mockStoredUrl: string | null = null;

vi.mock("@/lib/capacitor/platform", () => ({
  isNativeApp: () => mockIsNative,
}));

vi.mock("@/lib/capacitor/storage", () => ({
  getInstanceUrl: vi.fn(() => Promise.resolve(mockStoredUrl)),
}));

// Minimal stub so ServerSelector doesn't need a full render context.
vi.mock("@/components/mobile/server-selector", () => ({
  ServerSelector: () => <div data-testid="server-selector" />,
}));

// We must import AFTER mocks are registered.
async function importGuard() {
  const { OnboardingGuard } = await import("@/components/mobile/onboarding-screen");
  return OnboardingGuard;
}

describe("OnboardingGuard", () => {
  beforeEach(() => {
    vi.resetModules();
    mockIsNative = false;
    mockStoredUrl = null;
  });

  it("renders children immediately on web (no native check)", async () => {
    const OnboardingGuard = await importGuard();
    render(
      <OnboardingGuard>
        <div data-testid="app-content" />
      </OnboardingGuard>
    );
    await waitFor(() => expect(screen.getByTestId("app-content")).toBeInTheDocument());
    expect(screen.queryByTestId("server-selector")).not.toBeInTheDocument();
  });

  it("renders children when native and instance URL is set", async () => {
    mockIsNative = true;
    mockStoredUrl = "https://library.example.com";
    const OnboardingGuard = await importGuard();
    render(
      <OnboardingGuard>
        <div data-testid="app-content" />
      </OnboardingGuard>
    );
    await waitFor(() => expect(screen.getByTestId("app-content")).toBeInTheDocument());
    expect(screen.queryByTestId("server-selector")).not.toBeInTheDocument();
  });

  it("renders ServerSelector when native and no instance URL is stored", async () => {
    mockIsNative = true;
    mockStoredUrl = null;
    const OnboardingGuard = await importGuard();
    render(
      <OnboardingGuard>
        <div data-testid="app-content" />
      </OnboardingGuard>
    );
    await waitFor(() => expect(screen.getByTestId("server-selector")).toBeInTheDocument());
    expect(screen.queryByTestId("app-content")).not.toBeInTheDocument();
  });
});
