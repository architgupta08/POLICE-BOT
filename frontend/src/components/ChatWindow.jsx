import React, { useRef, useEffect, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { sendMessage, getSession } from '../services/api';
import SourceCitations from './SourceCitations';
import ExportPDF from './ExportPDF';

const SUGGESTIONS = [
  'What is the punishment for possession of drugs under NDPS Act?',
  'What are the procedures for conducting a search under NDPS?',
  'How should I document a drug seizure?',
  'What is the bail provision for NDPS offences?',
];

/**
 * Main chat window component.
 * Props:
 *  - sessionId {string|null}
 *  - onSessionCreated(id) {function}
 */
function ChatWindow({ sessionId, onSessionCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const prevSessionId = useRef(null);

  // Load existing session when sessionId changes
  useEffect(() => {
    if (sessionId === prevSessionId.current) return;
    prevSessionId.current = sessionId;

    if (!sessionId) {
      setMessages([]);
      return;
    }

    const load = async () => {
      try {
        const data = await getSession(sessionId);
        setMessages(data.messages || []);
      } catch {
        setMessages([]);
      }
    };
    load();
  }, [sessionId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-dismiss error after 5 s
  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 5000);
    return () => clearTimeout(t);
  }, [error]);

  const handleSend = useCallback(
    async (text) => {
      const query = (text || input).trim();
      if (!query || loading) return;

      setInput('');
      setError(null);

      const userMsg = {
        role: 'user',
        content: query,
        timestamp: format(new Date(), 'yyyy-MM-dd HH:mm'),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const resp = await sendMessage(query, sessionId);
        const botMsg = {
          role: 'assistant',
          content: resp.answer,
          timestamp: resp.timestamp,
          sources: resp.sources,
        };
        setMessages((prev) => [...prev, botMsg]);

        // Notify parent of new/existing session
        if (!sessionId && resp.session_id) {
          onSessionCreated(resp.session_id);
        }
      } catch (err) {
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          'An unexpected error occurred. Please try again.';
        setError(msg);
        setMessages((prev) => prev.slice(0, -1)); // remove optimistic user msg
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    },
    [input, loading, sessionId, onSessionCreated]
  );

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="chat-container">
      {/* ── Toolbar ── */}
      <div className="chat-toolbar">
        <ExportPDF sessionId={sessionId} disabled={!hasMessages} />
        {hasMessages && (
          <button
            className="btn-toolbar danger"
            onClick={() => {
              setMessages([]);
              onSessionCreated(null);
            }}
            title="Clear the current conversation"
          >
            🗑 Clear Chat
          </button>
        )}
      </div>

      {/* ── Messages area ── */}
      <div className="chat-messages">
        {!hasMessages ? (
          <div className="welcome">
            <div className="welcome-icon">👮</div>
            <h2>NDPS Legal Guidance System</h2>
            <p>
              Ask me anything about the Narcotic Drugs and Psychotropic Substances Act —
              procedures, penalties, bail provisions, and more.
            </p>
            <div className="welcome-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => handleSend(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '👮' : '🤖'}
              </div>
              <div className="message-body">
                <div className="message-bubble">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                {msg.role === 'assistant' && msg.sources?.length > 0 && (
                  <SourceCitations sources={msg.sources} />
                )}
                {msg.timestamp && (
                  <span className="message-time">{msg.timestamp}</span>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-body">
              <div className="message-bubble">
                <div className="typing-indicator">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="chat-input-bar">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            placeholder="Ask about NDPS laws, procedures, penalties… (Shift+Enter for new line)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
        </div>
        <button
          className="btn-send"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          title="Send message"
          aria-label="Send message"
        >
          ➤
        </button>
      </div>

      {/* ── Error toast ── */}
      {error && <div className="error-toast">⚠️ {error}</div>}
    </div>
  );
}

export default ChatWindow;
