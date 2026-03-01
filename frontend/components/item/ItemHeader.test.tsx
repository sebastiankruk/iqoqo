import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ItemHeader } from "@/components/item/item-header";
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

// Mock the hooks
vi.mock("@/lib/api/hooks", async () => {
  const actual = await vi.importActual("@/lib/api/hooks");
  return {
    ...actual,
    useManifestationWithPolling: vi.fn(),
    useRegenerateCover: vi.fn(),
  };
});

const mockItem: Item = {
  id: 1,
  owner_id: "user1",
  status: "available",
  title: "Test Book",
  authors: ["Test Author"],
  manifestation_id: 123,
  cover_status: "ready",
  meta: {},
  added_at: "2024-01-01",
  updated_at: "2024-01-01",
};

describe("ItemHeader", () => {
  const setItemMock = vi.fn();
  const mutateAsyncMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    vi.mocked(hooks.useManifestationWithPolling).mockReturnValue({
      item: mockItem,
      setItem: setItemMock,
    });

    vi.mocked(hooks.useRegenerateCover).mockReturnValue({
      mutateAsync: mutateAsyncMock,
    } as unknown as ReturnType<typeof hooks.useRegenerateCover>);
  });

  it("renders title and authors", () => {
    render(<ItemHeader item={mockItem} />);
    expect(screen.getByText("Test Book")).toBeInTheDocument();
    expect(screen.getByText("Test Author")).toBeInTheDocument();
  });

  it("calls regenerate mutation when button is clicked", async () => {
    render(<ItemHeader item={mockItem} />);

    const button = screen.getByRole("button", { name: /regenerate cover/i });
    fireEvent.click(button);

    expect(mutateAsyncMock).toHaveBeenCalledWith(123);

    await waitFor(() => {
      // Should optimistically update local state
      expect(setItemMock).toHaveBeenCalled();
    });
  });

  it("disables button and shows loading text when pending", () => {
    const pendingItem = { ...mockItem, cover_status: "pending" };

    vi.mocked(hooks.useManifestationWithPolling).mockReturnValue({
      item: pendingItem,
      setItem: setItemMock,
    });

    render(<ItemHeader item={pendingItem} />);

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(screen.getByText("Generating...")).toBeInTheDocument();
  });
});
