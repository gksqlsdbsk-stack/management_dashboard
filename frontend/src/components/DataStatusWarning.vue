<script setup>
// 기준 월에 미제출 부서가 있으면 경고를 표시한다 (제출된 데이터만 집계) [A-25, 04 §3.3]
defineProps({
  status: { type: Object, required: true },
})
</script>

<template>
  <div v-if="status.has_warning" class="alert alert-warning">
    일부 부서 미제출: {{ status.missing_departments.join(', ') }} (제출된 데이터만 집계)
  </div>
</template>
