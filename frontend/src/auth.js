import { reactive } from 'vue'

const TOKEN_KEY = 'token'

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // 저장소를 쓸 수 없어도 메모리 상태로 동작한다
  }
}

// 로그인 상태. 토큰은 localStorage에 보관한다 [A-12]
export const session = reactive({ token: readToken(), user: null })

export function setSession(token, user) {
  session.token = token
  session.user = user
  writeToken(token)
}

export function clearSession() {
  session.token = null
  session.user = null
  writeToken(null)
}

// 역할별 홈 화면 [04 §1]
export function homePathFor(user) {
  return user.role === 'ADMIN' ? '/admin/dashboard' : '/entry'
}
