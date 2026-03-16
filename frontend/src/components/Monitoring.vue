<template>
  <div class="monitoring-page">
    <div class="monitoring-header">
      <h2>系统监控</h2>
      <button @click="refreshData" class="refresh-btn">刷新</button>
    </div>

    <div class="metrics-cards">
      <div class="metric-card">
        <div class="metric-label">总请求数</div>
        <div class="metric-value">{{ totalRequests }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">总错误数</div>
        <div class="metric-value error">{{ totalErrors }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">错误率</div>
        <div class="metric-value" :class="{ error: errorRate > 0.05 }">{{ (errorRate * 100).toFixed(2) }}%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">平均响应时间</div>
        <div class="metric-value">{{ avgLatency }}ms</div>
      </div>
    </div>

    <div class="api-table">
      <h3>接口详情</h3>
      <table>
        <thead>
          <tr>
            <th>接口</th>
            <th>请求数</th>
            <th>错误数</th>
            <th>错误率</th>
            <th>平均延迟</th>
            <th>P95延迟</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(data, path) in metrics" :key="path">
            <td>{{ path }}</td>
            <td>{{ data.requests }}</td>
            <td :class="{ error: data.errors > 0 }">{{ data.errors }}</td>
            <td :class="{ error: data.error_rate > 0.05 }">{{ (data.error_rate * 100).toFixed(2) }}%</td>
            <td>{{ data.avg_latency_ms }}ms</td>
            <td>{{ data.p95_latency_ms }}ms</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

const metrics = ref({});

const fetchMetrics = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/metrics');
    metrics.value = response.data;
  } catch (error) {
    console.error('Failed to fetch metrics:', error);
  }
};

const refreshData = () => {
  fetchMetrics();
};

const totalRequests = computed(() => {
  return Object.values(metrics.value).reduce((sum, m) => sum + m.requests, 0);
});

const totalErrors = computed(() => {
  return Object.values(metrics.value).reduce((sum, m) => sum + m.errors, 0);
});

const errorRate = computed(() => {
  if (totalRequests.value === 0) return 0;
  return totalErrors.value / totalRequests.value;
});

const avgLatency = computed(() => {
  const values = Object.values(metrics.value).filter(m => m.requests > 0);
  if (values.length === 0) return 0;
  const sum = values.reduce((s, m) => s + m.avg_latency_ms, 0);
  return (sum / values.length).toFixed(2);
});

onMounted(() => {
  fetchMetrics();
  setInterval(fetchMetrics, 5000);
});
</script>

<style scoped>
.monitoring-page {
  max-width: 1200px;
  margin: 0 auto;
}

.monitoring-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.monitoring-header h2 {
  font-size: 1.5rem;
  color: #333;
}

.refresh-btn {
  padding: 0.5rem 1rem;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.refresh-btn:hover {
  background-color: #40a9ff;
}

.metrics-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.metric-label {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 2rem;
  font-weight: bold;
  color: #1890ff;
}

.metric-value.error {
  color: #ff4d4f;
}

.api-table {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.api-table h3 {
  margin-bottom: 1rem;
  color: #333;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

th {
  background-color: #fafafa;
  font-weight: 600;
  color: #333;
}

td {
  color: #666;
}

td.error {
  color: #ff4d4f;
}

tr:hover {
  background-color: #fafafa;
}

@media (max-width: 768px) {
  .metrics-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
