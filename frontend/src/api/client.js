import { session, clearSession } from '../auth'

const BASE_URL = '/api'

let onUnauthorized = () => {}

// 401 응답 시 실행할 동작(로그인 화면 이동)을 등록한다
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

// 서버 오류 응답 {code, detail, errors} 를 담는 오류
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || '요청을 처리하지 못했습니다.')
    this.status = status
    this.code = body?.code
    this.errors = body?.errors
  }
}

export async function request(path, { method = 'GET', body } = {}) {
  const headers = {}
  if (session.token) headers.Authorization = `Token ${session.token}`

  let payload
  if (body instanceof FormData) {
    payload = body // Content-Type(boundary)은 브라우저가 지정한다
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(BASE_URL + path, { method, headers, body: payload })
  } catch {
    throw new ApiError(0, { detail: '서버에 연결할 수 없습니다.' })
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401) {
      clearSession()
      onUnauthorized()
    }
    throw new ApiError(response.status, data)
  }
  return data
}
