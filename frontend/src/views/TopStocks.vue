<template>
  <div class="top-stocks">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="涨幅榜" name="gainers">
        <el-table :data="gainers" border style="width: 100%">
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
        <el-table :data="losers" border style="width: 100%">
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

const loadTopStocks = async () => {
  try {
    const [gainersRes, losersRes] = await Promise.all([
      stockAPI.getTopGainers(20),
      stockAPI.getTopLosers(20)
    ])
    gainers.value = gainersRes.data
    losers.value = losersRes.data
  } catch (error) {
    console.error('加载涨跌排行失败:', error)
  }
}

onMounted(() => {
  loadTopStocks()
})
</script>

<style scoped>
.top-stocks {
  max-width: 800px;
  margin: 0 auto;
}
</style>
