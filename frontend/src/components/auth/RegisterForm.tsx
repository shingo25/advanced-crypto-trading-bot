'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  CircularProgress,
  FormControl,
  FormHelperText,
} from '@mui/material';
import Link from 'next/link';

interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

interface ValidationErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export default function RegisterForm() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  const [formData, setFormData] = useState<RegisterFormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // ユーザー名バリデーション
    if (!formData.username.trim()) {
      errors.username = 'ユーザー名は必須です';
    } else if (formData.username.length < 3) {
      errors.username = 'ユーザー名は3文字以上である必要があります';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      errors.username = 'ユーザー名は英数字とアンダースコアのみ使用可能です';
    }

    // メールアドレスバリデーション
    if (!formData.email.trim()) {
      errors.email = 'メールアドレスは必須です';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = '有効なメールアドレスを入力してください';
    }

    // パスワードバリデーション
    if (!formData.password) {
      errors.password = 'パスワードは必須です';
    } else if (formData.password.length < 8) {
      errors.password = 'パスワードは8文字以上である必要があります';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      errors.password = 'パスワードは大文字、小文字、数字を含む必要があります';
    }

    // パスワード確認バリデーション
    if (!formData.confirmPassword) {
      errors.confirmPassword = 'パスワード確認は必須です';
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'パスワードが一致しません';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // リアルタイムバリデーション（エラーがある場合のみ）
    if (validationErrors[name as keyof ValidationErrors]) {
      setValidationErrors((prev) => ({ ...prev, [name]: undefined }));
    }

    if (error) {
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '登録に失敗しました');
      }

      const data = await response.json();
      setSuccess(true);

      // 3秒後にログインページにリダイレクト
      setTimeout(() => {
        router.push('/login?registered=true');
      }, 3000);
    } catch (error: any) {
      setError(error.message || '登録に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <Container maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
            <Alert severity="success" sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                アカウント作成完了！
              </Typography>
              <Typography variant="body2">
                ユーザー登録が正常に完了しました。
                <br />
                3秒後にログインページに移動します...
              </Typography>
            </Alert>
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <CircularProgress size={24} />
            </Box>
          </Paper>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            アカウント作成
          </Typography>
          <Typography variant="body1" align="center" color="text.secondary" gutterBottom>
            Crypto Bot への新規登録
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <FormControl fullWidth margin="normal" error={!!validationErrors.username}>
              <TextField
                required
                fullWidth
                id="username"
                label="ユーザー名"
                name="username"
                autoComplete="username"
                autoFocus
                value={formData.username}
                onChange={handleChange}
                disabled={isLoading}
                error={!!validationErrors.username}
              />
              {validationErrors.username && (
                <FormHelperText>{validationErrors.username}</FormHelperText>
              )}
            </FormControl>

            <FormControl fullWidth margin="normal" error={!!validationErrors.email}>
              <TextField
                required
                fullWidth
                id="email"
                label="メールアドレス"
                name="email"
                autoComplete="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
                error={!!validationErrors.email}
              />
              {validationErrors.email && <FormHelperText>{validationErrors.email}</FormHelperText>}
            </FormControl>

            <FormControl fullWidth margin="normal" error={!!validationErrors.password}>
              <TextField
                required
                fullWidth
                name="password"
                label="パスワード"
                type="password"
                id="password"
                autoComplete="new-password"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
                error={!!validationErrors.password}
              />
              {validationErrors.password && (
                <FormHelperText>{validationErrors.password}</FormHelperText>
              )}
            </FormControl>

            <FormControl fullWidth margin="normal" error={!!validationErrors.confirmPassword}>
              <TextField
                required
                fullWidth
                name="confirmPassword"
                label="パスワード確認"
                type="password"
                id="confirmPassword"
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={isLoading}
                error={!!validationErrors.confirmPassword}
              />
              {validationErrors.confirmPassword && (
                <FormHelperText>{validationErrors.confirmPassword}</FormHelperText>
              )}
            </FormControl>

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isLoading}
            >
              {isLoading ? <CircularProgress size={24} /> : 'アカウント作成'}
            </Button>

            <Box sx={{ textAlign: 'center' }}>
              <Link href="/login" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary" sx={{ cursor: 'pointer' }}>
                  既にアカウントをお持ちの場合はこちら
                </Typography>
              </Link>
            </Box>
          </Box>

          <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>デモアカウントでの利用:</strong>
              <br />
              既にデモアカウント（demo/demo）もご利用いただけます。
              <br />
              個人アカウントを作成すると、設定やデータが保存されます。
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
