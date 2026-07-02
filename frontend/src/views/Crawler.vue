<template>
  <div class="crawler">
    <h2>数据爬取管理</h2>

    <el-card class="crawler-card">
      <!-- 更新股票列表 -->
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>更新股票列表</h3>
          <p>从网络获取最新的A股股票代码和名称列表</p>
        </div>
        <el-button type="primary" :loading="loading.list" @click="updateStockList">
          {{ loading.list ? '更新中...' : '更新列表' }}
        </el-button>
      </div>
      <el-progress v-if="loading.list || listProgress > 0" :percentage="listProgress" :status="listProgress === 100 && !loading.list ? 'success' : ''" style="margin: 0 0 12px" />
      <div v-if="listResult" class="result-bar">
        <el-tag :type="listResult.fail_count === 0 ? 'success' : 'warning'" size="small">
          {{ listResult.message }}
        </el-tag>
        <span class="result-detail">
          成功 {{ listResult.success_count }} 只
          <template v-if="listResult.fail_count > 0">，失败 {{ listResult.fail_count }} 只</template>
          ，耗时 {{ listResult.elapsed }}秒
        </span>
      </div>

      <!-- 更新实时行情 -->
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>更新实时行情</h3>
          <p>获取所有股票的最新价格、涨跌幅等实时数据（快照接口）</p>
        </div>
        <el-button type="primary" :loading="loading.realtime" @click="updateRealtime">
          {{ loading.realtime ? '更新中...' : '更新实时行情' }}
        </el-button>
      </div>

      <div class="realtime-options">
        <el-checkbox v-model="forceRefresh" :disabled="loading.realtime">
          强制刷新（跳过当日成功记录检查）
        </el-checkbox>
        <div class="date-picker-wrap">
          <span class="date-label">数据日期：</span>
          <el-date-picker
            v-model="quoteDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled="loading.realtime"
            size="small"
          />
          <span class="date-hint">东方财富返回快照数据，非交易时间请选择最近交易日</span>
        </div>
      </div>

      <el-progress v-if="loading.realtime || realtimeProgress > 0" :percentage="realtimeProgress" :status="realtimeProgress === 100 && !loading.realtime ? 'success' : ''" style="margin: 0 0 12px" />
      <div v-if="realtimeResult" class="result-bar">
        <el-tag :type="realtimeResult.skipped ? 'info' : (realtimeResult.fail_count === 0 ? 'success' : 'warning')" size="small">
          {{ realtimeResult.message }}
        </el-tag>
        <span v-if="!realtimeResult.skipped" class="result-detail">
          成功 {{ realtimeResult.success_count }} 只
          <template v-if="realtimeResult.fail_count > 0">，失败 {{ realtimeResult.fail_count }} 只</template>
          ，耗时 {{ realtimeResult.elapsed }}秒
          <template v-if="realtimeResult.price_date">，数据日期 {{ realtimeResult.price_date }}</template>
        </span>
      </div>

      <!-- 个股历史数据 -->
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>获取个股历史数据</h3>
          <p>获取指定股票的日线历史数据（腾讯数据源）</p>
        </div>
        <div class="fetch-daily">
          <el-input v-model="dailyCode" placeholder="输入股票代码" class="daily-input" />
          <el-button type="primary" :loading="loading.daily" @click="fetchDaily">
            获取数据
          </el-button>
        </div>
      </div>

      <!-- 批量日线数据 -->
      <div class="crawler-item">
        <div class="crawler-info">
          <h3>批量获取日线数据</h3>
          <p>批量获取所有股票的日线历史数据（腾讯数据源）</p>
        </div>
        <el-button type="success" :loading="loading.dailyBatch" :disabled="dailyBatchProgress.running" @click="fetchDailyBatch">
          {{ loading.dailyBatch || dailyBatchProgress.running ? '爬取中...' : '批量爬取' }}
        </el-button>
      </div>

      <div class="batch-options">
        <div class="option-row">
          <span class="option-label">开始日期：</span>
          <el-date-picker
            v-model="batchStartDate"
            type="date"
            placeholder="开始日期"
            format="YYYY-MM-DD"
            value-format="YYYYMMDD"
            size="small"
            :disabled="dailyBatchProgress.running"
          />
        </div>
        <div class="option-row">
          <span class="option-label">结束日期：</span>
          <el-date-picker
            v-model="batchEndDate"
            type="date"
            placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYYMMDD"
            size="small"
            :disabled="dailyBatchProgress.running"
          />
        </div>
      </div>

      <div v-if="dailyBatchProgress.running || dailyBatchProgress.total > 0" class="batch-progress">
        <div class="progress-header">
          <span class="progress-text">
            进度：{{ dailyBatchProgress.current }} / {{ dailyBatchProgress.total }}
            <span v-if="dailyBatchProgress.current_code">（当前：{{ dailyBatchProgress.current_code }}）</span>
          </span>
          <span class="progress-percent">
            {{ dailyBatchProgress.total > 0 ? Math.round(dailyBatchProgress.current / dailyBatchProgress.total * 100) : 0 }}%
          </span>
        </div>
        <el-progress
          :percentage="dailyBatchProgress.total > 0 ? Math.round(dailyBatchProgress.current / dailyBatchProgress.total * 100) : 0"
          :status="!dailyBatchProgress.running && dailyBatchProgress.total > 0 && dailyBatchProgress.failed === 0 ? 'success' : ''"
        />
        <div class="batch-stats">
          <span>成功：{{ dailyBatchProgress.success }} 只</span>
          <span>失败：{{ dailyBatchProgress.failed }} 只</span>
          <span v-if="dailyBatchProgress.added !== undefined">新增：{{ dailyBatchProgress.added }} 条</span>
          <span v-if="dailyBatchProgress.updated !== undefined">更新：{{ dailyBatchProgress.updated }} 条</span>
        </div>
        <div v-if="dailyBatchProgress.error" class="batch-error">
          错误：{{ dailyBatchProgress.error }}
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
import { ref, reactive, onUnmounted, onMounted } from 'vue'
import { stockAPI } from '../api/stock'

