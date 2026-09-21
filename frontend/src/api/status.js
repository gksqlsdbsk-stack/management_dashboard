import { request } from './client'

export function getStatus(year, month) {
  return request(`/status/?year=${year}&month=${month}`)
}

export function getStatusMatrix(year) {
  return request(`/status/matrix/?year=${year}`)
}

// 부서 입력값 조회(읽기 전용). 응답은 직원 화면의 GET /my-report/ 와 같은 형태
export function getDepartmentReport(departmentId, year, month) {
  return request(`/departments/${departmentId}/report/${year}/${month}/`)
}

// (임시) 제출된 보고서를 초안으로 되돌린다 [A-19]
export function reopenDepartmentReport(departmentId, year, month) {
  return request(`/departments/${departmentId}/report/${year}/${month}/reopen/`, { method: 'POST' })
}
