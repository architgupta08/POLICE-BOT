import React from 'react';
import { format } from 'date-fns';
import { getSessions, deleteSession } from '../services/api';

/**
 * Sidebar component that lists all saved chat sessions.
 * Props:
 *  - activeSessionId {string}
 *  - onSelectSession(id) {function}
 *  - onNewSession() {function}
 *  - refreshTrigger {any} – change this value to force a refresh
 */
function ChatHistory({ activeSessionId, onSelectSession, onNewSession, refreshTrigger }) {
  const [sessions, setSessions] = React.useState([]);
  const [loading, setLoading] = React.useState(false);

  const loadSessions = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSessions();
      setSessions(data || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadSessions();
  }, [loadSessions, refreshTrigger]);

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (sessionId === activeSessionId) {
        onNewSession();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return '';
    try {
      return format(new Date(isoString), 'MMM d, HH:mm');
    } catch {
      return '';
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">Case History</span>
        <button className="btn-new-chat" onClick={onNewSession} title="Start a new chat">
          + New Chat
        </button>
      </div>

      <div className="sidebar-sessions">
        {loading && (
          <div className="sidebar-empty">Loading sessions…</div>
        )}
        {!loading && sessions.length === 0 && (
          <div className="sidebar-empty">No saved sessions yet. Start a conversation!</div>
        )}
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className={`session-item ${session.session_id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSelectSession(session.session_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onSelectSession(session.session_id)}
          >
            <div className="session-preview" title={session.preview}>
              {session.preview || 'Session'}
            </div>
            <div className="session-meta">
              <span>{formatDate(session.updated_at)}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>{session.message_count} msg{session.message_count !== 1 ? 's' : ''}</span>
                <button
                  className="btn-delete-session"
                  onClick={(e) => handleDelete(e, session.session_id)}
                  title="Delete this session"
                  aria-label="Delete session"
                >
                  🗑
                </button>
              </span>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default ChatHistory;
