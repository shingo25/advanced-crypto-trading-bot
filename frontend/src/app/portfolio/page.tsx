'use client';

import { Typography, Box, Paper } from '@mui/material';
import AppLayout from '@/components/layout/AppLayout';

// 個人利用版：認証チェックを削除して直接コンテンツを表示
export default function PortfolioPage() {
  return (
    <AppLayout>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          ポートフォリオ
        </Typography>
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            ポートフォリオ画面（実装予定）
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            詳細なポートフォリオ分析機能を実装予定です。
          </Typography>
        </Paper>
      </Box>
    </AppLayout>
  );
}
