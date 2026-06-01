import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const fetchDashboard = (date) =>
  api.get('/dashboard', { params: date ? { date } : {} }).then((r) => r.data)

export const fetchTrends = (days = 7) =>
  api.get('/trends', { params: { days } }).then((r) => r.data)

export const fetchRecoveryTimeline = (days = 30) =>
  api.get('/recovery-timeline', { params: { days } }).then((r) => r.data)

export const fetchTrainingLoad = (days = 30) =>
  api.get('/training-load', { params: { days } }).then((r) => r.data)

export const fetchActivities = (days = 14) =>
  api.get('/activities', { params: { days } }).then((r) => r.data)

export const fetchCyclingStats = (days = 60) =>
  api.get('/cycling-stats', { params: { days } }).then((r) => r.data)

export const fetchPowerCurveBest = (days = 90) =>
  api.get('/power-curve-best', { params: { days } }).then((r) => r.data)

export const fetchWhoopGarminCorrelation = (days = 60) =>
  api.get('/whoop-garmin-correlation', { params: { days } }).then((r) => r.data)

export const fetchStrainRecoveryCorrelation = (days = 60) =>
  api.get('/strain-recovery-correlation', { params: { days } }).then((r) => r.data)

export const fetchGymSessions = (days = 60) =>
  api.get('/gym-sessions', { params: { days } }).then((r) => r.data)

export const fetchStravaStatus = () =>
  axios.get('/strava/status').then((r) => r.data)

export const fetchInsights = (date) =>
  api.get('/insights', { params: date ? { date } : {}, timeout: 120000 }).then((r) => r.data)

export const triggerSync = () =>
  axios.post('/api/sync').then((r) => r.data)

export const triggerBackfill = (days = 90) =>
  axios.post('/api/backfill', null, { params: { days } }).then((r) => r.data)

export const fetchWhoopStatus = () =>
  axios.get('/whoop/status').then((r) => r.data)

export default api
