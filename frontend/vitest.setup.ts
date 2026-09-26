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

/* ── Next.js router ──────────────────────────────────────────────────────── */
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

/* ── Next.js Link ────────────────────────────────────────────────────────── */
vi.mock("next/link", async () => {
  const { createElement } = await import("react");
  return {
    /**
     * Mock component for next/link
     * @param props - Link properties
     * @param props.href - The URL of the link.
     * @param props.children - The link content.
     * @param props.className - Optional CSS classes.
     * @returns {JSX.Element} Plain anchor element
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    default: ({ href, children, className, ...rest }: any) =>
      createElement("a", { href, className, ...rest }, children),
  };
});

/* ── Next.js Image ───────────────────────────────────────────────────────── */
vi.mock("next/image", async () => {
  const { createElement } = await import("react");
  return {
    /**
     * Mock component for next/image
     * @param props - Image properties
     * @param props.src - Image source URL.
     * @param props.alt - Accessible image description.
     * @param props.className - Optional CSS classes.
     * @param props.fill - Whether the image fills its container.
     * @param props.sizes - Responsive image sizes.
     * @param props.unoptimized - Whether image optimization is disabled.
     * @param props.priority - Whether the image is prioritized.
     * @param props.placeholder - Placeholder type.
     * @param props.blurDataURL - Placeholder image data URL.
     * @returns {JSX.Element} Plain image element
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    default: ({ src, alt, className, fill, sizes, unoptimized, priority, placeholder, blurDataURL, ...rest }: any) => {
      void fill;
      void sizes;
      void unoptimized;
      void priority;
      void placeholder;
      void blurDataURL;
      return createElement("img", { src, alt, className, ...rest });
    },
  };
});

/* ── Sonner toasts ───────────────────────────────────────────────────────── */
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
  /**
   * Mock component for Toaster
   * @returns null
   */
  Toaster: () => null,
}));

/* ── TanStack React Query ────────────────────────────────────────────────── */
vi.mock("@tanstack/react-query", async importOriginal => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQueryClient: vi.fn().mockReturnValue({
      clear: vi.fn(),
      invalidateQueries: vi.fn(),
      removeQueries: vi.fn(),
      resetQueries: vi.fn(),
      cancelQueries: vi.fn(),
      getQueryData: vi.fn(),
      setQueryData: vi.fn(),
    }),
  };
});

/* ── Axios ───────────────────────────────────────────────────────────────── */
vi.mock("axios", async importOriginal => {
  const actual = await importOriginal<typeof import("axios")>();
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    defaults: {
      baseURL: "/api",
      headers: { "Content-Type": "application/json" },
    },
  };

  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn().mockReturnValue(mockAxiosInstance),
    },
  };
});

/* ── next-intl ───────────────────────────────────────────────────────────── */
vi.mock("next-intl", async () => {
  const { default: messages } = await import("./messages/en.json");
  return {
    useLocale: () => "en",
    useTranslations: (namespace: string) => {
      const dictionary = messages[namespace as keyof typeof messages] as Record<string, unknown> | undefined;
      return (key: string, values?: Record<string, string>) => {
        let translation: unknown = dictionary;
        for (const segment of key.split(".")) {
          if (!translation || typeof translation !== "object") {
            translation = undefined;
            break;
          }
          translation = (translation as Record<string, unknown>)[segment];
        }

        if (typeof translation !== "string") return key;
        if (!values) return translation;
        return Object.entries(values).reduce(
          (result, [name, value]) => result.replaceAll(`{${name}}`, value),
          translation
        );
      };
    },
  };
});
