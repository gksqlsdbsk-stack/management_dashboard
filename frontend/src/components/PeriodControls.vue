<script setup>
import { computed, onMounted, ref, watch } from 'vue'

// 연도·기준 월·자금 예측 기간 선택. 유효한 값만 `change` 로 알린다. 미래 월은 고를 수 없다 [A-17, 04 §3.3]
const emit = defineEmits(['change'])

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1

const year = ref(currentYear)
const month = ref(currentMonth)
const horizon = ref(3) // 자금 수지 예측 3~6개월, 기본 3 [A-31]

const monthOptions = computed(() =>
  Array.from({ length: year.value === currentYear ? currentMonth : 12 }, (_, i) => i + 1),
)

function notify() {
  emit('change', { year: year.value, month: month.value, horizon: horizon.value })
}

watch([year, month, horizon], () => {
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
  notify()
})

onMounted(notify)
</script>

<template>
  <div class="card card-body mb-3">
    <div class="row g-3 align-items-end">
      <div class="col-auto">
        <label for="period-year" class="form-label mb-1">연도</label>
        <input id="period-year" v-model.number="year" type="number" :max="currentYear" min="1" class="form-control" style="width: 7rem" />
      </div>
      <div class="col-auto">
        <label for="period-month" class="form-label mb-1">기준 월</label>
        <select id="period-month" v-model.number="month" class="form-select">
          <option v-for="m in monthOptions" :key="m" :value="m">{{ m }}월</option>
        </select>
      </div>
      <div class="col-auto">
        <label for="period-horizon" class="form-label mb-1">자금 예측 기간</label>
        <select id="period-horizon" v-model.number="horizon" class="form-select">
          <option v-for="n in [3, 4, 5, 6]" :key="n" :value="n">{{ n }}개월</option>
        </select>
      </div>
      <div class="col-auto ms-md-auto"><slot /></div>
    </div>
  </div>
</template>
