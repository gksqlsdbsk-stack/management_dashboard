import { request } from './client'

export function login(name, employeeNo, password) {
  return request('/auth/login/', {
    method: 'POST',
    body: { name, employee_no: employeeNo, password },
  })
}

export function logout() {
  return request('/auth/logout/', { method: 'POST' })
}

export function fetchMe() {
  return request('/auth/me/')
}
