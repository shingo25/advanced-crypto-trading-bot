# パッケージアップグレード計画

## 即座に対応可能（低リスク）

### 1. マイナー・パッチ更新

```bash
npm update @supabase/supabase-js@2.53.0
npm update @testing-library/jest-dom@6.6.4
npm update axios@1.11.0
npm update zustand@5.0.7
```

### 2. Next.js関連更新

```bash
npm update next@15.4.5
npm update eslint-config-next@15.4.5
```

## 中期対応（テスト必要）

### 3. ESLint 9.x 移行

```bash
# ESLint 9.x は設定ファイル形式が大幅変更
# 段階的移行が必要
npm install eslint@9.32.0 --save-dev
```

**影響範囲**:

- `eslint.config.js` への設定ファイル移行
- プラグインの互換性確認
- CI/CDパイプラインでの動作確認

## 長期対応（重大な変更）

### 4. React 19.x 移行

```bash
# React 19 は破壊的変更を含む
npm install react@19.1.1 react-dom@19.1.1
npm install @types/react@19.1.9 @types/react-dom@19.1.7
```

**影響範囲**:

- Concurrent Features の変更
- useEffect の動作変更
- StrictMode の強化

### 5. TailwindCSS 4.x 移行

```bash
# TailwindCSS 4.x は設定システムが大幅変更
npm install tailwindcss@4.1.11
```

**影響範囲**:

- 設定ファイルの構文変更
- プラグインシステムの変更
- ビルドプロセスの最適化

## 推奨実行順序

1. **フェーズ1**: マイナー・パッチ更新（今週）
2. **フェーズ2**: Next.js更新（来週）
3. **フェーズ3**: ESLint 9.x移行（来月）
4. **フェーズ4**: React 19.x検証（四半期後）
5. **フェーズ5**: TailwindCSS 4.x検証（四半期後）
