'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Switch,
  FormControlLabel,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import { TrendingUp, TrendingDown, Wifi, WifiOff, Refresh, Settings } from '@mui/icons-material';
import { useAuthStore } from '@/store/auth';

interface PriceData {
  symbol: string;
  price: number;
  change_24h: number;
  change_percent_24h: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  timestamp: string;
}

interface TradeData {
  symbol: string;
  price: number;
  quantity: number;
  side: 'buy' | 'sell';
  timestamp: string;
  trade_id: string;
}

interface WebSocketMessage {
  type: string;
  channel: string;
  data: PriceData | TradeData;
  timestamp: string;
  message_id: string;
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface PriceWebSocketProps {
  symbols?: string[];
  showTrades?: boolean;
  autoReconnect?: boolean;
}

export default function PriceWebSocket({
  symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT'],
  showTrades = false,
  autoReconnect = true,
}: PriceWebSocketProps) {
  // State
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [trades, setTrades] = useState<TradeData[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [messagesReceived, setMessagesReceived] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);

  // Refs
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  // Auth
  const { user } = useAuthStore();

  // WebSocket URL
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000';
    return `${protocol}//${host}/websocket/ws`;
  };

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    setError(null);

    try {
      const wsUrl = getWebSocketUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;

        // 認証は現在無効化（必要に応じて実装）

        // 価格チャンネルを購読
        const subscribeMessage = {
          type: 'subscribe',
          channel: 'prices',
        };
        ws.current?.send(JSON.stringify(subscribeMessage));

        // 取引チャンネルを購読（必要な場合）
        if (showTrades) {
          const tradeSubscribeMessage = {
            type: 'subscribe',
            channel: 'trades',
          };
          ws.current?.send(JSON.stringify(tradeSubscribeMessage));
        }

        setIsSubscribed(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setMessagesReceived((prev) => prev + 1);
          setLastUpdateTime(new Date());

          if (message.type === 'price_update' && message.channel === 'prices') {
            const priceData = message.data as PriceData;
            setPrices((prev) => ({
              ...prev,
              [priceData.symbol]: priceData,
            }));
          } else if (message.type === 'trade_execution' && message.channel === 'trades') {
            const tradeData = message.data as TradeData;
            setTrades((prev) => [tradeData, ...prev.slice(0, 49)]); // 最新50件を保持
          } else if (message.type === 'error') {
            console.error('WebSocket error message:', message.data);
            setError(String(message.data));
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        setError('WebSocket接続でエラーが発生しました');
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionStatus('disconnected');
        setIsSubscribed(false);

        // 自動再接続
        if (autoReconnect && reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectAttempts.current++;

          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (attempt ${reconnectAttempts.current})`);
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      setError('WebSocket接続の作成に失敗しました');
    }
  }, [showTrades, autoReconnect]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }

    setConnectionStatus('disconnected');
    setIsSubscribed(false);
    reconnectAttempts.current = 0;
  }, []);

  // Send heartbeat
  const sendHeartbeat = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const heartbeatMessage = {
        type: 'heartbeat',
      };
      ws.current.send(JSON.stringify(heartbeatMessage));
    }
  }, []);

  // Effects
  useEffect(() => {
    connect();

    // ハートビート送信（30秒間隔）
    const heartbeatInterval = setInterval(sendHeartbeat, 30000);

    return () => {
      clearInterval(heartbeatInterval);
      disconnect();
    };
  }, [connect, disconnect, sendHeartbeat]);

  // Formatters
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatVolume = (value: number) => {
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toFixed(2);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ja-JP');
  };

  // Connection status indicator
  const ConnectionIndicator = () => {
    const getStatusColor = () => {
      switch (connectionStatus) {
        case 'connected':
          return '#4caf50';
        case 'connecting':
          return '#ff9800';
        case 'disconnected':
          return '#757575';
        case 'error':
          return '#f44336';
        default:
          return '#757575';
      }
    };

    const getStatusIcon = () => {
      switch (connectionStatus) {
        case 'connected':
          return <Wifi />;
        case 'connecting':
          return <CircularProgress size={20} />;
        case 'disconnected':
        case 'error':
          return <WifiOff />;
        default:
          return <WifiOff />;
      }
    };

    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ color: getStatusColor() }}>{getStatusIcon()}</Box>
        <Typography variant="caption" sx={{ color: getStatusColor() }}>
          {connectionStatus.toUpperCase()}
        </Typography>
        {lastUpdateTime && (
          <Typography variant="caption" color="text.secondary">
            最終更新: {formatTime(lastUpdateTime.toISOString())}
          </Typography>
        )}
      </Box>
    );
  };

  // Price card component
  const PriceCard = ({ priceData }: { priceData: PriceData }) => {
    const isPositive = priceData.change_percent_24h >= 0;
    const changeColor = isPositive ? '#4caf50' : '#f44336';

    return (
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}
          >
            <Typography variant="h6" component="div">
              {priceData.symbol.replace('USDT', '/USDT')}
            </Typography>
            <Chip
              icon={isPositive ? <TrendingUp /> : <TrendingDown />}
              label={formatPercent(priceData.change_percent_24h)}
              sx={{
                backgroundColor: changeColor,
                color: 'white',
              }}
              size="small"
            />
          </Box>

          <Typography variant="h4" sx={{ mb: 1, fontWeight: 'bold' }}>
            {formatCurrency(priceData.price)}
          </Typography>

          <Grid container spacing={1}>
            <Grid size={6}>
              <Typography variant="caption" color="text.secondary">
                24H 高値
              </Typography>
              <Typography variant="body2">{formatCurrency(priceData.high_24h)}</Typography>
            </Grid>
            <Grid size={6}>
              <Typography variant="caption" color="text.secondary">
                24H 安値
              </Typography>
              <Typography variant="body2">{formatCurrency(priceData.low_24h)}</Typography>
            </Grid>
            <Grid size={12}>
              <Typography variant="caption" color="text.secondary">
                24H 出来高
              </Typography>
              <Typography variant="body2">{formatVolume(priceData.volume_24h)}</Typography>
            </Grid>
          </Grid>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            更新時刻: {formatTime(priceData.timestamp)}
          </Typography>
        </CardContent>
      </Card>
    );
  };

  // Trade list component
  const TradeList = () => {
    if (!showTrades || trades.length === 0) {
      return null;
    }

    return (
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            最新取引 (最新10件)
          </Typography>
          {trades.slice(0, 10).map((trade, index) => (
            <Box
              key={trade.trade_id}
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 0.5,
                borderBottom: index < 9 ? '1px solid #e0e0e0' : 'none',
              }}
            >
              <Box>
                <Typography variant="body2" component="span">
                  {trade.symbol.replace('USDT', '/USDT')}
                </Typography>
                <Chip
                  label={trade.side.toUpperCase()}
                  size="small"
                  sx={{
                    ml: 1,
                    backgroundColor: trade.side === 'buy' ? '#4caf50' : '#f44336',
                    color: 'white',
                  }}
                />
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="body2">{formatCurrency(trade.price)}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {trade.quantity.toFixed(4)}
                </Typography>
              </Box>
            </Box>
          ))}
        </CardContent>
      </Card>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" component="h2">
          リアルタイム価格
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <ConnectionIndicator />
          <Tooltip title="再接続">
            <IconButton
              onClick={() => {
                disconnect();
                connect();
              }}
              size="small"
            >
              <Refresh />
            </IconButton>
          </Tooltip>
          <FormControlLabel
            control={<Switch checked={showTrades} size="small" />}
            label="取引表示"
          />
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" color="text.secondary">
          接続状態: {connectionStatus} | 受信メッセージ数: {messagesReceived} | 価格データ:{' '}
          {Object.keys(prices).length}件
        </Typography>
      </Box>

      {/* Price Cards */}
      <Grid container spacing={2}>
        {symbols.map((symbol) => {
          const priceData = prices[symbol];
          if (!priceData) {
            return (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={symbol}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Typography variant="h6">{symbol.replace('USDT', '/USDT')}</Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                      <CircularProgress size={40} />
                    </Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 1, textAlign: 'center' }}
                    >
                      データを読み込み中...
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            );
          }

          return (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={symbol}>
              <PriceCard priceData={priceData} />
            </Grid>
          );
        })}
      </Grid>

      {/* Trade List */}
      <TradeList />
    </Box>
  );
}
