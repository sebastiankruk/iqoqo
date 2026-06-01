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
  getFederationInstances,
  addFederationInstance,
  updateInstanceTrust,
  removeFederationInstance,
  getFederationActivities,
  getFederationConsent,
  updateFederationConsent,
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

describe("Federation API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getFederationInstances", () => {
    it("should fetch and return instances list", async () => {
      const mockInstances = [
        { id: 1, domain: "remote.example.com", trust_level: "trusted", software_name: "iqoqo" },
        { id: 2, domain: "other.example.com", trust_level: "pending", software_name: "mastodon" },
      ];
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: mockInstances },
      });

      const result = await getFederationInstances();
      expect(result).toEqual(mockInstances);
      expect(apiClient.get).toHaveBeenCalledWith("/v1/admin/federation/instances");
    });

    it("should throw on failure", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: false, error: "Unauthorized" },
      });

      await expect(getFederationInstances()).rejects.toThrow("Unauthorized");
    });
  });

  describe("addFederationInstance", () => {
    it("should add a new instance by domain", async () => {
      const mockInstance = { id: 3, domain: "new.example.com", trust_level: "untrusted" };
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { success: true, data: mockInstance },
      });

      const result = await addFederationInstance("new.example.com");
      expect(result).toEqual(mockInstance);
      expect(apiClient.post).toHaveBeenCalledWith("/v1/admin/federation/instances", { domain: "new.example.com" });
    });

    it("should throw on failure", async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { success: false, error: "Invalid domain" },
      });

      await expect(addFederationInstance("")).rejects.toThrow("Invalid domain");
    });
  });

  describe("updateInstanceTrust", () => {
    it("should update trust level for an instance", async () => {
      const mockInstance = { id: 1, domain: "remote.example.com", trust_level: "blocked" };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: mockInstance },
      });

      const result = await updateInstanceTrust(1, "blocked");
      expect(result).toEqual(mockInstance);
      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/federation/instances/1/trust", { trust_level: "blocked" });
    });
  });

  describe("removeFederationInstance", () => {
    it("should delete an instance", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({
        data: { success: true, data: { deleted: true } },
      });

      await expect(removeFederationInstance(1)).resolves.toBeUndefined();
      expect(apiClient.delete).toHaveBeenCalledWith("/v1/admin/federation/instances/1");
    });

    it("should throw on failure", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({
        data: { success: false, error: "Not found" },
      });

      await expect(removeFederationInstance(999)).rejects.toThrow("Not found");
    });
  });

  describe("getFederationActivities", () => {
    it("should fetch paginated activities", async () => {
      const mockActivities = [{ id: "uuid-1", activity_type: "Follow", direction: "inbound", status: "delivered" }];
      const mockPagination = { page: 1, per_page: 20, total: 1 };
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: mockActivities, pagination: mockPagination },
      });

      const result = await getFederationActivities(1, { direction: "inbound" });
      expect(result.data).toEqual(mockActivities);
      expect(result.pagination).toEqual(mockPagination);
    });

    it("should apply filters as query params", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: [], pagination: { page: 1, per_page: 20, total: 0 } },
      });

      await getFederationActivities(2, { direction: "outbound", type: "Follow", status: "failed" });
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining("direction=outbound"));
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining("type=Follow"));
      expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining("status=failed"));
    });
  });

  describe("getFederationConsent", () => {
    it("should return consent settings", async () => {
      const mockConsent = { federated_profile: true, federated_collection: false };
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: true, data: mockConsent },
      });

      const result = await getFederationConsent();
      expect(result).toEqual(mockConsent);
    });

    it("should return null on error", async () => {
      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error("Network error"));

      const result = await getFederationConsent();
      expect(result).toBeNull();
    });

    it("should return null on unsuccessful response", async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: { success: false },
      });

      const result = await getFederationConsent();
      expect(result).toBeNull();
    });
  });

  describe("updateFederationConsent", () => {
    it("should update consent settings", async () => {
      const updatedConsent = { federated_profile: true, federated_collection: true };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: updatedConsent },
      });

      const result = await updateFederationConsent({ federated_collection: true });
      expect(result).toEqual(updatedConsent);
      expect(apiClient.put).toHaveBeenCalledWith("/federation/consent", { federated_collection: true });
    });

    it("should throw on failure", async () => {
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: false, error: "Unauthorized" },
      });

      await expect(updateFederationConsent({})).rejects.toThrow("Unauthorized");
    });
  });
});
