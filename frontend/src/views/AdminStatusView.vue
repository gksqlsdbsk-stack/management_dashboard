<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getStatus, getStatusMatrix, getDepartmentReport, reopenDepartmentReport } from '../api/status'
import { errorAlert, successAlert, noAlert } from '../utils/errors'
import { formatDateTime } from '../utils/format'
import InlineAlert from '../components/InlineAlert.vue'
import ProgressBar from '../components/ProgressBar.vue'
import ReportReadonly from '../components/ReportReadonly.vue'
import StatusBadge from '../components/StatusBadge.vue'

const MATRIX_LABELS = { NOT_STARTED: '-', DRAFT: '작성 중', SUBMITTED: '제출' }
const MATRIX_CLASSES = { NOT_STARTED: '', DRAFT: 'table-warning', SUBMITTED: 'table-success' }

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1

const year = ref(currentYear)
const month = ref(currentMonth) // 조회 가능 범위는 현재 월까지로 안내한다 [A-49]
const tab = ref('summary') // 'summary' | 'detail'
const summary = ref(null)
const matrix = ref(null)
const detail = ref(null) // { departmentId, name, report }
const alert = ref(noAlert())
const busy = ref(false)
let loadSeq = 0

const monthOptions = computed(() =>
  Array.from({ length: year.value === currentYear ? currentMonth : 12 }, (_, i) => i + 1),
)
const isFuture = (m) => year.value > currentYear || (year.value === currentYear && m > currentMonth)

async function loadSummary() {
  const seq = ++loadSeq
  try {
    const [status, matrixData] = await Promise.all([getStatus(year.value, month.value), getStatusMatrix(year.value)])
    if (seq === loadSeq) {
      summary.value = status
      matrix.value = matrixData
    }
  } catch (error) {
    if (seq === loadSeq) alert.value = errorAlert(error)
  }
}

async function loadDetail(departmentId, name) {
  try {
    const report = await getDepartmentReport(departmentId, year.value, month.value)
    detail.value = { departmentId, name, report }
  } catch (error) {
    alert.value = errorAlert(error)
  }
}

async function openDetail(row) {
  alert.value = noAlert()
  await loadDetail(row.department_id, row.name)
  if (detail.value) tab.value = 'detail'
}

async function reopen() {
  const { departmentId, name } = detail.value
  if (!confirm(`'${name}' ${year.value}년 ${month.value}월 보고서를 초안으로 되돌리시겠습니까?\n직원이 다시 수정하고 제출할 수 있게 됩니다.`)) return
  busy.value = true
  alert.value = noAlert()
  try {
    detail.value = { departmentId, name, report: await reopenDepartmentReport(departmentId, year.value, month.value) }
    alert.value = successAlert('초안으로 되돌렸습니다.')
  } catch (error) {
    alert.value = errorAlert(error)
    await loadDetail(departmentId, name) // 상태가 바뀌었을 수 있어 최신 값을 다시 불러온다
  } finally {
    busy.value = false
  }
  await loadSummary()
}

// 연·월이 바뀌면 다시 불러온다. 미래 월은 고를 수 없도록 보정한다.
watch([year, month], async () => {
  if (!Number.isInteger(year.value) || year.value < 1) return
  if (year.value > currentYear) {
    year.value = currentYear
    return
  }
  const lastMonth = year.value === currentYear ? currentMonth : 12
  if (month.value > lastMonth) {
    month.value = lastMonth
    return
  }
  alert.value = noAlert()
  await loadSummary()
  if (detail.value) await loadDetail(detail.value.departmentId, detail.value.name)
})

onMounted(loadSummary)
</script>

