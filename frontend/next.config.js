/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel最適化
  output: 'export',
  trailingSlash: true,
  distDir: 'out',

  // 開発環境でのAPI proxy設定 (export モードでは無効)
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

  // 環境変数の設定
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Webpack設定
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, 'src'),
    };
    return config;
  },
};

module.exports = nextConfig;
