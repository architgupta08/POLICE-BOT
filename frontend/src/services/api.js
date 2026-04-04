import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Chat ────────────────────────────────────────────────────────────────────

/**
 * Send a chat message to the backend.
 * @param {string} message
 * @param {string|null} sessionId
 * @param {number} topK
 * @returns {Promise<{session_id:string, answer:string, sources:string[], timestamp:string}>}
 */
export const sendMessage = async (message, sessionId = null, topK = 5) => {
  const response = await api.post('/api/chat', {
    message,
    session_id: sessionId,
    top_k: topK,
  });
  return response.data;
};

// ─── Sessions ────────────────────────────────────────────────────────────────

/** Fetch list of all saved sessions. */
export const getSessions = async () => {
  const response = await api.get('/api/sessions');
  return response.data;
};

/** Fetch full message history for a session. */
export const getSession = async (sessionId) => {
  const response = await api.get(`/api/sessions/${sessionId}`);
  return response.data;
};

/** Delete a session. */
export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/api/sessions/${sessionId}`);
  return response.data;
};

// ─── PDF Export ──────────────────────────────────────────────────────────────

/**
 * Trigger browser download of a session's PDF export.
 * @param {string} sessionId
 */
export const exportSessionPDF = async (sessionId) => {
  const response = await api.get(`/api/sessions/${sessionId}/export/pdf`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `police_bot_session_${sessionId.substring(0, 8)}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const getHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export default api;
