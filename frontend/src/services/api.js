import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || '';

const TOKEN_KEY = 'police_bot_token';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request when available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 Unauthorized responses: clear stored credentials and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem('police_bot_user');
      // Only redirect if not already on an auth page to avoid redirect loops
      if (!window.location.pathname.startsWith('/login') &&
          !window.location.pathname.startsWith('/signup')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── Authentication ───────────────────────────────────────────────────────────

/**
 * Register a new user.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{access_token:string, token_type:string, user_id:number, email:string}>}
 */
export const signupUser = async (email, password) => {
  const response = await api.post('/auth/signup', { email, password });
  return response.data;
};

/**
 * Login with email and password.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{access_token:string, token_type:string, user_id:number, email:string}>}
 */
export const loginUser = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};

/** Logout (server-side – client should also clear the token). */
export const logoutUser = async () => {
  const response = await api.post('/auth/logout');
  return response.data;
};

/** Fetch the currently authenticated user's profile. */
export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

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
