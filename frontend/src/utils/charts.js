// Chart.js 설정 생성 함수 모음 (Chart.js를 직접 사용, 래퍼 라이브러리 없음) [04 §3.3, A-38].
// 색상은 Bootstrap 기본 색상 계열로 통일한다. 값이 null 인 점은 비워 둔다.
import { formatByKind, formatMoney, formatPercent, formatQty } from './format'

const COLORS = {
  primary: '#0d6efd',
  success: '#198754',
  danger: '#dc3545',
  warning: '#ffc107',
  info: '#0dcaf0',
  secondary: '#6c757d',
}

const monthLabels = (points) => points.map((point) => `${point.month}월`)
const series = (points, key) => points.map((point) => point[key] ?? null)

// 툴팁: dataset 의 kind(money|qty|percent)에 맞게 값을 표시한다
function tooltipLabel(context) {
  const value = context.chart.options.indexAxis === 'y' ? context.parsed.x : context.parsed.y
  return `${context.dataset.label}: ${formatByKind(context.dataset.kind, value)}`
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: tooltipLabel } } },
    ...extra,
  }
}

const moneyAxis = (position = 'left', extra = {}) => ({
  position,
  ticks: { callback: (value) => formatMoney(value) },
  ...extra,
})
const percentAxis = (extra = {}) => ({
  position: 'right',
  grid: { drawOnChartArea: false },
  ticks: { callback: (value) => `${value}%` },
  ...extra,
})

const bar = (label, data, color, kind = 'money', extra = {}) => ({
  type: 'bar', label, data, kind, backgroundColor: color, ...extra,
})
const line = (label, data, color, kind, extra = {}) => ({
  type: 'line', label, data, kind, borderColor: color, backgroundColor: color, tension: 0.2, spanGaps: false, ...extra,
})

// 월별 매출/영업이익(막대) + 영업이익률(선)
export function costProfitChart(trend) {
  return {
    type: 'bar',
    data: {
      labels: monthLabels(trend),
      datasets: [
        bar('매출액', series(trend, 'revenue'), COLORS.primary, 'money', { yAxisID: 'y' }),
        bar('영업이익', series(trend, 'operating_profit'), COLORS.success, 'money', { yAxisID: 'y' }),
        line('영업이익률', series(trend, 'operating_margin'), COLORS.warning, 'percent', { yAxisID: 'y1' }),
      ],
    },
    options: baseOptions({ scales: { y: moneyAxis(), y1: percentAxis() } }),
  }
}

// 프로젝트별 매출·원가(가로 막대)
export function projectsChart(rows) {
  return {
    type: 'bar',
    data: {
      labels: rows.map((row) => row.project_name),
      datasets: [
        bar('매출액', rows.map((row) => row.revenue), COLORS.primary),
        bar('총원가', rows.map((row) => row.total_cost), COLORS.secondary),
      ],
    },
    options: baseOptions({ indexAxis: 'y', scales: { x: moneyAxis('bottom') } }),
  }
}

// 월별 매출·매입(막대) + 미수금 잔액(선)
export function tradeChart(trend) {
  return {
    type: 'bar',
    data: {
      labels: monthLabels(trend),
      datasets: [
        bar('매출액', series(trend, 'revenue'), COLORS.primary),
        bar('매입액', series(trend, 'purchase_amount'), COLORS.secondary),
        line('미수금 잔액', series(trend, 'receivable_balance'), COLORS.danger, 'money'),
      ],
    },
    options: baseOptions({ scales: { y: moneyAxis() } }),
  }
}

// 실적 + 예측 현금 잔액(선). 예측선은 기준 월 잔액에서 이어 그리고, 자금 부족 예상 월은 빨갛게 표시한다
export function cashChart(cash) {
  const history = cash.history
  const forecast = cash.forecast
  const labels = [...history.map((point) => `${point.month}월`), ...forecast.map((row) => `${row.month}월(예측)`)]
  const actual = [...history.map((point) => point.cash_balance ?? null), ...forecast.map(() => null)]
  const projected = [...history.map(() => null), ...forecast.map((row) => row.projected_cash ?? null)]
  if (cash.base_cash !== null && history.length) projected[history.length - 1] = cash.base_cash
  const projectedColors = projected.map((value) => (value !== null && value < 0 ? COLORS.danger : COLORS.info))
  return {
    type: 'line',
    data: {
      labels,
      datasets: [
        line('현금 잔액(실적)', actual, COLORS.primary, 'money'),
        line('예상 잔액', projected, COLORS.info, 'money', {
          borderDash: [6, 4],
          pointBackgroundColor: projectedColors,
          pointBorderColor: projectedColors,
        }),
      ],
    },
    options: baseOptions({ scales: { y: moneyAxis() } }),
  }
}

// 월별 생산량(막대) + 가동률(선)
export function productionChart(trend) {
  return {
    type: 'bar',
    data: {
      labels: monthLabels(trend),
      datasets: [
        bar('생산량', series(trend, 'production_qty'), COLORS.primary, 'qty', { yAxisID: 'y' }),
        line('가동률', series(trend, 'utilization_rate'), COLORS.warning, 'percent', { yAxisID: 'y1' }),
      ],
    },
    options: baseOptions({
      scales: { y: { position: 'left', ticks: { callback: (value) => formatQty(value) } }, y1: percentAxis() },
    }),
  }
}

// 월별 수주 잔고(선)
export function ordersChart(trend) {
  return {
    type: 'line',
    data: { labels: monthLabels(trend), datasets: [line('수주 잔고', series(trend, 'order_backlog'), COLORS.primary, 'money')] },
    options: baseOptions({ scales: { y: moneyAxis() } }),
  }
}

// 월별 인당 매출(선)
export function productivityChart(trend) {
  return {
    type: 'line',
    data: {
      labels: monthLabels(trend),
      datasets: [line('인당 매출액', series(trend, 'revenue_per_head'), COLORS.success, 'money')],
    },
    options: baseOptions({ scales: { y: moneyAxis() } }),
  }
}

// 100% 기준선을 세로선으로 그리는 인라인 플러그인
const referenceLine100 = {
  id: 'referenceLine100',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart
    if (!scales.x) return
    const x = scales.x.getPixelForValue(100)
    if (x < chartArea.left || x > chartArea.right) return
    ctx.save()
    ctx.strokeStyle = COLORS.danger
    ctx.setLineDash([5, 4])
    ctx.beginPath()
    ctx.moveTo(x, chartArea.top)
    ctx.lineTo(x, chartArea.bottom)
    ctx.stroke()
    ctx.restore()
  },
}

// 목표 달성률(가로 막대, 100% 기준선). 목표 미설정·계산 불가는 막대를 그리지 않는다
export function goalsChart(goals) {
  return {
    type: 'bar',
    data: {
      labels: goals.map((goal) => goal.label),
      datasets: [
        bar('달성률', goals.map((goal) => goal.achievement_rate ?? null), COLORS.success, 'percent', {
          backgroundColor: goals.map((goal) => ((goal.achievement_rate ?? 0) >= 100 ? COLORS.success : COLORS.warning)),
        }),
      ],
    },
    options: baseOptions({
      indexAxis: 'y',
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: tooltipLabel } } },
      scales: { x: { min: 0, ticks: { callback: (value) => formatPercent(value) } } },
    }),
    plugins: [referenceLine100],
  }
}
