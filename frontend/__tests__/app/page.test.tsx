import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import DashboardPage from '@/app/page'
import * as hooks from '@/lib/api/hooks'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('next/image', () => ({
  default: (props: React.ComponentProps<'img'> & Record<string, unknown>) => {
    const { fill, sizes, unoptimized, priority, placeholder, blurDataURL, ...rest } = props;
    void fill; void sizes; void unoptimized; void priority; void placeholder; void blurDataURL;
    const restImgProps = rest as React.ComponentProps<'img'>;
    // eslint-disable-next-line @next/next/no-img-element
    return <img alt={restImgProps.alt ?? ''} {...restImgProps} />;
  },
}))

const createTestQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithQueryClient = (component: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('Landing / Dashboard page', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders landing view for unauthenticated users', () => {
    vi.spyOn(hooks, 'useProfile').mockReturnValue({ data: null, isLoading: false } as unknown as ReturnType<typeof hooks.useProfile>)
    vi.spyOn(hooks, 'useGlobalStats').mockReturnValue({ data: { works: 10, manifestations: 20, items: 30, users: 5 }, isLoading: false } as unknown as ReturnType<typeof hooks.useGlobalStats>)
    vi.spyOn(hooks, 'useRecentManifestations').mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<typeof hooks.useRecentManifestations>)

    renderWithQueryClient(<DashboardPage />)

    expect(screen.getByText('The Library of Everything')).toBeInTheDocument()
    expect(screen.getByText('Works')).toBeInTheDocument()
    expect(screen.getByText('Start Your Catalog')).toBeInTheDocument()
  })

  it('renders dashboard view for authenticated users', () => {
    vi.spyOn(hooks, 'useProfile').mockReturnValue({ data: { display_name: 'testuser', email: 'test@example.com' }, isLoading: false } as unknown as ReturnType<typeof hooks.useProfile>)

    renderWithQueryClient(<DashboardPage />)

    expect(screen.getByText('Welcome back, testuser')).toBeInTheDocument()
  })
})
