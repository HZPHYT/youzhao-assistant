<template>
  <div class="chat-container">
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <span>对话历史</span>
        <button class="new-chat-btn" @click="createNewSession">+ 新建</button>
      </div>
      <div class="session-list">
        <div 
          v-for="session in sessions" 
          :key="session.id"
          :class="['session-item', { active: session.id === currentSessionId }]"
          @click="switchSession(session.id)"
        >
          <div class="session-info" v-if="editingSessionId !== session.id" @dblclick="startEditTitle(session.id, session.title)">
            <span class="session-title">{{ session.title || '新对话' }}</span>
            <span class="session-time">{{ formatTime(session.updated_at) }}</span>
          </div>
          <div class="session-edit" v-else>
            <input 
              v-model="editTitle" 
              @keyup.enter="saveTitle(session.id)"
              @blur="saveTitle(session.id)"
              @keyup.esc="cancelEditTitle"
              ref="titleInput"
              class="title-input"
            />
          </div>
          <button class="delete-btn" @click.stop="deleteSession(session.id)">×</button>
        </div>
      </div>
    </div>
    <div class="chat-main">
      <div class="chat-messages">
        <div v-for="(msg, index) in currentMessages" :key="index" :class="['message', msg.role]">
          <div class="message-content" v-html="msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content"></div>
          
          <div v-if="msg.task_type" class="task-type">
            <span class="task-label">任务类型:</span>
            <span class="task-value">{{ msg.task_type }}</span>
          </div>
          
          <div v-if="msg.metrics" class="metrics-panel">
            <div class="metrics-header">
              <span class="metrics-title">📊 本次回答评测</span>
            </div>
            <div class="metrics-grid">
              <div class="metric-item" :class="{ good: msg.metrics.retrieval_recall > 0 }">
                <span class="metric-name">检索召回</span>
                <span class="metric-value">{{ (msg.metrics.retrieval_recall * 100).toFixed(0) }}%</span>
              </div>
              <div class="metric-item" :class="{ good: msg.metrics.context_precision > 0.5 }">
                <span class="metric-name">上下文精确度</span>
                <span class="metric-value">{{ (msg.metrics.context_precision * 100).toFixed(0) }}%</span>
              </div>
              <div class="metric-item" :class="{ good: msg.metrics.answer_relevancy > 0.5 }">
                <span class="metric-name">答案相关度</span>
                <span class="metric-value">{{ (msg.metrics.answer_relevancy * 100).toFixed(0) }}%</span>
              </div>
              <div class="metric-item" :class="{ good: msg.metrics.faithfulness > 0.5 }">
                <span class="metric-name">知识忠诚度</span>
                <span class="metric-value">{{ (msg.metrics.faithfulness * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          
          <div v-if="msg.sources && msg.sources.length > 0" class="sources">
            <div class="sources-title">📚 引用知识库：</div>
            <ul>
              <li v-for="(source, idx) in msg.sources" :key="idx">
                <div class="source-content">{{ typeof source === 'string' ? source : source.content }}</div>
                <div class="source-meta" v-if="typeof source === 'object'">
                  <span v-if="source.category">🏷️ {{ source.category }}</span>
                  <span v-if="source.source_file">📄 {{ source.source_file }}</span>
                </div>
              </li>
            </ul>
          </div>
          
          <div v-if="msg.role === 'assistant' && !msg.feedbackSubmitted" class="feedback-panel">
            <span class="feedback-label">评价回答：</span>
            <button class="feedback-btn good" @click="submitFeedback(index, 5, 'helpful')">👍 有帮助</button>
            <button class="feedback-btn bad" @click="submitFeedback(index, 1, 'not_helpful')">👎 没帮助</button>
          </div>
          <div v-else-if="msg.role === 'assistant' && msg.feedbackSubmitted && msg.feedbackType === 'helpful'" class="feedback-submitted good">
            ✓ 感谢您的认可！
          </div>
          <div v-else-if="msg.role === 'assistant' && msg.feedbackSubmitted && msg.feedbackType === 'not_helpful'" class="feedback-submitted bad">
            ⚠️ 抱歉回答不理想，已记录将改进
          </div>
        </div>
        <div v-if="isLoading" class="message assistant">
          <div class="message-content">正在思考...</div>
        </div>
      </div>
      <div class="chat-input">
        <input 
          v-model="inputMessage" 
          type="text" 
          placeholder="请输入您的问题..."
          @keyup.enter="sendMessage"
        />
        <button @click="sendMessage">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';
import { marked } from 'marked';
import { useChatStore } from '../stores/chatStore';

const { 
  state, 
  getSessions, 
  getCurrentSessionId, 
  setCurrentSessionId,
  getMessages, 
  addMessage, 
  clearMessages,
  addSession,
  removeSession,
  initSessions
} = useChatStore();

const sessions = computed(() => state.sessions);
const currentSessionId = computed(() => state.currentSessionId);

const currentMessages = computed(() => {
  if (!currentSessionId.value) return [];
  return getMessages(currentSessionId.value);
});

const inputMessage = ref('');
const isLoading = ref(false);
const feedbackTargets = ref({});
const editingSessionId = ref(null);
const editTitle = ref('');
const titleInput = ref(null);

const startEditTitle = (sessionId, currentTitle) => {
  editingSessionId.value = sessionId;
  editTitle.value = currentTitle || '';
  setTimeout(() => {
    if (titleInput.value) {
      titleInput.value.focus();
    }
  }, 50);
};

const saveTitle = (sessionId) => {
  if (editingSessionId.value === sessionId) {
    const session = sessions.value.find(s => s.id === sessionId);
    if (session) {
      session.title = editTitle.value || '新对话';
    }
    editingSessionId.value = null;
    editTitle.value = '';
  }
};

const cancelEditTitle = () => {
  editingSessionId.value = null;
  editTitle.value = '';
};

const renderMarkdown = (text) => {
  return marked(text);
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const createNewSession = async () => {
  try {
    const response = await axios.post('http://localhost:8000/api/chat/session');
    const newSession = {
      id: response.data.session_id,
      title: '新对话',
      created_at: Date.now() / 1000,
      updated_at: Date.now() / 1000
    };
    addSession(newSession);
    setCurrentSessionId(newSession.id);
    clearMessages(newSession.id);
    addMessage(newSession.id, {
      role: 'assistant',
      content: '你好！我是有招小助手，有什么可以帮您的吗？',
      sources: [],
      metrics: null,
      task_type: null
    });
  } catch (error) {
    console.error('Error creating session:', error);
  }
};

const switchSession = (sessionId) => {
  setCurrentSessionId(sessionId);
};

const deleteSession = async (sessionId) => {
  try {
    await axios.delete(`http://localhost:8000/api/chat/session/${sessionId}`);
    removeSession(sessionId);
    if (sessions.value.length === 0) {
      createNewSession();
    }
  } catch (error) {
    console.error('Error deleting session:', error);
  }
};

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return;
  
  if (!currentSessionId.value) {
    await createNewSession();
  }
  
  addMessage(currentSessionId.value, {
    role: 'user',
    content: inputMessage.value
  });
  
  const userInput = inputMessage.value;
  inputMessage.value = '';
  isLoading.value = true;
  
  try {
    const response = await axios.post('http://localhost:8000/api/chat', {
      message: userInput,
      session_id: currentSessionId.value
    });
    
    setCurrentSessionId(response.data.session_id);
    
    const msgData = {
      role: 'assistant',
      content: response.data.answer,
      sources: response.data.sources || [],
      metrics: response.data.metrics || null,
      task_type: response.data.task_type || null,
      question: userInput
    };
    addMessage(currentSessionId.value, msgData);
    
    const msgIndex = currentMessages.value.length - 1;
    feedbackTargets.value[msgIndex] = {
      session_id: currentSessionId.value,
      question: userInput,
      answer: response.data.answer
    };
    
    const titleSession = sessions.value.find(s => s.id === currentSessionId.value);
    if (titleSession && !titleSession.title) {
      titleSession.title = userInput.slice(0, 20) + (userInput.length > 20 ? '...' : '');
    }
  } catch (error) {
    console.error('Error sending message:', error);
    let errorMessage = '抱歉，系统暂时无法响应，请稍后再试。';
    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail;
    }
    addMessage(currentSessionId.value, {
      role: 'assistant',
      content: errorMessage,
      sources: [],
      metrics: null,
      task_type: null
    });
  } finally {
    isLoading.value = false;
  }
};

const submitFeedback = async (msgIndex, rating, feedbackType) => {
  const target = feedbackTargets.value[msgIndex];
  if (!target) return;
  
  try {
    await axios.post('http://localhost:8000/api/feedback', {
      session_id: target.session_id,
      question: target.question,
      answer: target.answer,
      rating: rating,
      feedback_type: feedbackType
    });
    
    const msgs = currentMessages.value;
    if (msgs[msgIndex]) {
      msgs[msgIndex].feedbackSubmitted = true;
      msgs[msgIndex].feedbackType = feedbackType;
    }
  } catch (error) {
    console.error('Error submitting feedback:', error);
  }
};

const loadSessions = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/chat/sessions');
    if (response.data.sessions && response.data.sessions.length > 0) {
      const serverSessions = response.data.sessions;
      const localSessions = sessions.value;
      
      const mergedSessions = serverSessions.map(s => {
        const local = localSessions.find(ls => ls.id === s.id);
        return local ? { ...s, title: local.title } : s;
      });
      
      initSessions(mergedSessions);
      
      const msgs = getMessages(currentSessionId.value);
      if (msgs.length === 0 && currentSessionId.value) {
        const historyRes = await axios.get(`http://localhost:8000/api/chat/history/${currentSessionId.value}`);
        if (historyRes.data.history) {
          historyRes.data.history.forEach(msg => {
            addMessage(currentSessionId.value, msg);
          });
        }
      }
    } else if (sessions.value.length === 0) {
      await createNewSession();
    }
  } catch (error) {
    console.error('Error loading sessions:', error);
    if (sessions.value.length === 0) {
      await createNewSession();
    }
  }
};

