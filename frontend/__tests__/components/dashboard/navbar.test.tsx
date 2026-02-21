/**
 * Tests for the Navbar component.
 *
 * next/link and next/navigation are mocked globally in vitest.setup.ts.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Navbar } from "@/components/dashboard/navbar";

describe("Navbar", () => {
  it("renders the iqoqo brand name", () => {
    render(<Navbar />);
    expect(screen.getByText("iqoqo")).toBeInTheDocument();
  });

  it("renders a search input", () => {
    render(<Navbar />);
    expect(
      screen.getByPlaceholderText("Search your collection..."),
    ).toBeInTheDocument();
  });

  it("contains a link to the Collection page", () => {
    render(<Navbar />);
    const link = screen.getByRole("link", { name: /collection/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("contains a link to the Scan page", () => {
    render(<Navbar />);
    const links = screen.getAllByRole("link");
    const scanLink = links.find((l) => l.getAttribute("href") === "/scan");
    expect(scanLink).toBeDefined();
  });

  it("contains a link to the home page via the brand", () => {
    render(<Navbar />);
    const homeLink = screen.getByRole("link", { name: /iqoqo/i });
    expect(homeLink).toHaveAttribute("href", "/");
  });
});