<template>
  <h1 class="h4 mb-3">입력 현황</h1>

  <div class="card card-body mb-3">
    <div class="row g-3 align-items-end">
      <div class="col-auto">
        <label for="status-year" class="form-label mb-1">연도</label>
        <input id="status-year" v-model.number="year" type="number" :max="currentYear" min="1" class="form-control" style="width: 7rem" />
      </div>
      <div class="col-auto">
        <label for="status-month" class="form-label mb-1">월</label>
        <select id="status-month" v-model.number="month" class="form-select">
          <option v-for="m in monthOptions" :key="m" :value="m">{{ m }}월</option>
        </select>
      </div>
    </div>
  </div>

  <InlineAlert :alert="alert" />

  <ul class="nav nav-tabs mb-3">
    <li class="nav-item">
      <a href="#" class="nav-link" :class="{ active: tab === 'summary' }" @click.prevent="tab = 'summary'">요약</a>
    </li>
    <li v-if="detail" class="nav-item">
      <a href="#" class="nav-link" :class="{ active: tab === 'detail' }" @click.prevent="tab = 'detail'">
        상세: {{ detail.name }}
      </a>
    </li>
  </ul>

  <!-- 요약 탭 -->
  <div v-if="tab === 'summary' && summary">
    <div class="mb-3">
      <ProgressBar
        :percent="summary.submitted_percent"
        :label="`제출 ${summary.submitted_count}/${summary.total_departments} 부서 (${summary.submitted_percent}%)`"
      />
    </div>

    <div v-if="summary.unsubmitted.length" class="alert alert-warning">
      <strong>미제출 부서</strong>
      <ul class="mb-0 mt-1">
        <li v-for="name in summary.unsubmitted" :key="name">{{ name }}</li>
      </ul>
    </div>
    <div v-else-if="summary.total_departments" class="alert alert-success">모든 부서가 제출했습니다.</div>

    <table class="table table-sm align-middle">
      <thead>
        <tr>
          <th>부서</th>
          <th>상태</th>
          <th style="width: 14rem">진행률</th>
          <th>제출자</th>
          <th>제출일시</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in summary.departments" :key="row.department_id">
          <td>{{ row.name }}</td>
          <td><StatusBadge :status="row.status" /></td>
          <td><ProgressBar :percent="row.progress_percent" /></td>
          <td>{{ row.submitted_by_name ?? '-' }}</td>
          <td>{{ formatDateTime(row.submitted_at) }}</td>
          <td class="text-end">
            <button type="button" class="btn btn-outline-primary btn-sm" @click="openDetail(row)">상세 보기</button>
          </td>
        </tr>
        <tr v-if="!summary.departments.length">
          <td colspan="6" class="text-center text-muted">부서가 없습니다.</td>
        </tr>
      </tbody>
    </table>

    <h2 class="h6 mt-4">{{ matrix?.year }}년 월별 제출 현황</h2>
    <table v-if="matrix" class="table table-sm table-bordered text-center align-middle">
      <thead>
        <tr>
          <th></th>
          <th v-for="department in matrix.departments" :key="department.id">{{ department.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in matrix.months" :key="row.month">
          <th class="text-nowrap">{{ row.month }}월</th>
          <td
            v-for="department in matrix.departments"
            :key="department.id"
            :class="isFuture(row.month) ? 'text-muted' : MATRIX_CLASSES[row.statuses[department.id]]"
          >
            {{ isFuture(row.month) ? '-' : MATRIX_LABELS[row.statuses[department.id]] }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 상세 탭 -->
  <div v-if="tab === 'detail' && detail">
    <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
      <div>
        <h2 class="h6 mb-1">{{ detail.name }} — {{ detail.report.year }}년 {{ detail.report.month }}월</h2>
        <StatusBadge :status="detail.report.status" />
        <span v-if="detail.report.status === 'SUBMITTED'" class="ms-2 small text-muted">
          제출일시 {{ formatDateTime(detail.report.submitted_at) }}
        </span>
        <span class="ms-2 small text-muted">
          입력 진행률 {{ detail.report.progress.percent }}% ({{ detail.report.progress.filled }}/{{ detail.report.progress.required }} 필수 항목)
        </span>
      </div>
      <button
        v-if="detail.report.status === 'SUBMITTED'"
        type="button"
        class="btn btn-outline-danger btn-sm"
        :disabled="busy"
        @click="reopen"
      >
        초안으로 되돌리기
      </button>
    </div>
    <ReportReadonly :report="detail.report" />
  </div>
</template>
