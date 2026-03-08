import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RegisterPage from '@/app/register/page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('disables submit button until terms are accepted', () => {
    render(<RegisterPage />);

    const submitButton = screen.getByRole('button', { name: 'Sign Up' });
    const termsCheckbox = screen.getByRole('checkbox', { name: /I agree to the/i });

    expect(submitButton).toBeDisabled();

    fireEvent.click(termsCheckbox);
    expect(submitButton).not.toBeDisabled();
  });

  it('shows error message on failed registration', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Email already registered' }),
    });

    render(<RegisterPage />);

    fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'exist@iqoqo.local' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'pass123' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /I agree to the/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Sign Up' }));

    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
  });
});
