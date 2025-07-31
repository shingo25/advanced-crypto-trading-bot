/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel デプロイ最適化
  output: 'standalone',

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
    unoptimized: process.env.NODE_ENV === 'production',
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

  // サーバーサイドで外部パッケージを利用する場合に設定
  serverExternalPackages: [],
};

module.exports = nextConfig;
