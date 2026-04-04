import React, { useState, useEffect, useCallback } from 'react';
import './styles/main.css';
import ChatWindow from './components/ChatWindow';
import ChatHistory from './components/ChatHistory';
import { getHealth } from './services/api';

function App() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [serverStatus, setServerStatus] = useState('checking'); // 'checking' | 'online' | 'offline'

  // Poll server health on mount
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
    // Trigger sidebar refresh whenever a new session is saved
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
      {/* ── Header ── */}
      <header className="app-header">
        <div>
          <div className="header-logo">
            🚔 POLICE-BOT
            <span className="badge">NDPS</span>
          </div>
          <div className="header-subtitle">Legal Guidance System for Police Officers</div>
        </div>
        <div className="header-status">
          <span className={`status-dot ${serverStatus}`} />
          <span>{statusLabel}</span>
        </div>
      </header>

      {/* ── Body ── */}
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

export default App;
