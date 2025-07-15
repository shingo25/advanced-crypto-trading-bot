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
  CircularProgress
} from '@mui/material';
import { useAuthStore } from '@/store/auth';

export default function LoginForm() {
  const router = useRouter();
  const { login, isLoading, error, clearError } = useAuthStore();
  
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    if (error) {
      clearError();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await login(formData.username, formData.password);
      router.push('/dashboard');
    } catch (error) {
      // エラーはstoreで管理
      console.error('Login error:', error);
    }
  };

  const renderErrorMessage = () => {
    if (!error) return null;
    
    // エラーが文字列の場合はそのまま表示
    if (typeof error === 'string') {
      return (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      );
    }
    
    // エラーがオブジェクトの場合は適切に処理
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        ログインに失敗しました
      </Alert>
    );
  };

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
            Crypto Bot
          </Typography>
          <Typography variant="body1" align="center" color="text.secondary" gutterBottom>
            ログインして取引ボットを管理
          </Typography>
          
          {renderErrorMessage()}
          
          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
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
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="パスワード"
              type="password"
              id="password"
              autoComplete="current-password"
              value={formData.password}
              onChange={handleChange}
              disabled={isLoading}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isLoading}
            >
              {isLoading ? (
                <CircularProgress size={24} />
              ) : (
                'ログイン'
              )}
            </Button>
          </Box>
          
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>デモアカウント:</strong><br />
              ユーザー名: demo<br />
              パスワード: demo
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}