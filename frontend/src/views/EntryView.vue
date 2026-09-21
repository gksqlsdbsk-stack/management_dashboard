<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { getMyReport, saveMyReport, submitMyReport, uploadMyReport } from '../api/report'
import { errorAlert, successAlert, noAlert } from '../utils/errors'
import InlineAlert from '../components/InlineAlert.vue'
import ProgressBar from '../components/ProgressBar.vue'
import ReportItemInput from '../components/ReportItemInput.vue'
import UploadPanel from '../components/UploadPanel.vue'

const STATUS_LABELS = { NOT_STARTED: '미작성', DRAFT: '작성 중', SUBMITTED: '제출 완료' }
const STATUS_BADGES = { NOT_STARTED: 'bg-secondary', DRAFT: 'bg-warning text-dark', SUBMITTED: 'bg-success' }

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1

const year = ref(currentYear)
const month = ref(currentMonth) // 기본은 현재 월, 현재 월 이하만 선택 가능 [A-17]
const report = ref(null)
const noDepartmentMessage = ref('')
const loading = ref(false)
const busy = ref(false)
const pageAlert = ref(noAlert())
const uploadAlert = ref(noAlert())
const uploadPanel = ref(null)
const state = reactive({}) // 항목 id → { value } (월 합계형) | { rows } (프로젝트별형)
let rowSeq = 0
let loadSeq = 0

const monthOptions = computed(() =>
  Array.from({ length: year.value === currentYear ? currentMonth : 12 }, (_, i) => i + 1),
)
const locked = computed(() => report.value?.status === 'SUBMITTED')
const submittedAtText = computed(() =>
  report.value?.submitted_at ? new Date(report.value.submitted_at).toLocaleString('ko-KR') : '',
)

function newRow(name = '', value = '') {
  return { key: ++rowSeq, name, value: value === '' ? '' : String(value) }
}

function applyReport(data) {
  report.value = data
  for (const key of Object.keys(state)) delete state[key]
  for (const item of data.items) {
    const values = data.values.filter((v) => v.item_id === item.id)
    if (item.scope === 'PROJECT') {
      state[item.id] = { rows: values.length ? values.map((v) => newRow(v.project_name, v.value)) : [newRow()] }
    } else {
      state[item.id] = { value: values.length ? String(values[0].value) : '' }
    }
  }
}

function addRow(item) {
  state[item.id].rows.push(newRow())
}

function removeRow(item, index) {
  state[item.id].rows.splice(index, 1)
}

// ---- 진행률 (입력 중 실시간 표시. 서버 규칙과 동일 [A-20, A-05]) ----
function isFilled(item) {
  const itemState = state[item.id]
  if (!itemState) return false
  if (item.scope === 'PROJECT') {
    return itemState.rows.some((row) => row.name.trim() !== '' && String(row.value).trim() !== '')
  }
  return String(itemState.value).trim() !== ''
}

const progress = computed(() => {
  const required = report.value?.items.filter((item) => item.is_required) ?? []
  const filled = required.filter(isFilled).length
  const percent = required.length ? Math.floor((filled * 100) / required.length) : 100
  return { filled, required: required.length, percent }
})

const progressLabel = computed(() => `입력 진행률 ${progress.value.percent}% (${progress.value.filled}/${progress.value.required} 필수 항목)`)

