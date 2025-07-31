/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel Functions対応
  trailingSlash: true,
  
  // Vercel最適化設定
  output: 'standalone',
  poweredByHeader: false,
  compress: true,

  // 開発環境でのAPI proxy設定
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
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000'),
  },

  // 画像最適化設定（Vercel対応）
  images: {
    domains: [],
    formats: ['image/webp', 'image/avif'],
  },

  // Webpack設定
  webpack: (config, { isServer }) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, 'src'),
    };
    
    // サーバーサイドでのfs使用を許可
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }
    
    return config;
  },

  // 実験的機能（必要に応じて）
  experimental: {
    serverComponentsExternalPackages: [],
  },
};

module.exports = nextConfig;
