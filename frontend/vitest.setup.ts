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
 * Global Vitest setup file.
 *
 * Runs once before every test file. Pulls in the jest-dom matchers so we can
 * use `.toBeInTheDocument()`, `.toHaveTextContent()` etc., and registers the
 * module mocks that stub out Next.js internals and third-party side-effects
 * (navigation, sonner toasts) that would otherwise error in jsdom.
 */
import "@testing-library/jest-dom";
import { vi } from "vitest";

/* ── Next.js router ────────────────────────────────────────────────────────
 * Stub useRouter / usePathname / useParams so components that call them work
 * inside happy-dom without a real Next.js runtime.
 * Each hook is a vi.fn() spy so tests can inspect calls and override
 * return values with .mockReturnValue().                                    */
vi.mock("next/navigation", () => ({
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: vi.fn().mockReturnValue("/"),
  useParams: vi.fn().mockReturnValue({}),
  useSearchParams: vi.fn().mockReturnValue(new URLSearchParams()),
}));

/* ── Next.js Link ──────────────────────────────────────────────────────────
 * Render as a plain <a> so RTL can assert href values and text.
 * The async factory lets us import React without hoisting problems.       */
vi.mock("next/link", async () => {
  const { createElement } = await import("react");
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    default: ({ href, children, className, ...rest }: any) =>
      createElement("a", { href, className, ...rest }, children),
  };
});
/* ── Next.js Image ───────────────────────────────────────────────────────
 * Render as a plain <img> so RTL assertions on src/alt work normally and
 * we don't need a real Next.js image-optimisation server running.          */
vi.mock("next/image", async () => {
  const { createElement } = await import("react");
  return {
    // Strips Next.js-specific props (fill, sizes, unoptimized, priority) so
    // only standard <img> attributes are forwarded to the DOM element.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    default: ({ src, alt, className, fill, sizes, unoptimized, priority, placeholder, blurDataURL, ...rest }: any) => {
      void fill; void sizes; void unoptimized; void priority; void placeholder; void blurDataURL;
      return createElement("img", { src, alt, className, ...rest });
    },
  };
});
/* ── Sonner toasts ─────────────────────────────────────────────────────────
 * Replace with no-op spies – tests that care can assert on these calls.   */
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
  Toaster: () => null,
}));
