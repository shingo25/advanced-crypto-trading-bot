import { create } from 'zustand';
import { strategyApi } from '@/lib/api';
import type { Strategy } from '@/types/api';

interface StrategyState {
  strategies: Strategy[];
  isLoading: boolean;
  error: string | null;
  
  // アクション
  fetchStrategies: () => Promise<void>;
  startStrategy: (id: string) => Promise<void>;
  stopStrategy: (id: string) => Promise<void>;
  updateStrategy: (id: string, data: Partial<Strategy>) => Promise<void>;
  clearError: () => void;
}

export const useStrategyStore = create<StrategyState>((set, get) => ({
  strategies: [],
  isLoading: false,
  error: null,

  fetchStrategies: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const strategies = await strategyApi.getStrategies();
      set({
        strategies,
        isLoading: false,
        error: null
      });
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || '戦略の取得に失敗しました'
      });
    }
  },

  startStrategy: async (id: string) => {
    try {
      await strategyApi.startStrategy(id);
      
      // 戦略リストを更新
      const strategies = get().strategies.map(strategy => 
        strategy.id === id 
          ? { ...strategy, status: 'running' as const }
          : strategy
      );
      
      set({ strategies });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '戦略の開始に失敗しました'
      });
      throw error;
    }
  },

  stopStrategy: async (id: string) => {
    try {
      await strategyApi.stopStrategy(id);
      
      // 戦略リストを更新
      const strategies = get().strategies.map(strategy => 
        strategy.id === id 
          ? { ...strategy, status: 'stopped' as const }
          : strategy
      );
      
      set({ strategies });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '戦略の停止に失敗しました'
      });
      throw error;
    }
  },

  updateStrategy: async (id: string, data: Partial<Strategy>) => {
    try {
      const updatedStrategy = await strategyApi.updateStrategy(id, data);
      
      // 戦略リストを更新
      const strategies = get().strategies.map(strategy => 
        strategy.id === id ? updatedStrategy : strategy
      );
      
      set({ strategies });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || '戦略の更新に失敗しました'
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  }
}));