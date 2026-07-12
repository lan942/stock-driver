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

export function runBacktest(data) {
  return axios.post(`${BASE}/backtest`, data, { timeout: 300000 })
}

export function clearBacktest() {
  return axios.post(`${BASE}/backtest/clear`)
}
