<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  note: { type: String, default: '' },
})
</script>

<template>
  <div class="card h-100">
    <div class="card-body py-3">
      <div class="small text-muted">{{ label }}</div>
      <div class="fs-5 fw-semibold text-nowrap">{{ value }}</div>
      <div v-if="note" class="small text-muted">{{ note }}</div>
    </div>
  </div>
</template>
