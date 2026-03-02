import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ItemHeader } from "./item-header";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";

// Mock dependencies
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock Item data
const mockItem = {
  id: 1,
  manifestation_id: 123,
  title: "Fallback Title",
  work: {
    title: "The Great Gatsby",
    authors: ["F. Scott Fitzgerald"],
  },
  manifestation_meta: {
    cover_status: "ready",
    Year: "1925",
    Pages: "180",
  },
} as any;

describe("ItemHeader", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    // Mock window.location.reload
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { reload: vi.fn() },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("renders item information correctly", () => {
    render(<ItemHeader item={mockItem} />);

    expect(screen.getByText("The Great Gatsby")).toBeInTheDocument();
    expect(screen.getByText("F. Scott Fitzgerald")).toBeInTheDocument();
    expect(screen.getByText("1925")).toBeInTheDocument();
    expect(screen.getByText("180 pages")).toBeInTheDocument();
  });

  it("triggers cover regeneration", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { success: true } });

    render(<ItemHeader item={mockItem} />);

    const regenBtn = screen.getByText("Regenerate Cover");
    fireEvent.click(regenBtn);

    expect(regenBtn).toBeDisabled();
    expect(screen.getByText("Generating...")).toBeInTheDocument();

    expect(apiClient.post).toHaveBeenCalledWith("/api/manifestations/123/regenerate-cover");

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Cover regeneration started");
    });
  });

  it("triggers metadata refetch", async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { success: true } });

    render(<ItemHeader item={mockItem} />);

    const refetchBtn = screen.getByText("Refetch Metadata");
    fireEvent.click(refetchBtn);

    expect(refetchBtn).toBeDisabled();
    expect(screen.getByText("Fetching...")).toBeInTheDocument();

    expect(apiClient.post).toHaveBeenCalledWith("/api/manifestations/123/refetch-metadata");

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("Metadata refetched"));
      // Should reload page on success
      expect(window.location.reload).toHaveBeenCalled();
    });
  });
});
