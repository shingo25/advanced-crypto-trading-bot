'use client';

import { useEffect, useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  Switch,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Settings,
  TrendingUp,
  TrendingDown
} from '@mui/icons-material';
import { useStrategyStore } from '@/store/strategies';
import type { Strategy } from '@/types/api';

export default function StrategyList() {
  const { strategies, fetchStrategies, startStrategy, stopStrategy, isLoading, error } = useStrategyStore();
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    strategy: Strategy | null;
    action: 'start' | 'stop';
  }>({ open: false, strategy: null, action: 'start' });

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'stopped':
        return 'default';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running':
        return '稼働中';
      case 'stopped':
        return '停止中';
      case 'error':
        return 'エラー';
      default:
        return '不明';
    }
  };

  const handleToggleStrategy = (strategy: Strategy) => {
    setConfirmDialog({
      open: true,
      strategy,
      action: strategy.status === 'running' ? 'stop' : 'start'
    });
  };

  const handleConfirmAction = async () => {
    if (!confirmDialog.strategy) return;

    try {
      if (confirmDialog.action === 'start') {
        await startStrategy(confirmDialog.strategy.id);
      } else {
        await stopStrategy(confirmDialog.strategy.id);
      }
      setConfirmDialog({ open: false, strategy: null, action: 'start' });
    } catch (error) {
      // エラーハンドリングはstore内で処理
    }
  };

  const handleCancelAction = () => {
    setConfirmDialog({ open: false, strategy: null, action: 'start' });
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        戦略管理
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>戦略名</TableCell>
                <TableCell>タイプ</TableCell>
                <TableCell>通貨ペア</TableCell>
                <TableCell>時間枠</TableCell>
                <TableCell>状態</TableCell>
                <TableCell>有効</TableCell>
                <TableCell>総リターン</TableCell>
                <TableCell>シャープレシオ</TableCell>
                <TableCell>勝率</TableCell>
                <TableCell>最大ドローダウン</TableCell>
                <TableCell>取引数</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow key={strategy.id} hover>
                  <TableCell component="th" scope="row">
                    <Typography variant="subtitle2" fontWeight="bold">
                      {strategy.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={strategy.type.toUpperCase()} size="small" />
                  </TableCell>
                  <TableCell>{strategy.symbol}</TableCell>
                  <TableCell>{strategy.timeframe}</TableCell>
                  <TableCell>
                    <Chip
                      label={getStatusText(strategy.status)}
                      color={getStatusColor(strategy.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={strategy.enabled}
                      size="small"
                      disabled={strategy.status === 'error'}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {strategy.performance.total_return > 0 ? (
                        <TrendingUp sx={{ color: 'success.main', mr: 0.5 }} />
                      ) : (
                        <TrendingDown sx={{ color: 'error.main', mr: 0.5 }} />
                      )}
                      <Typography
                        variant="body2"
                        color={strategy.performance.total_return > 0 ? 'success.main' : 'error.main'}
                        fontWeight="bold"
                      >
                        {formatPercent(strategy.performance.total_return)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {strategy.performance.sharpe_ratio.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatPercent(strategy.performance.win_rate)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="error.main">
                      {formatPercent(strategy.performance.max_drawdown)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {strategy.performance.total_trades}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleToggleStrategy(strategy)}
                        color={strategy.status === 'running' ? 'error' : 'success'}
                        disabled={strategy.status === 'error'}
                      >
                        {strategy.status === 'running' ? <Stop /> : <PlayArrow />}
                      </IconButton>
                      <IconButton size="small" color="primary">
                        <Settings />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 確認ダイアログ */}
      <Dialog
        open={confirmDialog.open}
        onClose={handleCancelAction}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          戦略{confirmDialog.action === 'start' ? '開始' : '停止'}の確認
        </DialogTitle>
        <DialogContent>
          <Typography>
            戦略「{confirmDialog.strategy?.name}」を
            {confirmDialog.action === 'start' ? '開始' : '停止'}します。よろしいですか？
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelAction}>
            キャンセル
          </Button>
          <Button
            onClick={handleConfirmAction}
            variant="contained"
            color={confirmDialog.action === 'start' ? 'success' : 'error'}
          >
            {confirmDialog.action === 'start' ? '開始' : '停止'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}