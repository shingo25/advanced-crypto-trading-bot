'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardContent,
  Alert,
  Snackbar,
  Fab,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Assessment as AssessmentIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { useAuthStore } from '@/store/auth';
import BacktestResultsList from '@/components/backtest/BacktestResultsList';
import BacktestVisualization from '@/components/backtest/BacktestVisualization';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`backtest-tabpanel-${index}`}
      aria-labelledby={`backtest-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function BacktestPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState(0);
  const [newBacktestDialog, setNewBacktestDialog] = useState(false);
  const [compareDialog, setCompareDialog] = useState(false);
  const [selectedResults, setSelectedResults] = useState<string[]>([]);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // バックテスト実行状況
  const [runningBacktests, setRunningBacktests] = useState<{
    [key: string]: {
      strategy: string;
      symbol: string;
      progress: number;
      status: string;
    };
  }>({});

  // バックテスト統計
  const [backtestStats, setBacktestStats] = useState({
    totalTests: 0,
    runningTests: 0,
    successfulTests: 0,
    averageReturn: 0,
    bestStrategy: '',
  });

  useEffect(() => {
    // バックテスト統計を取得
    fetchBacktestStats();

    // 実行中のバックテストをポーリング
    const interval = setInterval(() => {
      checkRunningBacktests();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchBacktestStats = async () => {
    try {
      // API呼び出し（実装例）
      const response = await fetch('/api/backtest/stats');
      if (response.ok) {
        const stats = await response.json();
        setBacktestStats(stats);
      }
    } catch (error) {
      console.error('統計データの取得に失敗:', error);
      // デモデータ
      setBacktestStats({
        totalTests: 15,
        runningTests: 2,
        successfulTests: 12,
        averageReturn: 0.08,
        bestStrategy: 'RSIスイング戦略',
      });
    }
  };

  const checkRunningBacktests = async () => {
    try {
      const response = await fetch('/api/backtest/running');
      if (response.ok) {
        const running = await response.json();
        setRunningBacktests(running);
      }
    } catch (error) {
      console.error('実行中バックテストの確認に失敗:', error);
    }
  };

  const handleStartBacktest = () => {
    setNewBacktestDialog(true);
  };

  const handleCompareResults = (ids: string[]) => {
    setSelectedResults(ids);
    setCompareDialog(true);
  };

  const handleDeleteResult = async (id: string) => {
    try {
      const response = await fetch(`/api/backtest/results/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setNotification({
          open: true,
          message: 'バックテスト結果を削除しました',
          severity: 'success',
        });
        // リストを更新
        window.location.reload();
      } else {
        throw new Error('削除に失敗しました');
      }
    } catch (error) {
      setNotification({
        open: true,
        message: error instanceof Error ? error.message : '削除中にエラーが発生しました',
        severity: 'error',
      });
    }
  };

  const formatPercent = (value: number) => {
    const percent = (value * 100).toFixed(2);
    const sign = value >= 0 ? '+' : '';
    return `${sign}${percent}%`;
  };

  // ダッシュボード統計カード
  const StatsCards = () => (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
      <Box sx={{ flex: '1 1 300px', minWidth: '250px' }}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <AssessmentIcon sx={{ mr: 2, color: '#1976d2' }} />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  総テスト数
                </Typography>
                <Typography variant="h5" component="div">
                  {backtestStats.totalTests}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ flex: '1 1 300px', minWidth: '250px' }}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <PlayIcon sx={{ mr: 2, color: '#4caf50' }} />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  実行中
                </Typography>
                <Typography variant="h5" component="div">
                  {backtestStats.runningTests}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ flex: '1 1 300px', minWidth: '250px' }}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <HistoryIcon sx={{ mr: 2, color: '#ff9800' }} />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  成功率
                </Typography>
                <Typography variant="h5" component="div">
                  {backtestStats.totalTests > 0
                    ? Math.round((backtestStats.successfulTests / backtestStats.totalTests) * 100)
                    : 0}
                  %
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ flex: '1 1 300px', minWidth: '250px' }}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <AssessmentIcon sx={{ mr: 2, color: '#9c27b0' }} />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  平均リターン
                </Typography>
                <Typography
                  variant="h5"
                  component="div"
                  sx={{
                    color: backtestStats.averageReturn >= 0 ? '#4caf50' : '#f44336',
                  }}
                >
                  {formatPercent(backtestStats.averageReturn)}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );

  // 実行中バックテスト表示
  const RunningBacktests = () => {
    const runningList = Object.entries(runningBacktests);

    if (runningList.length === 0) {
      return null;
    }

    return (
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          実行中のバックテスト
        </Typography>
        <Grid container spacing={2}>
          {runningList.map(([id, backtest]) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={id}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    {backtest.strategy}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {backtest.symbol}
                  </Typography>
                  <Box
                    sx={{
                      width: '100%',
                      height: 6,
                      bgcolor: 'grey.300',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: `${backtest.progress}%`,
                        height: '100%',
                        bgcolor: '#4caf50',
                        borderRadius: 1,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {backtest.status} ({backtest.progress}%)
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>
    );
  };

  // バックテスト設定フォーム（簡易版）
  const BacktestForm = () => (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        新しいバックテストを開始
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        詳細なバックテスト設定は別途実装予定です。
        現在は結果表示機能のデモンストレーションが利用可能です。
      </Alert>
      {/* フォーム実装はここに追加 */}
    </Box>
  );

  // 結果比較ビュー（簡易版）
  const CompareResults = () => (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        バックテスト結果比較
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        選択された結果: {selectedResults.length}件
      </Alert>
      <Typography variant="body2" color="text.secondary">
        複数のバックテスト結果を比較する機能は今後実装予定です。
      </Typography>
    </Box>
  );

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          バックテスト
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleStartBacktest}
          size="large"
        >
          新規バックテスト
        </Button>
      </Box>

      <StatsCards />
      <RunningBacktests />

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            aria-label="バックテストタブ"
          >
            <Tab label="結果一覧" />
            <Tab label="パフォーマンス分析" />
            <Tab label="戦略比較" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          <BacktestResultsList
            onViewResult={(id) => console.log('View result:', id)}
            onDeleteResult={handleDeleteResult}
            onCompareResults={handleCompareResults}
          />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              パフォーマンス分析
            </Typography>
            <Alert severity="info">
              特定のバックテスト結果を選択すると、詳細な分析が表示されます。
            </Alert>
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <CompareResults />
        </TabPanel>
      </Paper>

      {/* 新規バックテストダイアログ */}
      <Dialog
        open={newBacktestDialog}
        onClose={() => setNewBacktestDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>新規バックテスト設定</DialogTitle>
        <DialogContent>
          <BacktestForm />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewBacktestDialog(false)}>キャンセル</Button>
          <Button variant="contained" disabled>
            実行 (未実装)
          </Button>
        </DialogActions>
      </Dialog>

      {/* 結果比較ダイアログ */}
      <Dialog open={compareDialog} onClose={() => setCompareDialog(false)} maxWidth="xl" fullWidth>
        <DialogTitle>バックテスト結果比較</DialogTitle>
        <DialogContent>
          <CompareResults />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompareDialog(false)}>閉じる</Button>
        </DialogActions>
      </Dialog>

      {/* 通知スナックバー */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={() => setNotification({ ...notification, open: false })}
      >
        <Alert
          onClose={() => setNotification({ ...notification, open: false })}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>

      {/* フローティングアクションボタン */}
      <Fab
        color="primary"
        aria-label="新規バックテスト"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={handleStartBacktest}
      >
        <AddIcon />
      </Fab>
    </Container>
  );
}
