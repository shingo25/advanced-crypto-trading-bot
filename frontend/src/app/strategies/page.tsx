'use client';

import AppLayout from '@/components/layout/AppLayout';
import StrategyList from '@/components/strategies/StrategyList';

// 個人利用版：認証チェックを削除して直接コンテンツを表示
export default function StrategiesPage() {
  return (
    <AppLayout>
      <StrategyList />
    </AppLayout>
  );
}
