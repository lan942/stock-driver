<template>
  <div class="data-summary">
    <div class="search-bar">
      <div class="date-range">
        <span class="date-label">日期范围：</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          clearable
          @change="onDateRangeChange"
          size="default"
        />
      </div>
      <el-button type="primary" @click="loadSummary">查询</el-button>
      <el-button @click="resetDateRange">重置</el-button>
    </div>

    <div class="summary-stats">
      <el-card class="stat-card">
        <div class="stat-label">查询日期范围</div>
        <div class="stat-value">{{ dateRangeText }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-label">数据日期数量</div>
        <div class="stat-value">{{ summaryData.length }} 天</div>
      </el-card>
    </div>

    <el-table :data="summaryData" border style="width: 100%" :default-sort="{ prop: 'date', order: 'descending' }">
      <el-table-column prop="date" label="日期" width="140" sortable />
      <el-table-column prop="count" label="数据条数" width="120" sortable>
        <template #default="{ row }">
          <span :class="{ 'low-count': row.count < row.total_stocks * 0.9 }">
            {{ row.count.toLocaleString() }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="total_stocks" label="总股票数" width="120">
        <template #default="{ row }">
          {{ row.total_stocks.toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="coverage_percent" label="覆盖率" width="200" sortable>
        <template #default="{ row }">
          <div class="coverage-cell">
            <el-progress
              :percentage="row.coverage_percent"
              :color="getCoverageColor(row.coverage_percent)"
              :stroke-width="12"
              :show-text="false"
            />
            <span class="coverage-text" :style="{ color: getCoverageColor(row.coverage_percent) }">
              {{ row.coverage_percent.toFixed(2) }}%
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="goToStockList(row.date)">查看当日数据</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { stockAPI } from '../api/stock'
import { useRouter } from 'vue-router'

const router = useRouter()
const summaryData = ref([])
const dateRange = ref([])

const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const dateRangeText = computed(() => {
  if (!dateRange.value || dateRange.value.length === 0) {
    return '最近90天'
  }
  return `${dateRange.value[0]} 至 ${dateRange.value[1]}`
})

const getCoverageColor = (percent) => {
  if (percent >= 95) return '#22c55e'
  if (percent >= 80) return '#eab308'
  return '#ef4444'
}

const loadSummary = async () => {
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const response = await stockAPI.getDailySummary(params)
    summaryData.value = response.data
  } catch (error) {
    console.error('加载每日数据摘要失败:', error)
  }
}

const onDateRangeChange = () => {
  loadSummary()
}

const resetDateRange = () => {
  dateRange.value = []
  loadSummary()
}

const goToStockList = (date) => {
  router.push({ path: '/', query: { date } })
}

onMounted(async () => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 90)
  dateRange.value = [formatDate(startDate), formatDate(endDate)]
  await loadSummary()
})
</script>

<style scoped>
.data-summary {
  padding: 0 20px;
}

.search-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.summary-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.low-count {
  color: #ef4444;
  font-weight: 600;
}

.coverage-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coverage-text {
  font-size: 14px;
  font-weight: 600;
  min-width: 60px;
  text-align: right;
}
</style>