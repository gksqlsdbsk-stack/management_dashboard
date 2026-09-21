import { download, request } from './client'

const query = ({ year, month, horizon }) => `?year=${year}&month=${month}&horizon=${horizon}`

// 누적 대시보드: 각 섹션 cumulative + trend
export function getDashboard(period) {
  return request(`/dashboard/${query(period)}`)
}

// 월별 리포트: 각 섹션 month(당월) + cumulative
export function getMonthlyReport(period) {
  return request(`/monthly-report/${query(period)}`)
}

// CSV 다운로드. kind: 'dashboard' | 'monthly-report'. { blob, filename } 을 돌려준다
export function downloadCsv(kind, period) {
  return download(`/${kind}/export/${query(period)}`)
}
