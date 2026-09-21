import { session, clearSession } from '../auth'

// 개발은 Vite 프록시(/api)를 쓴다. 운영(Render)은 API 서버가 다른 주소이므로 빌드 시 VITE_API_BASE_URL 로 지정한다 [A-39, A-52]
const BASE_URL = `${(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')}/api`

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

// 파일 다운로드(CSV): 인증 헤더가 필요해 fetch 로 받아 Blob 으로 돌려준다 [03 §8.5].
// 오류는 JSON 본문이므로 request 와 같은 ApiError 로 던진다.
export async function download(path) {
  const headers = session.token ? { Authorization: `Token ${session.token}` } : {}
  let response
  try {
    response = await fetch(BASE_URL + path, { headers })
  } catch {
    throw new ApiError(0, { detail: '서버에 연결할 수 없습니다.' })
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    if (response.status === 401) {
      clearSession()
      onUnauthorized()
    }
    throw new ApiError(response.status, data)
  }
  const filename = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')?.[1] ?? 'download.csv'
  return { blob: await response.blob(), filename }
}
