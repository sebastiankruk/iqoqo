import { render, screen } from "@testing-library/react";
import AdminSettingsPage from "@/app/admin/settings/page";
import { useProfile } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { vi } from "vitest";

// Mock dependencies
vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

describe("AdminSettingsPage", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as any);
  });

  it("shows a loading state initially", () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: true } as any);
    
    render(<AdminSettingsPage />);
    
    // Page title should not be visible while loading
    expect(screen.queryByText("Admin Settings")).toBeNull();
  });

  it("redirects non-admin users to the home page", () => {
    vi.mocked(useProfile).mockReturnValue({ 
      data: { id: "1", email: "user@test.com", roles: ["user"] }, 
      isLoading: false 
    } as any);
    
    render(<AdminSettingsPage />);
    
    // Should trigger redirect
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("renders the admin dashboard and sidebar tabs for admin users", () => {
    vi.mocked(useProfile).mockReturnValue({ 
      data: { id: "2", email: "admin@test.com", roles: ["admin"] }, 
      isLoading: false 
    } as any);
    
    render(<AdminSettingsPage />);
    
    // Should not redirect
    expect(mockPush).not.toHaveBeenCalled();
    
    // Should render main layout elements
    expect(screen.getByRole("heading", { name: "Admin Settings", level: 1 })).toBeInTheDocument();
    
    // Should render sidebar navigation buttons
    expect(screen.getByText("Instance Settings")).toBeInTheDocument();
    expect(screen.getByText("User Management")).toBeInTheDocument();
    expect(screen.getByText("Integrations & Monetization")).toBeInTheDocument();
  });
});