<template>
  <div class="stock-list">
    <div class="search-bar">
      <div class="date-selector">
        <span class="date-label">数据日期：</span>
        <el-date-picker
          v-model="queryDate"
          type="date"
          placeholder="选择日期（留空=全部日期）"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          clearable
          @change="onDateChange"
          size="default"
        />
        <el-button v-if="!queryDate" size="small" @click="useLatestDate">最新日期</el-button>
      </div>
      <el-input
        v-model="searchForm.name"
        placeholder="搜索股票名称"
        class="search-input"
        @keyup.enter="loadStocks"
      />
      <el-input
        v-model="searchForm.code"
        placeholder="搜索股票代码"
        class="search-input"
        @keyup.enter="loadStocks"
      />
      <el-button type="primary" @click="loadStocks">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div v-if="priceDate" class="current-date-info">
      当前显示：{{ priceDate }} 的行情数据
    </div>
    <div v-else-if="hasSearch" class="current-date-info warn">
      当前显示：全部日期的搜索结果（共 {{ pagination.total }} 条），最新数据日期：{{ latestDate }}
    </div>

    <el-table :data="stocks" border style="width: 100%" @row-click="goToDetail">
      <el-table-column prop="code" label="代码" width="100" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="price" label="收盘价" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.change_percent >= 0 ? '#ef4444' : '#22c55e' }">
            {{ row.price ? row.price.toFixed(2) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="open" label="开盘价" width="100">
        <template #default="{ row }">
          {{ row.open ? row.open.toFixed(2) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="high" label="最高价" width="100">
        <template #default="{ row }">
          <span style="color: #ef4444">{{ row.high ? row.high.toFixed(2) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="low" label="最低价" width="100">
        <template #default="{ row }">
          <span style="color: #22c55e">{{ row.low ? row.low.toFixed(2) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="change_percent" label="涨跌幅" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.change_percent >= 0 ? '#ef4444' : '#22c55e' }">
            {{ row.change_percent >= 0 ? '+' : '' }}{{ row.change_percent ? row.change_percent.toFixed(2) : '-' }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="volume" label="成交量" width="120" />
      <el-table-column prop="turnover_rate" label="换手率" width="100">
        <template #default="{ row }">
          {{ row.turnover_rate ? row.turnover_rate.toFixed(2) : '-' }}%
        </template>
      </el-table-column>
      <el-table-column prop="pe" label="市盈率" width="100" />
      <el-table-column prop="market_cap" label="总市值" width="120" />
      <el-table-column prop="price_date" label="价格日期" width="120" />
    </el-table>

    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.per_page"
      :total="pagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="loadStocks"
      @current-change="loadStocks"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { stockAPI } from '../api/stock'
import { useRouter } from 'vue-router'

const router = useRouter()
const stocks = ref([])
const queryDate = ref('')
const priceDate = ref('')
const latestDate = ref('')
const searchForm = reactive({
  name: '',
  code: ''
})
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const hasSearch = computed(() => !!searchForm.name || !!searchForm.code)

const loadStocks = async () => {
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...searchForm
    }
    if (queryDate.value) {
      params.date = queryDate.value
    }
    const response = await stockAPI.getStocks(params)
    stocks.value = response.data.data
    pagination.total = response.data.total
    if (response.data.price_date) {
      priceDate.value = response.data.price_date
    } else {
      priceDate.value = ''
    }
    if (response.data.latest_date) {
      latestDate.value = response.data.latest_date
    }
  } catch (error) {
    console.error('加载股票列表失败:', error)
  }
}

const onDateChange = () => {
  pagination.page = 1
  loadStocks()
}

const useLatestDate = () => {
  queryDate.value = latestDate.value || ''
  pagination.page = 1
  loadStocks()
}

const resetSearch = () => {
  searchForm.name = ''
  searchForm.code = ''
  queryDate.value = latestDate.value || ''
  pagination.page = 1
  loadStocks()
}

const goToDetail = (row) => {
  router.push(`/stock/${row.code}`)
}

onMounted(async () => {
  await loadStocks()
  if (!queryDate.value && latestDate.value) {
    queryDate.value = latestDate.value
    await loadStocks()
  }
})
</script>

<style scoped>
.stock-list {
  max-width: 1400px;
  margin: 0 auto;
}

.search-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.date-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.current-date-info {
  margin-bottom: 12px;
  padding: 6px 12px;
  background: #ecf5ff;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
}

.current-date-info.warn {
  background: #fdf6ec;
  color: #e6a23c;
}

.search-input {
  width: 200px;
}
</style>
