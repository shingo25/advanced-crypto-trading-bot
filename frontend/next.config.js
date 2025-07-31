/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercelへのデプロイに最適化された設定
  trailingSlash: true,
  output: 'standalone',
  poweredByHeader: false,
  compress: true,

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

  // 画像最適化
  images: {
    domains: [],
    formats: ['image/webp', 'image/avif'],
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

  // サーバーサイドで外部パッケージを利用する場合に設定 (Next.js 14.1+ 推奨)
  serverExternalPackages: [],
};

module.exports = nextConfig;
