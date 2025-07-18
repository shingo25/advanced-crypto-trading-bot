import { create } from 'zustand';
import { dashboardApi } from '@/lib/api';
import type { DashboardSummary, PerformanceData } from '@/types/api';

interface DashboardState {
  summary: DashboardSummary | null;
  performanceData: PerformanceData[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;

  // アクション
  fetchSummary: () => Promise<void>;
  fetchPerformanceData: (period?: string) => Promise<void>;
  updateSummary: (data: Partial<DashboardSummary>) => void;
  clearError: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  summary: null,
  performanceData: [],
  isLoading: false,
  error: null,
  lastUpdated: null,

  fetchSummary: async () => {
    set({ isLoading: true, error: null });

    try {
      const summary = await dashboardApi.getSummary();
      set({
        summary,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
      });
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || 'データの取得に失敗しました',
      });
    }
  },

  fetchPerformanceData: async (period = '7d') => {
    try {
      const performanceData = await dashboardApi.getPerformanceHistory(period);
      set({ performanceData });
    } catch (error: any) {
      console.error('Performance data fetch error:', error);
      set({
        error: error.response?.data?.detail || 'パフォーマンスデータの取得に失敗しました',
      });
    }
  },

  updateSummary: (data: Partial<DashboardSummary>) => {
    const currentSummary = get().summary;
    if (currentSummary) {
      set({
        summary: { ...currentSummary, ...data },
        lastUpdated: new Date(),
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
