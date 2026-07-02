import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const stockAPI = {
  getStocks(params) {
    return api.get('/stocks', { params })
  },
  getStock(code) {
    return api.get(`/stocks/${code}`)
  },
  getStockDaily(code, days = 60) {
    return api.get(`/stocks/${code}/daily`, { params: { days } })
  },
  getStockChart(code, days = 60) {
    return api.get(`/stocks/${code}/chart`, { params: { days } })
  },
  getTopGainers(limit = 10) {
    return api.get('/stocks/top/gainers', { params: { limit } })
  },
  getTopLosers(limit = 10) {
    return api.get('/stocks/top/losers', { params: { limit } })
  },
  updateStockList() {
    return api.post('/crawler/update_list', {}, { timeout: 180000 })
  },
  updateRealtime(params = {}) {
    return api.post('/crawler/update_realtime', {
      force: params.force !== undefined ? params.force : true,
      date: params.date || null
    }, { timeout: 180000 })
  },
  fetchDaily(code) {
    return api.post(`/crawler/fetch_daily/${code}`)
  },
  fetchDailyBatch(params = {}) {
    return api.post('/crawler/fetch_daily_batch', params)
  },
  getDailyProgress() {
    return api.get('/crawler/progress/daily')
  }
}

export default api
