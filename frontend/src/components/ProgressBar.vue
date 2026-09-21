<script setup>
defineProps({
  percent: { type: Number, required: true },
  label: { type: String, default: '' },
})
</script>

<template>
  <div>
    <div v-if="label" class="small mb-1">{{ label }}</div>
    <div class="progress">
      <div
        class="progress-bar"
        :class="percent >= 100 ? 'bg-success' : ''"
        role="progressbar"
        :style="{ width: `${percent}%` }"
        :aria-valuenow="percent"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        {{ percent }}%
      </div>
    </div>
  </div>
</template>
