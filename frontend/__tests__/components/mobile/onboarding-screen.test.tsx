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
import { OnboardingGuard } from "@/components/mobile/onboarding-screen";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";
import * as splash from "@/lib/capacitor/splash";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const messages: Record<string, string> = {
      serverSelectorTitle: "Connect to your library",
      serverSelectorDescription: "Enter the URL of your self-hosted iqoqo instance to begin.",
      serverUrlLabel: "Server URL",
      serverUrlPlaceholder: "https://library.example.com",
      verifyConnection: "Verify connection",
      invalidUrl: "Please enter a valid HTTP or HTTPS URL.",
    };
    return messages[key] || key;
  },
}));

describe("OnboardingGuard Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(splash, "hideSplashScreen").mockResolvedValue();
  });

  it("renders children directly on web browsers", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);

    render(
      <OnboardingGuard>
        <div data-testid="app-content">Normal Web Content</div>
      </OnboardingGuard>
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-content")).toBeDefined();
    });
    expect(screen.queryByText("Connect to your library")).toBeNull();
  });

  it("renders ServerSelector on native app when no instance URL is set", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getInstanceUrl").mockResolvedValue(null);

    render(
      <OnboardingGuard>
        <div data-testid="app-content">Protected App Content</div>
      </OnboardingGuard>
    );

    await waitFor(() => {
      expect(screen.getByText("Connect to your library")).toBeDefined();
    });
    expect(screen.queryByTestId("app-content")).toBeNull();
    expect(splash.hideSplashScreen).toHaveBeenCalled();
  });

  it("renders children on native app when instance URL is already configured", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getInstanceUrl").mockResolvedValue("https://iqoqo.kruk.cc");

    render(
      <OnboardingGuard>
        <div data-testid="app-content">Protected App Content</div>
      </OnboardingGuard>
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-content")).toBeDefined();
    });
    expect(screen.queryByText("Connect to your library")).toBeNull();
    expect(splash.hideSplashScreen).toHaveBeenCalled();
  });
});
