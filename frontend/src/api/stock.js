import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const stockAPI = {
  getStocks(params) {
    return api.get('/stocks', { params })
  },
  searchStocks(query) {
    return api.get('/stocks/search', { params: { q: query } })
  },
  getStock(code) {
    return api.get(`/stocks/${code}`)
  },
  getStockIndicators(code, days = 120, indicators = '', params = '') {
    const queryParams = { days }
    if (indicators) queryParams.indicators = indicators
    if (params) queryParams.params = params
    return api.get(`/stocks/${code}/indicators`, { params: queryParams })
  },
  getStockTransactions(code) {
    return api.get(`/stocks/${code}/transactions`)
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
  },
  getPortfolioOverview() {
    return api.get('/portfolio/overview')
  },
  getHoldings() {
    return api.get('/portfolio/holdings')
  },
  addHolding(data) {
    return api.post('/portfolio/holdings', data)
  },
  updateHolding(id, data) {
    return api.put(`/portfolio/holdings/${id}`, data)
  },
  deleteHolding(id) {
    return api.delete(`/portfolio/holdings/${id}`)
  },
  getTransactions(limit = 50) {
    return api.get('/portfolio/transactions', { params: { limit } })
  },
  addTransaction(data) {
    return api.post('/portfolio/transactions', data)
  },
  clearTransactions() {
    return api.delete('/portfolio/transactions')
  },
  updateCashBalance(amount) {
    return api.post('/portfolio/cash', { amount })
  },
  getBacktestOverview() {
    return api.get('/backtest/overview')
  },
  getBacktestHoldings() {
    return api.get('/backtest/holdings')
  },
  addBacktestHolding(data) {
    return api.post('/backtest/holdings', data)
  },
  updateBacktestHolding(id, data) {
    return api.put(`/backtest/holdings/${id}`, data)
  },
  deleteBacktestHolding(id) {
    return api.delete(`/backtest/holdings/${id}`)
  },
  getBacktestTransactions(limit = 50) {
    return api.get('/backtest/transactions', { params: { limit } })
  },
  addBacktestTransaction(data) {
    return api.post('/backtest/transactions', data)
  },
  clearBacktestTransactions() {
    return api.delete('/backtest/transactions')
  },
  updateBacktestCash(amount) {
    return api.post('/backtest/cash', { amount })
  }
}

export default api
