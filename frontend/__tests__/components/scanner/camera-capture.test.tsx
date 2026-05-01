// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, afterEach } from "vitest";
import { CameraCapture } from "@/components/scanner/camera-capture";

describe("CameraCapture", () => {
  const originalMediaDevices = navigator.mediaDevices;

  afterEach(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: originalMediaDevices,
    });
    vi.restoreAllMocks();
  });

  it("renders standard camera button when video inputs are present", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        enumerateDevices: vi.fn().mockResolvedValue([{ kind: "videoinput" }]),
      },
    });

    render(<CameraCapture label="Snap Cover" />);

    await waitFor(() => {
      expect(screen.getByText("Snap Cover")).toBeInTheDocument();
      expect(screen.queryByText(/Drag & Drop/i)).not.toBeInTheDocument();
    });
  });

  it("renders Drag & Drop fallback when no video inputs are present (Desktop mode)", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        enumerateDevices: vi.fn().mockResolvedValue([{ kind: "audioinput" }]), // No video
      },
    });

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
});