// ---- 서버 통신 ----
async function load() {
  const seq = ++loadSeq
  loading.value = true
  pageAlert.value = noAlert()
  uploadAlert.value = noAlert()
  noDepartmentMessage.value = ''
  try {
    const data = await getMyReport(year.value, month.value)
    if (seq === loadSeq) applyReport(data)
  } catch (error) {
    if (seq !== loadSeq) return
    report.value = null
    if (error.status === 403) noDepartmentMessage.value = error.message
    else pageAlert.value = errorAlert(error)
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function collectValues() {
  const values = []
  for (const item of report.value.items) {
    const itemState = state[item.id]
    if (item.scope === 'PROJECT') {
      for (const row of itemState.rows) {
        const name = row.name.trim()
        const value = String(row.value).trim()
        if (!name && !value) continue // 빈 행
        values.push({ item_id: item.id, project_name: name, value: value === '' ? null : Number(value) })
      }
    } else {
      const value = String(itemState.value).trim()
      if (value !== '') values.push({ item_id: item.id, project_name: '', value: Number(value) })
    }
  }
  return values
}

async function handleError(error) {
  if (error.code === 'incomplete_required') {
    pageAlert.value = {
      type: 'danger',
      message: '필수 항목이 모두 입력되지 않아 제출할 수 없습니다. (입력한 값은 임시 저장되었습니다.)',
      details: (error.errors?.missing_items ?? []).map((item) => `미입력: ${item.name}`),
    }
  } else if (error.status === 409) {
    // 다른 담당자가 이미 제출했거나 잠긴 경우: 최신 상태를 다시 불러온다
    await load()
    pageAlert.value = errorAlert(error)
  } else {
    pageAlert.value = errorAlert(error, { values: '' })
  }
}

async function saveDraft() {
  busy.value = true
  pageAlert.value = noAlert()
  try {
    applyReport(await saveMyReport(year.value, month.value, collectValues()))
    pageAlert.value = successAlert('임시 저장되었습니다.')
  } catch (error) {
    await handleError(error)
  } finally {
    busy.value = false
  }
}

async function submit() {
  if (!confirm('제출하면 수정할 수 없습니다. 제출하시겠습니까?')) return
  busy.value = true
  pageAlert.value = noAlert()
  try {
    await saveMyReport(year.value, month.value, collectValues())
    applyReport(await submitMyReport(year.value, month.value))
    pageAlert.value = successAlert('제출되었습니다.')
  } catch (error) {
    await handleError(error)
  } finally {
    busy.value = false
  }
}

// 업로드: 화면에 입력 중인 값을 잃지 않도록 먼저 임시 저장한 뒤 파일을 반영한다 [06 §5].
// 파일 값이 같은 (항목, 프로젝트명)의 입력값을 덮어쓰고, 파일에 없는 값은 유지된다.
async function uploadFile(file) {
  busy.value = true
  pageAlert.value = noAlert()
  uploadAlert.value = noAlert()
  let step = 'save'
  try {
    const values = collectValues()
    if (values.length || report.value.status !== 'NOT_STARTED') {
      await saveMyReport(year.value, month.value, values)
    }
    step = 'upload'
    const result = await uploadMyReport(year.value, month.value, file)
    applyReport(result.report)
    uploadAlert.value = successAlert(`${result.applied_count}건 반영됨, 확인 후 제출하세요.`)
    uploadPanel.value?.clear()
  } catch (error) {
    if (error.status === 409) {
      await load()
      pageAlert.value = errorAlert(error)
    } else if (step === 'save') {
      const alert = errorAlert(error, { values: '' })
      pageAlert.value = { ...alert, message: `입력 중인 값을 저장하지 못해 업로드하지 않았습니다. ${alert.message}` }
    } else if (error.code === 'upload_invalid') {
      uploadAlert.value = {
        type: 'danger',
        message: `${error.message} (어떤 값도 반영되지 않았습니다.)`,
        details: (error.errors?.rows ?? []).map((row) => row.message),
      }
    } else {
      pageAlert.value = errorAlert(error)
    }
  } finally {
    busy.value = false
  }
}

// 연·월이 바뀌면 다시 불러온다. 미래 월은 고를 수 없도록 보정한다.
watch([year, month], () => {
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
  load()
})

onMounted(load)
</script>

<template>
  <h1 class="h4 mb-3">월 실적 입력</h1>

  <div v-if="noDepartmentMessage" class="alert alert-warning">{{ noDepartmentMessage }}</div>
  <InlineAlert v-else :alert="pageAlert" />

  <template v-if="!noDepartmentMessage">
    <div class="card card-body mb-3">
      <div class="row g-3 align-items-end">
        <div class="col-auto">
          <label for="entry-year" class="form-label mb-1">연도</label>
          <input id="entry-year" v-model.number="year" type="number" :max="currentYear" min="1" class="form-control" style="width: 7rem" />
        </div>
        <div class="col-auto">
          <label for="entry-month" class="form-label mb-1">월</label>
          <select id="entry-month" v-model.number="month" class="form-select">
            <option v-for="m in monthOptions" :key="m" :value="m">{{ m }}월</option>
          </select>
        </div>
        <div v-if="report" class="col-auto ms-md-auto">
          <span class="me-3">부서: <strong>{{ report.department.name }}</strong></span>
          <span>상태: <span class="badge" :class="STATUS_BADGES[report.status]">{{ STATUS_LABELS[report.status] }}</span></span>
        </div>
      </div>
    </div>

    <p v-if="loading && !report" class="text-muted">불러오는 중...</p>

    <template v-if="report">
      <div class="mb-3">
        <ProgressBar :percent="progress.percent" :label="progressLabel" />
      </div>

      <div v-if="locked" class="alert alert-success">제출 완료 ({{ submittedAtText }}) — 수정할 수 없습니다.</div>
      <div v-if="report.department.input_guide" class="alert alert-info" style="white-space: pre-line">
        ⓘ {{ report.department.input_guide }}
      </div>

      <form class="card card-body" @submit.prevent>
        <fieldset :disabled="locked || busy">
          <ReportItemInput
            v-for="item in report.items"
            :key="item.id"
            :item="item"
            :state="state[item.id]"
            @add-row="addRow(item)"
            @remove-row="(index) => removeRow(item, index)"
          />
          <p v-if="!report.items.length" class="text-muted mb-0">입력할 항목이 없습니다. 관리자에게 문의하세요.</p>
          <UploadPanel ref="uploadPanel" :alert="uploadAlert" @upload="uploadFile" />
        </fieldset>
        <div class="d-flex justify-content-end gap-2 border-top pt-3">
          <button type="button" class="btn btn-outline-primary" :disabled="locked || busy" @click="saveDraft">임시 저장</button>
          <button type="button" class="btn btn-primary" :disabled="locked || busy" @click="submit">제출</button>
        </div>
      </form>
    </template>
  </template>
</template>
