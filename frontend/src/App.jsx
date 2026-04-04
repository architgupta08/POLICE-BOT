import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './styles/main.css';
import ChatWindow from './components/ChatWindow';
import ChatHistory from './components/ChatHistory';
import LoginPage from './components/LoginPage';
import SignupPage from './components/SignupPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { getHealth } from './services/api';

// ── Protected route wrapper ──────────────────────────────────────────────────

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

// ── Main app shell (shown when logged in) ────────────────────────────────────

function AppShell() {
  const { user, logout } = useAuth();
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [serverStatus, setServerStatus] = useState('checking');

  useEffect(() => {
    const check = async () => {
      try {
        await getHealth();
        setServerStatus('online');
      } catch {
        setServerStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSessionCreated = useCallback((id) => {
    setActiveSessionId(id);
    setHistoryRefresh((n) => n + 1);
  }, []);

  const handleSelectSession = useCallback((id) => {
    setActiveSessionId(id);
  }, []);

  const handleNewSession = useCallback(() => {
    setActiveSessionId(null);
  }, []);

  const statusLabel =
    serverStatus === 'online'
      ? 'System Online'
      : serverStatus === 'offline'
      ? 'Backend Offline'
      : 'Connecting…';

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <div className="header-logo">
            🚔 POLICE-BOT
            <span className="badge">NDPS</span>
          </div>
          <div className="header-subtitle">Legal Guidance System for Police Officers</div>
        </div>
        <div className="header-right">
          <div className="header-status">
            <span className={`status-dot ${serverStatus}`} />
            <span>{statusLabel}</span>
          </div>
          {user && (
            <div className="header-user">
              <span className="user-email" title={user.email}>👮 {user.email}</span>
              <button className="btn-logout" onClick={logout} title="Sign out">
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="app-body">
        <ChatHistory
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          refreshTrigger={historyRefresh}
        />
        <ChatWindow
          sessionId={activeSessionId}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  );
}

// ── Root component ───────────────────────────────────────────────────────────

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
