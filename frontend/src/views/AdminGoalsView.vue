<script setup>
import { onMounted, ref, watch } from 'vue'
import { getGoals, saveGoals } from '../api/goals'
import { errorAlert, successAlert, noAlert } from '../utils/errors'
import InlineAlert from '../components/InlineAlert.vue'

const year = ref(new Date().getFullYear())
const goals = ref([]) // [{ metric_key, label, unit, input }] — input: 화면에 입력한 문자열
const alert = ref(noAlert())
const busy = ref(false)
let loadSeq = 0

function apply(data) {
  goals.value = data.goals.map((goal) => ({
    metric_key: goal.metric_key,
    label: goal.label,
    unit: goal.unit,
    input: goal.target_value === null ? '' : String(goal.target_value),
  }))
}

async function load() {
  const seq = ++loadSeq
  alert.value = noAlert()
  try {
    const data = await getGoals(year.value)
    if (seq === loadSeq) apply(data)
  } catch (error) {
    if (seq === loadSeq) alert.value = errorAlert(error)
  }
}

// 값을 비우고 저장하면 해당 지표의 목표가 삭제된다(목표 미설정) [04 §3.6]
async function save() {
  busy.value = true
  alert.value = noAlert()
  const payload = goals.value.map((goal) => ({
    metric_key: goal.metric_key,
    target_value: String(goal.input).trim() === '' ? null : Number(goal.input),
  }))
  try {
    apply(await saveGoals(year.value, payload))
    alert.value = successAlert('저장되었습니다.')
  } catch (error) {
    alert.value = errorAlert(error, { goals: '' })
  } finally {
    busy.value = false
  }
}

watch(year, () => {
  if (Number.isInteger(year.value) && year.value >= 1) load()
})

onMounted(load)
</script>

<template>
  <h1 class="h4 mb-3">연간 목표</h1>

  <div class="card card-body mb-3">
    <div class="row g-3 align-items-end">
      <div class="col-auto">
        <label for="goal-year" class="form-label mb-1">연도</label>
        <input id="goal-year" v-model.number="year" type="number" min="1" class="form-control" style="width: 7rem" />
      </div>
    </div>
  </div>

  <InlineAlert :alert="alert" />

  <form v-if="goals.length" @submit.prevent="save">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>지표</th>
          <th style="width: 18rem">목표값</th>
          <th>단위</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="goal in goals" :key="goal.metric_key">
          <td><label :for="`goal-${goal.metric_key}`">{{ goal.label }}</label></td>
          <td>
            <input
              :id="`goal-${goal.metric_key}`"
              v-model="goal.input"
              type="number"
              step="any"
              min="0"
              class="form-control"
              :disabled="busy"
            />
          </td>
          <td>{{ goal.unit }}</td>
          <td>
            <span v-if="String(goal.input).trim() === ''" class="badge bg-secondary">목표 미설정</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="small text-muted">값을 비우고 저장하면 해당 지표의 목표가 삭제됩니다(목표 미설정). 현재 실적은 대시보드에서 확인합니다.</p>
    <button type="submit" class="btn btn-primary" :disabled="busy">저장</button>
  </form>
</template>
