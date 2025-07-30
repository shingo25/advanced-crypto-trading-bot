'use client';

import { Typography, Box, Paper, Stack } from '@mui/material';
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

        <Stack spacing={3} direction={{ xs: 'column', md: 'row' }}>
          {/* 取引モード設定 */}
          <Box sx={{ flex: '2 1 0' }}>
            <TradingModeSwitch />
          </Box>

          {/* その他の設定（将来の実装用） */}
          <Box sx={{ flex: '1 1 0' }}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                その他の設定
              </Typography>
              <Typography variant="body2" color="text.secondary">
                システム設定と戦略パラメータ調整機能を実装予定です。
              </Typography>
            </Paper>
          </Box>
        </Stack>
      </Box>
    </AppLayout>
  );
}
