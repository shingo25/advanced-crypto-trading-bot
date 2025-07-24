'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    // 認証機能は削除されました - ダッシュボードに直接リダイレクト
    router.push('/dashboard');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">認証機能は無効化されました</h1>
        <p className="text-gray-600 mb-4">ダッシュボードに自動リダイレクトします...</p>
        <p className="text-sm text-gray-500">個人利用版のため認証は不要です</p>
      </div>
    </div>
  );
}
