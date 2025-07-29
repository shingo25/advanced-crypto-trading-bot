# 🚀 Crypto Bot 機能拡張ロードマップ

## 📋 現在の状態（v5.0.0 - 個人利用版）

### ✅ 実装済み機能

- **シンプルAPI**: 認証なしの個人利用向けAPI
- **基本エンドポイント**: `/api`, `/api/health`, `/api/prices`, `/api/portfolio`, `/api/trades`
- **モックデータ**: 開発・テスト用のダミーデータ提供
- **Vercelデプロイ**: サーバーレス環境での稼働
- **フロントエンド**: Next.js Static Export対応

### 🎯 設計方針

- **個人利用**: 複数ユーザー対応なし
- **認証レス**: Password Protection無効化前提
- **シンプル**: 最小限の依存関係とコード

---

## 🔮 将来の機能拡張計画

### Phase 1: 基本認証システム復活 🔐

**目標**: マルチユーザー対応とセキュリティ強化

#### 1.1 認証基盤

- **Supabase Auth復活**: ユーザー管理・認証
- **JWT実装**: セキュアなトークン認証
- **Role-based Access**: 管理者・一般ユーザー権限

#### 1.2 ユーザー管理機能

```typescript
// 想定API
POST / api / auth / register; // 新規ユーザー登録
POST / api / auth / login; // ログイン
POST / api / auth / logout; // ログアウト
GET / api / auth / me; // ユーザー情報取得
PUT / api / auth / profile; // プロファイル更新
```

#### 1.3 デモ機能

- **デモアカウント**: demo/demo でのテスト利用
- **サンプルデータ**: デモ用のポートフォリオ・取引履歴
- **機能制限**: デモユーザーでの操作制限

#### 1.4 認証UI復活

- **ログインページ**: モダンなUI/UX
- **登録ページ**: 新規ユーザー向け
- **プロファイル管理**: ユーザー設定画面

---

### Phase 2: 実データ統合 📊

**目標**: 実際の暗号通貨データとの連携

#### 2.1 価格データAPI

- **CoinGecko API**: リアルタイム価格取得
- **履歴データ**: チャート表示用データ
- **WebSocket**: リアルタイム価格更新

#### 2.2 取引所API統合

- **Binance API**: 実際のトレーディング
- **取引履歴同期**: API経由での履歴取得
- **残高管理**: 実際のウォレット連携

#### 2.3 ポートフォリオ管理

```typescript
// 想定API
GET / api / portfolio / real; // 実際のポートフォリオ
POST / api / portfolio / sync; // 取引所との同期
GET / api / portfolio / history; // 資産履歴
```

---

### Phase 3: 高度なトレーディング機能 🤖

**目標**: 自動売買とアルゴリズム取引

#### 3.1 取引戦略

- **戦略エンジン**: カスタム取引ロジック
- **バックテスト**: 過去データでの戦略検証
- **パフォーマンス分析**: 収益率・リスク分析

#### 3.2 自動売買

- **スケージューラー**: 定期実行システム
- **アラート機能**: 価格通知・取引通知
- **リスク管理**: ストップロス・利確設定

#### 3.3 機械学習統合

- **価格予測**: ML/AIモデルでの予測
- **感情分析**: ニュース・SNS分析
- **最適化**: 遺伝的アルゴリズム等

---

### Phase 4: エンタープライズ機能 🏢

**目標**: 本格的なサービス化

#### 4.1 マルチテナント

- **組織管理**: チーム・企業向け機能
- **権限管理**: 細かい権限設定
- **API制限**: レート制限・使用量管理

#### 4.2 監査・コンプライアンス

- **取引ログ**: 完全な監査証跡
- **レポート機能**: 税務・会計レポート
- **規制対応**: 各国の暗号通貨規制対応

#### 4.3 スケーラビリティ

- **データベース**: PostgreSQL/MongoDB
- **キャッシュ**: Redis実装
- **CDN**: グローバル配信

---

## 🛠️ 技術的な移行計画

### アーキテクチャ進化

```
v5.0.0 (現在)     → v6.0.0 (認証復活)  → v7.0.0 (実データ)  → v8.0.0 (自動売買)
・FastAPI単体      ・Supabase Auth     ・外部API統合      ・ML/AI統合
・モックデータ      ・JWT認証          ・WebSocket       ・スケジューラー
・認証なし         ・ユーザー管理       ・リアルタイム     ・アルゴリズム
```

### データベース設計

```sql
-- Phase 1: 認証復活時
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE,
  username TEXT UNIQUE,
  created_at TIMESTAMP,
  role TEXT DEFAULT 'user'
);

-- Phase 2: 実データ統合時
CREATE TABLE portfolios (
  user_id UUID REFERENCES users(id),
  symbol TEXT,
  amount DECIMAL,
  updated_at TIMESTAMP
);

-- Phase 3: 取引戦略時
CREATE TABLE strategies (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name TEXT,
  config JSONB,
  is_active BOOLEAN
);
```

---

## 💰 課金・収益化計画

### 料金プラン設計

- **Free**: 個人利用・基本機能
- **Pro**: 実データ・高度分析 (月額 ¥2,980)
- **Enterprise**: 自動売買・API制限解除 (月額 ¥9,800)

### 機能制限

```javascript
const featureLimits = {
  free: {
    portfolios: 3,
    strategies: 1,
    apiCalls: 1000,
    dataRetention: "30 days",
  },
  pro: {
    portfolios: 10,
    strategies: 5,
    apiCalls: 10000,
    dataRetention: "1 year",
  },
  enterprise: {
    portfolios: "unlimited",
    strategies: "unlimited",
    apiCalls: "unlimited",
    dataRetention: "unlimited",
  },
};
```

---

## 📅 実装スケジュール

### 短期 (1-3ヶ月)

- [ ] Phase 1.1: Supabase Auth復活
- [ ] Phase 1.2: 基本ユーザー管理
- [ ] Phase 1.3: デモ機能実装

### 中期 (3-6ヶ月)

- [ ] Phase 2.1: 外部API統合
- [ ] Phase 2.2: リアルタイム価格
- [ ] Phase 1.4: 認証UI完成

### 長期 (6-12ヶ月)

- [ ] Phase 3.1: 取引戦略エンジン
- [ ] Phase 3.2: 自動売買機能
- [ ] Phase 4.1: エンタープライズ機能

---

## 📝 開発メモ

### 現在の技術スタック保持

- **Backend**: FastAPI + Mangum (Vercel)
- **Frontend**: Next.js + Static Export
- **Database**: 当面はSupabase、将来的にPostgreSQL
- **Deploy**: Vercel (個人利用十分)

### 移行時の注意点

- **後方互換性**: 既存APIの維持
- **段階的移行**: フェーズごとの安全な移行
- **データ移行**: ユーザーデータの安全な移行
- **テスト**: 各フェーズでの十分なテスト

---

## 🎯 成功指標

### KPI設定

- **ユーザー数**: 1,000ユーザー (6ヶ月)
- **アクティブ率**: 月間40%以上
- **収益**: 月額 ¥100,000 (12ヶ月)
- **API使用量**: 1M requests/month

### 品質指標

- **稼働率**: 99.9%以上
- **レスポンス時間**: 200ms以下
- **エラー率**: 0.1%以下

---

**最終更新**: 2025-07-24  
**作成者**: Claude Code  
**バージョン**: v5.0.0 Planning Document
