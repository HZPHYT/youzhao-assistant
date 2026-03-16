<template>
  <div class="app-container">
    <nav class="navigation">
      <h1>有招小助手</h1>
      <div class="nav-buttons">
        <button @click="currentPage = 'chat'" :class="{ active: currentPage === 'chat' }">
          智能对话
        </button>
        <button @click="currentPage = 'upload'" :class="{ active: currentPage === 'upload' }">
          知识管理
        </button>
        <button @click="currentPage = 'evaluation'" :class="{ active: currentPage === 'evaluation' }">
          RAG评测
        </button>
        <button @click="currentPage = 'monitoring'" :class="{ active: currentPage === 'monitoring' }">
          系统监控
        </button>
      </div>
    </nav>

    <div class="page-content">
      <ChatInterface v-if="currentPage === 'chat'" />
      <KnowledgeUpload v-if="currentPage === 'upload'" />
      <RagEvaluation v-if="currentPage === 'evaluation'" />
      <Monitoring v-if="currentPage === 'monitoring'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import ChatInterface from './components/ChatInterface.vue';
import KnowledgeUpload from './components/KnowledgeUpload.vue';
import RagEvaluation from './components/RagEvaluation.vue';
import Monitoring from './components/Monitoring.vue';

const currentPage = ref('chat');
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: Arial, sans-serif;
  line-height: 1.6;
  color: #333;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navigation {
  background-color: #1890ff;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navigation h1 {
  font-size: 1.5rem;
}

.nav-buttons {
  display: flex;
  gap: 1rem;
}

.nav-buttons button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
  cursor: pointer;
  transition: background-color 0.3s;
}

.nav-buttons button:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

.nav-buttons button.active {
  background-color: white;
  color: #1890ff;
  font-weight: bold;
}

.page-content {
  flex: 1;
  padding: 2rem;
  background-color: #f5f5f5;
}

@media (max-width: 768px) {
  .navigation {
    flex-direction: column;
    gap: 1rem;
  }

  .nav-buttons {
    flex-wrap: wrap;
    justify-content: center;
  }

  .page-content {
    padding: 1rem;
  }
}
</style>