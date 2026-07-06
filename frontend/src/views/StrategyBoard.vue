<template>
  <div class="strategy-board">
    <h2>量化策略看板</h2>

    <!-- 收益对比卡片 -->
    <el-row :gutter="16" class="stats-cards">
      <el-col :span="6">
        <el-card shadow="hover" :class="stats.on_track ? 'card-success' : 'card-warn'">
          <div class="card-title">年化收益率</div>
          <div class="card-value">{{ stats.annualized_return ?? '-' }}%</div>
          <div class="card-sub">目标: {{ stats.target_annual_return ?? '-' }}%</div>
          <el-progress
            :percentage="Math.min(stats.annualized_return / stats.target_annual_return * 100, 200)"
            :color="stats.on_track ? '#67c23a' : '#f56c6c'"
            :show-text="false"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-title">胜率</div>
          <div class="card-value">{{ stats.win_rate ?? '-' }}%</div>
          <div class="card-sub">盈利 {{ stats.win_trades }} / 总 {{ stats.total_trades }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-title">总权益</div>
          <div class="card-value">{{ formatMoney(stats.total_equity) }}</div>
          <div class="card-sub">初始 {{ formatMoney(stats.initial_capital) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="card-title">持仓/可用资金</div>
          <div class="card-value">{{ stats.positions_count }} 只</div>
          <div class="card-sub">现金 {{ formatMoney(stats.available_cash) }}</div>
        </el-card>
      </el-col>
    </el-row>

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

      <!-- 预期收益预览 -->
      <el-alert type="info" :closable="false" style="margin-top: 12px">
        <template #title>
          盈亏比 {{ expectedReturn.risk_reward_ratio }} : 1 &nbsp;|&nbsp;
          预期每笔收益 {{ (expectedReturn.expected_per_trade * 100).toFixed(2) }}% &nbsp;|&nbsp;
          基于 {{ (expectedReturn.win_rate_estimate * 100).toFixed(0) }}% 估计胜率
        </template>
      </el-alert>
    </el-card>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button type="success" @click="handleRun" :loading="running">
        运行策略
      </el-button>
      <el-tag v-if="runResult" type="success" style="margin-left: 12px">
        卖出 {{ runResult.sold_count }} 笔，推荐 {{ runResult.recommendations_count }} 只
      </el-tag>
    </div>

    <!-- 回测面板 -->
    <el-card class="section-card">
      <template #header>
        <span>策略回测</span>
        <div style="float:right;display:flex;gap:8px">
          <el-button size="small" @click="clearBacktestHandler">清空数据</el-button>
          <el-button type="warning" size="small" @click="runBacktestHandler" :loading="backtesting">
            开始回测
          </el-button>
        </div>
      </template>
      <el-form inline>
        <el-form-item label="起始日期">
          <el-date-picker v-model="backtestDates" type="daterange" range-separator="至"
            start-placeholder="起始日" end-placeholder="截止日" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
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

        <!-- 权益曲线 -->
        <div ref="equityChartRef" style="width:100%;height:300px;margin-top:16px"></div>

        <!-- 交易明细 -->
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
              <el-tag :type="row.reason === 'sold' ? 'success' : 'warning'" size="small">
                {{ row.reason === 'sold' ? '止盈/止损' : '超时' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 每日推荐 -->
    <el-card class="section-card">
      <template #header><span>买入推荐</span></template>
      <el-empty v-if="recommendations.length === 0" description="暂无推荐（可能持仓已满或数据不足）" />
      <el-table v-else :data="recommendations" border stripe size="small">
        <el-table-column type="index" label="#" width="40" />
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="name" label="名称" width="100" />
        <el-table-column prop="score" label="评分" width="70" />
        <el-table-column label="趋势" width="70">
          <template #default="{ row }">{{ row.factor_scores?.trend?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="动量" width="70">
          <template #default="{ row }">{{ row.factor_scores?.momentum?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="量能" width="70">
          <template #default="{ row }">{{ row.factor_scores?.volume?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="反转" width="70">
          <template #default="{ row }">{{ row.factor_scores?.reversal?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="波动" width="70">
          <template #default="{ row }">{{ row.factor_scores?.volatility?.toFixed(2) }}</template>
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
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="executeBuy(row)" :loading="executing === row.code">
              执行买入
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 当前持仓 -->
    <el-card class="section-card">
      <template #header><span>当前持仓</span></template>
      <el-empty v-if="positions.length === 0" description="无持仓" />
      <el-table v-else :data="positions" border stripe size="small">
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="name" label="名称" width="100" />
        <el-table-column prop="buy_price" label="买入价" width="80" />
        <el-table-column prop="quantity" label="数量" width="60" />
        <el-table-column prop="buy_date" label="买入日" width="100" />
        <el-table-column prop="hold_days" label="持有天数" width="80" />
        <el-table-column label="浮动盈亏" width="120">
          <template #default="{ row }">
            <span :style="{ color: (row.unrealized_pl_pct ?? 0) >= 0 ? '#ef4444' : '#22c55e' }">
              {{ row.unrealized_pl_pct != null ? row.unrealized_pl_pct.toFixed(2) + '%' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="target_price" label="目标价" width="80" />
        <el-table-column prop="stop_price" label="止损价" width="80" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'holding' ? 'warning' : row.status === 'sold' ? 'success' : 'info'" size="small">
              {{ row.status === 'holding' ? '持仓中' : row.status === 'sold' ? '已卖出' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" v-if="positions.some(p => p.status === 'holding')">
          <template #default="{ row }">
            <el-popconfirm
              v-if="row.status === 'holding'"
              title="确认以最新收盘价卖出？"
              @confirm="executeSell(row)"
            >
              <template #reference>
                <el-button type="success" size="small" :loading="selling === row.id">卖出</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <el-table-column prop="profit_pct" label="实际盈亏" width="100">
          <template #default="{ row }">
            <span v-if="row.profit_pct != null" :style="{ color: row.profit_pct >= 0 ? '#ef4444' : '#22c55e' }">
              {{ row.profit_pct.toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 交易记录 -->
    <el-card class="section-card">
      <template #header><span>交易记录</span></template>
      <el-table :data="transactions" border stripe size="small" v-loading="loadingTx">
        <el-table-column prop="trade_date" label="日期" width="100" />
        <el-table-column label="类型" width="60">
          <template #default="{ row }">
            <el-tag :type="row.type === 'buy' ? 'danger' : 'success'" size="small">
              {{ row.type === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="price" label="价格" width="80" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="amount" label="金额" width="100" />
      </el-table>
      <el-pagination
        v-if="txTotal > 0"
        v-model:current-page="txPage"
        :page-size="txPageSize"
        :total="txTotal"
        layout="prev, pager, next"
        @current-change="loadTransactions"
        style="margin-top:12px"
      />
    </el-card>

    <!-- 其他统计 -->
    <el-card class="section-card" v-if="stats.total_trades > 0">
      <template #header><span>统计明细</span></template>
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="平均盈利">{{ stats.avg_profit_pct }}%</el-descriptions-item>
        <el-descriptions-item label="平均亏损">{{ stats.avg_loss_pct }}%</el-descriptions-item>
        <el-descriptions-item label="盈亏比">{{ (stats.avg_profit_pct / (stats.avg_loss_pct || 1)).toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="运行天数">{{ stats.running_days }}</el-descriptions-item>
        <el-descriptions-item label="已实现收益">{{ stats.realized_return }}%</el-descriptions-item>
        <el-descriptions-item label="浮动盈亏">{{ stats.unrealized_return }}%</el-descriptions-item>
        <el-descriptions-item label="总收益率">{{ stats.total_return }}%</el-descriptions-item>
        <el-descriptions-item label="达标状态">
          <el-tag :type="stats.on_track ? 'success' : 'danger'" size="small">
            {{ stats.on_track ? '达标' : '未达标' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
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
  getPositions,
  getTransactions,
  getStats,
  runStrategy,
  executeRecommendation,
  sellPosition,
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
const stats = reactive({})
const recommendations = ref([])
const positions = ref([])
const transactions = ref([])
const runResult = ref(null)
const running = ref(false)
const executing = ref(null)
const selling = ref(null)
const savingConfig = ref(false)
const backtestDates = ref(null)
const backtesting = ref(false)
const backtestResult = ref(null)
const equityChartRef = ref(null)
const loadingTx = ref(false)
const txPage = ref(1)
const txPageSize = ref(20)
const txTotal = ref(0)

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
    // 重新加载统计数据和预期收益（初始资金变更后同步刷新）
    await Promise.all([loadStats(), loadConfig()])
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

async function loadPositions() {
  try {
    const res = await getPositions()
    positions.value = res.data.data || []
  } catch (e) {
    console.error('加载持仓失败', e)
  }
}

async function loadTransactions() {
  loadingTx.value = true
  try {
    const res = await getTransactions({ page: txPage.value, page_size: txPageSize.value })
    transactions.value = res.data.data || []
    txTotal.value = res.data.total || 0
  } catch (e) {
    console.error('加载交易记录失败', e)
  } finally {
    loadingTx.value = false
  }
}

async function loadStats() {
  try {
    const res = await getStats()
    Object.assign(stats, res.data)
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

async function handleRun() {
  running.value = true
  try {
    const res = await runStrategy()
    runResult.value = res.data
    // 刷新所有数据
    await Promise.all([loadPositions(), loadStats(), loadRecommendations(), loadTransactions()])
  } catch (e) {
    ElMessage.error('策略执行失败')
  } finally {
    running.value = false
  }
}

async function executeBuy(row) {
  executing.value = row.code
  try {
    const data = {
      code: row.code,
      name: row.name,
      quantity: 100,  // 最小交易单位
      buy_price: row.suggested_buy_price,
      suggested_buy_price: row.suggested_buy_price,
      target_price: row.target_price,
      stop_price: row.stop_price,
    }
    await executeRecommendation(data)
    ElMessage.success(`已买入 ${row.code} ${row.name}`)
    // 刷新所有数据
    await Promise.all([loadRecommendations(), loadPositions(), loadStats(), loadTransactions()])
  } catch (e) {
    ElMessage.error('执行买入失败: ' + (e.response?.data?.error || e.message))
  } finally {
    executing.value = null
  }
}

async function executeSell(row) {
  selling.value = row.id
  try {
    // 使用最新收盘价作为卖出价
    const price = row.current_price || row.buy_price
    await sellPosition({ position_id: row.id, sell_price: price })
    ElMessage.success(`已卖出 ${row.code} ${row.name}`)
    await Promise.all([loadRecommendations(), loadPositions(), loadStats(), loadTransactions()])
  } catch (e) {
    ElMessage.error('卖出失败: ' + (e.response?.data?.error || e.message))
  } finally {
    selling.value = null
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
    // 绘制权益曲线
    await nextTick()
    drawEquityChart()
  } catch (e) {
    ElMessage.error('回测失败: ' + (e.response?.data?.error || e.message))
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

onMounted(async () => {
  await loadConfig()
  onProfitLossChange()
  await Promise.all([loadRecommendations(), loadPositions(), loadTransactions(), loadStats()])
})
</script>

<style scoped>
.strategy-board {
  padding: 20px;
}
.stats-cards {
  margin-bottom: 16px;
}
.stats-cards .card-title {
  font-size: 13px;
  color: #909399;
}
.stats-cards .card-value {
  font-size: 24px;
  font-weight: bold;
  margin: 6px 0;
}
.stats-cards .card-sub {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.card-success {
  border-left: 4px solid #67c23a;
}
.card-warn {
  border-left: 4px solid #f56c6c;
}
.section-card {
  margin-top: 16px;
}
.action-bar {
  margin-top: 16px;
  display: flex;
  align-items: center;
}
.unit {
  font-size: 12px;
  color: #909399;
  margin-left: 6px;
}
</style>
