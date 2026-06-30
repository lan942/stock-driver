<template>
  <div class="stock-list">
    <div class="search-bar">
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

    <el-table :data="stocks" border style="width: 100%" @row-click="goToDetail">
      <el-table-column prop="code" label="代码" width="100" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="price" label="价格" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.change_percent >= 0 ? '#ef4444' : '#22c55e' }">
            {{ row.price ? row.price.toFixed(2) : '-' }}
          </span>
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
      <el-table-column prop="pe" label="市盈率" width="100" />
      <el-table-column prop="market_cap" label="总市值" width="120" />
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
import { ref, reactive, onMounted } from 'vue'
import { stockAPI } from '../api/stock'
import { useRouter } from 'vue-router'

const router = useRouter()
const stocks = ref([])
const searchForm = reactive({
  name: '',
  code: ''
})
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const loadStocks = async () => {
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page,
      ...searchForm
    }
    const response = await stockAPI.getStocks(params)
    stocks.value = response.data.data
    pagination.total = response.data.total
  } catch (error) {
    console.error('加载股票列表失败:', error)
  }
}

const resetSearch = () => {
  searchForm.name = ''
  searchForm.code = ''
  pagination.page = 1
  loadStocks()
}

const goToDetail = (row) => {
  router.push(`/stock/${row.code}`)
}

onMounted(() => {
  loadStocks()
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
  margin-bottom: 24px;
  align-items: center;
}

.search-input {
  width: 200px;
}
</style>
