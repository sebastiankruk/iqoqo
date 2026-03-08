import { vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
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
    (global.fetch as any).mockResolvedValueOnce({
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
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    const federationButtons = screen.getAllByRole('button');
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