onMounted(() => {
  loadSessions();
});
</script>

<style scoped>
.chat-container {
  width: 100%;
  height: 100%;
  display: flex;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.chat-sidebar {
  width: 220px;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.sidebar-header {
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-header span {
  font-weight: bold;
  font-size: 14px;
}

.new-chat-btn {
  padding: 4px 10px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.new-chat-btn:hover {
  background: #40a9ff;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.session-item:hover {
  background: #e6f7ff;
}

.session-item.active {
  background: #bae7ff;
}

.session-info {
  flex: 1;
  overflow: hidden;
}

.session-title {
  display: block;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 11px;
  color: #999;
}

.session-edit {
  flex: 1;
}

.title-input {
  width: 100%;
  padding: 2px 4px;
  font-size: 13px;
  border: 1px solid #1890ff;
  border-radius: 2px;
}

.delete-btn {
  background: none;
  border: none;
  color: #999;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}

.delete-btn:hover {
  color: #ff4d4f;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background-color: #f5f5f5;
}

.message {
  margin-bottom: 16px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  margin-left: auto;
}

.message.assistant {
  align-self: flex-start;
}

.message-content {
  padding: 12px 16px;
  border-radius: 8px;
  word-wrap: break-word;
}

.message.user .message-content {
  background-color: #e6f7ff;
  border-bottom-right-radius: 0;
}

.message.assistant .message-content {
  background-color: white;
  border-bottom-left-radius: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.task-type {
  margin-top: 8px;
  padding: 6px 12px;
  background-color: #fff7e6;
  border-radius: 4px;
  font-size: 12px;
}

.task-label {
  color: #fa8c16;
  font-weight: bold;
  margin-right: 6px;
}

.task-value {
  color: #d46b08;
}

.metrics-panel {
  margin-top: 10px;
  padding: 12px;
  background-color: #f0f5ff;
  border-radius: 8px;
  border: 1px solid #adc6ff;
}

.metrics-header {
  margin-bottom: 10px;
}

.metrics-title {
  font-size: 13px;
  font-weight: bold;
  color: #1890ff;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  background-color: white;
  border-radius: 4px;
  font-size: 12px;
}

.metric-item.good {
  background-color: #f6ffed;
  border: 1px solid #b7eb8f;
}

.metric-item.good .metric-value {
  color: #52c41a;
}

.metric-name {
  color: #666;
}

.metric-value {
  font-weight: bold;
  color: #faad14;
}

.sources {
  margin-top: 10px;
  padding: 10px 12px;
  background-color: #f8f8f8;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.sources-title {
  font-weight: bold;
  margin-bottom: 6px;
  color: #333;
}

.sources ul {
  margin: 0;
  padding-left: 20px;
}

.sources li {
  margin: 4px 0;
  word-wrap: break-word;
}

.source-content {
  font-size: 12px;
  color: #666;
}

.source-meta {
  margin-top: 4px;
  font-size: 11px;
  color: #999;
}

.source-meta span {
  margin-right: 12px;
}

.feedback-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.feedback-label {
  font-size: 12px;
  color: #999;
  margin-right: 8px;
}

.feedback-btn {
  padding: 4px 12px;
  margin-right: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 12px;
  color: #333;
}

.feedback-btn.good:hover {
  background: #52c41a;
  color: white;
  border-color: #52c41a;
}

.feedback-btn.bad:hover {
  background: #ff4d4f;
  color: white;
  border-color: #ff4d4f;
}

.feedback-submitted {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
}

.feedback-submitted.good {
  color: #52c41a;
}

.feedback-submitted.bad {
  color: #faad14;
}

.chat-input {
  display: flex;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  background-color: white;
}

.chat-input input {
  flex: 1;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  margin-right: 8px;
  font-size: 14px;
}

.chat-input button {
  padding: 0 24px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.chat-input button:hover {
  background-color: #40a9ff;
}

.chat-input button:active {
  background-color: #096dd9;
}
</style>
