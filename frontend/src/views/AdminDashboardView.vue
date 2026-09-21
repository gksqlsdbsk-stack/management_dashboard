<script setup>
import { computed, ref } from 'vue'
import { getDashboard } from '../api/analytics'
import { errorAlert, noAlert } from '../utils/errors'
import { formatMoney, formatPercent } from '../utils/format'
import { SECTION_ROWS, SECTION_TITLES } from '../utils/sections'
import {
  cashChart, costProfitChart, goalsChart, ordersChart, productionChart, productivityChart, projectsChart, tradeChart,
} from '../utils/charts'
import ChartCanvas from '../components/ChartCanvas.vue'
import DataStatusWarning from '../components/DataStatusWarning.vue'
import InlineAlert from '../components/InlineAlert.vue'
import KpiCard from '../components/KpiCard.vue'
import MetricTable from '../components/MetricTable.vue'
import PeriodControls from '../components/PeriodControls.vue'
import ProjectTable from '../components/ProjectTable.vue'

const data = ref(null)
const alert = ref(noAlert())
const loading = ref(false)
let loadSeq = 0

async function load(period) {
  const seq = ++loadSeq
  loading.value = true
  alert.value = noAlert()
  try {
    const result = await getDashboard(period)
    if (seq === loadSeq) data.value = result
  } catch (error) {
    if (seq === loadSeq) {
      data.value = null
      alert.value = errorAlert(error)
    }
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// 차트 설정은 데이터가 바뀔 때만 다시 만든다(화면이 다시 그려질 때마다 차트가 재생성되지 않도록)
const charts = computed(() => {
  const d = data.value
  if (!d) return null
  return {
    costProfit: costProfitChart(d.cost_profit.trend),
    projects: projectsChart(d.projects.cumulative),
    trade: tradeChart(d.trade.trend),
    cash: cashChart(d.cash_forecast),
    production: productionChart(d.production.trend),
    orders: ordersChart(d.orders.trend),
    productivity: productivityChart(d.productivity.trend),
    goals: goalsChart(d.goals),
  }
})

const cumulative = (section) => (data.value ? [{ label: '누적', data: data.value[section].cumulative }] : [])
const hasData = computed(() => data.value?.cost_profit.cumulative.revenue !== null)
const bepRate = computed(() => data.value?.bep.cumulative.bep_achievement_rate ?? null)
const cash = computed(() => data.value?.cash_forecast)
const cashSummary = computed(() => {
  const c = cash.value
  const range = c.reference_months.length ? `${c.reference_months[0]}~${c.reference_months.at(-1)}월` : ''
  const base =
    c.base_cash === null
      ? '현금 잔액 데이터가 없어 예상 잔액을 산출할 수 없습니다.'
      : `기준 잔액 ${formatMoney(c.base_cash)}원${c.base_cash_as_of_month !== c.base_month ? ` (${c.base_cash_as_of_month}월 기준)` : ''}`
  return c.reference_months.length
    ? `${base} · 참조 기간 ${range} 평균 (월 유입 ${formatMoney(c.avg_inflow)}원, 월 유출 ${formatMoney(c.avg_outflow)}원)`
    : ''
})
const goalValue = (goal, value) => (goal.unit === '%' ? formatPercent(value) : formatMoney(value))
</script>

<template>
  <h1 class="h4 mb-3">누적 대시보드</h1>

  <PeriodControls @change="load" />
  <InlineAlert :alert="alert" />
  <p v-if="loading && !data" class="text-muted">불러오는 중...</p>

  <template v-if="data">
    <DataStatusWarning :status="data.data_status" />
    <div v-if="!hasData" class="alert alert-secondary">
      {{ data.year }}년 1~{{ data.month }}월에 제출된 데이터가 없습니다. 모든 지표가 '-' 로 표시됩니다.
    </div>

    <!-- KPI 요약 -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="누적 매출액" :value="`${formatMoney(data.cost_profit.cumulative.revenue)}원`" />
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="영업이익" :value="`${formatMoney(data.cost_profit.cumulative.operating_profit)}원`" />
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="영업이익률" :value="formatPercent(data.cost_profit.cumulative.operating_margin)" />
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="가동률" :value="formatPercent(data.production.cumulative.utilization_rate)" />
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="BEP 달성률" :value="formatPercent(bepRate)" />
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <KpiCard label="인당 매출액" :value="`${formatMoney(data.productivity.cumulative.revenue_per_head)}원`" />
      </div>
    </div>

    <!-- 종합 원가/이익률 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.cost_profit }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.cost_profit" :blocks="cumulative('cost_profit')" :base-month="data.month" />
        </div>
        <div class="col-lg-7"><ChartCanvas :config="charts.costProfit" /></div>
      </div>
    </section>

    <!-- 프로젝트별 원가/이익률 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.projects }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-6"><ProjectTable :rows="data.projects.cumulative" /></div>
        <div class="col-lg-6">
          <ChartCanvas
            :config="charts.projects"
            :height="`${Math.max(200, data.projects.cumulative.length * 48 + 90)}px`"
          />
        </div>
      </div>
    </section>

    <!-- 매입·매출·미수금 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.trade }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.trade" :blocks="cumulative('trade')" :base-month="data.month" />
        </div>
        <div class="col-lg-7"><ChartCanvas :config="charts.trade" /></div>
      </div>
    </section>

    <!-- 자금 수지 예측 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.cash_forecast }} ({{ cash.horizon }}개월)</div>
      <div class="card-body">
        <div v-if="!cash.reference_months.length" class="alert alert-secondary">
          산출 불가 — 최근 3개월(기준 월 포함) 안에 제출된 데이터가 없습니다.
        </div>
        <p v-else class="small text-muted">{{ cashSummary }}</p>
        <div class="row g-4">
          <div class="col-lg-6">
            <table class="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th>예측 월</th>
                  <th class="text-end">예상 유입</th>
                  <th class="text-end">예상 유출</th>
                  <th class="text-end">순현금흐름</th>
                  <th class="text-end">예상 잔액</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in cash.forecast" :key="`${row.year}-${row.month}`" :class="{ 'table-danger': row.shortfall }">
                  <td class="text-nowrap">
                    {{ row.year }}.{{ row.month }}
                    <span v-if="row.shortfall" class="badge bg-danger">자금 부족 예상</span>
                  </td>
                  <td class="text-end">{{ formatMoney(row.inflow) }}</td>
                  <td class="text-end">{{ formatMoney(row.outflow) }}</td>
                  <td class="text-end">{{ formatMoney(row.net_cash_flow) }}</td>
                  <td class="text-end">{{ formatMoney(row.projected_cash) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="col-lg-6"><ChartCanvas :config="charts.cash" /></div>
        </div>
      </div>
    </section>

    <!-- BEP -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.bep }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.bep" :blocks="cumulative('bep')" :base-month="data.month" />
        </div>
        <div class="col-lg-7">
          <template v-if="bepRate !== null">
            <div class="small mb-1">
              현재 매출 {{ formatMoney(data.cost_profit.cumulative.revenue) }}원 / BEP 매출액
              {{ formatMoney(data.bep.cumulative.bep_revenue) }}원
            </div>
            <div class="progress" style="height: 1.5rem">
              <div
                class="progress-bar"
                :class="bepRate >= 100 ? 'bg-success' : 'bg-warning text-dark'"
                role="progressbar"
                :style="{ width: `${Math.min(bepRate, 100)}%` }"
                :aria-valuenow="bepRate"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                {{ formatPercent(bepRate) }}
              </div>
            </div>
            <div class="small text-muted mt-1">100% 이상이면 손익분기점을 넘었습니다.</div>
          </template>
          <div v-else class="alert alert-secondary mb-0">
            산출 불가 — 매출이 없거나 공헌이익률이 0 이하이면 BEP를 계산할 수 없습니다.
          </div>
        </div>
      </div>
    </section>

    <!-- 생산량·가동률 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.production }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.production" :blocks="cumulative('production')" :base-month="data.month" />
        </div>
        <div class="col-lg-7"><ChartCanvas :config="charts.production" /></div>
      </div>
    </section>

    <!-- 수주 잔고·영업 파이프라인 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.orders }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.orders" :blocks="cumulative('orders')" :base-month="data.month" />
        </div>
        <div class="col-lg-7"><ChartCanvas :config="charts.orders" /></div>
      </div>
    </section>

    <!-- 인당 생산성 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.productivity }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-5">
          <MetricTable :rows="SECTION_ROWS.productivity" :blocks="cumulative('productivity')" :base-month="data.month" />
        </div>
        <div class="col-lg-7"><ChartCanvas :config="charts.productivity" /></div>
      </div>
    </section>

    <!-- 목표 대비 달성률 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.goals }}</div>
      <div class="card-body row g-4">
        <div class="col-lg-6">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th>지표</th>
                <th class="text-end">목표</th>
                <th class="text-end">실적(누적)</th>
                <th class="text-end">달성률</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="goal in data.goals" :key="goal.metric_key">
                <td>{{ goal.label }} <span class="small text-muted">({{ goal.unit }})</span></td>
                <td class="text-end" :class="{ 'text-muted': goal.target === null }">
                  {{ goal.target === null ? '목표 미설정' : goalValue(goal, goal.target) }}
                </td>
                <td class="text-end">{{ goalValue(goal, goal.actual) }}</td>
                <td class="text-end">{{ formatPercent(goal.achievement_rate) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="small text-muted mt-2 mb-0">목표는 '연간 목표' 메뉴에서 설정합니다.</p>
        </div>
        <div class="col-lg-6"><ChartCanvas :config="charts.goals" height="240px" /></div>
      </div>
    </section>
  </template>
</template>
