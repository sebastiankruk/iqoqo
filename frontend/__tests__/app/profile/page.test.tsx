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
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import ProfilePage from '@/app/profile/page';

describe('ProfilePage', () => {
  const mockProfile = {
    email: 'user@iqoqo.local',
    display_name: 'Test User',
    consents: { federation: false, telemetry: true }
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // 1. Initialize fetch as a Vitest mock function
    global.fetch = vi.fn();

    // 2. Now you can safely call mock methods on it
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockProfile,
    });
  });

  it('renders loading state initially, then profile data', async () => {
    render(<ProfilePage />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('user@iqoqo.local')).toBeInTheDocument();
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
  });

  it('toggles GDPR consents', async () => {
    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    // Mock the subsequent fetch call for the consent toggle
    (global.fetch as Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    const federationButtons = screen.getAllByRole("button", { name: /Opted/i });

    // Actually use the variable to click the button
    fireEvent.click(federationButtons[0]);

    // Then assert your fetch mock was called with the right data
    expect(global.fetch).toHaveBeenCalledWith("/api/profile/consent", expect.any(Object));

    // Find the button specifically for federation (currently "Opted Out" based on mock data)
    const fedButton = screen.getByText('Opted Out');

    fireEvent.click(fedButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/profile/consent',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ consent_type: 'federation', is_granted: true })
        })
      );
    });
  });
});
