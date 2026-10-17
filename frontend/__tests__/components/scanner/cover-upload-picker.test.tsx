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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { CoverUploadPicker } from "@/components/scanner/cover-upload-picker";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/hooks";
import type { Manifestation } from "@/types/frbr";

// Mock next-intl translations
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) =>
    ({
      "cameraCapture.snapCover": "Snap Cover",
      "cameraCapture.takePhoto": "Take Photo",
      "cameraCapture.chooseFromGallery": "Choose from Gallery",
      "cameraCapture.cancel": "Cancel",
      "cameraCapture.continue": "Continue",
      "cameraCapture.processing": "Processing...",
      "cameraCapture.processImageFailed": "Failed to process cover image",
    })[key] ?? key,
}));

// Mock API Client
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: { success: true } }),
  },
}));

// Mock Sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";

describe("CoverUploadPicker Component", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderComponent = (props: React.ComponentProps<typeof CoverUploadPicker>) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CoverUploadPicker {...props} />
      </QueryClientProvider>
    );
  };

  describe("2.1 Camera vs File Selection Triggering", () => {
    it("renders Contribute Cover trigger without replacement modal when no cover exists", () => {
      renderComponent({
        manifestation_id: 42,
        label: "Contribute Cover",
      });

      expect(screen.getByRole("button", { name: /Contribute Cover/i })).toBeInTheDocument();
      expect(screen.queryByText(/Replace Existing Cover/i)).not.toBeInTheDocument();
      expect(screen.getByTestId("camera-file-input")).toBeInTheDocument();
      expect(screen.getByTestId("gallery-file-input")).toBeInTheDocument();
    });

    it("opens dropdown menu and triggers camera input upon selecting Take Photo", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Contribute Cover",
      });

      const cameraInput = screen.getByTestId("camera-file-input") as HTMLInputElement;
      const clickSpy = vi.spyOn(cameraInput, "click");

      // Open dropdown
      const button = screen.getByRole("button", { name: /Contribute Cover/i });
      fireEvent.pointerDown(button, { pointerType: "mouse" });
      fireEvent.click(button);

      const takePhotoItem = await screen.findByTestId("menu-take-photo");
      expect(takePhotoItem).toBeInTheDocument();

      fireEvent.click(takePhotoItem);
      expect(clickSpy).toHaveBeenCalled();
    });

    it("opens dropdown menu and triggers gallery input upon selecting Choose from Gallery", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Contribute Cover",
      });

      const galleryInput = screen.getByTestId("gallery-file-input") as HTMLInputElement;
      const clickSpy = vi.spyOn(galleryInput, "click");

      // Open dropdown
      const button = screen.getByRole("button", { name: /Contribute Cover/i });
      fireEvent.pointerDown(button, { pointerType: "mouse" });
      fireEvent.click(button);

      const chooseGalleryItem = await screen.findByTestId("menu-choose-gallery");
      expect(chooseGalleryItem).toBeInTheDocument();

      fireEvent.click(chooseGalleryItem);
      expect(clickSpy).toHaveBeenCalled();
    });

    it("uploads file selected via camera with scanner_camera source binding", async () => {
      const onUploadComplete = vi.fn();
      renderComponent({
        manifestation_id: 42,
        format: "cd",
        onUploadComplete,
      });

      const file = new File(["dummy camera content"], "photo.jpg", { type: "image/jpeg" });
      const cameraInput = screen.getByTestId("camera-file-input");

      fireEvent.change(cameraInput, { target: { files: [file] } });

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledTimes(1);
      });

      const [endpoint, formData] = vi.mocked(apiClient.post).mock.calls[0] as [string, FormData, unknown];
      expect(endpoint).toBe("/manifestations/42/cover");
      expect(formData.get("source")).toBe("scanner_camera");
      expect(formData.get("format")).toBe("cd");
      expect(formData.get("cover")).toBe(file);
      expect(onUploadComplete).toHaveBeenCalled();
    });

    it("uploads file selected via gallery with user_upload source binding", async () => {
      const onUploadComplete = vi.fn();
      renderComponent({
        manifestation_id: 99,
        format: "book",
        onUploadComplete,
      });

      const file = new File(["dummy gallery content"], "cover.png", { type: "image/png" });
      const galleryInput = screen.getByTestId("gallery-file-input");

      fireEvent.change(galleryInput, { target: { files: [file] } });

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledTimes(1);
      });

      const [endpoint, formData] = vi.mocked(apiClient.post).mock.calls[0] as [string, FormData, unknown];
      expect(endpoint).toBe("/manifestations/99/cover");
      expect(formData.get("source")).toBe("user_upload");
      expect(formData.get("format")).toBe("book");
      expect(formData.get("cover")).toBe(file);
      expect(onUploadComplete).toHaveBeenCalled();
    });
  });

  describe("2.2 Optimistic Cache Update", () => {
    it("updates optimistic manifestation cache with cover_status: 'processing' on completion", async () => {
      const initialManifestation: Manifestation = {
        id: 42,
        expression_id: 1,
        cover_url: null,
        meta: { cover_status: "ready" },
      } as unknown as Manifestation;

      queryClient.setQueryData(queryKeys.manifestation(42), initialManifestation);

      const handleUploadComplete = () => {
        queryClient.setQueryData(queryKeys.manifestation(42), (prev: Manifestation | undefined) => {
          if (!prev) return prev;
          return {
            ...prev,
            meta: { ...(prev.meta || {}), cover_status: "processing" },
          };
        });
      };

      renderComponent({
        manifestation_id: 42,
        onUploadComplete: handleUploadComplete,
      });

      const file = new File(["test data"], "cover.webp", { type: "image/webp" });
      fireEvent.change(screen.getByTestId("gallery-file-input"), { target: { files: [file] } });

      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalled();
      });

      const cached = queryClient.getQueryData<Manifestation>(queryKeys.manifestation(42));
      expect(cached?.meta?.cover_status).toBe("processing");
    });
  });

  describe("2.3 Replacement Confirmation Modal", () => {
    it("renders confirmation modal when confirmTitle and confirmMessage are provided", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Replace Cover",
        confirmTitle: "Replace Existing Cover?",
        confirmMessage: "This manifestation already has a cover. Are you sure you want to replace it?",
      });

      // Dialog is not visible before clicking Replace Cover
      expect(screen.queryByText("Replace Existing Cover?")).not.toBeInTheDocument();

      // Click Replace Cover button
      fireEvent.click(screen.getByRole("button", { name: /Replace Cover/i }));

      // Confirmation dialog should be visible
      expect(await screen.findByText("Replace Existing Cover?")).toBeInTheDocument();
      expect(
        screen.getByText("This manifestation already has a cover. Are you sure you want to replace it?")
      ).toBeInTheDocument();
      expect(screen.getByTestId("confirm-take-photo")).toBeInTheDocument();
      expect(screen.getByTestId("confirm-choose-gallery")).toBeInTheDocument();
    });

    it("cancels replacement without triggering any input", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Replace Cover",
        confirmTitle: "Replace Existing Cover?",
        confirmMessage: "Warning about overwriting cover.",
      });

      const cameraInput = screen.getByTestId("camera-file-input") as HTMLInputElement;
      const galleryInput = screen.getByTestId("gallery-file-input") as HTMLInputElement;
      const cameraSpy = vi.spyOn(cameraInput, "click");
      const gallerySpy = vi.spyOn(galleryInput, "click");

      fireEvent.click(screen.getByRole("button", { name: /Replace Cover/i }));
      expect(await screen.findByText("Replace Existing Cover?")).toBeInTheDocument();

      // Click Cancel
      fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));

      expect(cameraSpy).not.toHaveBeenCalled();
      expect(gallerySpy).not.toHaveBeenCalled();
    });

    it("allows user to confirm with camera option from replacement modal", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Replace Cover",
        confirmTitle: "Replace Existing Cover?",
        confirmMessage: "Warning about overwriting cover.",
      });

      const cameraInput = screen.getByTestId("camera-file-input") as HTMLInputElement;
      const cameraSpy = vi.spyOn(cameraInput, "click");

      fireEvent.click(screen.getByRole("button", { name: /Replace Cover/i }));
      expect(await screen.findByText("Replace Existing Cover?")).toBeInTheDocument();

      // Click Take Photo option inside confirmation dialog
      fireEvent.click(screen.getByTestId("confirm-take-photo"));
      expect(cameraSpy).toHaveBeenCalled();
    });

    it("allows user to confirm with gallery option from replacement modal", async () => {
      renderComponent({
        manifestation_id: 42,
        label: "Replace Cover",
        confirmTitle: "Replace Existing Cover?",
        confirmMessage: "Warning about overwriting cover.",
      });

      const galleryInput = screen.getByTestId("gallery-file-input") as HTMLInputElement;
      const gallerySpy = vi.spyOn(galleryInput, "click");

      fireEvent.click(screen.getByRole("button", { name: /Replace Cover/i }));
      expect(await screen.findByText("Replace Existing Cover?")).toBeInTheDocument();

      // Click Choose from Gallery option inside confirmation dialog
      fireEvent.click(screen.getByTestId("confirm-choose-gallery"));
      expect(gallerySpy).toHaveBeenCalled();
    });

    it("handles upload failure gracefully and alerts with error toast", async () => {
      vi.mocked(apiClient.post).mockRejectedValueOnce(new Error("Network Error"));

      renderComponent({
        manifestation_id: 42,
      });

      const file = new File(["test data"], "cover.jpg", { type: "image/jpeg" });
      fireEvent.change(screen.getByTestId("camera-file-input"), { target: { files: [file] } });

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Network Error");
      });
    });
  });
});
