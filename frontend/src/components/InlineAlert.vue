<script setup>
// 저장 성공·오류를 화면에 인라인으로 표시한다 (토스트/모달 없음) [04 §2]
defineProps({
  alert: { type: Object, required: true },
})
</script>

<template>
  <div v-if="alert.message" class="alert" :class="`alert-${alert.type}`" role="alert">
    {{ alert.message }}
    <ul v-if="alert.details.length" class="mb-0 mt-1" style="max-height: 16rem; overflow-y: auto">
      <li v-for="(detail, index) in alert.details" :key="index">{{ detail }}</li>
    </ul>
  </div>
</template>
