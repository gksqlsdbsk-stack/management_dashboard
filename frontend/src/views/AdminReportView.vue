<script setup>
import { computed, ref } from 'vue'
import { getMonthlyReport } from '../api/analytics'
import { errorAlert, noAlert } from '../utils/errors'
import { formatMoney, formatPercent } from '../utils/format'
import { SECTION_ROWS, SECTION_TITLES } from '../utils/sections'
import { cashChart, projectsChart } from '../utils/charts'
import ChartCanvas from '../components/ChartCanvas.vue'
import CsvDownloadButton from '../components/CsvDownloadButton.vue'
import DataStatusWarning from '../components/DataStatusWarning.vue'
import InlineAlert from '../components/InlineAlert.vue'
import MetricTable from '../components/MetricTable.vue'
import PeriodControls from '../components/PeriodControls.vue'
import ProjectTable from '../components/ProjectTable.vue'

// 표 중심 월별 리포트: 각 지표에 당월/누적 두 열을 병기하고 차트는 자금 수지 예측·프로젝트별 2개만 둔다 [04 §3.4]
const SECTIONS_AFTER_CASH = ['bep', 'production', 'orders', 'productivity']

const data = ref(null)
const period = ref(null) // 마지막으로 선택된 { year, month, horizon } (CSV 다운로드에 사용)
const alert = ref(noAlert())
const loading = ref(false)
let loadSeq = 0

async function load(selected) {
  period.value = selected
  const seq = ++loadSeq
  loading.value = true
  alert.value = noAlert()
  try {
    const result = await getMonthlyReport(selected)
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

function onDownloadError(error) {
  alert.value = errorAlert(error)
}

const blocks = (section) => [
  { label: '당월', data: data.value[section].month },
  { label: '누적', data: data.value[section].cumulative },
]
const hasCumulativeData = computed(() => data.value?.cost_profit.cumulative.revenue !== null)
const hasMonthData = computed(() => data.value?.cost_profit.month.revenue !== null)
const cash = computed(() => data.value?.cash_forecast)
const charts = computed(() =>
  data.value ? { projects: projectsChart(data.value.projects.cumulative), cash: cashChart(data.value.cash_forecast) } : null,
)
const goalValue = (goal, value) => (goal.unit === '%' ? formatPercent(value) : formatMoney(value))
</script>

<template>
  <h1 class="h4 mb-3">월별 리포트</h1>

  <PeriodControls @change="load">
    <CsvDownloadButton kind="monthly-report" :period="period" @error="onDownloadError" />
  </PeriodControls>
  <InlineAlert :alert="alert" />
  <p v-if="loading && !data" class="text-muted">불러오는 중...</p>

  <template v-if="data">
    <DataStatusWarning :status="data.data_status" />
    <div v-if="!hasCumulativeData" class="alert alert-secondary">
      {{ data.year }}년 1~{{ data.month }}월에 제출된 데이터가 없습니다. 모든 지표가 '-' 로 표시됩니다.
    </div>
    <div v-else-if="!hasMonthData" class="alert alert-secondary">
      {{ data.month }}월에 제출된 데이터가 없어 당월 값은 '-' 로 표시됩니다.
    </div>

    <!-- 종합 원가/이익률 -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.cost_profit }}</div>
      <div class="card-body">
        <MetricTable :rows="SECTION_ROWS.cost_profit" :blocks="blocks('cost_profit')" :base-month="data.month" />
      </div>
    </section>

    <!-- 프로젝트별 원가/이익률 (표 + 차트) -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.projects }}</div>
      <div class="card-body">
        <div class="row g-4">
          <div class="col-lg-6">
            <div class="small fw-semibold mb-1">당월</div>
            <ProjectTable :rows="data.projects.month" />
          </div>
          <div class="col-lg-6">
            <div class="small fw-semibold mb-1">누적</div>
            <ProjectTable :rows="data.projects.cumulative" />
          </div>
        </div>
        <div class="mt-4">
          <div class="small fw-semibold mb-1">누적 프로젝트별 매출·원가</div>
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
      <div class="card-body">
        <MetricTable :rows="SECTION_ROWS.trade" :blocks="blocks('trade')" :base-month="data.month" />
      </div>
    </section>

    <!-- 자금 수지 예측 (표 + 차트) -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.cash_forecast }} ({{ cash.horizon }}개월)</div>
      <div class="card-body">
        <div v-if="!cash.reference_months.length" class="alert alert-secondary">
          산출 불가 — 최근 3개월(기준 월 포함) 안에 제출된 데이터가 없습니다.
        </div>
        <p v-else class="small text-muted">
          기준 잔액 {{ formatMoney(cash.base_cash) }}원<template v-if="cash.base_cash !== null && cash.base_cash_as_of_month !== cash.base_month">
            ({{ cash.base_cash_as_of_month }}월 기준)</template>
          · 참조 기간 {{ cash.reference_months[0] }}~{{ cash.reference_months.at(-1) }}월 평균 (월 유입
          {{ formatMoney(cash.avg_inflow) }}원, 월 유출 {{ formatMoney(cash.avg_outflow) }}원)
          <template v-if="cash.base_cash === null"> — 현금 잔액 데이터가 없어 예상 잔액을 산출할 수 없습니다.</template>
        </p>
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

    <!-- BEP · 생산량·가동률 · 수주·파이프라인 · 인당 생산성 -->
    <section v-for="section in SECTIONS_AFTER_CASH" :key="section" class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES[section] }}</div>
      <div class="card-body">
        <MetricTable :rows="SECTION_ROWS[section]" :blocks="blocks(section)" :base-month="data.month" />
      </div>
    </section>

    <!-- 목표 대비 달성률 (실적은 누적 기준) -->
    <section class="card mb-4">
      <div class="card-header fw-semibold">{{ SECTION_TITLES.goals }} <span class="small text-muted">(실적은 누적 기준)</span></div>
      <div class="card-body">
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
      </div>
    </section>
  </template>
</template>
