// 표시 형식 [A-36]: 금액은 원 단위 정수에 천 단위 콤마, 비율은 소수 1자리(%), 수량은 정수 콤마.
// 값이 없으면(계산 불가 `null`) '-' 로 표시한다.
const isEmpty = (value) => value === null || value === undefined || value === ''

const integer = (value) => {
  const rounded = Math.round(Number(value))
  return (rounded === 0 ? 0 : rounded).toLocaleString('ko-KR') // -0 방지
}

export function formatNumber(value) {
  if (isEmpty(value)) return '-'
  return Number(value).toLocaleString('ko-KR', { maximumFractionDigits: 4 })
}

export function formatMoney(value) {
  return isEmpty(value) ? '-' : integer(value)
}

export function formatQty(value) {
  return isEmpty(value) ? '-' : integer(value)
}

export function formatPercent(value) {
  if (isEmpty(value)) return '-'
  const text = Number(value).toFixed(1)
  return `${text === '-0.0' ? '0.0' : text}%`
}

// 소수 1자리까지 보여주는 수량(인당 생산량 등)
export function formatDecimal(value) {
  return isEmpty(value) ? '-' : Number(value).toLocaleString('ko-KR', { maximumFractionDigits: 1 })
}

const FORMATTERS = { money: formatMoney, qty: formatQty, percent: formatPercent, decimal: formatDecimal }

export function formatByKind(kind, value) {
  return (FORMATTERS[kind] ?? formatNumber)(value)
}

export function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString('ko-KR') : '-'
}
