import axios from 'axios'

const BASE = '/api/strategy'

export function getStrategyConfig() {
  return axios.get(`${BASE}/config`)
}

export function updateStrategyConfig(data) {
  return axios.put(`${BASE}/config`, data)
}

export function getRecommendations() {
  return axios.get(`${BASE}/recommendations`)
}

export function getPositions(status) {
  return axios.get(`${BASE}/positions`, { params: { status } })
}

export function getTransactions(params) {
  return axios.get(`${BASE}/transactions`, { params })
}

export function getStats() {
  return axios.get(`${BASE}/stats`)
}

export function runStrategy(date) {
  return axios.post(`${BASE}/run`, { date })
}

export function executeRecommendation(data) {
  return axios.post(`${BASE}/execute`, data)
}

export function sellPosition(data) {
  return axios.post(`${BASE}/sell`, data)
}

export function runBacktest(data) {
  return axios.post(`${BASE}/backtest`, data)
}

export function clearBacktest() {
  return axios.post(`${BASE}/backtest/clear`)
}
