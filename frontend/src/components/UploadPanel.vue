<script setup>
import { ref } from 'vue'
import InlineAlert from './InlineAlert.vue'

// 엑셀/CSV 파일 선택·업로드 영역 [04 §3.2, 06]. 업로드 처리는 부모가 하고 결과는 `alert`로 받는다.
defineProps({
  alert: { type: Object, required: true },
})
const emit = defineEmits(['upload'])

const fileInput = ref(null)
const file = ref(null)

function onChange(event) {
  file.value = event.target.files[0] ?? null
}

function onUpload() {
  if (file.value) emit('upload', file.value)
}

// 업로드 성공 후 선택한 파일을 비운다
function clear() {
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
}

defineExpose({ clear })
</script>

<template>
  <div class="border rounded p-3 mb-3 bg-light">
    <div class="fw-semibold mb-1">엑셀/CSV 업로드</div>
    <p class="small text-muted mb-2">
      엑셀(.xlsx) 또는 CSV(.csv) 파일을 올리면 현재 선택한 월의 입력값에 반영됩니다. 첫 행에 '항목명', '프로젝트명', '값' 열이
      있어야 하며, 월 합계 항목은 프로젝트명을 비워 두세요. 파일에 없는 항목은 기존 값이 유지됩니다.
    </p>
    <InlineAlert :alert="alert" />
    <div class="d-flex gap-2 align-items-center">
      <input ref="fileInput" type="file" class="form-control" accept=".xlsx,.csv" aria-label="업로드할 파일" @change="onChange" />
      <button type="button" class="btn btn-outline-primary text-nowrap" :disabled="!file" @click="onUpload">업로드</button>
    </div>
    <div class="form-text">열: 항목명, 프로젝트명, 값 · 파일 크기 최대 5MB, 데이터 최대 1,000행 · 반영 후에도 제출은 따로 해야 합니다.</div>
  </div>
</template>
