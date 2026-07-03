<template>
  <div class="top-stocks">
    <div class="search-bar">
      <div class="date-selector">
        <span class="date-label">数据日期：</span>
        <el-date-picker
          v-model="queryDate"
          type="date"
          placeholder="选择日期（留空=最新）"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          clearable
          @change="onDateChange"
          size="default"
        />
      </div>
    </div>

    <div v-if="priceDate" class="current-date-info">
      当前显示：{{ priceDate }} 的排行数据
    </div>
    <div v-else class="current-date-info warn">
      当前无排行数据
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="涨幅榜" name="gainers">
        <el-empty v-if="gainers.length === 0" description="该日期暂无排行数据" />
        <el-table v-else :data="gainers" border style="width: 100%">
          <el-table-column type="index" label="排名" width="60" />
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="price" label="价格" width="100">
            <template #default="{ row }">
              <span style="color: #ef4444">
                {{ row.price ? row.price.toFixed(2) : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="change_percent" label="涨跌幅" width="100">
            <template #default="{ row }">
              <span style="color: #ef4444">
                +{{ row.change_percent ? row.change_percent.toFixed(2) : '-' }}%
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="跌幅榜" name="losers">
        <el-empty v-if="losers.length === 0" description="该日期暂无排行数据" />
        <el-table v-else :data="losers" border style="width: 100%">
          <el-table-column type="index" label="排名" width="60" />
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="price" label="价格" width="100">
            <template #default="{ row }">
              <span style="color: #22c55e">
                {{ row.price ? row.price.toFixed(2) : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="change_percent" label="涨跌幅" width="100">
            <template #default="{ row }">
              <span style="color: #22c55e">
                {{ row.change_percent ? row.change_percent.toFixed(2) : '-' }}%
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockAPI } from '../api/stock'

const activeTab = ref('gainers')
const gainers = ref([])
const losers = ref([])
const queryDate = ref('')
const priceDate = ref('')
const latestDate = ref('')

const loadTopStocks = async () => {
  try {
    const dateParam = queryDate.value || null
    const [gainersRes, losersRes] = await Promise.all([
      stockAPI.getTopGainers(20, dateParam),
      stockAPI.getTopLosers(20, dateParam)
    ])
    gainers.value = gainersRes.data
    losers.value = losersRes.data

    const firstDate = gainersRes.data[0]?.price_date || losersRes.data[0]?.price_date || ''
    priceDate.value = firstDate
    if (firstDate && !latestDate.value) {
      latestDate.value = firstDate
    }
  } catch (error) {
    console.error('加载涨跌排行失败:', error)
  }
}

const onDateChange = () => {
  loadTopStocks()
}

onMounted(async () => {
  await loadTopStocks()
  if (!queryDate.value && latestDate.value) {
    queryDate.value = latestDate.value
  }
})
</script>

<style scoped>
.top-stocks {
  max-width: 800px;
  margin: 0 auto;
}

.search-bar {
  margin-bottom: 12px;
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
</style>
