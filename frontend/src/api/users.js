import { request } from './client'

export function listUsers() {
  return request('/users/')
}

export function createUser(data) {
  return request('/users/', { method: 'POST', body: data })
}

export function updateUser(id, data) {
  return request(`/users/${id}/`, { method: 'PATCH', body: data })
}

export function deleteUser(id) {
  return request(`/users/${id}/`, { method: 'DELETE' })
}
