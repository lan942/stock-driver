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
    return api.post('/crawler/update_list')
  },
  updateRealtime() {
    return api.post('/crawler/update_realtime')
  },
  fetchDaily(code) {
    return api.post(`/crawler/fetch_daily/${code}`)
  }
}

export default api