const loading = reactive({
  list: false,
  realtime: false,
  daily: false,
  dailyBatch: false
})

const listProgress = ref(0)
const realtimeProgress = ref(0)
let listTimer = null
let realtimeTimer = null
let dailyBatchTimer = null

const dailyBatchProgress = reactive({
  running: false,
  current: 0,
  total: 0,
  current_code: '',
  success: 0,
  failed: 0,
  added: 0,
  updated: 0,
  start_time: null,
  error: null
})

const batchStartDate = ref('20250101')
const batchEndDate = ref(new Date().toISOString().slice(0, 10).replace(/-/g, ''))

const startListProgress = () => {
  if (listTimer) clearInterval(listTimer)
  listProgress.value = 0
  listTimer = setInterval(() => {
    if (listProgress.value < 90) {
      listProgress.value = Math.min(listProgress.value + 3, 90)
    }
  }, 1000)
}

const finishListProgress = () => {
  if (listTimer) {
    clearInterval(listTimer)
    listTimer = null
  }
  listProgress.value = 100
  setTimeout(() => {
    listProgress.value = 0
  }, 2000)
}

const startRealtimeProgress = () => {
  if (realtimeTimer) clearInterval(realtimeTimer)
  realtimeProgress.value = 0
  realtimeTimer = setInterval(() => {
    if (realtimeProgress.value < 90) {
      realtimeProgress.value = Math.min(realtimeProgress.value + 2, 90)
    }
  }, 1000)
}

const finishRealtimeProgress = () => {
  if (realtimeTimer) {
    clearInterval(realtimeTimer)
    realtimeTimer = null
  }
  realtimeProgress.value = 100
  setTimeout(() => {
    realtimeProgress.value = 0
  }, 2000)
}

