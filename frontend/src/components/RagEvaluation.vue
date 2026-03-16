<template>
  <div class="rag-evaluation-container">
    <h2>RAG 评测</h2>
    
    <div class="evaluation-section">
      <h3>评测配置</h3>
      <div class="config-item">
        <label>评测问题数量:</label>
        <input type="number" v-model.number="config.questionCount" min="1" max="10" />
      </div>
      <div class="config-item">
        <label>评测类型:</label>
        <select v-model="config.evaluationType">
          <option value="全部">全部</option>
          <option value="贷前KYC">贷前KYC</option>
          <option value="贷中营销">贷中营销</option>
          <option value="贷后跟进">贷后跟进</option>
          <option value="CORS跨域">CORS跨域</option>
        </select>
      </div>
      <button @click="startEvaluation" class="start-btn" :disabled="isLoading">
        {{ isLoading ? '评测中...' : '开始评测' }}
      </button>
    </div>

    <div class="evaluation-results" v-if="evaluationResults">
      <h3>评测结果</h3>
      
      <div class="score-overview">
        <div class="score-circle">
          <span class="score-value">{{ (evaluationResults.overallScore * 100).toFixed(1) }}</span>
          <span class="score-unit">%</span>
        </div>
        <div class="score-info">
          <div class="result-item">
            <span class="result-label">评测类型:</span>
            <span class="result-value">{{ evaluationResults.evaluationType }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">评测问题数:</span>
            <span class="result-value">{{ evaluationResults.questionCount }}</span>
          </div>
        </div>
      </div>

      <h4>评测指标</h4>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-name">Faithfulness</div>
          <div class="metric-desc">忠诚度</div>
          <div class="metric-value">{{ (evaluationResults.metrics.faithfulness * 100).toFixed(1) }}%</div>
        </div>
        <div class="metric-card">
          <div class="metric-name">Answer Relevancy</div>
          <div class="metric-desc">答案相关性</div>
          <div class="metric-value">{{ (evaluationResults.metrics.answer_relevancy * 100).toFixed(1) }}%</div>
        </div>
        <div class="metric-card">
          <div class="metric-name">Context Precision</div>
          <div class="metric-desc">上下文精确度</div>
          <div class="metric-value">{{ (evaluationResults.metrics.context_precision * 100).toFixed(1) }}%</div>
        </div>
        <div class="metric-card">
          <div class="metric-name">Context Recall</div>
          <div class="metric-desc">上下文召回率</div>
          <div class="metric-value">{{ (evaluationResults.metrics.context_recall * 100).toFixed(1) }}%</div>
        </div>
        <div class="metric-card">
          <div class="metric-name">Retrieval Recall</div>
          <div class="metric-desc">检索召回率</div>
          <div class="metric-value">{{ (evaluationResults.metrics.retrieval_recall * 100).toFixed(1) }}%</div>
        </div>
      </div>
      
      <h4>详细评测</h4>
      <div class="detailed-results">
        <div v-for="(result, index) in evaluationResults.details" :key="index" class="result-card">
          <div class="question">
            <span class="q-label">问题:</span>
            {{ result.question }}
          </div>
          <div class="answer">
            <span class="q-label">回答:</span>
            {{ result.answer }}
          </div>
          <div class="result-metrics">
            <span class="metric-tag">F: {{ (result.metrics.faithfulness * 100).toFixed(0) }}%</span>
            <span class="metric-tag">AR: {{ (result.metrics.answer_relevancy * 100).toFixed(0) }}%</span>
            <span class="metric-tag">CP: {{ (result.metrics.context_precision * 100).toFixed(0) }}%</span>
            <span class="metric-tag">CR: {{ (result.metrics.context_recall * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <div class="status-message" v-if="statusMessage" :class="{ error: isError }">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const config = ref({
  questionCount: 3,
  evaluationType: 'CORS跨域'
});

const evaluationResults = ref(null);
const statusMessage = ref('');
const isLoading = ref(false);
const isError = ref(false);

const startEvaluation = async () => {
  isLoading.value = true;
  statusMessage.value = '正在进行RAG评测，请稍候...';
  isError.value = false;
  evaluationResults.value = null;
  
  try {
    const response = await axios.post('http://localhost:8000/api/rag/evaluate', config.value);
    evaluationResults.value = response.data;
    statusMessage.value = '评测完成！';
  } catch (error) {
    statusMessage.value = '评测失败: ' + error.message;
    isError.value = true;
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.rag-evaluation-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  color: #333;
  margin-bottom: 20px;
}

h3, h4 {
  color: #555;
  margin: 15px 0;
}

.evaluation-section {
  margin-bottom: 30px;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
}

.config-item {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.config-item label {
  display: inline-block;
  width: 120px;
  font-weight: bold;
}

.config-item input,
.config-item select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 200px;
  font-size: 14px;
}

.start-btn {
  margin-top: 20px;
  padding: 12px 30px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.start-btn:hover:not(:disabled) {
  background-color: #1976d2;
}

.start-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.evaluation-results {
  padding: 20px;
  background-color: white;
  border-radius: 8px;
}

.score-overview {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.score-circle {
  display: flex;
  align-items: baseline;
  margin-right: 30px;
}

.score-value {
  font-size: 48px;
  font-weight: bold;
}

.score-unit {
  font-size: 20px;
  margin-left: 4px;
}

.score-info {
  flex: 1;
}

.result-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 8px 12px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.result-label {
  font-weight: bold;
}

.result-value {
  font-size: 16px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.metric-card {
  padding: 15px 10px;
  background-color: #f8f9fa;
  border-radius: 8px;
  text-align: center;
  border: 1px solid #e9ecef;
}

.metric-name {
  font-size: 12px;
  font-weight: bold;
  color: #2196f3;
}

.metric-desc {
  font-size: 11px;
  color: #666;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.detailed-results {
  margin-top: 20px;
}

.result-card {
  padding: 15px;
  background-color: #f0f8ff;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 4px solid #2196f3;
}

.question {
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
}

.q-label {
  color: #2196f3;
  margin-right: 8px;
}

.answer {
  margin-bottom: 10px;
  line-height: 1.5;
  color: #555;
  padding: 10px;
  background-color: white;
  border-radius: 4px;
}

.result-metrics {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.metric-tag {
  padding: 4px 10px;
  background-color: #e3f2fd;
  border-radius: 12px;
  font-size: 12px;
  color: #1976d2;
}

.status-message {
  margin-top: 20px;
  padding: 12px;
  background-color: #e3f2fd;
  border-left: 4px solid #2196f3;
  border-radius: 4px;
  color: #1976d2;
}

.status-message.error {
  background-color: #ffebee;
  border-left-color: #f44336;
  color: #c62828;
}

@media (max-width: 600px) {
  .rag-evaluation-container {
    padding: 10px;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .score-overview {
    flex-direction: column;
    text-align: center;
  }

  .config-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .config-item label {
    width: 100%;
    margin-bottom: 5px;
  }

  .config-item input,
  .config-item select {
    width: 100%;
  }
}
</style>
