import { request } from './client'

export function getGoals(year) {
  return request(`/goals/?year=${year}`)
}

// 목표 일괄 저장. target_value 가 null 이면 해당 지표 목표를 삭제한다
export function saveGoals(year, goals) {
  return request(`/goals/${year}/`, { method: 'PUT', body: { goals } })
}
