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
        <div class="chart-controls">
          <el-select v-model="days" @change="loadAll">
            <el-option label="30天" :value="30" />
            <el-option label="60天" :value="60" />
            <el-option label="120天" :value="120" />
            <el-option label="250天" :value="250" />
          </el-select>
        </div>
      </div>
      <div class="overlay-controls">
        <span class="overlay-label">叠加指标:</span>
        <el-checkbox v-model="showMA5" @change="renderChart">MA5</el-checkbox>
        <el-checkbox v-model="showMA10" @change="renderChart">MA10</el-checkbox>
        <el-checkbox v-model="showMA20" @change="renderChart">MA20</el-checkbox>
        <el-checkbox v-model="showMA60" @change="renderChart">MA60</el-checkbox>
        <el-checkbox v-model="showBOLL" @change="renderChart">布林带</el-checkbox>
      </div>
      <div ref="chartRef" class="chart"></div>
    </div>

    <div class="analysis-section">
      <div class="analysis-header">
        <h3>技术指标</h3>
        <el-button size="small" @click="loadAll" :loading="loading">刷新</el-button>
      </div>
      <el-table :data="tableData" border style="width: 100%" v-loading="loading" max-height="500">
        <el-table-column prop="date" label="日期" width="110" fixed />
        <el-table-column prop="close" label="收盘价" width="100" />
        <el-table-column prop="ma5" label="MA5" width="90" />
        <el-table-column prop="ma10" label="MA10" width="90" />
        <el-table-column prop="ma20" label="MA20" width="90" />
        <el-table-column prop="ma60" label="MA60" width="90" />
        <el-table-column prop="macd" label="MACD" width="100" />
        <el-table-column prop="signal" label="Signal" width="100" />
        <el-table-column prop="rsi" label="RSI" width="80" />
        <el-table-column prop="boll_upper" label="BOLL上轨" width="100" />
        <el-table-column prop="boll_mid" label="BOLL中轨" width="100" />
        <el-table-column prop="boll_lower" label="BOLL下轨" width="100" />
        <el-table-column prop="kdj_k" label="K" width="80" />
        <el-table-column prop="kdj_d" label="D" width="80" />
        <el-table-column prop="kdj_j" label="J" width="80" />
        <el-table-column prop="atr" label="ATR" width="80" />
        <el-table-column prop="adx" label="ADX" width="80" />
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
const indicatorData = ref(null)
const tableData = ref([])
const loading = ref(false)
const days = ref(60)
const chartRef = ref(null)

// 叠加开关
const showMA5 = ref(true)
const showMA10 = ref(true)
const showMA20 = ref(true)
const showMA60 = ref(false)
const showBOLL = ref(false)

let chartInstance = null

// 前端计算 SMA
function calcSMA(values, period) {
  const result = new Array(values.length).fill(null)
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= period - 1) {
      result[i] = +(sum / period).toFixed(2)
      sum -= values[i - period + 1]
    }
  }
  return result
}

// 将 API 数据转为表格行
function buildTableData(data) {
  const dates = data.dates || []
  const close = data.prices?.close || []
  const indicators = data.indicators || {}

  const ma5 = calcSMA(close, 5)
  const ma10 = calcSMA(close, 10)
  const ma20 = calcSMA(close, 20)
  const ma60 = calcSMA(close, 60)

  const rows = []
  for (let i = 0; i < dates.length; i++) {
    const row = {
      date: dates[i],
      close: close[i]?.toFixed(2),
      ma5: ma5[i],
      ma10: ma10[i],
      ma20: ma20[i],
      ma60: ma60[i],
      macd: indicators.macd?.macd?.[i],
      signal: indicators.macd?.signal?.[i],
      rsi: indicators.rsi?.values?.[i],
      boll_upper: indicators.boll?.upper?.[i],
      boll_mid: indicators.boll?.mid?.[i],
      boll_lower: indicators.boll?.lower?.[i],
      kdj_k: indicators.kdj?.k?.[i],
      kdj_d: indicators.kdj?.d?.[i],
      kdj_j: indicators.kdj?.j?.[i],
      atr: indicators.atr?.values?.[i],
      adx: indicators.adx?.values?.[i],
    }
    rows.push(row)
  }
  return rows
}

