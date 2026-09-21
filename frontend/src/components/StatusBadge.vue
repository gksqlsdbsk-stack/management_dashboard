<script setup>
// 보고서 상태 배지: 미작성 / 작성 중 / 제출 완료 [04 §3.5]
defineProps({
  status: { type: String, required: true },
})
const LABELS = { NOT_STARTED: '미작성', DRAFT: '작성 중', SUBMITTED: '제출 완료' }
const CLASSES = { NOT_STARTED: 'bg-secondary', DRAFT: 'bg-warning text-dark', SUBMITTED: 'bg-success' }
</script>

<template>
  <span class="badge" :class="CLASSES[status]">{{ LABELS[status] }}</span>
</template>