onUnmounted(() => {
  if (listTimer) clearInterval(listTimer)
  if (realtimeTimer) clearInterval(realtimeTimer)
  if (dailyBatchTimer) clearInterval(dailyBatchTimer)
})

const pollDailyProgress = async () => {
  try {
    const response = await stockAPI.getDailyProgress()
    const data = response.data
    dailyBatchProgress.running = data.running
    dailyBatchProgress.current = data.current
    dailyBatchProgress.total = data.total
    dailyBatchProgress.current_code = data.current_code
    dailyBatchProgress.success = data.success
    dailyBatchProgress.failed = data.failed
    dailyBatchProgress.added = data.added
    dailyBatchProgress.updated = data.updated
    dailyBatchProgress.start_time = data.start_time
    dailyBatchProgress.error = data.error

    if (!data.running && data.total > 0) {
      if (dailyBatchTimer) {
        clearInterval(dailyBatchTimer)
        dailyBatchTimer = null
      }
      addLog(`批量日线爬取完成：成功 ${data.success} 只，失败 ${data.failed} 只`)
    }
  } catch (e) {
    console.error('获取进度失败', e)
  }
}

onMounted(() => {
  pollDailyProgress()
})

const dailyCode = ref('')
const logs = ref([])

// 实时行情选项
const forceRefresh = ref(false)
const quoteDate = ref(new Date().toISOString().slice(0, 10))

// 结果展示
const listResult = ref(null)
const realtimeResult = ref(null)

const addLog = (message) => {
  const time = new Date().toLocaleString('zh-CN')
  logs.value.unshift({ time, message })
  if (logs.value.length > 50) {
    logs.value.pop()
  }
}

const updateStockList = async () => {
  loading.list = true
  listResult.value = null
  startListProgress()
  try {
    const response = await stockAPI.updateStockList()
    const data = response.data
    listResult.value = data
    addLog(data.message)
  } catch (error) {
    addLog(`更新股票列表失败: ${error.message}`)
    listResult.value = {
      message: `失败: ${error.message}`,
      success_count: 0,
      fail_count: 0,
      elapsed: 0
    }
  } finally {
    finishListProgress()
    loading.list = false
  }
}

const updateRealtime = async () => {
  loading.realtime = true
  realtimeResult.value = null
  startRealtimeProgress()
  try {
    const response = await stockAPI.updateRealtime({
      force: forceRefresh.value,
      date: quoteDate.value
    })
    const data = response.data
    realtimeResult.value = data
    addLog(data.message)
  } catch (error) {
    addLog(`更新实时行情失败: ${error.message}`)
    realtimeResult.value = {
      message: `失败: ${error.message}`,
      success_count: 0,
      fail_count: 0,
      elapsed: 0
    }
  } finally {
    finishRealtimeProgress()
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

const fetchDailyBatch = async () => {
  loading.dailyBatch = true
  try {
    const response = await stockAPI.fetchDailyBatch({
      start_date: batchStartDate.value,
      end_date: batchEndDate.value,
      adjust: 'qfq'
    })
    addLog(response.data.message)

    if (!dailyBatchTimer) {
      dailyBatchTimer = setInterval(pollDailyProgress, 2000)
    }
  } catch (error) {
    addLog(`批量爬取失败: ${error.message}`)
    loading.dailyBatch = false
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

.realtime-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 0 0 12px;
  border-bottom: 1px solid #f0f0f0;
}

.date-picker-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.date-label {
  font-size: 13px;
  color: #606266;
}

.date-hint {
  font-size: 11px;
  color: #999;
}

.result-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.result-detail {
  font-size: 13px;
  color: #606266;
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

.batch-options {
  display: flex;
  gap: 24px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.option-label {
  font-size: 13px;
  color: #606266;
}

.batch-progress {
  margin-top: 16px;
  padding: 14px 16px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 13px;
  color: #606266;
}

.progress-percent {
  font-size: 14px;
  font-weight: 500;
  color: #409eff;
}

.batch-stats {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.batch-error {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 12px;
}
</style>