const loadStockInfo = async () => {
  try {
    const response = await stockAPI.getStock(route.params.code)
    stock.value = response.data
  } catch (error) {
    console.error('加载股票信息失败:', error)
  }
}

const loadAll = async () => {
  loading.value = true
  try {
    // 请求除 MA 外的所有指标（MA 由前端计算）
    const response = await stockAPI.getStockIndicators(
      route.params.code,
      days.value,
      'RSI,MACD,BOLL,KDJ,ATR,ADX'
    )
    indicatorData.value = response.data
    tableData.value = buildTableData(response.data)
    await nextTick()
    renderChart()
  } catch (error) {
    console.error('加载指标数据失败:', error)
  } finally {
    loading.value = false
  }
}

const renderChart = () => {
  if (!chartRef.value || !indicatorData.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const data = indicatorData.value
  const dates = data.dates || []
  const prices = data.prices || {}
  const closeArr = prices.close || []

  // 构建 K 线数据 [open, close, low, high]
  const klineData = dates.map((_, i) => [
    prices.open?.[i] ?? 0,
    prices.close?.[i] ?? 0,
    prices.low?.[i] ?? 0,
    prices.high?.[i] ?? 0,
  ])

  const ma5 = calcSMA(closeArr, 5)
  const ma10 = calcSMA(closeArr, 10)
  const ma20 = calcSMA(closeArr, 20)
  const ma60 = calcSMA(closeArr, 60)

  const series = [
    {
      name: 'K线',
      type: 'candlestick',
      data: klineData,
      itemStyle: {
        color: '#ef4444',
        color0: '#22c55e',
        borderColor: '#ef4444',
        borderColor0: '#22c55e',
      },
    },
  ]

  const maColors = { MA5: '#FF9800', MA10: '#2196F3', MA20: '#9C27B0', MA60: '#4CAF50' }

  const addMALine = (name, values, color) => {
    if (!values || values.length === 0) return
    series.push({
      name,
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { color, width: 1.5, opacity: 0.7 },
      symbol: 'none',
      itemStyle: { color },
    })
  }

  if (showMA5.value) addMALine('MA5', ma5, maColors.MA5)
  if (showMA10.value) addMALine('MA10', ma10, maColors.MA10)
  if (showMA20.value) addMALine('MA20', ma20, maColors.MA20)
  if (showMA60.value) addMALine('MA60', ma60, maColors.MA60)

  // 布林带
  if (showBOLL.value && data.indicators?.boll) {
    const boll = data.indicators.boll
    const bollStyle = { width: 1, opacity: 0.5 }
    if (boll.upper) series.push({ name: 'BOLL上轨', type: 'line', data: boll.upper, lineStyle: { ...bollStyle, color: '#FF5722', type: 'dashed' }, symbol: 'none' })
    if (boll.mid) series.push({ name: 'BOLL中轨', type: 'line', data: boll.mid, lineStyle: { ...bollStyle, color: '#607D8B' }, symbol: 'none' })
    if (boll.lower) series.push({ name: 'BOLL下轨', type: 'line', data: boll.lower, lineStyle: { ...bollStyle, color: '#FF5722', type: 'dashed' }, symbol: 'none' })
  }

  const option = {
    legend: { data: series.filter(s => s.name !== 'K线').map(s => s.name), top: 0 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: { left: '3%', right: '4%', top: '8%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45 },
    },
    yAxis: { type: 'value', scale: true },
    series,
  }

  chartInstance.setOption(option)

  window.addEventListener('resize', () => {
    chartInstance && chartInstance.resize()
  })
}

onMounted(async () => {
  await loadStockInfo()
  await loadAll()
})

watch(() => route.params.code, async () => {
  await loadStockInfo()
  await loadAll()
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
  margin-bottom: 8px;
  font-size: 18px;
  font-weight: 600;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.overlay-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 6px;
  flex-wrap: wrap;
}

.overlay-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
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

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.analysis-header h3 {
  margin: 0;
  font-size: 18px;
}
</style>