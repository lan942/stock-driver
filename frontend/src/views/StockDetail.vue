<template>
  <div class="stock-detail">
    <div v-if="stock" class="stock-info">
      <h2>{{ stock.name }} ({{ stock.code }})</h2>
      <div class="info-row">
        <div class="info-item">
          <span class="label">价格</span>
          <span class="value" :style="{ color: stock.change_percent >= 0 ? '#ef4444' : '#22c55e' }">
            {{ stock.price ? stock.price.toFixed(2) : '-' }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">涨跌幅</span>
          <span class="value" :style="{ color: stock.change_percent >= 0 ? '#ef4444' : '#22c55e' }">
            {{ stock.change_percent >= 0 ? '+' : '' }}{{ stock.change_percent ? stock.change_percent.toFixed(2) : '-' }}%
          </span>
        </div>
        <div class="info-item">
          <span class="label">成交量</span>
          <span class="value">{{ stock.volume || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">成交额</span>
          <span class="value">{{ stock.turnover || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">市盈率</span>
          <span class="value">{{ stock.pe || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">市净率</span>
          <span class="value">{{ stock.pb || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">总市值</span>
          <span class="value">{{ stock.market_cap || '-' }}</span>
        </div>
      </div>
    </div>

    <div class="chart-container">
      <div class="chart-header">
        <span>股票走势</span>
        <el-select v-model="days" @change="loadChart">
          <el-option label="30天" :value="30" />
          <el-option label="60天" :value="60" />
          <el-option label="120天" :value="120" />
          <el-option label="250天" :value="250" />
        </el-select>
      </div>
      <div ref="chartRef" class="chart"></div>
    </div>

    <div class="analysis-section">
      <h3>技术指标</h3>
      <el-table :data="analysisData" border style="width: 100%">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="close" label="收盘价" width="100" />
        <el-table-column prop="ma5" label="MA5" width="100" />
        <el-table-column prop="ma10" label="MA10" width="100" />
        <el-table-column prop="ma20" label="MA20" width="100" />
        <el-table-column prop="macd" label="MACD" width="100" />
        <el-table-column prop="rsi" label="RSI" width="100" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { stockAPI } from '../api/stock'
import * as echarts from 'echarts'

const route = useRoute()
const stock = ref(null)
const chartData = ref([])
const analysisData = ref([])
const days = ref(60)
const chartRef = ref(null)
let chartInstance = null

const loadStockInfo = async () => {
  try {
    const response = await stockAPI.getStock(route.params.code)
    stock.value = response.data
  } catch (error) {
    console.error('加载股票信息失败:', error)
  }
}

const loadChart = async () => {
  try {
    const response = await stockAPI.getStockChart(route.params.code, days.value)
    chartData.value = response.data
    renderChart()
  } catch (error) {
    console.error('加载图表数据失败:', error)
  }
}

const loadAnalysis = async () => {
  try {
    const response = await stockAPI.getStockDaily(route.params.code, days.value)
    analysisData.value = response.data
  } catch (error) {
    console.error('加载分析数据失败:', error)
  }
}

const renderChart = () => {
  if (!chartRef.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  
  const dates = chartData.value.map(item => item.date)
  const values = chartData.value.map(item => [item.open, item.close, item.low, item.high])
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function(params) {
        const data = params[0]
        if (data) {
          const values = data.data
          return `<div>日期: ${data.name}</div>
                  <div>开盘: ${values[1]}</div>
                  <div>收盘: ${values[2]}</div>
                  <div>最低: ${values[3]}</div>
                  <div>最高: ${values[4]}</div>`
        }
        return ''
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      type: 'candlestick',
      data: values,
      itemStyle: {
        color: '#ef4444',
        color0: '#22c55e',
        borderColor: '#ef4444',
        borderColor0: '#22c55e'
      }
    }]
  }
  
  chartInstance.setOption(option)
  
  window.addEventListener('resize', () => {
    chartInstance && chartInstance.resize()
  })
}

onMounted(async () => {
  await loadStockInfo()
  await loadChart()
  await loadAnalysis()
  
  nextTick(() => {
    renderChart()
  })
})

watch(() => route.params.code, async () => {
  await loadStockInfo()
  await loadChart()
  await loadAnalysis()
})
</script>

<style scoped>
.stock-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.stock-info {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.stock-info h2 {
  font-size: 24px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item .label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.info-item .value {
  font-size: 18px;
  font-weight: 600;
}

.chart-container {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
}

.chart {
  height: 500px;
}

.analysis-section {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.analysis-section h3 {
  margin-bottom: 16px;
  font-size: 18px;
}
</style>
