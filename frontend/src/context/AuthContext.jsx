import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { loginUser, signupUser, logoutUser } from '../services/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'police_bot_token';
const USER_KEY = 'police_bot_user';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Keep axios default header in sync with token
  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }, [token]);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loginUser(email, password);
      setToken(data.access_token);
      const userInfo = { id: data.user_id, email: data.email };
      setUser(userInfo);
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
      return true;
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Login failed. Please check your credentials.';
      setError(msg);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await signupUser(email, password);
      setToken(data.access_token);
      const userInfo = { id: data.user_id, email: data.email };
      setUser(userInfo);
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
      return true;
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Signup failed. Please try again.';
      setError(msg);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // ignore server errors on logout
    }
    setToken(null);
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const isAuthenticated = Boolean(token);

  return (
    <AuthContext.Provider
      value={{ token, user, isAuthenticated, loading, error, login, signup, logout, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

export default AuthContext;
