<template>
  <div class="backtest">
    <div class="overview-cards">
      <el-card class="overview-card">
        <div class="card-icon total-icon">💰</div>
        <div class="card-content">
          <div class="card-label">总资产</div>
          <div class="card-value">¥{{ formatNumber(overview.total_value) }}</div>
        </div>
      </el-card>
      <el-card class="overview-card">
        <div class="card-icon cash-icon">💵</div>
        <div class="card-content">
          <div class="card-label">现金余额</div>
          <div class="card-value-row">
            <div class="card-value">¥{{ formatNumber(overview.cash_balance) }}</div>
            <el-button size="small" type="text" @click="openCashDialog" class="update-btn">更新</el-button>
          </div>
        </div>
      </el-card>
      <el-card class="overview-card">
        <div class="card-icon profit-icon">📈</div>
        <div class="card-content">
          <div class="card-label">持仓市值</div>
          <div class="card-value">¥{{ formatNumber(overview.market_value) }}</div>
        </div>
      </el-card>
      <el-card class="overview-card">
        <div class="card-icon rate-icon">📊</div>
        <div class="card-content">
          <div class="card-label">总收益</div>
          <div class="card-value" :class="{ 'profit-positive': overview.total_profit >= 0, 'profit-negative': overview.total_profit < 0 }">
            {{ overview.total_profit >= 0 ? '+' : '' }}¥{{ formatNumber(overview.total_profit) }}
            <span class="profit-rate" :class="{ 'profit-positive': overview.total_profit_rate >= 0, 'profit-negative': overview.total_profit_rate < 0 }">
              ({{ overview.total_profit_rate >= 0 ? '+' : '' }}{{ overview.total_profit_rate.toFixed(2) }}%)
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>持仓明细</span>
          <el-button type="primary" @click="openAddHoldingDialog">添加持仓</el-button>
        </div>
      </template>
      <el-table :data="holdings" border style="width: 100%" fit>
        <el-table-column prop="code" label="股票代码" width="100" />
        <el-table-column prop="name" label="股票名称" min-width="120" />
        <el-table-column prop="quantity" label="持仓数量" width="100" align="center">
          <template #default="{ row }">
            {{ row.quantity.toLocaleString() }} 股
          </template>
        </el-table-column>
        <el-table-column prop="available_quantity" label="可用数量" width="100" align="center">
          <template #default="{ row }">
            <span :class="{ 't-plus-one': row.available_quantity < row.quantity }">
              {{ row.available_quantity.toLocaleString() }} 股
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="cost_price" label="成本价" width="100" align="center">
          <template #default="{ row }">
            ¥{{ row.cost_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="current_price" label="现价" width="100" align="center">
          <template #default="{ row }">
            ¥{{ row.current_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="market_value" label="市值" width="120" align="center">
          <template #default="{ row }">
            ¥{{ formatNumber(row.market_value) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="收益" width="120" align="center">
          <template #default="{ row }">
            <span :class="{ 'profit-positive': row.profit >= 0, 'profit-negative': row.profit < 0 }">
              {{ row.profit >= 0 ? '+' : '' }}¥{{ formatNumber(row.profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="收益率" width="100" align="center">
          <template #default="{ row }">
            <span :class="{ 'profit-positive': row.profit_rate >= 0, 'profit-negative': row.profit_rate < 0 }">
              {{ row.profit_rate >= 0 ? '+' : '' }}{{ row.profit_rate.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <div class="actions-wrapper">
              <el-button size="small" @click="openEditHoldingDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteHolding(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="holdings.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无持仓数据</div>
        <div class="empty-hint">点击上方"添加持仓"按钮开始记录您的持仓</div>
      </div>
    </el-card>

    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>交易记录</span>
          <div class="header-actions">
            <el-button type="danger" plain @click="clearAllTransactions">清除记录</el-button>
            <el-button type="primary" @click="openAddTransactionDialog">添加交易</el-button>
          </div>
        </div>
      </template>
      <el-table :data="transactions" border style="width: 100%" fit>
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === 'buy' ? 'success' : 'danger'">
              {{ row.type === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="股票代码" width="100" />
        <el-table-column prop="name" label="股票名称" width="120" />
        <el-table-column prop="quantity" label="数量" width="100">
          <template #default="{ row }">
            {{ row.quantity.toLocaleString() }} 股
          </template>
        </el-table-column>
        <el-table-column prop="price" label="成交价" width="100">
          <template #default="{ row }">
            ¥{{ row.price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="成交金额" width="120">
          <template #default="{ row }">
            ¥{{ formatNumber(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="trade_date" label="交易日期" width="110">
          <template #default="{ row }">
            {{ row.trade_date || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
      </el-table>
      <div v-if="transactions.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <div class="empty-text">暂无交易记录</div>
        <div class="empty-hint">点击上方"添加交易"按钮记录您的交易</div>
      </div>
    </el-card>

    <el-dialog v-model="addHoldingDialogVisible" title="添加持仓" width="400px">
      <el-form :model="addHoldingForm" label-width="80px">
        <el-form-item label="股票代码" required>
          <el-select
            v-model="addHoldingForm.code"
            filterable
            remote
            reserve-keyword
            placeholder="请输入股票代码或名称搜索"
            :remote-method="searchStocks"
            :loading="stockSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="item in stockOptions"
              :key="item.code"
              :label="`${item.code} - ${item.name}`"
              :value="item.code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="持仓数量" required>
          <el-input-number v-model="addHoldingForm.quantity" :min="100" :step="100" placeholder="请输入持仓数量" />
        </el-form-item>
        <el-form-item label="成本价" required>
          <el-input-number v-model="addHoldingForm.cost_price" :min="0.01" :step="0.01" :precision="2" placeholder="请输入成本价" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addHoldingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddHolding">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editHoldingDialogVisible" title="编辑持仓" width="400px">
      <el-form :model="editHoldingForm" label-width="80px">
        <el-form-item label="股票代码">
          <el-input :value="editHoldingForm.code" disabled />
        </el-form-item>
        <el-form-item label="持仓数量" required>
          <el-input-number v-model="editHoldingForm.quantity" :min="100" :step="100" />
        </el-form-item>
        <el-form-item label="成本价" required>
          <el-input-number v-model="editHoldingForm.cost_price" :min="0.01" :step="0.01" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editHoldingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEditHolding">确认修改</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addTransactionDialogVisible" title="添加交易记录" width="420px">
      <el-form :model="addTransactionForm" label-width="80px">
        <el-form-item label="交易类型" required>
          <el-radio-group v-model="addTransactionForm.type" @change="onTransactionTypeChange">
            <el-radio label="buy">买入</el-radio>
            <el-radio label="sell">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="股票代码" required>
          <!-- 卖出：从持仓中选择 -->
          <el-select
            v-if="addTransactionForm.type === 'sell'"
            v-model="addTransactionForm.code"
            filterable
            placeholder="请选择持仓中的股票"
            style="width: 100%"
            @change="onSellCodeChange"
          >
            <el-option
              v-for="item in holdings"
              :key="item.code"
              :label="`${item.code} - ${item.name} (持仓 ${item.quantity} 股)`"
              :value="item.code"
            />
          </el-select>
          <!-- 买入：远程搜索全部股票 -->
          <el-select
            v-else
            v-model="addTransactionForm.code"
            filterable
            remote
            reserve-keyword
            placeholder="请输入股票代码或名称搜索"
            :remote-method="searchStocks"
            :loading="stockSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="item in stockOptions"
              :key="item.code"
              :label="`${item.code} - ${item.name}`"
              :value="item.code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="交易数量" required>
          <el-input-number
            v-model="addTransactionForm.quantity"
            :min="100"
            :step="100"
            :max="sellMaxQuantity"
            placeholder="100的整数倍"
          />
          <span v-if="addTransactionForm.type === 'sell' && sellMaxQuantity < Infinity" class="form-hint">
            可卖出上限: {{ sellMaxQuantity }} 股
          </span>
        </el-form-item>
        <el-form-item label="成交价格" required>
          <el-input-number v-model="addTransactionForm.price" :min="0.01" :step="0.01" :precision="2" placeholder="请输入成交价格" />
        </el-form-item>
        <el-form-item label="交易日期">
          <el-date-picker
            v-model="addTransactionForm.trade_date"
            type="date"
            placeholder="选择交易日期"
            value-format="YYYY-MM-DD"
            :disabled-date="disableFutureDate"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addTransactionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAddTransaction">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cashDialogVisible" title="更新现金余额" width="400px">
      <el-form :model="cashForm" label-width="80px">
        <el-form-item label="变动金额">
          <el-input-number v-model="cashForm.amount" :step="100" :precision="2" placeholder="正数为存入，负数为取出" />
          <span class="form-hint">当前余额: ¥{{ formatNumber(overview.cash_balance) }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cashDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCashUpdate">确认更新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { stockAPI } from '../api/stock'
import { ElMessage, ElMessageBox } from 'element-plus'

const overview = ref({
  total_value: 0,
  cash_balance: 0,
  market_value: 0,
  total_profit: 0,
  total_profit_rate: 0,
  holdings_count: 0
})

const holdings = ref([])
const transactions = ref([])

const stockOptions = ref([])
const stockSearchLoading = ref(false)

const addHoldingDialogVisible = ref(false)
const addHoldingForm = reactive({
  code: '',
  quantity: null,
  cost_price: null
})

const editHoldingDialogVisible = ref(false)
const editHoldingForm = reactive({
  id: null,
  code: '',
  quantity: null,
  cost_price: null
})

const addTransactionDialogVisible = ref(false)
const getTodayStr = () => {
  const d = new Date()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

const addTransactionForm = reactive({
  type: 'buy',
  code: '',
  quantity: null,
  price: null,
  trade_date: getTodayStr()
})

const cashDialogVisible = ref(false)
const cashForm = reactive({
  amount: null
})

const formatNumber = (num) => {
  if (num === null || num === undefined) return '0.00'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const disableFutureDate = (time) => {
  return time.getTime() > Date.now()
}

const loadOverview = async () => {
  try {
    const response = await stockAPI.getBacktestOverview()
    overview.value = response.data
  } catch (error) {
    console.error('加载回测总览失败:', error)
  }
}

const loadHoldings = async () => {
  try {
    const response = await stockAPI.getBacktestHoldings()
    holdings.value = response.data
  } catch (error) {
    console.error('加载回测持仓失败:', error)
  }
}

const loadTransactions = async () => {
  try {
    const response = await stockAPI.getBacktestTransactions()
    transactions.value = response.data
  } catch (error) {
    console.error('加载回测交易记录失败:', error)
  }
}

const refreshData = () => {
  loadOverview()
  loadHoldings()
  loadTransactions()
}

let searchTimer = null

const searchStocks = async (query) => {
  if (searchTimer) clearTimeout(searchTimer)
  
  if (!query) {
    stockOptions.value = []
    return
  }

  searchTimer = setTimeout(async () => {
    stockSearchLoading.value = true
    try {
      const response = await stockAPI.searchStocks(query)
      stockOptions.value = response.data.data || []
    } catch (error) {
      console.error('搜索股票失败:', error)
      stockOptions.value = []
    } finally {
      stockSearchLoading.value = false
    }
  }, 300)
}

const openAddHoldingDialog = () => {
  addHoldingForm.code = ''
  addHoldingForm.quantity = null
  addHoldingForm.cost_price = null
  addHoldingDialogVisible.value = true
}

const submitAddHolding = async () => {
  if (!addHoldingForm.code || addHoldingForm.quantity === null || addHoldingForm.cost_price === null) {
    ElMessage.error('请填写完整信息')
    return
  }
  try {
    await stockAPI.addBacktestHolding({
      code: addHoldingForm.code,
      quantity: addHoldingForm.quantity,
      cost_price: addHoldingForm.cost_price
    })
    ElMessage.success('持仓添加成功')
    addHoldingDialogVisible.value = false
    refreshData()
  } catch (error) {
    const message = error.response?.data?.error || '添加失败'
    ElMessage.error(message)
  }
}

const openEditHoldingDialog = (row) => {
  editHoldingForm.id = row.id
  editHoldingForm.code = row.code
  editHoldingForm.quantity = row.quantity
  editHoldingForm.cost_price = row.cost_price
  editHoldingDialogVisible.value = true
}

const submitEditHolding = async () => {
  if (editHoldingForm.quantity === null || editHoldingForm.cost_price === null) {
    ElMessage.error('请填写完整信息')
    return
  }
  try {
    await stockAPI.updateBacktestHolding(editHoldingForm.id, {
      quantity: editHoldingForm.quantity,
      cost_price: editHoldingForm.cost_price
    })
    ElMessage.success('持仓修改成功')
    editHoldingDialogVisible.value = false
    refreshData()
  } catch (error) {
    const message = error.response?.data?.error || '修改失败'
    ElMessage.error(message)
  }
}

const deleteHolding = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条持仓吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await stockAPI.deleteBacktestHolding(id)
    ElMessage.success('持仓删除成功')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      const message = error.response?.data?.error || '删除失败'
      ElMessage.error(message)
    }
  }
}

const clearAllTransactions = async () => {
  try {
    await ElMessageBox.confirm('确定要清除所有交易记录吗？此操作不可恢复。', '确认清除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await stockAPI.clearBacktestTransactions()
    ElMessage.success('交易记录已全部清除')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      const message = error.response?.data?.error || '清除失败'
      ElMessage.error(message)
    }
  }
}

const sellMaxQuantity = computed(() => {
  if (addTransactionForm.type !== 'sell' || !addTransactionForm.code) return Infinity
  const holding = holdings.value.find(h => h.code === addTransactionForm.code)
  return holding ? holding.quantity : 0
})

const onTransactionTypeChange = () => {
  addTransactionForm.code = ''
  addTransactionForm.quantity = null
}

const onSellCodeChange = () => {
  addTransactionForm.quantity = null
}

const openAddTransactionDialog = () => {
  addTransactionForm.type = 'buy'
  addTransactionForm.code = ''
  addTransactionForm.quantity = null
  addTransactionForm.price = null
  addTransactionForm.trade_date = getTodayStr()
  addTransactionDialogVisible.value = true
}

const submitAddTransaction = async () => {
  if (!addTransactionForm.type || !addTransactionForm.code || addTransactionForm.quantity === null || addTransactionForm.price === null) {
    ElMessage.error('请填写完整信息')
    return
  }
  if (addTransactionForm.quantity % 100 !== 0) {
    ElMessage.error('交易数量必须是100的整数倍')
    return
  }
  if (addTransactionForm.type === 'sell' && addTransactionForm.quantity > sellMaxQuantity.value) {
    ElMessage.error(`卖出数量不能超过持仓数量 (${sellMaxQuantity.value} 股)`)
    return
  }
  try {
    await stockAPI.addBacktestTransaction({
      type: addTransactionForm.type,
      code: addTransactionForm.code,
      quantity: addTransactionForm.quantity,
      price: addTransactionForm.price,
      trade_date: addTransactionForm.trade_date
    })
    ElMessage.success('交易记录添加成功')
    addTransactionDialogVisible.value = false
    refreshData()
  } catch (error) {
    const message = error.response?.data?.error || '添加失败'
    ElMessage.error(message)
  }
}

const openCashDialog = () => {
  cashForm.amount = null
  cashDialogVisible.value = true
}

const submitCashUpdate = async () => {
  if (cashForm.amount === null) {
    ElMessage.error('请输入金额')
    return
  }
  try {
    await stockAPI.updateBacktestCash(cashForm.amount)
    ElMessage.success('现金余额更新成功')
    cashDialogVisible.value = false
    refreshData()
  } catch (error) {
    const message = error.response?.data?.error || '更新失败'
    ElMessage.error(message)
  }
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.backtest {
  padding: 0 20px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-icon {
  font-size: 32px;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.total-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.cash-icon {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.profit-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.rate-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.card-content {
  flex: 1;
  position: relative;
}

.card-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 4px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.card-value-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.update-btn {
  flex-shrink: 0;
  padding: 0;
  font-size: 12px;
}

.profit-positive {
  color: #22c55e;
}

.profit-negative {
  color: #ef4444;
}

.t-plus-one {
  color: #e6a23c;
  font-weight: 500;
}

.profit-rate {
  font-size: 14px;
  margin-left: 8px;
}

.main-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 18px;
  color: #303133;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.actions-wrapper {
  display: flex;
  justify-content: center;
  gap: 8px;
}

@media (max-width: 1200px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }
}
</style>
