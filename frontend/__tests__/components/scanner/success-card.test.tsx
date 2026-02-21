/**
 * Tests for the SuccessCard component.
 *
 * Simulates post-scan state: the card receives isbn + meta props, lets the
 * user dismiss the result or add the book to the library.
 *
 * Mocks:
 * - next/navigation (useRouter) – global in vitest.setup.ts
 * - sonner (toast) – global in vitest.setup.ts
 * - @/lib/api/client (apiClient.post) – per-test via the mock factory below
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  apiFetch: vi.fn(),
}));

import { apiClient } from "@/lib/api/client";
import { SuccessCard } from "@/components/scanner/success-card";

const mockPush = vi.fn();
const mockApiPost = vi.mocked(apiClient.post);
const mockToastSuccess = vi.mocked(toast.success);
const mockToastError = vi.mocked(toast.error);

const SAMPLE_META = {
  Title: "Dune",
  Authors: ["Frank Herbert"],
  Publisher: "Chilton Books",
  Year: "1965",
  "ISBN-13": "9780441013593",
};

describe("SuccessCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    } as ReturnType<typeof useRouter>);
  });

  it("displays the book title from meta", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
  });

  it("displays the author name", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Frank Herbert")).toBeInTheDocument();
  });

  it("shows a 'Book Found' success header", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Book Found")).toBeInTheDocument();
  });

  it("calls onDismiss when the header X button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss result/i }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls onDismiss when the bottom Dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls apiClient.post and shows success toast when 'Add to Library' succeeds", async () => {
    mockApiPost.mockResolvedValueOnce({ data: { item_id: 99 } });
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add to library/i }));
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/item/9780441013593", SAMPLE_META);
      expect(mockToastSuccess).toHaveBeenCalledWith('"Dune" added to your library!');
      expect(mockPush).toHaveBeenCalledWith("/item/99");
    });
  });

  it("shows an error toast when 'Add to Library' fails", async () => {
    mockApiPost.mockRejectedValueOnce(new Error("Network error"));
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add to library/i }));
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Network error");
    });
  });

  it("displays the ISBN under the title", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText(/isbn: 9780441013593/i)).toBeInTheDocument();
  });
});
