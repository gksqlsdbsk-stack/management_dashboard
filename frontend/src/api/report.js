import { request } from './client'

const path = (year, month) => `/my-report/${year}/${month}/`

export function getMyReport(year, month) {
  return request(path(year, month))
}

// 임시 저장: 화면의 값 전체를 보내 저장된 값을 통째로 교체한다
export function saveMyReport(year, month, values) {
  return request(path(year, month), { method: 'PUT', body: { values } })
}

export function submitMyReport(year, month) {
  return request(`${path(year, month)}submit/`, { method: 'POST' })
}
