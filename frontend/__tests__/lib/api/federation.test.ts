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
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listFederationInstances,
  addFederationInstance,
  updateFederationInstance,
  deleteFederationInstance,
  listFederationActivities,
  getFederationKeyFingerprint,
} from "@/lib/api/federation";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Federation Admin API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("listFederationInstances", () => {
    it("fetches instances successfully", async () => {
      const mockInstances = [
        {
          id: 1,
          domain: "library.alpha.org",
          software_name: "iqoqo",
          software_version: "0.9.1",
          trust_level: "trusted",
          last_seen_at: "2026-10-21T00:00:00Z",
          created_at: "2026-10-20T00:00:00Z",
        },
      ];

      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: mockInstances },
      } as any);

      const result = await listFederationInstances();
      expect(apiClient.get).toHaveBeenCalledWith("/v1/admin/federation/instances");
      expect(result).toEqual(mockInstances);
    });

    it("throws error when response indicates failure", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: false, error: "Unauthorized" },
      } as any);

      await expect(listFederationInstances()).rejects.toThrow("Unauthorized");
    });
  });

  describe("addFederationInstance", () => {
    it("adds a new peer instance via domain probe", async () => {
      const mockCreated = {
        id: 2,
        domain: "library.beta.org",
        trust_level: "pending",
        software_name: "iqoqo",
      };

      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { success: true, data: mockCreated },
      } as any);

      const result = await addFederationInstance("library.beta.org");
      expect(apiClient.post).toHaveBeenCalledWith("/v1/admin/federation/instances", {
        domain: "library.beta.org",
      });
      expect(result).toEqual(mockCreated);
    });

    it("throws error when adding instance fails", async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { success: false, error: "Could not resolve NodeInfo" },
      } as any);

      await expect(addFederationInstance("invalid.domain")).rejects.toThrow("Could not resolve NodeInfo");
    });
  });

  describe("updateFederationInstance", () => {
    it("updates trust level for an existing instance", async () => {
      const mockUpdated = {
        id: 1,
        domain: "library.alpha.org",
        trust_level: "trusted",
      };

      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: mockUpdated },
      } as any);

      const result = await updateFederationInstance(1, "trusted");
      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/federation/instances/1/trust", {
        trust_level: "trusted",
      });
      expect(result).toEqual(mockUpdated);
    });

    it("throws error when trust update fails", async () => {
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: false, error: "Instance not found" },
      } as any);

      await expect(updateFederationInstance(999, "blocked")).rejects.toThrow("Instance not found");
    });
  });

  describe("deleteFederationInstance", () => {
    it("removes a federation instance successfully", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({
        data: { success: true, data: { deleted: true } },
      } as any);

      await expect(deleteFederationInstance(1)).resolves.toBeUndefined();
      expect(apiClient.delete).toHaveBeenCalledWith("/v1/admin/federation/instances/1");
    });

    it("throws error when deletion fails", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({
        data: { success: false, error: "Cannot delete instance" },
      } as any);

      await expect(deleteFederationInstance(1)).rejects.toThrow("Cannot delete instance");
    });
  });

  describe("listFederationActivities", () => {
    it("fetches activities with pagination and filters", async () => {
      const mockActivities = [
        {
          id: 10,
          activity_type: "Create",
          actor_uri: "https://remote.library/users/bob",
          target_uri: null,
          direction: "inbound",
          status: "delivered",
          created_at: "2026-10-21T01:00:00Z",
        },
      ];
      const mockPagination = { page: 2, per_page: 20, total: 25, pages: 2 };

      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: mockActivities, pagination: mockPagination },
      } as any);

      const result = await listFederationActivities(2, {
        direction: "inbound",
        type: "Create",
        status: "delivered",
      });

      expect(apiClient.get).toHaveBeenCalledWith(
        "/v1/admin/federation/activities?page=2&direction=inbound&type=Create&status=delivered"
      );
      expect(result).toEqual({ data: mockActivities, pagination: mockPagination });
    });

    it("throws error when activity fetch fails", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: false, error: "Internal server error" },
      } as any);

      await expect(listFederationActivities(1)).rejects.toThrow("Internal server error");
    });
  });

  describe("getFederationKeyFingerprint", () => {
    it("retrieves instance actor public key fingerprint", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: { fingerprint: "SHA256:abcd1234efgh" } },
      } as any);

      const fp = await getFederationKeyFingerprint();
      expect(apiClient.get).toHaveBeenCalledWith("/v1/admin/federation/key-fingerprint");
      expect(fp).toBe("SHA256:abcd1234efgh");
    });
  });
});
