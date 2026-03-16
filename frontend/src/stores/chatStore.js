import { reactive, watch } from 'vue';

const STORAGE_KEY = 'chat_sessions';

const loadFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('Failed to load from localStorage:', e);
  }
  return null;
};

const saveToStorage = (data) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.error('Failed to save to localStorage:', e);
  }
};

const savedState = loadFromStorage();

const state = reactive({
  sessions: savedState?.sessions || [],
  currentSessionId: savedState?.currentSessionId || null,
  messages: savedState?.messages || {}
});

watch(
  () => ({ sessions: state.sessions, currentSessionId: state.currentSessionId, messages: state.messages }),
  (newState) => {
    saveToStorage(newState);
  },
  { deep: true }
);

export function useChatStore() {
  const getSessions = () => state.sessions;
  
  const getCurrentSessionId = () => state.currentSessionId;
  
  const setCurrentSessionId = (id) => {
    state.currentSessionId = id;
  };
  
  const getMessages = (sessionId) => {
    return state.messages[sessionId] || [];
  };
  
  const addMessage = (sessionId, message) => {
    if (!state.messages[sessionId]) {
      state.messages[sessionId] = [];
    }
    state.messages[sessionId].push(message);
  };
  
  const clearMessages = (sessionId) => {
    state.messages[sessionId] = [];
  };
  
  const addSession = (session) => {
    state.sessions.unshift(session);
  };
  
  const updateSession = (sessionId, updates) => {
    const idx = state.sessions.findIndex(s => s.id === sessionId);
    if (idx !== -1) {
      state.sessions[idx] = { ...state.sessions[idx], ...updates };
    }
  };
  
  const removeSession = (sessionId) => {
    const idx = state.sessions.findIndex(s => s.id === sessionId);
    if (idx !== -1) {
      state.sessions.splice(idx, 1);
    }
    delete state.messages[sessionId];
    if (state.currentSessionId === sessionId) {
      state.currentSessionId = state.sessions[0]?.id || null;
    }
  };
  
  const initSessions = (sessions) => {
    if (sessions.length > 0) {
      state.sessions = sessions;
      if (!state.currentSessionId) {
        state.currentSessionId = sessions[0].id;
      }
    }
  };
  
  return {
    state,
    getSessions,
    getCurrentSessionId,
    setCurrentSessionId,
    getMessages,
    addMessage,
    clearMessages,
    addSession,
    updateSession,
    removeSession,
    initSessions
  };
}
