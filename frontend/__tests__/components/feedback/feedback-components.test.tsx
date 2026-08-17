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
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FeedbackModal } from "@/components/feedback/feedback-modal";
import { FeedbackDetailModal } from "@/components/feedback/feedback-detail-modal";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

describe("FeedbackModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.post).mockReset();
  });

  it("submits feedback and transitions to success state with Close button", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { success: true } } as any);
    const onOpenChange = vi.fn();
    const onSuccess = vi.fn();

    render(<FeedbackModal open={true} onOpenChange={onOpenChange} onSuccess={onSuccess} />);

    expect(screen.getByText("Send feedback")).toBeInTheDocument();
    const textarea = screen.getByPlaceholderText("Describe the issue or idea...");
    fireEvent.change(textarea, { target: { value: "Test bug report description" } });

    const submitBtn = screen.getByRole("button", { name: "Submit feedback" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/feedback",
        expect.any(FormData),
        expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" } })
      );
    });

    // Form disappears and success state appears
    await waitFor(() => {
      expect(screen.getByText("Feedback Submitted")).toBeInTheDocument();
      expect(screen.getByText("Thanks — your feedback was successfully submitted and logged.")).toBeInTheDocument();
    });

    expect(screen.queryByPlaceholderText("Describe the issue or idea...")).not.toBeInTheDocument();
  });

  it("keeps submission disabled until a description is entered", () => {
    render(<FeedbackModal open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Submit feedback" })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("Describe the issue or idea..."), {
      target: { value: "A useful report" },
    });
    expect(screen.getByRole("button", { name: "Submit feedback" })).toBeEnabled();
  });

  it("sends the selected type and screenshot in multipart form data", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { success: true } } as any);
    render(<FeedbackModal open={true} onOpenChange={vi.fn()} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "feature_request" } });
    fireEvent.change(screen.getByPlaceholderText("Describe the issue or idea..."), {
      target: { value: "Please add keyboard shortcuts" },
    });
    const file = new File(["image"], "screen.png", { type: "image/png" });
    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    const form = vi.mocked(apiClient.post).mock.calls[0][1] as FormData;
    expect(form.get("type")).toBe("feature_request");
    expect(form.get("description")).toBe("Please add keyboard shortcuts");
    expect(form.get("screenshots")).toEqual(file);
  });

  it("shows the API error and remains in the form state", async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error("Upload failed"));
    render(<FeedbackModal open={true} onOpenChange={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("Describe the issue or idea..."), {
      target: { value: "A report that cannot be uploaded" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    expect(await screen.findByText("Upload failed")).toBeInTheDocument();
    expect(screen.getByText("Send feedback")).toBeInTheDocument();
  });
});

describe("FeedbackDetailModal", () => {
  const mockItem = {
    id: 42,
    user_id: "user-123",
    user_display_name: "Test User",
    user_email: "test@example.com",
    feedback_type: "bug",
    description: "Detailed bug description here",
    status: "new",
    attachments: [],
    comments: [
      {
        id: "c1",
        user_id: "admin-999",
        user_display_name: "Admin Support",
        comment: "We are reviewing this.",
        created_at: "2026-08-14T07:00:00Z",
      },
    ],
    comments_count: 1,
    created_at: "2026-08-14T06:00:00Z",
    updated_at: "2026-08-14T07:00:00Z",
  };

  it("renders ticket details and allows admin to change status and post comments", async () => {
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ data: { success: true } } as any);
    const onUpdated = vi.fn();

    render(
      <FeedbackDetailModal
        item={mockItem}
        open={true}
        onOpenChange={vi.fn()}
        isAdmin={true}
        currentUserId="admin-999"
        onUpdated={onUpdated}
      />
    );

    expect(screen.getByText("Ticket #42")).toBeInTheDocument();
    expect(screen.getAllByText("Detailed bug description here").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Admin Support")).toBeInTheDocument();
    expect(screen.getByText("We are reviewing this.")).toBeInTheDocument();

    // Admin status select
    const statusSelect = screen.getByRole("combobox");
    fireEvent.change(statusSelect, { target: { value: "in_progress" } });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/feedback/42", { status: "in_progress" });
      expect(onUpdated).toHaveBeenCalled();
    });
  });

  it("renders image attachments when provided", () => {
    const itemWithAttachments = {
      ...mockItem,
      attachments: ["/static/gallery/feedback-screenshot1.jpg", "/static/gallery/feedback-screenshot2.jpg"],
    };

    render(
      <FeedbackDetailModal
        item={itemWithAttachments}
        open={true}
        onOpenChange={vi.fn()}
        isAdmin={false}
        currentUserId="user-123"
        onUpdated={vi.fn()}
      />
    );

    expect(screen.getByText("Attachments (2)")).toBeInTheDocument();
    const images = screen.getAllByRole("img");
    expect(images.length).toBeGreaterThanOrEqual(2);
  });
});
