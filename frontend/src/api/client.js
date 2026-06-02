import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

function rangeParams(days, startDate) {
  return { days, ...(startDate ? { start_date: startDate } : {}) }
}

export const fetchDashboard = (date) =>
  api.get('/dashboard', { params: date ? { date } : {} }).then((r) => r.data)

export const fetchTrends = (days = 7, startDate = null) =>
  api.get('/trends', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchRecoveryTimeline = (days = 30, startDate = null) =>
  api.get('/recovery-timeline', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchTrainingLoad = (days = 30, startDate = null) =>
  api.get('/training-load', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchActivities = (days = 14, startDate = null) =>
  api.get('/activities', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchCyclingStats = (days = 60, startDate = null) =>
  api.get('/cycling-stats', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchPowerCurveBest = (days = 90, startDate = null) =>
  api.get('/power-curve-best', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchWhoopGarminCorrelation = (days = 60, startDate = null) =>
  api.get('/whoop-garmin-correlation', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchStrainRecoveryCorrelation = (days = 60, startDate = null) =>
  api.get('/strain-recovery-correlation', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchRecoveryPrediction = (date) =>
  api.get('/recovery-prediction', { params: date ? { date } : {} }).then((r) => r.data)

export const fetchGymSessions = (days = 60, startDate = null) =>
  api.get('/gym-sessions', { params: rangeParams(days, startDate) }).then((r) => r.data)

export const fetchInsights = (date) =>
  api.get('/insights', { params: date ? { date } : {}, timeout: 120000 }).then((r) => r.data)

export const triggerSync = () =>
  axios.post('/api/sync').then((r) => r.data)

export const triggerBackfill = (days = 90) =>
  axios.post('/api/backfill', null, { params: { days } }).then((r) => r.data)

export const triggerBackfillFromDate = (startDate) =>
  axios.post('/api/backfill', null, { params: { start_date: startDate } }).then((r) => r.data)

export const fetchBackfillStatus = () =>
  axios.get('/api/backfill/status').then((r) => r.data)

export const fetchWhoopStatus = () =>
  axios.get('/whoop/status').then((r) => r.data)

export default api
