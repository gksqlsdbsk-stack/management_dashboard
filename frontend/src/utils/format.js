// 표시 형식 [A-36]: 금액은 원 단위 정수에 천 단위 콤마, 비율은 소수 1자리(%), 수량은 정수 콤마.
// 값이 없으면(계산 불가 `null`) '-' 로 표시한다.
const isEmpty = (value) => value === null || value === undefined || value === ''

// 정수 반올림은 절반을 0에서 먼 쪽으로 올린다(CSV 다운로드와 같은 규칙 [A-51]). -0 은 0 으로 표시한다
const integer = (value) => {
  const number = Number(value)
  const rounded = Math.sign(number) * Math.round(Math.abs(number))
  return (rounded === 0 ? 0 : rounded).toLocaleString('ko-KR')
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

// 소수 1자리 수량(인당 생산량 등). 비율과 같은 방식(toFixed)으로 반올림해 CSV와 같은 값을 낸다 [A-51]
export function formatDecimal(value) {
  if (isEmpty(value)) return '-'
  const fixed = Number(value).toFixed(1)
  const negative = fixed.startsWith('-') && Number(fixed) !== 0 // -0.0 방지
  const [whole, fraction] = fixed.replace('-', '').split('.')
  return `${negative ? '-' : ''}${Number(whole).toLocaleString('ko-KR')}.${fraction}`
}

const FORMATTERS = { money: formatMoney, qty: formatQty, percent: formatPercent, decimal: formatDecimal }

export function formatByKind(kind, value) {
  return (FORMATTERS[kind] ?? formatNumber)(value)
}

export function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString('ko-KR') : '-'
}
