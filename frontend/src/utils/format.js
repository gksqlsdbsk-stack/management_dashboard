// 표시 형식 [A-36]: 천 단위 콤마, 값이 없으면 '-'
export function formatNumber(value) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toLocaleString('ko-KR', { maximumFractionDigits: 4 })
}

export function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString('ko-KR') : '-'
}
