-- Crypto Bot Database Schema for Supabase
-- This file contains the complete database schema for the crypto trading bot

-- 1. profiles テーブル
-- ユーザー情報を格納します。auth.usersと連携します。
CREATE TABLE public.profiles (
    id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);
-- profilesテーブルのRLS設定
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own profile." ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile." ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 2. exchanges テーブル
-- 取引所のAPIキーなどを保存します。
-- pgsodiumを使った暗号化を推奨します。これはSupabaseで有効化できるわ。
CREATE TABLE public.exchanges (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name text NOT NULL,
    api_key text NOT NULL, -- 暗号化して保存すること！
    api_secret text NOT NULL, -- 暗号化して保存すること！
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);
-- インデックス
CREATE INDEX idx_exchanges_user_id ON public.exchanges(user_id);
-- exchangesテーブルのRLS設定
ALTER TABLE public.exchanges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own exchange connections." ON public.exchanges FOR ALL USING (auth.uid() = user_id);

-- 3. strategies テーブル
-- 取引戦略を管理します。
CREATE TABLE public.strategies (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    parameters jsonb,
    is_active boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);
-- インデックス
CREATE INDEX idx_strategies_user_id ON public.strategies(user_id);
-- strategiesテーブルのRLS設定
ALTER TABLE public.strategies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own strategies." ON public.strategies FOR ALL USING (auth.uid() = user_id);

-- 4. trades テーブル
-- 取引履歴を保存します。
CREATE TABLE public.trades (
    id bigserial NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    strategy_id uuid REFERENCES public.strategies(id) ON DELETE SET NULL,
    exchange_id uuid NOT NULL REFERENCES public.exchanges(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    order_id text,
    side text NOT NULL,
    type text NOT NULL,
    amount numeric NOT NULL,
    price numeric NOT NULL,
    fee numeric,
    "timestamp" timestamp with time zone NOT NULL
);
-- インデックス
CREATE INDEX idx_trades_user_id ON public.trades(user_id);
CREATE INDEX idx_trades_strategy_id ON public.trades(strategy_id);
CREATE INDEX idx_trades_exchange_id ON public.trades(exchange_id);
CREATE INDEX idx_trades_timestamp ON public.trades("timestamp");
CREATE INDEX idx_trades_symbol ON public.trades(symbol);
-- tradesテーブルのRLS設定
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own trades." ON public.trades FOR ALL USING (auth.uid() = user_id);

-- 5. positions テーブル
-- 現在のポジションを管理します。
CREATE TABLE public.positions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    amount numeric NOT NULL,
    average_entry_price numeric NOT NULL,
    last_updated timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT positions_user_id_symbol_key UNIQUE (user_id, symbol)
);
-- インデックス
CREATE INDEX idx_positions_user_id ON public.positions(user_id);
-- positionsテーブルのRLS設定
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own positions." ON public.positions FOR ALL USING (auth.uid() = user_id);

-- 6. backtest_results テーブル
-- バックテスト結果を保存します。
CREATE TABLE public.backtest_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    strategy_id uuid NOT NULL REFERENCES public.strategies(id) ON DELETE CASCADE,
    start_period timestamp with time zone NOT NULL,
    end_period timestamp with time zone NOT NULL,
    results_data jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);
-- インデックス
CREATE INDEX idx_backtest_results_user_id ON public.backtest_results(user_id);
CREATE INDEX idx_backtest_results_strategy_id ON public.backtest_results(strategy_id);
-- backtest_resultsテーブルのRLS設定
ALTER TABLE public.backtest_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own backtest results." ON public.backtest_results FOR ALL USING (auth.uid() = user_id);

-- 7. settings テーブル
-- ユーザーごとの設定を保存します。
CREATE TABLE public.settings (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    key text NOT NULL,
    value jsonb,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT settings_user_id_key_key UNIQUE (user_id, key)
);
-- インデックス
CREATE INDEX idx_settings_user_id ON public.settings(user_id);
-- settingsテーブルのRLS設定
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own settings." ON public.settings FOR ALL USING (auth.uid() = user_id);

-- 8. price_data テーブル
-- 取引所から取得したOHLCV価格データを保存します。
CREATE TABLE public.price_data (
    id bigserial NOT NULL PRIMARY KEY,
    exchange text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    timestamp timestamp with time zone NOT NULL,
    open_price numeric(20,8) NOT NULL,
    high_price numeric(20,8) NOT NULL,
    low_price numeric(20,8) NOT NULL,
    close_price numeric(20,8) NOT NULL,
    volume numeric(20,8) NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(exchange, symbol, timeframe, timestamp)
);

-- インデックス（パフォーマンス最適化）
CREATE INDEX idx_price_data_exchange_symbol ON public.price_data(exchange, symbol);
CREATE INDEX idx_price_data_timeframe ON public.price_data(timeframe);
CREATE INDEX idx_price_data_timestamp ON public.price_data(timestamp DESC);
CREATE INDEX idx_price_data_composite ON public.price_data(exchange, symbol, timeframe, timestamp DESC);

-- price_dataテーブルのRLS設定（パブリックデータなので読み取り専用）
ALTER TABLE public.price_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read price data." ON public.price_data FOR SELECT USING (true);
CREATE POLICY "Service can manage price data." ON public.price_data FOR ALL USING (true);

-- 最後に、新規ユーザーが作成されたときに自動でprofilesを作成するトリガーを設定するの。
-- これ、とっても便利よ。
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username)
  VALUES (new.id, new.raw_user_meta_data->>'username');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
