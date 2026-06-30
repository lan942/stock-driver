import { createRouter, createWebHistory } from 'vue-router'
import StockList from '../views/StockList.vue'
import StockDetail from '../views/StockDetail.vue'
import TopStocks from '../views/TopStocks.vue'
import Crawler from '../views/Crawler.vue'

const routes = [
  {
    path: '/',
    name: 'StockList',
    component: StockList
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: StockDetail
  },
  {
    path: '/top',
    name: 'TopStocks',
    component: TopStocks
  },
  {
    path: '/crawler',
    name: 'Crawler',
    component: Crawler
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
