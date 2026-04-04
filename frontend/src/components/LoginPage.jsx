import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LoginPage() {
  const { login, loading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldError, setFieldError] = useState('');

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFieldError('');

    if (!email.trim() || !password) {
      setFieldError('Please enter your email and password.');
      return;
    }

    const ok = await login(email.trim(), password);
    if (ok) navigate('/', { replace: true });
  };

  const displayError = fieldError || error;

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🚔 POLICE-BOT</div>
        <h2 className="auth-title">Sign in to your account</h2>
        <p className="auth-subtitle">NDPS Legal Guidance System</p>

        {displayError && (
          <div className="auth-error" role="alert">
            ⚠️ {displayError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer@police.gov.in"
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={loading}
              required
            />
          </div>

          <button type="submit" className="btn-auth" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account?{' '}
          <Link to="/signup">Create one here</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
