<template>
  <div class="crawler">
    <h2>数据爬取管理</h2>
    
    <el-card class="crawler-card">
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>更新股票列表</h3>
          <p>从网络获取最新的A股股票代码和名称列表</p>
        </div>
        <el-button type="primary" :loading="loading.list" @click="updateStockList">
          更新列表
        </el-button>
      </div>
      
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>更新实时行情</h3>
          <p>获取所有股票的最新价格、涨跌幅等实时数据</p>
        </div>
        <el-button type="primary" :loading="loading.realtime" @click="updateRealtime">
          更新实时行情
        </el-button>
      </div>
      
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>获取个股历史数据</h3>
          <p>获取指定股票的日线历史数据</p>
        </div>
        <div class="fetch-daily">
          <el-input v-model="dailyCode" placeholder="输入股票代码" class="daily-input" />
          <el-button type="primary" :loading="loading.daily" @click="fetchDaily">
            获取数据
          </el-button>
        </div>
      </div>
    </el-card>
    
    <el-card class="log-card">
      <h3>操作日志</h3>
      <div class="log-list">
        <div v-for="(log, index) in logs" :key="index" class="log-item">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="empty-log">
          暂无操作记录
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { stockAPI } from '../api/stock'

const loading = reactive({
  list: false,
  realtime: false,
  daily: false
})

const dailyCode = ref('')
const logs = ref([])

const addLog = (message) => {
  const time = new Date().toLocaleString('zh-CN')
  logs.value.unshift({ time, message })
  if (logs.value.length > 50) {
    logs.value.pop()
  }
}

const updateStockList = async () => {
  loading.list = true
  try {
    const response = await stockAPI.updateStockList()
    addLog(response.data.message)
  } catch (error) {
    addLog(`更新股票列表失败: ${error.message}`)
  } finally {
    loading.list = false
  }
}

const updateRealtime = async () => {
  loading.realtime = true
  try {
    const response = await stockAPI.updateRealtime()
    addLog(response.data.message)
  } catch (error) {
    addLog(`更新实时行情失败: ${error.message}`)
  } finally {
    loading.realtime = false
  }
}

const fetchDaily = async () => {
  if (!dailyCode.value) {
    addLog('请输入股票代码')
    return
  }
  
  loading.daily = true
  try {
    const response = await stockAPI.fetchDaily(dailyCode.value)
    addLog(response.data.message)
    dailyCode.value = ''
  } catch (error) {
    addLog(`获取历史数据失败: ${error.message}`)
  } finally {
    loading.daily = false
  }
}
</script>

<style scoped>
.crawler {
  max-width: 800px;
  margin: 0 auto;
}

.crawler h2 {
  margin-bottom: 24px;
}

.crawler-card {
  margin-bottom: 24px;
}

.crawler-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.crawler-item:last-child {
  border-bottom: none;
}

.crawler-info h3 {
  margin-bottom: 4px;
  font-size: 16px;
}

.crawler-info p {
  color: #999;
  font-size: 12px;
}

.fetch-daily {
  display: flex;
  gap: 12px;
}

.daily-input {
  width: 150px;
}

.log-card {
  max-height: 400px;
}

.log-card h3 {
  margin-bottom: 16px;
  font-size: 16px;
}

.log-list {
  max-height: 300px;
  overflow-y: auto;
}

.log-item {
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  display: flex;
  gap: 16px;
}

.log-time {
  color: #999;
  font-size: 12px;
  min-width: 140px;
}

.log-message {
  font-size: 14px;
}

.empty-log {
  text-align: center;
  color: #999;
  padding: 40px;
}
</style>
