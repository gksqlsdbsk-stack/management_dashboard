import { request } from './client'

export function listDepartments() {
  return request('/departments/')
}

export function createDepartment(data) {
  return request('/departments/', { method: 'POST', body: data })
}

export function updateDepartment(id, data) {
  return request(`/departments/${id}/`, { method: 'PATCH', body: data })
}

export function deleteDepartment(id) {
  return request(`/departments/${id}/`, { method: 'DELETE' })
}

export function listItems(departmentId) {
  return request(`/departments/${departmentId}/items/`)
}

export function createItem(departmentId, data) {
  return request(`/departments/${departmentId}/items/`, { method: 'POST', body: data })
}

export function updateItem(id, data) {
  return request(`/items/${id}/`, { method: 'PATCH', body: data })
}

export function deleteItem(id) {
  return request(`/items/${id}/`, { method: 'DELETE' })
}

export function listMetricKeys() {
  return request('/metric-keys/')
}
