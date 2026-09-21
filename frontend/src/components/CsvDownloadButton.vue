<script setup>
import { ref } from 'vue'
import { downloadCsv } from '../api/analytics'

// `CSV 다운로드` 버튼: fetch 로 받은 CSV 를 Blob 으로 저장한다 [FR-A09, 03 §8.5].
// 실패하면 `error` 이벤트로 오류를 알린다.
const props = defineProps({
  kind: { type: String, required: true }, // 'dashboard' | 'monthly-report'
  period: { type: Object, default: null }, // { year, month, horizon }
})
const emit = defineEmits(['error'])

const busy = ref(false)

async function onClick() {
  busy.value = true
  try {
    const { blob, filename } = await downloadCsv(props.kind, props.period)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    emit('error', error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button type="button" class="btn btn-outline-success" :disabled="!period || busy" @click="onClick">
    {{ busy ? '내려받는 중...' : 'CSV 다운로드' }}
  </button>
</template>
