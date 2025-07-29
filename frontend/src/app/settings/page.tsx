'use client';

import { Typography, Box, Grid, Paper } from '@mui/material';
import AppLayout from '@/components/layout/AppLayout';
import TradingModeSwitch from '@/components/settings/TradingModeSwitch';

// 個人利用版：認証チェックを削除して直接コンテンツを表示
export default function SettingsPage() {
  return (
    <AppLayout>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          設定
        </Typography>
        
        <Grid container spacing={3}>
          {/* 取引モード設定 */}
          <Grid item xs={12} md={8}>
            <TradingModeSwitch />
          </Grid>
          
          {/* その他の設定（将来の実装用） */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                その他の設定
              </Typography>
              <Typography variant="body2" color="text.secondary">
                システム設定と戦略パラメータ調整機能を実装予定です。
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </AppLayout>
  );
}
