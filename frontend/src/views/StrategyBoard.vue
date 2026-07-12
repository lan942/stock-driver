<template>
  <div class="strategy-board">
    <h2>量化策略看板</h2>

    <!-- 配置面板 -->
    <el-card class="section-card">
      <template #header>
        <span>策略配置</span>
        <el-button type="primary" size="small" style="float:right" @click="saveConfig" :loading="savingConfig">
          保存配置
        </el-button>
      </template>
      <el-form :model="config" label-width="160px" inline>
        <el-form-item label="期望年化收益率">
          <el-input-number v-model="config.target_annual_return" :min="0" :max="1" :step="0.01" :precision="2" size="small" />
          <span class="unit">(如 0.15 = 15%)</span>
        </el-form-item>
        <el-form-item label="初始资金（元）">
          <el-input-number v-model="config.initial_capital" :min="10000" :max="99999999" :step="10000" size="small" />
        </el-form-item>
        <el-form-item label="最大持仓只数">
          <el-input-number v-model="config.max_positions" :min="1" :max="20" :step="1" size="small" />
        </el-form-item>
        <el-form-item label="单只仓位占比">
          <el-input-number v-model="config.position_ratio" :min="0.05" :max="1" :step="0.05" :precision="2" size="small" />
        </el-form-item>
        <el-form-item label="止盈比例">
          <el-input-number v-model="config.stop_profit_pct" :min="0.01" :max="0.5" :step="0.01" :precision="2" size="small" @change="onProfitLossChange" />
          <span class="unit">(如 0.06 = +6%)</span>
        </el-form-item>
        <el-form-item label="止损比例">
          <el-input-number v-model="config.stop_loss_pct" :min="0.01" :max="0.5" :step="0.01" :precision="2" size="small" @change="onProfitLossChange" />
          <span class="unit">(如 0.03 = -3%)</span>
        </el-form-item>
        <el-form-item label="最大持有天数">
          <el-input-number v-model="config.max_hold_days" :min="1" :max="30" :step="1" size="small" />
        </el-form-item>
      </el-form>

      <el-alert type="info" :closable="false" style="margin-top: 12px">
        <template #title>
          盈亏比 {{ expectedReturn.risk_reward_ratio }} : 1 &nbsp;|&nbsp;
          预期每笔收益 {{ (expectedReturn.expected_per_trade * 100).toFixed(2) }}% &nbsp;|&nbsp;
          基于 {{ (expectedReturn.win_rate_estimate * 100).toFixed(0) }}% 估计胜率
        </template>
      </el-alert>
    </el-card>

    <!-- 回测面板 -->
    <el-card class="section-card">
      <template #header>
        <span class="header-title">
          策略回测
          <el-tooltip placement="right" effect="light">
            <template #content>
              <div style="max-width: 380px; line-height: 1.7; font-size: 12px;">
                <div style="font-weight: bold; margin-bottom: 6px;">回测时间范围说明</div>
                <div>· <b>起始/截止日期</b>：整个回测运行的时间范围</div>
                <div>· <b>第一天</b>从空仓开始买入（无卖出操作）</div>
                <div>· <b>每日循环</b>：检测卖出（止盈/止损/超时）→ 选股买入 → 记录权益</div>
                <div>· <b>选股评分</b>：用当天之前 30 个交易日的历史数据计算因子</div>
                <div>· <b>截止日</b>统计总收益、胜率、年化收益等指标</div>
              </div>
            </template>
            <span class="help-icon">?</span>
          </el-tooltip>
        </span>
        <div style="float:right;display:flex;gap:8px">
          <el-button size="small" @click="clearBacktestHandler">清空数据</el-button>
          <el-button type="warning" size="small" @click="runBacktestHandler" :loading="backtesting">
            开始回测
          </el-button>
        </div>
      </template>
      <el-form inline>
        <el-form-item label="起始日期" :validate-state="!backtestDates || backtestDates.length !== 2 ? 'error' : ''">
          <el-date-picker v-model="backtestDates" type="daterange" range-separator="至"
            start-placeholder="起始日" end-placeholder="截止日" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
          <div v-if="!backtestDates || backtestDates.length !== 2" style="color:#f56c6c;font-size:12px;margin-top:4px">
            请选择回测日期范围
          </div>
        </el-form-item>
      </el-form>
      <div v-if="backtestResult" style="margin-top:12px">
        <el-row :gutter="16">
          <el-col :span="4">
            <el-statistic title="最终权益" :value="formatMoney(backtestResult.summary?.final_equity)" />
          </el-col>
          <el-col :span="4">
            <el-statistic title="总收益率" :value="backtestResult.summary?.total_return_pct + '%'" />
          </el-col>
          <el-col :span="4">
            <el-statistic title="年化收益" :value="backtestResult.summary?.annualized_return + '%'" />
          </el-col>
          <el-col :span="4">
            <el-statistic title="胜率" :value="backtestResult.summary?.win_rate + '%'" />
          </el-col>
          <el-col :span="4">
            <el-statistic title="交易次数" :value="backtestResult.summary?.total_trades" />
          </el-col>
          <el-col :span="4">
            <el-statistic title="盈亏比" :value="backtestResult.summary?.win_trades + ':' + backtestResult.summary?.lose_trades" />
          </el-col>
        </el-row>
        <el-alert type="success" :closable="false" style="margin-top:8px">
          持仓和交易明细已写入数据库 →
          <router-link to="/backtest" style="font-weight:bold">前往回测管理页面查看</router-link>
        </el-alert>

        <div ref="equityChartRef" style="width:100%;height:300px;margin-top:16px"></div>

        <el-table :data="backtestResult.trades" border stripe size="small" style="margin-top:12px" max-height="300">
          <el-table-column prop="code" label="代码" width="90" />
          <el-table-column prop="buy_price" label="买入价" width="80" />
          <el-table-column prop="sell_price" label="卖出价" width="80" />
          <el-table-column label="盈亏" width="80">
            <template #default="{ row }">
              <span :style="{ color: row.profit_pct >= 0 ? '#ef4444' : '#22c55e' }">
                {{ row.profit_pct }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="date" label="卖出日" width="100" />
          <el-table-column prop="reason" label="原因" width="80">
            <template #default="{ row }">
              <el-tag :type="getReasonType(row.reason)" size="small">
                {{ getReasonText(row.reason) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 每日推荐 -->
    <el-card class="section-card">
      <template #header><span>买入推荐</span></template>
      <el-empty v-if="recommendations.length === 0" description="暂无推荐（数据不足）" />
      <el-table v-else :data="recommendations" border stripe size="small">
        <el-table-column type="index" label="#" width="40" />
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="name" label="名称" width="100" />
        <el-table-column prop="score" label="评分" width="70" />
        <el-table-column label="上涨概率" width="80">
          <template #default="{ row }">{{ row.factor_scores?.xgboost_prob?.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column prop="current_close" label="现价" width="70" />
        <el-table-column prop="suggested_buy_price" label="建议买入" width="90" />
        <el-table-column prop="target_price" label="目标价" width="80">
          <template #default="{ row }">
            <span style="color:#ef4444">{{ row.target_price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stop_price" label="止损价" width="80">
          <template #default="{ row }">
            <span style="color:#22c55e">{{ row.stop_price }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getStrategyConfig,
  updateStrategyConfig,
  getRecommendations,
  runBacktest,
  clearBacktest,
} from '../api/strategy'

const config = reactive({
  target_annual_return: 0.15,
  initial_capital: 100000,
  max_positions: 5,
  position_ratio: 0.2,
  stop_profit_pct: 0.06,
  stop_loss_pct: 0.03,
  max_hold_days: 5,
})

const expectedReturn = reactive({ risk_reward_ratio: 2, expected_per_trade: 0.01, win_rate_estimate: 0.45 })
const recommendations = ref([])
const savingConfig = ref(false)
const backtestDates = ref(null)
const backtesting = ref(false)
const backtestResult = ref(null)
const equityChartRef = ref(null)

function formatMoney(val) {
  if (val == null) return '-'
  return '¥' + Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function onProfitLossChange() {
  const wp = config.stop_profit_pct
  const wl = config.stop_loss_pct
  if (wl > 0) {
    expectedReturn.risk_reward_ratio = (wp / wl).toFixed(2)
  }
  expectedReturn.expected_per_trade = 0.45 * wp - 0.55 * wl
}

async function loadConfig() {
  try {
    const res = await getStrategyConfig()
    const data = res.data
    if (data.config) {
      Object.assign(config, data.config)
    }
    if (data.expected_return) {
      Object.assign(expectedReturn, data.expected_return)
    }
  } catch (e) {
    console.error('加载配置失败', e)
  }
}

async function saveConfig() {
  savingConfig.value = true
  try {
    await updateStrategyConfig({ ...config })
    await loadConfig()
    ElMessage.success('配置保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    savingConfig.value = false
  }
}

async function loadRecommendations() {
  try {
    const res = await getRecommendations()
    recommendations.value = res.data.data || []
  } catch (e) {
    console.error('加载推荐失败', e)
  }
}

async function runBacktestHandler() {
  if (!backtestDates.value || backtestDates.value.length !== 2) {
    ElMessage.warning('请选择回测日期范围')
    return
  }
  backtesting.value = true
  backtestResult.value = null
  try {
    const res = await runBacktest({
      start_date: backtestDates.value[0],
      end_date: backtestDates.value[1],
      initial_capital: config.initial_capital,
      max_positions: config.max_positions,
      stop_profit_pct: config.stop_profit_pct,
      stop_loss_pct: config.stop_loss_pct,
      max_hold_days: config.max_hold_days,
      position_ratio: config.position_ratio,
    })
    backtestResult.value = res.data
    await nextTick()
    drawEquityChart()
  } catch (e) {
    const errorMsg = e.response?.data?.error || e.message
    if (errorMsg.includes('无交易数据')) {
      ElMessage.error('回测失败: ' + errorMsg + '\\n请检查数据库中是否有该日期范围的数据')
    } else {
      ElMessage.error('回测失败: ' + errorMsg)
    }
  } finally {
    backtesting.value = false
  }
}

function drawEquityChart() {
  if (!equityChartRef.value || !backtestResult.value?.daily_records) return
  const records = backtestResult.value.daily_records
  const chart = echarts.init(equityChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: records.map(r => r.date), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '权益(元)' },
    series: [{
      name: '权益', type: 'line', data: records.map(r => r.equity),
      smooth: true, areaStyle: { opacity: 0.1 },
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' },
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

async function clearBacktestHandler() {
  try {
    await clearBacktest()
    backtestResult.value = null
    ElMessage.success('回测数据已清除')
  } catch (e) {
    ElMessage.error('清除失败')
  }
}

function getReasonType(reason) {
  if (!reason) return 'info'
  const profitReasons = ['take_profit', 'atr_profit', 'sold']
  const lossReasons = ['stop_loss', 'atr_loss']
  if (profitReasons.includes(reason)) return 'success'
  if (lossReasons.includes(reason)) return 'danger'
  return 'warning'
}

function getReasonText(reason) {
  const reasonMap = {
    'take_profit': '止盈',
    'atr_profit': 'ATR止盈',
    'stop_loss': '止损',
    'atr_loss': 'ATR止损',
    'timeout': '超时',
    'force_close': '强制清仓',
    'sold': '止盈/止损',
  }
  return reasonMap[reason] || reason
}

onMounted(async () => {
  await loadConfig()
  onProfitLossChange()
  await loadRecommendations()
})
</script>

<style scoped>
.strategy-board {
  padding: 20px;
}
.section-card {
  margin-top: 16px;
}
.header-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 12px;
  font-weight: bold;
  color: #909399;
  border: 1px solid #c0c4cc;
  border-radius: 50%;
  cursor: help;
  user-select: none;
  line-height: 1;
}
.help-icon:hover {
  color: #409eff;
  border-color: #409eff;
}
.unit {
  font-size: 12px;
  color: #909399;
  margin-left: 6px;
}
</style>
