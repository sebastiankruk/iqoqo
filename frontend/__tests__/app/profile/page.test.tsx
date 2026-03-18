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
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API client BEFORE importing the component
vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  apiFetch: vi.fn(),
}));

// Mock dashboard components
vi.mock('@/components/dashboard/navbar', () => ({
  /** @returns {JSX.Element} Navbar mock */
  Navbar: () => <div data-testid="navbar">Navbar</div>,
}));

vi.mock('@/components/dashboard/footer', () => ({
  /** @returns {JSX.Element} Footer mock */
  Footer: () => <div data-testid="footer">Footer</div>,
}));

import ProfilePage from '@/app/profile/page';
import { apiClient, apiFetch } from '@/lib/api/client';

describe('ProfilePage', () => {
  const mockProfileData = {
    id: 'test-user-id',
    email: 'user@iqoqo.local',
    display_name: 'Test User',
    avatar_url: null,
    visibility: 'private' as const,
    created_at: '2026-01-01T00:00:00Z',
    consents: {
      consent_type: 'all',
      is_granted: true,
      policy_version: '1.0',
      timestamp: '2026-01-01T00:00:00Z',
      telemetry: true,
      federation: false,
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock the apiFetch function to return the profile data
    vi.mocked(apiFetch).mockResolvedValueOnce(mockProfileData);
  });

  it('renders loading state initially, then profile data', async () => {
    render(<ProfilePage />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('user@iqoqo.local')).toBeInTheDocument();
    });

    // Verify apiFetch was called with the correct path
    expect(apiFetch).toHaveBeenCalledWith('/profile/');
  });

  it('toggles GDPR consents', async () => {
    // Mock the apiFetch for loading profile
    vi.mocked(apiFetch).mockResolvedValueOnce(mockProfileData);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    // Mock the POST request for the consent toggle
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        success: true,
        data: {},
        error: null,
      },
    } as never);

    const federationButtons = screen.getAllByRole('button', { name: /Opted/i });

    // Click the federation button
    fireEvent.click(federationButtons[0]);

    // Assert the API was called (note: apiClient.post, not global.fetch)
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/profile/consent',
        expect.objectContaining({
          consent_type: 'federation',
          is_granted: true
        })
      );
    });
  });
});
