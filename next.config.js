/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel デプロイ最適化 - Vercel自動最適化を使用
  // output: 'standalone', // Vercel用に無効化

  // 開発環境でのAPIプロキシ
  ...(process.env.NODE_ENV === 'development'
    ? {
        async rewrites() {
          return [
            {
              source: '/api/:path*',
              destination: 'http://localhost:8000/api/:path*',
            },
          ];
        },
      }
    : {}),

  // 環境変数
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000'),
  },

  // 画像最適化（Vercel対応）
  images: {
    domains: [],
    formats: ['image/webp', 'image/avif'],
    unoptimized: false, // Vercel最適化を有効化
  },

  // Webpackのカスタム設定
  webpack: (config, { isServer }) => {
    // エイリアスの設定
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, 'src'),
    };

    // クライアントサイドで 'fs' モジュールを除外
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }

    return config;
  },

  // React Strict Mode有効化
  reactStrictMode: true,

  // 実験的機能
  experimental: {
    // App Routerでの最適化
    optimizePackageImports: ['@mui/material', '@mui/icons-material'],
  },
};

module.exports = nextConfig;
