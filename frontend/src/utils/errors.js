// 서버 오류를 화면 알림용 {type, message, details} 로 바꾼다.
// `labels`: 필드 이름 → 화면에 보일 한글 이름 (없으면 필드 이름 그대로)
export function errorAlert(error, labels = {}) {
  const details = []
  for (const [field, messages] of Object.entries(error.errors ?? {})) {
    if (Array.isArray(messages)) details.push(`${labels[field] ?? field}: ${messages.join(' ')}`)
  }
  return { type: 'danger', message: error.message || '요청을 처리하지 못했습니다.', details }
}

export function successAlert(message) {
  return { type: 'success', message, details: [] }
}

export const noAlert = () => ({ type: 'info', message: '', details: [] })
