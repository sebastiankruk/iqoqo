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
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import RegisterPage from "@/app/register/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Rely on global mock from vitest.setup.ts

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

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it("disables submit button until terms are accepted", () => {
    renderWithQueryClient(<RegisterPage />);

    const submitButton = screen.getByRole("button", { name: "Sign Up" });
    const termsCheckbox = screen.getByRole("checkbox", { name: /I agree to the/i });

    expect(submitButton).toBeDisabled();

    fireEvent.click(termsCheckbox);
    expect(submitButton).not.toBeDisabled();
  });

  it("shows error message on failed registration", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: false,
      /**
       * Mock for json response.
       *
       * @returns {Promise<{error: string}>} The mocked json response.
       */
      json: async () => ({ error: "Email already registered" }),
    });

    renderWithQueryClient(<RegisterPage />);

    fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: "exist@iqoqo.local" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "pass123" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /I agree to the/i }));
    fireEvent.click(screen.getByRole("button", { name: "Sign Up" }));

    await waitFor(() => {
      expect(screen.getByText("Email already registered")).toBeInTheDocument();
    });
  });
});
