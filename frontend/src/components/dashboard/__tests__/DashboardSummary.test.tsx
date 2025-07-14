import { render, screen } from '@testing-library/react';
import DashboardSummary from '../DashboardSummary';
import { useDashboardStore } from '@/store/dashboard';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

// Mock the dashboard store
jest.mock('@/store/dashboard');

const mockUseDashboardStore = useDashboardStore as jest.MockedFunction<typeof useDashboardStore>;

const mockSummary = {
  total_value: 10000,
  daily_pnl: 500,
  daily_pnl_pct: 0.05,
  total_pnl: 2000,
  active_strategies: 5,
  unread_alerts: 2,
  open_positions: 3,
  active_orders: 1,
  portfolio: {
    assets: {
      'BTCUSDT': {
        balance: 0.5,
        market_value: 25000,
        actual_weight: 0.5,
        target_weight: 0.4
      }
    }
  },
  recent_trades: [
    {
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.1,
      price: 50000,
      pnl: 100,
      timestamp: '2023-01-01T00:00:00Z'
    }
  ]
};

describe('DashboardSummary', () => {
  beforeEach(() => {
    mockUseDashboardStore.mockReturnValue({
      summary: mockSummary,
      fetchSummary: jest.fn(),
      fetchPerformanceData: jest.fn(),
      performanceData: null
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders dashboard summary correctly', () => {
    render(
      <ThemeProvider>
        <DashboardSummary />
      </ThemeProvider>
    );

    expect(screen.getByText('ダッシュボード')).toBeInTheDocument();
    expect(screen.getByText('総資産')).toBeInTheDocument();
    expect(screen.getByText('累計損益')).toBeInTheDocument();
    expect(screen.getByText('稼働戦略')).toBeInTheDocument();
  });

  it('displays loading state when no summary data', () => {
    mockUseDashboardStore.mockReturnValue({
      summary: null,
      fetchSummary: jest.fn(),
      fetchPerformanceData: jest.fn(),
      performanceData: null
    });

    render(
      <ThemeProvider>
        <DashboardSummary />
      </ThemeProvider>
    );

    expect(screen.getByText('データを読み込み中...')).toBeInTheDocument();
  });

  it('formats currency values correctly', () => {
    render(
      <ThemeProvider>
        <DashboardSummary />
      </ThemeProvider>
    );

    expect(screen.getByText('$10,000')).toBeInTheDocument();
    expect(screen.getByText('$500')).toBeInTheDocument();
  });

  it('displays portfolio assets', () => {
    render(
      <ThemeProvider>
        <DashboardSummary />
      </ThemeProvider>
    );

    expect(screen.getByText('ポートフォリオ概要')).toBeInTheDocument();
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('0.5000')).toBeInTheDocument();
  });

  it('displays recent trades', () => {
    render(
      <ThemeProvider>
        <DashboardSummary />
      </ThemeProvider>
    );

    expect(screen.getByText('最近の取引')).toBeInTheDocument();
    expect(screen.getByText('BTCUSDT - BUY')).toBeInTheDocument();
    expect(screen.getByText('$100')).toBeInTheDocument();
  });
});