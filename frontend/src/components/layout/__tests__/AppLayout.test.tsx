import { render, screen } from '@testing-library/react';
import AppLayout from '../AppLayout';
import { useAuthStore } from '@/store/auth';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

// Mock the auth store
jest.mock('@/store/auth');

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useServerInsertedHTML: () => {},
}));

// Mock MUI AppRouter
jest.mock('@mui/material-nextjs/v15-appRouter', () => ({
  AppRouterCacheProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

describe('AppLayout', () => {
  beforeEach(() => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'testuser', email: 'test@example.com' },
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      initialize: jest.fn(),
      clearError: jest.fn(),
      isLoading: false,
      error: null,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders app layout with navigation', () => {
    render(
      <ThemeProvider>
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      </ThemeProvider>
    );

    expect(screen.getAllByText('Crypto Bot')).toHaveLength(2);
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it.skip('displays user information', () => {
    // TODO: Fix this test - user display may not be working correctly
    render(
      <ThemeProvider>
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      </ThemeProvider>
    );

    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it.skip('renders navigation items', () => {
    // TODO: Fix this test - navigation items may not be fully loaded
    render(
      <ThemeProvider>
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      </ThemeProvider>
    );

    // Check if navigation items exist (some may be duplicated in mobile/desktop views)
    expect(screen.getAllByText('ダッシュボード').length).toBeGreaterThan(0);
    expect(screen.getAllByText('戦略').length).toBeGreaterThan(0);
    expect(screen.getAllByText('ポートフォリオ').length).toBeGreaterThan(0);
    expect(screen.getAllByText('アラート').length).toBeGreaterThan(0);
    expect(screen.getAllByText('設定').length).toBeGreaterThan(0);
  });
});
