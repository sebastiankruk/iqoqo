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
import fs from "fs";
import path from "path";
import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, it, expect, vi } from "vitest";
import DashboardPage from "@/app/page";
import * as hooks from "@/lib/api/hooks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/image", () => ({
  /**
   * Mock for Next.js Image component.
   *
   * @param {object} props - The component props.
   * @returns {React.ReactElement} The rendered component.
   */
  default: (props: React.ComponentProps<"img"> & Record<string, unknown>) => {
    const { fill, sizes, unoptimized, priority, placeholder, blurDataURL, ...rest } = props;
    void fill;
    void sizes;
    void unoptimized;
    void priority;
    void placeholder;
    void blurDataURL;
    const restImgProps = rest as React.ComponentProps<"img">;
    // eslint-disable-next-line @next/next/no-img-element
    return <img alt={restImgProps.alt ?? ""} {...restImgProps} />;
  },
}));

/**
 * Creates a test query client with retries disabled.
 *
 * @returns {QueryClient} The query client instance.
 */
const createTestQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

/**
 * Renders a component wrapped in a QueryClientProvider.
 *
 * @param {React.ReactElement} component - The component to render.
 * @returns {import('@testing-library/react').RenderResult} The render result.
 */
const renderWithQueryClient = (component: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(<QueryClientProvider client={testQueryClient}>{component}</QueryClientProvider>);
};

describe("Landing / Dashboard page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders landing view for unauthenticated users", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: null, isLoading: false } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useGlobalStats").mockReturnValue({
      data: { works: 10, manifestations: 20, items: 30, users: 5 },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useGlobalStats>);
    vi.spyOn(hooks, "useRecentManifestations").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useRecentManifestations
    >);

    renderWithQueryClient(<DashboardPage />);

    expect(screen.getByText("The Library of Everything")).toBeInTheDocument();
    expect(screen.getByText("Works")).toBeInTheDocument();
    expect(screen.getByText("Start Your Catalog")).toBeInTheDocument();
  });

  it("renders dashboard view for authenticated users", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({
      data: { display_name: "testuser", email: "test@example.com" },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useProfile>);

    renderWithQueryClient(<DashboardPage />);

    expect(screen.getByText("Welcome back, testuser")).toBeInTheDocument();
  });
});

describe("Dashboard RSS Feed Integration", () => {
  it("should expose correct RSS alternate discovery links in the layout metadata", () => {
    const layoutPath = path.resolve(__dirname, "../../app/layout.tsx");
    const layoutContent = fs.readFileSync(layoutPath, "utf-8");
    expect(layoutContent).toContain('url: "/api/public/feed.xml"');
    expect(layoutContent).toContain('title: "iqoqo Fresh Arrivals Feed"');
    expect(layoutContent).toContain('"application/rss+xml"');
  });

  it("should render the RSS button next to Fresh Arrivals header pointing to the global feed", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: null, isLoading: false } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useGlobalStats").mockReturnValue({
      data: { works: 10, manifestations: 20, items: 30, users: 5 },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useGlobalStats>);
    vi.spyOn(hooks, "useRecentManifestations").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useRecentManifestations
    >);

    renderWithQueryClient(<DashboardPage />);

    const heading = screen.getByRole("heading", { name: /Fresh Arrivals/i });
    expect(heading).toBeInTheDocument();

    const rssLink = screen.getByTitle("Subscribe to Fresh Arrivals RSS feed");
    expect(rssLink).toBeInTheDocument();
    expect(rssLink.getAttribute("href")).toBe("/api/public/feed.xml");
    expect(rssLink.getAttribute("target")).toBe("_blank");
  });
});
