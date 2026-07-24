// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, afterEach } from "vitest";
import { CameraCapture } from "@/components/scanner/camera-capture";

// Mocks at top level
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: { success: true } }),
  },
}));

import { apiClient } from "@/lib/api/client";

describe("CameraCapture", () => {
  const originalMediaDevices = navigator.mediaDevices;

  afterEach(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: originalMediaDevices,
    });
    vi.restoreAllMocks();
  });

  const setupCamera = (hasVideo = true) => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        enumerateDevices: vi.fn().mockResolvedValue(hasVideo ? [{ kind: "videoinput" }] : []),
      },
    });
  };

  it("renders standard camera button when video inputs are present", async () => {
    setupCamera(true);
    render(<CameraCapture label="Snap Cover" />);
    await waitFor(() => {
      expect(screen.getByText("Snap Cover")).toBeInTheDocument();
      expect(screen.queryByText(/Drag & Drop/i)).not.toBeInTheDocument();
    });
  });

  it("renders Drag & Drop fallback when no video inputs are present (Desktop mode)", async () => {
    setupCamera(false);
    render(<CameraCapture label="Snap Cover" />);
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Browse Files/i })).toBeInTheDocument();
      expect(screen.queryByText("Snap Cover")).not.toBeInTheDocument();
    });
  });

  it("aborts enumeration on unmount", async () => {
    const abortSpy = vi.spyOn(AbortController.prototype, "abort");
    const { unmount } = render(<CameraCapture label="Snap Cover" />);
    unmount();
    expect(abortSpy).toHaveBeenCalled();
  });

  it("cover mode uploads file to correct cover endpoint", async () => {
    setupCamera(false);
    const onUploadComplete = vi.fn();
    vi.mocked(apiClient.post).mockResolvedValue({ data: { success: true } });

    render(
      <CameraCapture manifestation_id={42} mode="cover" label="Upload Cover" onUploadComplete={onUploadComplete} />
    );

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });

    const file = new File(["dummy"], "cover.jpg", { type: "image/jpeg" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/manifestations/42/cover",
        expect.any(FormData),
        expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" } })
      );
    });
  });

  it("gallery mode uploads file to images endpoint", async () => {
    setupCamera(false);
    const onGalleryUploadComplete = vi.fn();
    vi.mocked(apiClient.post).mockResolvedValue({ data: { success: true } });

    render(
      <CameraCapture
        manifestation_id={42}
        mode="gallery"
        label="Add Photo"
        galleryLabel="front"
        onGalleryUploadComplete={onGalleryUploadComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });

    const file = new File(["dummy"], "photo.jpg", { type: "image/jpeg" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/manifestations/42/images",
        expect.any(FormData),
        expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" } })
      );
    });
  });

  it("vision mode renders without crash", async () => {
    setupCamera(true);
    render(<CameraCapture label="Scan Book" mode="vision" format="book" />);
    await waitFor(() => {
      expect(screen.getByText("Scan Book")).toBeInTheDocument();
    });
  });

  it("drag and drop triggers file processing", async () => {
    setupCamera(false);
    render(<CameraCapture label="Snap Cover" />);

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });

    const dropZone = screen.getByText(/Drag & Drop cover image here/i).closest("div.w-full");
    expect(dropZone).toBeInTheDocument();

    if (dropZone) {
      fireEvent.dragOver(dropZone);
    }

    // Component doesn't crash after drag
    expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
  });

  it("confirmation dialog appears when confirmTitle and confirmMessage are provided", async () => {
    setupCamera(false);

    render(
      <CameraCapture
        label="Confirm Upload"
        confirmTitle="Are you sure?"
        confirmMessage="This will upload the cover image."
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Browse Files/i }));

    await waitFor(() => {
      expect(screen.getByText("Are you sure?")).toBeInTheDocument();
      expect(screen.getByText("This will upload the cover image.")).toBeInTheDocument();
      expect(screen.getByText("Continue")).toBeInTheDocument();
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });
  });

  it("error handling on upload failure - component does not crash", async () => {
    setupCamera(false);
    vi.mocked(apiClient.post).mockRejectedValue(new Error("Upload failed"));

    render(<CameraCapture manifestation_id={42} mode="cover" label="Upload Cover" />);

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });

    const file = new File(["dummy"], "cover.jpg", { type: "image/jpeg" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    if (input) {
      fireEvent.change(input, { target: { files: [file] } });
    }

    // Component should not crash (error is handled in catch block)
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop cover image here/i)).toBeInTheDocument();
    });
  });
});
