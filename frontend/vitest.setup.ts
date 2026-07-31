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
    /**
     * Mock component for next/link
     * @param props - Component props
     * @param props.href - The URL of the link.
     * @param props.children - The content of the link.
     * @param props.className - The CSS class names for the link.
     * @returns {JSX.Element} React element
     */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    default: ({ href, children, className, ...rest }: any) =>
      createElement("a", { href, className, ...rest }, children),
  };
});
/* ── Next.js Image ───────────────────────────────────────────────────────
 * Render as a plain <img> so RTL assertions on src/alt work normally and
 * we don't need a real Next.js image-optimization server running.          */
vi.mock("next/image", async () => {
  const { createElement } = await import("react");
  return {
    // Strips Next.js-specific props (fill, sizes, unoptimized, priority) so
    // only standard <img> attributes are forwarded to the DOM element.
    /**
     * Mock component for next/image
     * @param props - Component props
     * @param props.src - The image source URL.
     * @param props.alt - The image alt text.
     * @param props.className - The CSS class names for the image.
     * @param props.fill - Whether the image should fill the container.
     * @param props.sizes - Image sizes attribute.
     * @param props.unoptimized - Whether the image should be unoptimized.
     * @param props.priority - Whether the image has high priority.
     * @param props.placeholder - Image placeholder type.
     * @param props.blurDataURL - Image blur data URL.
     * @returns {JSX.Element} React element
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
/* ── Sonner toasts ─────────────────────────────────────────────────────────
 * Replace with no-op spies – tests that care can assert on these calls.   */
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

/* ── TanStack React Query ──────────────────────────────────────────────────
 * Stub useQueryClient so components that call it (e.g. Navbar clears cache
 * on logout) work in unit tests without a real QueryClientProvider wrapper.
 * All other exports (useQuery, useMutation, …) are forwarded to the real
 * library so per-test mocks of hooks like useProfile still work normally.  */
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

/* ── Global axios mock ────────────────────────────────────────────────────── */
vi.mock("axios", async importOriginal => {
  const actual = await importOriginal<typeof import("axios")>();
  const mockAxiosInstance = {
    get: vi.fn().mockResolvedValue({ data: { success: true, data: [] } }),
    post: vi.fn().mockResolvedValue({ data: { success: true, data: {} } }),
    put: vi.fn().mockResolvedValue({ data: { success: true, data: {} } }),
    delete: vi.fn().mockResolvedValue({ data: { success: true, data: {} } }),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    defaults: {
      baseURL: "/api",
      headers: {
        "Content-Type": "application/json",
      },
    },
  };

  return {
    default: {
      ...actual.default,
      create: vi.fn().mockReturnValue(mockAxiosInstance),
    },
  };
});

/* ── next-intl mock ──────────────────────────────────────────────────────── */
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace: string) => {
    const dictionaries: Record<string, Record<string, string>> = {
      Navbar: {
        maintenanceMode: "Maintenance Mode Active – Some features may be limited",
        searchPlaceholder: "Search your collection...",
        collection: "Collection",
        scan: "Scan",
        signIn: "Sign In",
        publicProfile: "Public Profile",
        profileSettings: "Profile Settings",
        manageCollections: "Manage Collections",
        adminConfiguration: "Admin Configuration",
        logOut: "Log out",
        home: "Home",
        profile: "Profile",
        languageSubmenu: "Language",
        themeSubmenu: "Theme",
        themeLight: "Light",
        themeDark: "Dark",
        themeSystem: "System",
      },
      Dashboard: {
        welcomeBack: "Welcome back, {name}",
        collectionGrowing: "Your collection is growing nicely. Here is what is happening.",
      },
      Hero: {
        title: "The Library of Everything",
        description:
          "iqoqo empowers you to create, share, and discover personal catalogs of books, music, movies, and board games. Built on the open Semantic Web, designed for a distributed future.",
        startCatalog: "Start Your Catalog",
        browseInstance: "Browse Instance",
        github: "GitHub",
      },
      GlobalStats: {
        works: "Works",
        manifestations: "Manifestations",
        itemsTracked: "Items Tracked",
        curators: "Curators",
      },
      StatsCards: {
        items: "Items",
        itemsDesc: "Total in collection",
        reading: "Reading",
        readingDesc: "Currently active reads",
        wishList: "On Wish List",
        wishListDesc: "On your list",
        lentOut: "Lent Out",
        lentOutDesc: "Currently with friends",
        borrowed: "Borrowed",
        borrowedDesc: "Borrowed from others",
        ariaLabel: "Collection statistics",
      },
      CurrentContext: {
        ariaLabelActive: "Currently active items",
        titleBoth: "Currently Reading and Wish List",
        emptyState: "Your “Currently Reading and Wish List” is empty. ",
        browseCollection: "Browse your collection",
        toAddItems: " to add items.",
        ariaLabelReading: "Currently reading items",
        titleReading: "Currently Reading",
        active: "active",
        ariaLabelWishList: "Wish list items",
        titleWishList: "Wish List",
      },
      FreshArrivals: {
        ariaLabel: "Recently added items",
        title: "Fresh Arrivals",
        errorLoad: "Could not load items — the API may be unavailable.",
        latest: "Latest",
        rssTitle: "Subscribe to Fresh Arrivals RSS feed",
        viewGlobal: "View global library",
        generating: "Generating...",
        processing: "Processing...",
        untitled: "Untitled",
        unknown: "Unknown",
      },
      Footer: {
        libraryOfEverything: "The Library of Everything",
        githubSponsors: "GitHub Sponsors",
        buyMeACoffee: "Buy Me a Coffee",
        rules: "Your library, your rules.",
      },
      Login: {
        title: "Sign in to iqoqo",
        googleSignIn: "Sign in with Google",
        or: "Or",
        emailPlaceholder: "Email",
        passwordPlaceholder: "Password",
        signInButton: "Sign In",
        noAccount: "Don't have an account? ",
        signUp: "Sign up",
        loginFailed: "Login failed",
      },
      Register: {
        title: "Create an account",
        subtitle: "Join the distributed library",
        googleSignUp: "Sign up with Google",
        orEmail: "Or continue with email",
        displayNamePlaceholder: "Display Name (Optional)",
        emailPlaceholder: "Email",
        passwordPlaceholder: "Password",
        agreeTerms: "I agree to the ",
        termsOfService: "Terms of Service",
        and: " and ",
        privacyPolicy: "Privacy Policy",
        signUpButton: "Sign Up",
        alreadyAccount: "Already have an account? ",
        signIn: "Sign in",
        mustAcceptTerms: "You must accept the Terms of Service and Privacy Policy.",
        registrationFailed: "Registration failed. Please try again.",
      },
      NotFound: {
        title: "404 - Page Not Found",
        description: "The page you are looking for does not exist, has been removed, or has been made private.",
        goBackHome: "Go back home",
      },
      CookieConsent: {
        haikuLine1: "Small crumbs of data,",
        haikuLine2: "Guide your journey through the books,",
        haikuLine3: "Accept and read on.",
        privacyPolicy: "Privacy Policy",
        gotIt: "Got it",
      },
      Manifestation: {
        notFound: "Manifestation not found.",
        contributeCover: "Contribute Cover",
        coverContributed: "Cover contributed! Processing started.",
        unknownAuthor: "Unknown Author",
        browseAuthor: "Browse all works by {author}",
        pubDetails: "Publication Details",
        isbn13: "ISBN-13",
        ean: "EAN",
        upc: "UPC",
        publisher: "Publisher",
        year: "Year",
        language: "Language",
        indexedTags: "Indexed Tags",
        seriesComplexParts: "Series / Complex Work Parts",
        inCollection: "In Collection",
        currentEdition: "Current Edition",
        viewMyItem: "View My Item",
        viewInCollection: "View in Collection",
        ownedByOne: "Owned by {count} person",
        ownedByMultiple: "Owned by {count} people",
        reviewsFeedback: "Reviews & Feedback",
        tabWork: "Conceptual Work",
        descWork: "Story / artistic creation",
        tabExpression: "Expression",
        descExpression: "Realization (Language/Format)",
        tabEdition: "Edition",
        descEdition: "Printed publication (ISBN)",
        feedbackTitleWork: "Conceptual Work",
        feedbackTitleExpression: "Expression",
        feedbackTitleManifestation: "Manifestation Edition",
        book: "Book",
        movie: "Movie",
        music: "Music",
        game: "Game",
        seriesSuffix: "{label} (Series)",
        cdAudio: "CD / Audio",
      },
      Collection: {
        loading: "Loading collection...",
        searchResults: 'Search results for "{query}"',
        title: "Collection",
        browseAuthor: "Browse all items by {author}",
        foundOne: "Found 1 item",
        foundMultiple: "Found {count} items",
        browseManage: "Browse and manage your library",
        tabMyItems: "My Items",
        tabGlobalLibrary: "Global Library",
        tabExpressions: "Expressions",
        tabWorks: "Works",
        tabRoadmaps: "Roadmaps",
        searchPlaceholder: "Search title, author, or ISBN...",
        filters: "Filters",
        noWorksMatching: 'No works matching "{query}"',
        noWorksInCollection: "No works in collection",
        tryAdjusting: "Try adjusting your search or filters.",
        itemsCountOne: "1 item",
        itemsCountMultiple: "{count} items",
        viewManifestation: "View manifestation",
        viewMyItem: "View my item",
        edition: "Edition",
        myItem: "My Item",
        noExpressionsMatching: 'No expressions matching "{query}"',
        noExpressionsInCollection: "No expressions in collection",
      },
      CollectionFilters: {
        title: "Filters",
        secMediaCategory: "Media Category",
        secMyCollections: "My Collections",
        secTags: "Tags",
        secGenres: "Genres",
        secPublishers: "Publishers",
        secPhysicalKind: "Physical Kind",
        secCollectionStatus: "Collection Status",
        secProgress: "Progress",
        secCuration: "Curation",
        statusHelp: 'Status filters apply to physical items only. Switch to "My Items" view to filter by status.',
        notApplicable: "Not applicable here.",
        noCover: "No Cover",
        noId: "No ID",
        findCollection: "Find collection...",
        findTag: "Find tag...",
        findGenre: "Find genre...",
        findPublisher: "Find publisher...",
        filterDrawer: "Filter drawer",
        closeFilters: "Close filters",
        showResults: "Show Results",
        noMatches: "No matches.",
        cat_text: "Text",
        cat_audiobook: "Audiobook",
        cat_music: "Music",
        cat_movie: "Movie",
        cat_board_game: "Board Game",
        cat_puzzle: "Puzzle",
        status_wish_list: "On Wish List",
        status_ordered: "Ordered",
        status_available: "On Shelf",
        status_borrowed: "Borrowed by me",
        status_lent: "Lent Out",
        status_damaged: "Damaged",
        status_lost: "Lost",
        progress_want_to_read: "Want to Read",
        progress_reading: "Reading",
        progress_read: "Read",
        progress_want_to_listen: "Want to Listen",
        progress_listening: "Listening",
        progress_listened: "Listened",
        progress_want_to_watch: "Want to Watch",
        progress_watching: "Watching",
        progress_watched: "Watched",
        progress_want_to_play: "Want to Play",
        progress_playing: "Playing",
        progress_played: "Played",
        fmt_book: "Book",
        fmt_cd: "CD",
        fmt_vinyl: "Vinyl",
        fmt_dvd: "DVD",
        fmt_bluray: "Blu-ray",
        fmt_audiobook_cd: "Audiobook CD",
        fmt_cassette: "Cassette",
        fmt_graphic_novel: "Graphic Novel / TPB",
        fmt_comic_book: "Comic Book (Single Issue)",
        fmt_magazine: "Magazine",
        fmt_ebook: "eBook",
        fmt_audiobook_cassette: "Audiobook Cassette",
        fmt_audiobook_digital: "Digital Audiobook",
        fmt_sacd: "SACD",
        fmt_minidisc: "MiniDisc",
        fmt_cd_dvd_combo: "CD + DVD Edition",
        fmt_bluray_audio: "Blu-ray Pure Audio",
        fmt_4k_uhd: "4K UHD",
        fmt_vcd: "Video CD (VCD)",
        fmt_vhs: "VHS",
        fmt_laserdisc: "LaserDisc",
        fmt_board_game: "Board Game",
        fmt_cards: "Card Game",
        fmt_rpg_manual: "RPG Manual",
        fmt_miniatures: "Miniatures / Wargame",
        fmt_jigsaw_puzzle: "Jigsaw Puzzle",
        fmt_mechanical_puzzle: "Mechanical / 3D Puzzle",
        fmt_unknown_text: "Unknown Text Format",
        fmt_unknown_audio: "Unknown Audio Format",
        fmt_unknown_video: "Unknown Video Format",
      },
    };

    const dictionary = dictionaries[namespace] || {};
    return (key: string, values?: Record<string, string>) => {
      let translation = dictionary[key] || key;
      if (values) {
        Object.entries(values).forEach(([k, v]) => {
          translation = translation.replace(`{${k}}`, v);
        });
      }
      return translation;
    };
  },
}));
