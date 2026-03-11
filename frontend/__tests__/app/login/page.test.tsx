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
import { vi, describe, it, expect, beforeEach, type Mock } from "vitest";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from '@/app/login/page';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const renderWithQueryClient = (component: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true
    });
  });

  it('renders login form and Google SSO button', () => {
    renderWithQueryClient(<LoginPage />);
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign in with Google/i })).toBeInTheDocument();
  });

  it('handles successful local login and redirects', async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ token: 'mock-jwt-token' }),
    });

    renderWithQueryClient(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'test@iqoqo.local' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/login'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'test@iqoqo.local', password: 'password123' })
        })
      );
      expect(window.location.href).toContain('/api/auth-exchange?token=mock-jwt-token');
    });
  });
});
