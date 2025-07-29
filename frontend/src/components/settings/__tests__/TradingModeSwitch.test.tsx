import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TradingModeSwitch from '../TradingModeSwitch';
import { api } from '@/lib/api';

// APIモック
jest.mock('@/lib/api', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

describe('TradingModeSwitch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('初期レンダリング時にPaperモードが表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    render(<TradingModeSwitch />);

    // ローディング状態の確認
    expect(screen.getByText('取引モードを読み込み中...')).toBeInTheDocument();

    // データロード後の確認
    await waitFor(() => {
      expect(screen.getByText('Paper Trading (模擬取引)')).toBeInTheDocument();
    });

    expect(screen.getByText('取引モード設定')).toBeInTheDocument();
    expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
  });

  it('Liveモードが正しく表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'live',
        message: '現在のモードは Live Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByText('Live Trading (本番取引)')).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/Live Trading/)).toBeChecked();
  });

  it('Paper→Liveスイッチで確認ダイアログが表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
    });

    // スイッチをクリック
    const switchElement = screen.getByLabelText(/Live Trading/);
    fireEvent.click(switchElement);

    // 確認ダイアログが表示される
    await waitFor(() => {
      expect(screen.getByText('Live Trading確認')).toBeInTheDocument();
    });
    expect(screen.getByText(/重要な警告/)).toBeInTheDocument();
    expect(screen.getByText(/実際の資金での取引が実行されます/)).toBeInTheDocument();
  });

  it('確認ダイアログで正しい確認テキストが必要', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    // const user = userEvent.setup();
    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
    });

    // スイッチをクリックしてダイアログを開く
    const switchElement = screen.getByLabelText(/Live Trading/);
    await fireEvent.click(switchElement);

    // 確認テキストを入力
    const confirmationInput = screen.getByLabelText('確認テキスト');
    await fireEvent.type(confirmationInput, 'WRONG');

    // エラーメッセージが表示される
    expect(screen.getByText('正確に "LIVE" と入力してください')).toBeInTheDocument();

    // 確認ボタンが無効
    const confirmButton = screen.getByText('Live Trading有効化');
    expect(confirmButton).toBeDisabled();

    // 正しいテキストを入力
    await fireEvent.clear(confirmationInput);
    await fireEvent.type(confirmationInput, 'LIVE');

    // 確認ボタンが有効になる
    expect(confirmButton).not.toBeDisabled();
  });

  it('Live→Paper切り替えが即座に実行される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'live',
        message: '現在のモードは Live Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    mockApi.post.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '取引モードを PAPER に変更しました',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    // const user = userEvent.setup();
    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).toBeChecked();
    });

    // スイッチをクリック（Live→Paper）
    const switchElement = screen.getByLabelText(/Live Trading/);
    await fireEvent.click(switchElement);

    // 確認ダイアログは表示されず、即座にAPIが呼ばれる
    expect(screen.queryByText('Live Trading確認')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith('/auth/trading-mode', {
        mode: 'paper',
        confirmation_text: '',
      });
    });
  });

  it('APIエラー時にエラーメッセージが表示される', async () => {
    mockApi.get.mockRejectedValue(new Error('Network error'));

    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByText('取引モードの取得に失敗しました')).toBeInTheDocument();
    });

    // デフォルトでPaperモードになる
    expect(screen.getByText('Paper Trading (模擬取引)')).toBeInTheDocument();
  });

  it('Live Trading切り替え成功時に成功メッセージが表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    mockApi.post.mockResolvedValue({
      data: {
        current_mode: 'live',
        message: '取引モードを LIVE に変更しました (⚠️ 実際の資金での取引になります)',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    // const user = userEvent.setup();
    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
    });

    // スイッチをクリック
    const switchElement = screen.getByLabelText(/Live Trading/);
    await fireEvent.click(switchElement);

    // 確認テキストを入力
    const confirmationInput = screen.getByLabelText('確認テキスト');
    await fireEvent.type(confirmationInput, 'LIVE');

    // 確認ボタンをクリック
    const confirmButton = screen.getByText('Live Trading有効化');
    await fireEvent.click(confirmButton);

    // 成功メッセージが表示される
    await waitFor(() => {
      expect(screen.getByText(/取引モードを LIVE に変更しました/)).toBeInTheDocument();
    });

    // ダイアログが閉じる
    expect(screen.queryByText('Live Trading確認')).not.toBeInTheDocument();
  });

  it('Live Trading切り替え失敗時にエラーメッセージが表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    mockApi.post.mockRejectedValue({
      response: {
        data: {
          detail: 'Live Trading アクセスには管理者権限が必要です',
        },
      },
    });

    // const user = userEvent.setup();
    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
    });

    // スイッチをクリック
    const switchElement = screen.getByLabelText(/Live Trading/);
    await fireEvent.click(switchElement);

    // 確認テキストを入力
    const confirmationInput = screen.getByLabelText('確認テキスト');
    await fireEvent.type(confirmationInput, 'LIVE');

    // 確認ボタンをクリック
    const confirmButton = screen.getByText('Live Trading有効化');
    await fireEvent.click(confirmButton);

    // エラーメッセージが表示される
    await waitFor(() => {
      expect(screen.getByText('Live Trading アクセスには管理者権限が必要です')).toBeInTheDocument();
    });
  });

  it('セキュリティ警告が適切に表示される', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByText('重要な注意事項:')).toBeInTheDocument();
    });

    // セキュリティ関連の警告テキストを確認
    expect(screen.getByText(/Live Tradingでは実際の資金で取引が行われます/)).toBeInTheDocument();
    expect(screen.getByText(/管理者権限が必要です/)).toBeInTheDocument();
    expect(screen.getByText(/本番環境でのみ利用可能です/)).toBeInTheDocument();
    expect(screen.getByText(/すべての操作が監査ログに記録されます/)).toBeInTheDocument();
  });

  it('確認ダイアログのキャンセル機能が正常動作する', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        current_mode: 'paper',
        message: '現在のモードは Paper Trading です',
        timestamp: '2024-01-01T00:00:00Z',
      },
    });

    // const user = userEvent.setup();
    render(<TradingModeSwitch />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
    });

    // スイッチをクリック
    const switchElement = screen.getByLabelText(/Live Trading/);
    await fireEvent.click(switchElement);

    // ダイアログが表示される
    expect(screen.getByText('Live Trading確認')).toBeInTheDocument();

    // キャンセルボタンをクリック
    const cancelButton = screen.getByText('キャンセル');
    await fireEvent.click(cancelButton);

    // ダイアログが閉じる
    expect(screen.queryByText('Live Trading確認')).not.toBeInTheDocument();

    // スイッチがPaperのままになる
    expect(screen.getByLabelText(/Live Trading/)).not.toBeChecked();
  });
});