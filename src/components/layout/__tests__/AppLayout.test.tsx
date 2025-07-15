import { render, screen } from '@testing-library/react';
import AppLayout from '../AppLayout';
import { useAuthStore } from '@/store/auth';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

// Mock the auth store
jest.mock('@/store/auth');

const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

describe('AppLayout', () => {
  beforeEach(() => {
    mockUseAuthStore.mockReturnValue({
      user: { username: 'testuser' },
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      initialize: jest.fn(),
      loading: false,
      error: null
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

    expect(screen.getByText('Crypto Bot')).toBeInTheDocument();
    expect(screen.getByText('ダッシュボード')).toBeInTheDocument();
    expect(screen.getByText('戦略')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('displays user information', () => {
    render(
      <ThemeProvider>
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      </ThemeProvider>
    );

    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it('renders navigation items', () => {
    render(
      <ThemeProvider>
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      </ThemeProvider>
    );

    expect(screen.getByText('ダッシュボード')).toBeInTheDocument();
    expect(screen.getByText('戦略')).toBeInTheDocument();
    expect(screen.getByText('ポートフォリオ')).toBeInTheDocument();
    expect(screen.getByText('アラート')).toBeInTheDocument();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });
});