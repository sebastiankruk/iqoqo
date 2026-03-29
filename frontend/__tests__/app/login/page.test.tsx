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
import { vi, describe, it, expect, beforeEach, type Mock } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "@/app/login/page";

vi.mock("next/navigation", () => ({
  /**
   * Mock for useRouter.
   *
   * @returns {object} The mocked router object.
   */
  useRouter: () => ({ push: vi.fn() }),
}));

/**
 * Creates a test query client with retries disabled.
 *
 * @returns {QueryClient} The query client instance.
 */
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

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

describe("LoginPage", () => {
  let alertMock: Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    process.env.NEXT_PUBLIC_API_URL = "/api";

    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });

    // Fix: explicitly mock window.alert since it doesn't exist in jsdom by default
    alertMock = vi.fn();
    window.alert = alertMock;
  });

  it("renders login form and Google SSO button", () => {
    renderWithQueryClient(<LoginPage />);
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign in with Google/i })).toBeInTheDocument();
  });

  it("redirects to Google SSO when button is clicked", () => {
    renderWithQueryClient(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /Sign in with Google/i }));
    expect(window.location.href).toContain("/api/auth/login/google");
  });

  it("handles successful local login and redirects", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      /**
       * Mock for json response.
       *
       * @returns {Promise<{token: string}>} The mocked json response.
       */
      json: async () => ({ token: "mock-jwt-token" }),
    });

    renderWithQueryClient(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: "test@iqoqo.local" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/auth/login"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ email: "test@iqoqo.local", password: "password123" }),
        })
      );
      expect(window.location.href).toContain("/api/auth-exchange?token=mock-jwt-token");
    });
  });

  it("handles failed local login and shows alert", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: false,
      /**
       * Mock for json response.
       *
       * @returns {Promise<{error: string}>} The mocked json response.
       */
      json: async () => ({ error: "Invalid credentials" }),
    });

    renderWithQueryClient(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: "wrong@iqoqo.local" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "wrong123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith("Login failed");
    });
  });
});
