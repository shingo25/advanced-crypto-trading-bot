'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Switch,
  FormControlLabel,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Chip,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Security as SecurityIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { api } from '@/lib/api';

interface TradingModeResponse {
  current_mode: string;
  message: string;
  timestamp: string;
}

/**
 * Paper/Live取引モード切り替えコンポーネント
 *
 * セキュリティ機能:
 * - 多段階確認プロセス
 * - 管理者権限要求
 * - 環境制限チェック
 * - 確認テキスト入力
 * - 包括的な監査ログ
 */
export default function TradingModeSwitch() {
  const [currentMode, setCurrentMode] = useState<'paper' | 'live'>('paper');
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [confirmationText, setConfirmationText] = useState('');
  const [targetMode, setTargetMode] = useState<'paper' | 'live'>('paper');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string>('');

  // 現在のモードを取得
  useEffect(() => {
    fetchCurrentMode();
  }, []);

  const fetchCurrentMode = async () => {
    try {
      setLoading(true);
      const response = await api.get<TradingModeResponse>('/auth/trading-mode');
      setCurrentMode(response.data.current_mode as 'paper' | 'live');
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch trading mode:', err);
      setError('取引モードの取得に失敗しました');
      // デフォルトでPaperモードを設定（セキュリティ優先）
      setCurrentMode('paper');
    } finally {
      setLoading(false);
    }
  };

  const fetchCsrfToken = async () => {
    try {
      const response = await api.get('/auth/csrf-token');
      setCsrfToken(response.data.csrf_token);
      return response.data.csrf_token;
    } catch (err: any) {
      console.error('Failed to fetch CSRF token:', err);
      setError('セキュリティトークンの取得に失敗しました');
      return null;
    }
  };

  const handleModeChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const newMode = event.target.checked ? 'live' : 'paper';

    if (newMode === 'live') {
      // Live切り替えは確認ダイアログを表示（CSRFトークンも取得）
      const token = await fetchCsrfToken();
      if (token) {
        setTargetMode('live');
        setConfirmationOpen(true);
      }
    } else {
      // Paper切り替えは即座に実行（安全なため）
      const token = await fetchCsrfToken();
      if (token) {
        switchTradingMode('paper', '', token);
      }
    }
  };

  const switchTradingMode = async (
    mode: 'paper' | 'live',
    confirmation: string,
    token?: string
  ) => {
    try {
      setSwitching(true);
      setError(null);
      setSuccess(null);

      // CSRFトークンが提供されていない場合は取得
      const csrfTokenToUse = token || csrfToken || (await fetchCsrfToken());

      if (!csrfTokenToUse) {
        throw new Error('セキュリティトークンの取得に失敗しました');
      }

      const response = await api.post<TradingModeResponse>('/auth/trading-mode', {
        mode,
        confirmation_text: confirmation,
        csrf_token: csrfTokenToUse,
      });

      setCurrentMode(mode);
      setSuccess(response.data.message);
      setConfirmationOpen(false);
      setConfirmationText('');

      // 成功メッセージを3秒後に自動削除
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error('Failed to switch trading mode:', err);
      const errorMessage = err.response?.data?.detail || '取引モード切り替えに失敗しました';
      setError(errorMessage);

      // エラーメッセージを5秒後に自動削除
      setTimeout(() => setError(null), 5000);
    } finally {
      setSwitching(false);
    }
  };

  const handleConfirmationSubmit = () => {
    switchTradingMode(targetMode, confirmationText, csrfToken);
  };

  const handleConfirmationCancel = () => {
    setConfirmationOpen(false);
    setConfirmationText('');
    setTargetMode('paper');
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" p={3}>
            <CircularProgress size={24} sx={{ mr: 2 }} />
            <Typography>取引モードを読み込み中...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            <SecurityIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            取引モード設定
          </Typography>

          {/* 現在のモード表示 */}
          <Box mb={3}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              現在のモード
            </Typography>
            <Chip
              icon={currentMode === 'live' ? <WarningIcon /> : <CheckCircleIcon />}
              label={
                currentMode === 'live' ? 'Live Trading (本番取引)' : 'Paper Trading (模擬取引)'
              }
              color={currentMode === 'live' ? 'error' : 'success'}
              variant="filled"
              size="medium"
            />
          </Box>

          <Divider sx={{ mb: 3 }} />

          {/* 成功・エラーメッセージ */}
          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {success}
            </Alert>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* モード切り替えスイッチ */}
          <Box mb={3}>
            <FormControlLabel
              control={
                <Switch
                  checked={currentMode === 'live'}
                  onChange={handleModeChange}
                  disabled={switching}
                  color="error"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">Live Trading (実際の資金での取引)</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {switching ? '切り替え中...' : '注意: 実際の資金でのリスクがあります'}
                  </Typography>
                </Box>
              }
            />
          </Box>

          {/* 警告メッセージ */}
          <Alert severity="warning" icon={<WarningIcon />}>
            <Typography variant="body2">
              <strong>重要な注意事項:</strong>
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText
                  primary="• Live Tradingでは実際の資金で取引が行われます"
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="• 管理者権限が必要です"
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="• 本番環境でのみ利用可能です"
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="• すべての操作が監査ログに記録されます"
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            </List>
          </Alert>
        </CardContent>
      </Card>

      {/* Live Trading確認ダイアログ */}
      <Dialog open={confirmationOpen} onClose={handleConfirmationCancel} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <ErrorIcon color="error" sx={{ mr: 1 }} />
            Live Trading確認
          </Box>
        </DialogTitle>

        <DialogContent>
          <Alert severity="error" sx={{ mb: 3 }}>
            <Typography variant="body1" gutterBottom>
              <strong>⚠️ 重要な警告</strong>
            </Typography>
            <Typography variant="body2">
              Live Tradingモードでは実際の資金での取引が実行されます。
              損失のリスクがあることを理解し、責任を持って使用してください。
            </Typography>
          </Alert>

          <Typography variant="body1" gutterBottom>
            Live Tradingを有効にするには、下記に
            <strong style={{ color: 'red' }}> "LIVE" </strong>
            と正確に入力してください:
          </Typography>

          <TextField
            fullWidth
            label="確認テキスト"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder="LIVE"
            error={confirmationText !== '' && confirmationText !== 'LIVE'}
            helperText={
              confirmationText !== '' && confirmationText !== 'LIVE'
                ? '正確に "LIVE" と入力してください'
                : 'Live Tradingを確認するため "LIVE" と入力'
            }
            sx={{ mt: 2 }}
            autoFocus
          />

          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
            ※この操作は監査ログに記録され、管理者権限が必要です
          </Typography>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleConfirmationCancel} color="inherit">
            キャンセル
          </Button>
          <Button
            onClick={handleConfirmationSubmit}
            color="error"
            variant="contained"
            disabled={confirmationText !== 'LIVE' || switching}
            startIcon={switching ? <CircularProgress size={20} /> : <WarningIcon />}
          >
            {switching ? '切り替え中...' : 'Live Trading有効化'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
