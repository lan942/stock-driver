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
  getTopGainers(limit = 10, date = null) {
    const params = { limit }
    if (date) params.date = date
    return api.get('/stocks/top/gainers', { params })
  },
  getTopLosers(limit = 10, date = null) {
    const params = { limit }
    if (date) params.date = date
    return api.get('/stocks/top/losers', { params })
  },
  updateStockList() {
    return api.post('/crawler/update_list', {}, { timeout: 180000 })
  },
  fetchDailyBatch(params = {}) {
    return api.post('/crawler/fetch_daily_batch', params)
  },
  getDailyProgress() {
    return api.get('/crawler/progress/daily')
  },
  getDailySummary(params = {}) {
    return api.get('/stocks/daily_summary', { params })
  }
}

export default api
