'use client';

import React, { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Fullscreen as FullscreenIcon,
} from '@mui/icons-material';
import PriceWebSocket from '@/components/realtime/PriceWebSocket';
import { useAuthStore } from '@/store/auth';

const AVAILABLE_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT',
  'SOLUSDT', 'XRPUSDT', 'DOTUSDT', 'AVAXUSDT',
  'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'LTCUSDT'
];

const LAYOUT_OPTIONS = [
  { value: 'grid-2', label: '2列グリッド', columns: 2 },
  { value: 'grid-3', label: '3列グリッド', columns: 3 },
  { value: 'grid-4', label: '4列グリッド', columns: 4 },
  { value: 'grid-6', label: '6列グリッド', columns: 6 },
];

export default function RealtimeDashboard() {
  const { user } = useAuthStore();

  // State
  const [selectedSymbols, setSelectedSymbols] = useState([
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT'
  ]);
  const [showTrades, setShowTrades] = useState(false);
  const [layout, setLayout] = useState('grid-4');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [addSymbolOpen, setAddSymbolOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [newSymbol, setNewSymbol] = useState('');

  // Get available symbols that aren't already selected
  const availableToAdd = AVAILABLE_SYMBOLS.filter(
    symbol => !selectedSymbols.includes(symbol)
  );

  // Handle symbol addition
  const handleAddSymbol = () => {
    if (newSymbol && !selectedSymbols.includes(newSymbol)) {
      setSelectedSymbols(prev => [...prev, newSymbol]);
      setNewSymbol('');
      setAddSymbolOpen(false);
    }
  };

  // Handle symbol removal
  const handleRemoveSymbol = (symbolToRemove: string) => {
    setSelectedSymbols(prev => prev.filter(symbol => symbol !== symbolToRemove));
  };

  // Get grid columns based on layout
  const getGridColumns = () => {
    const layoutOption = LAYOUT_OPTIONS.find(option => option.value === layout);
    return 12 / (layoutOption?.columns || 4);
  };

  // Settings dialog
  const SettingsDialog = () => (
    <Dialog
      open={settingsOpen}
      onClose={() => setSettingsOpen(false)}
      maxWidth=\"sm\"
      fullWidth
    >
      <DialogTitle>リアルタイム表示設定</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={3}>
            {/* Layout Selection */}
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>レイアウト</InputLabel>
                <Select
                  value={layout}
                  label=\"レイアウト\"
                  onChange={(e) => setLayout(e.target.value)}
                >
                  {LAYOUT_OPTIONS.map(option => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Display Options */}
            <Grid item xs={12}>
              <Typography variant=\"subtitle2\" gutterBottom>
                表示オプション
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={showTrades}
                      onChange={(e) => setShowTrades(e.target.checked)}
                    />
                  }
                  label=\"取引データを表示\"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoRefresh}
                      onChange={(e) => setAutoRefresh(e.target.checked)}
                    />
                  }
                  label=\"自動更新\"
                />
              </Box>
            </Grid>

            {/* Selected Symbols */}
            <Grid item xs={12}>
              <Typography variant=\"subtitle2\" gutterBottom>
                表示中のシンボル ({selectedSymbols.length})
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {selectedSymbols.map(symbol => (
                  <Chip
                    key={symbol}
                    label={symbol.replace('USDT', '/USDT')}
                    onDelete={() => handleRemoveSymbol(symbol)}
                    deleteIcon={<RemoveIcon />}
                    variant=\"outlined\"
                  />
                ))}
              </Box>
              <Button
                startIcon={<AddIcon />}
                onClick={() => setAddSymbolOpen(true)}
                sx={{ mt: 1 }}
                disabled={availableToAdd.length === 0}
              >
                シンボルを追加
              </Button>
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setSettingsOpen(false)}>
          閉じる
        </Button>
      </DialogActions>
    </Dialog>
  );

  // Add symbol dialog
  const AddSymbolDialog = () => (
    <Dialog
      open={addSymbolOpen}
      onClose={() => setAddSymbolOpen(false)}
      maxWidth=\"xs\"
      fullWidth
    >
      <DialogTitle>シンボルを追加</DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel>シンボル</InputLabel>
          <Select
            value={newSymbol}
            label=\"シンボル\"
            onChange={(e) => setNewSymbol(e.target.value)}
          >
            {availableToAdd.map(symbol => (
              <MenuItem key={symbol} value={symbol}>
                {symbol.replace('USDT', '/USDT')}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setAddSymbolOpen(false)}>
          キャンセル
        </Button>
        <Button
          onClick={handleAddSymbol}
          variant=\"contained\"
          disabled={!newSymbol}
        >
          追加
        </Button>
      </DialogActions>
    </Dialog>
  );

  // Quick actions
  const QuickActions = () => (
    <Box sx={{ mb: 3 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant=\"h6\" color=\"primary\">
                {selectedSymbols.length}
              </Typography>
              <Typography variant=\"body2\" color=\"text.secondary\">
                監視中のシンボル
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant=\"h6\" color=\"success.main\">
                ライブ
              </Typography>
              <Typography variant=\"body2\" color=\"text.secondary\">
                接続状況
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant=\"h6\" color=\"info.main\">
                Binance
              </Typography>
              <Typography variant=\"body2\" color=\"text.secondary\">
                データソース
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant=\"h6\" color=\"warning.main\">
                WebSocket
              </Typography>
              <Typography variant=\"body2\" color=\"text.secondary\">
                接続タイプ
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  return (
    <Container
      maxWidth={fullscreen ? false : \"xl\"}
      sx={{
        py: 4,
        ...(fullscreen && {
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 9999,
          backgroundColor: 'background.default',
          overflow: 'auto',
        })
      }}
    >
      {/* Header */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 3
      }}>
        <Typography variant=\"h4\" component=\"h1\">
          リアルタイム価格ダッシュボード
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title=\"フルスクリーン表示\">
            <IconButton
              onClick={() => setFullscreen(!fullscreen)}
              color={fullscreen ? \"primary\" : \"default\"}
            >
              <FullscreenIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title=\"設定\">
            <IconButton onClick={() => setSettingsOpen(true)}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* User info */}
      {user && (
        <Alert severity=\"info\" sx={{ mb: 3 }}>
          ようこそ、{user.username}さん！リアルタイム価格データをお楽しみください。
        </Alert>
      )}

      {/* Quick Actions */}
      <QuickActions />

      {/* Main Price Display */}
      <Box sx={{ mb: 3 }}>
        <PriceWebSocket
          symbols={selectedSymbols}
          showTrades={showTrades}
          autoReconnect={autoRefresh}
        />
      </Box>

      {/* Information */}
      <Card>
        <CardContent>
          <Typography variant=\"h6\" gutterBottom>
            ご利用について
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant=\"body2\" paragraph>
                <strong>データソース:</strong> Binance公式WebSocket API
              </Typography>
              <Typography variant=\"body2\" paragraph>
                <strong>更新頻度:</strong> リアルタイム（約1秒間隔）
              </Typography>
              <Typography variant=\"body2\" paragraph>
                <strong>自動再接続:</strong> 接続が切れた場合は自動的に再接続します
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant=\"body2\" paragraph>
                <strong>表示データ:</strong>
                <br />• 現在価格
                <br />• 24時間変動率
                <br />• 24時間高値・安値
                <br />• 24時間出来高
              </Typography>
              {showTrades && (
                <Typography variant=\"body2\" paragraph>
                  <strong>取引データ:</strong> 最新の個別取引情報を表示
                </Typography>
              )}
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <SettingsDialog />
      <AddSymbolDialog />
    </Container>
  );
}
