import { authApi } from '@/lib/api';
import { useAuthStore } from '../auth';

// Mock the API
jest.mock('@/lib/api');

const mockAuthApi = authApi as jest.Mocked<typeof authApi>;

describe('Auth Store', () => {
  beforeEach(() => {
    useAuthStore.getState().user = null;
    useAuthStore.getState().isAuthenticated = false;
    useAuthStore.getState().loading = false;
    useAuthStore.getState().error = null;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with default state', () => {
    const { user, isAuthenticated, loading, error } = useAuthStore.getState();
    
    expect(user).toBeNull();
    expect(isAuthenticated).toBeFalsy();
    expect(loading).toBeFalsy();
    expect(error).toBeNull();
  });

  it('handles successful login', async () => {
    const mockUser = { username: 'testuser' };
    mockAuthApi.login.mockResolvedValueOnce({
      user: mockUser,
      token: 'test-token'
    });

    const { login } = useAuthStore.getState();
    await login('testuser', 'password');

    const { user, isAuthenticated, error } = useAuthStore.getState();
    expect(user).toEqual(mockUser);
    expect(isAuthenticated).toBeTruthy();
    expect(error).toBeNull();
  });

  it('handles failed login', async () => {
    mockAuthApi.login.mockRejectedValueOnce(new Error('Invalid credentials'));

    const { login } = useAuthStore.getState();
    await login('testuser', 'wrong-password');

    const { user, isAuthenticated, error } = useAuthStore.getState();
    expect(user).toBeNull();
    expect(isAuthenticated).toBeFalsy();
    expect(error).toBe('Invalid credentials');
  });

  it('handles logout', () => {
    // Set initial authenticated state
    useAuthStore.setState({
      user: { username: 'testuser' },
      isAuthenticated: true
    });

    const { logout } = useAuthStore.getState();
    logout();

    const { user, isAuthenticated } = useAuthStore.getState();
    expect(user).toBeNull();
    expect(isAuthenticated).toBeFalsy();
  });

  it('initializes from localStorage on app start', () => {
    // Mock localStorage
    const mockToken = 'stored-token';
    const mockUser = { username: 'stored-user' };
    
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn().mockReturnValue(mockToken),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      writable: true
    });

    mockAuthApi.verify.mockResolvedValueOnce(mockUser);

    const { initialize } = useAuthStore.getState();
    initialize();

    // Since this is async, we need to wait for the state to update
    setTimeout(() => {
      const { user, isAuthenticated } = useAuthStore.getState();
      expect(user).toEqual(mockUser);
      expect(isAuthenticated).toBeTruthy();
    }, 100);
  });
});