import { useAuthStore } from '../auth';

// 個人利用版：常に認証済み状態のテスト
// 将来認証機能を復活する際は、以下のテストを元の実装に戻してください
describe('Auth Store - Personal Use Version', () => {
  // 個人利用版では状態が固定のため、beforeEachでの状態リセットは不要

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with constant authenticated state (personal use)', () => {
    const { user, isAuthenticated, isLoading, error } = useAuthStore.getState();

    // 個人利用版では常に認証済み状態
    expect(user).toEqual({ id: 'local-user', username: 'local', email: 'local@example.com' });
    expect(isAuthenticated).toBeTruthy();
    expect(isLoading).toBeFalsy();
    expect(error).toBeNull();
  });

  it('login does nothing in personal use version', async () => {
    const initialState = useAuthStore.getState();

    // loginを実行
    await initialState.login('testuser', 'password');

    const finalState = useAuthStore.getState();
    // 個人利用版ではloginは何もしないため、状態は変わらない
    expect(finalState.user).toEqual(initialState.user);
    expect(finalState.isAuthenticated).toBe(true);
    expect(finalState.error).toBeNull();
  });

  it('login never fails in personal use version', async () => {
    const initialState = useAuthStore.getState();

    // どんな引数でもloginはエラーを投げない
    await expect(initialState.login('wrong-user', 'wrong-password')).resolves.not.toThrow();

    const finalState = useAuthStore.getState();
    // 状態は変わらず、エラーも発生しない
    expect(finalState.user).toEqual(initialState.user);
    expect(finalState.isAuthenticated).toBe(true);
    expect(finalState.error).toBeNull();
  });

  it('logout does nothing in personal use version', () => {
    const initialState = useAuthStore.getState();

    // logoutを実行
    initialState.logout();

    const finalState = useAuthStore.getState();
    // 個人利用版ではlogoutは何もしないため、状態は変わらない
    expect(finalState.user).toEqual(initialState.user);
    expect(finalState.isAuthenticated).toBe(true);
  });

  it('initialize does nothing in personal use version', () => {
    const initialState = useAuthStore.getState();

    // initializeを実行
    initialState.initialize();

    const finalState = useAuthStore.getState();
    // 個人利用版ではinitializeは何もしないため、状態は変わらない
    expect(finalState.user).toEqual(initialState.user);
    expect(finalState.isAuthenticated).toBe(true);
    expect(finalState.error).toBeNull();
  });

  it('clearError does nothing in personal use version', () => {
    const initialState = useAuthStore.getState();

    // clearErrorを実行
    initialState.clearError();

    const finalState = useAuthStore.getState();
    // 個人利用版ではclearErrorは何もしないため、状態は変わらない
    expect(finalState.error).toBeNull();
  });

  // 将来の認証機能復活時のためのメモ
  // TODO: 認証機能を復活する際は、以下のテストを追加してください：
  // - 正常なログインフローのテスト
  // - ログイン失敗時のエラーハンドリング
  // - ログアウトの動作
  // - localStorageからの初期化処理
});
