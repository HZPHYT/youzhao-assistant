<template>
  <div class="knowledge-upload-container">
    <h2>知识管理</h2>
    
    <div class="upload-section">
      <h3>上传知识文档</h3>
      <input type="file" ref="fileInput" @change="handleFileChange" accept=".txt,.md,.docx,.pdf" />
      <button @click="uploadKnowledge" :disabled="!selectedFile" class="upload-btn">
        上传到知识库
      </button>
      <div v-if="selectedFile" class="file-info">
        已选择文件: {{ selectedFile.name }}
      </div>
      <button @click="clearKnowledge" class="clear-btn">
        清空知识库
      </button>
    </div>

    <div class="knowledge-list" v-if="knowledgeList.length > 0">
      <h3>知识库内容</h3>
      <ul>
        <li v-for="(item, index) in knowledgeList" :key="index">
          {{ item.content.substring(0, 100) }}{{ item.content.length > 100 ? '...' : '' }}
          <button @click="deleteKnowledge(index)" class="delete-btn">删除</button>
        </li>
      </ul>
    </div>

    <div class="status-message" v-if="statusMessage">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const selectedFile = ref(null);
const knowledgeList = ref([]);
const statusMessage = ref('');
const fileInput = ref(null);

const handleFileChange = (event) => {
  selectedFile.value = event.target.files[0];
};

const uploadKnowledge = async () => {
  if (!selectedFile.value) return;

  statusMessage.value = '正在上传...';
  
  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    
    const response = await axios.post('/api/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    statusMessage.value = response.data.message;
    selectedFile.value = null;
    fileInput.value.value = '';
    fetchKnowledgeList();
  } catch (error) {
    statusMessage.value = '上传失败: ' + error.message;
  }
};

const fetchKnowledgeList = async () => {
  try {
    const response = await axios.get('/api/knowledge/list');
    knowledgeList.value = response.data;
  } catch (error) {
    console.error('获取知识库列表失败:', error);
  }
};

const deleteKnowledge = async (index) => {
  const knowledge = knowledgeList.value[index];
  try {
    await axios.delete(`/api/knowledge/delete`, {
      data: { id: knowledge.id }
    });
    knowledgeList.value.splice(index, 1);
    statusMessage.value = '删除成功';
  } catch (error) {
    statusMessage.value = '删除失败: ' + error.message;
  }
};

const clearKnowledge = async () => {
  if (!confirm('确定要清空所有知识库内容吗？此操作不可恢复！')) return;
  
  try {
    await axios.post('/api/knowledge/clear');
    knowledgeList.value = [];
    statusMessage.value = '知识库已清空';
  } catch (error) {
    statusMessage.value = '清空失败: ' + error.message;
  }
};

onMounted(() => {
  fetchKnowledgeList();
});
</script>

<style scoped>
.knowledge-upload-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.upload-section {
  margin-bottom: 30px;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
}

.upload-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.upload-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.clear-btn {
  margin-top: 10px;
  margin-left: 10px;
  padding: 8px 16px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.file-info {
  margin-top: 10px;
  font-size: 14px;
  color: #666;
}

.knowledge-list {
  padding: 20px;
  background-color: white;
  border-radius: 8px;
}

.knowledge-list ul {
  list-style-type: none;
  padding: 0;
}

.knowledge-list li {
  padding: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.delete-btn {
  padding: 4px 8px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.status-message {
  margin-top: 20px;
  padding: 10px;
  background-color: #e3f2fd;
  border-left: 4px solid #2196f3;
  border-radius: 4px;
  color: #1976d2;
}

@media (max-width: 600px) {
  .knowledge-upload-container {
    padding: 10px;
  }

  .upload-section,
  .knowledge-list {
    padding: 15px;
  }
}
</style>