'use client';

import { useEffect } from 'react';

export default function RegisterPage() {
  useEffect(() => {
    // Static Export環境でも確実に動作するリダイレクト
    window.location.href = '/dashboard/';
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-4">ダッシュボードにリダイレクト中...</h1>
        <p className="text-gray-600 mb-4">認証機能は無効化されました</p>
        <p className="text-sm text-gray-500">個人利用版のため認証は不要です</p>
        <div className="mt-4">
          <a href="/dashboard/" className="text-blue-500 hover:underline">
            自動リダイレクトされない場合はこちら
          </a>
        </div>
      </div>
    </div>
  );
}
