<script setup>
// 입력 항목 1개의 입력 칸. 월 합계형은 값 1개, 프로젝트별형은 (프로젝트명, 값) 행 목록 [04 §3.2]
// `state`는 부모(EntryView)가 가진 입력 상태 객체이며 여기서 직접 편집한다.
defineProps({
  item: { type: Object, required: true },
  state: { type: Object, required: true },
})
const emit = defineEmits(['add-row', 'remove-row'])
</script>

<template>
  <div class="mb-4">
    <label :for="`item-${item.id}`" class="form-label fw-semibold">
      {{ item.name }}
      <span v-if="item.unit" class="text-muted fw-normal">({{ item.unit }})</span>
      <span v-if="item.is_required" class="text-danger small">★필수</span>
    </label>

    <template v-if="item.scope === 'PROJECT'">
      <div v-for="(row, index) in state.rows" :key="row.key" class="row g-2 mb-2">
        <div class="col-5">
          <input
            v-model="row.name"
            type="text"
            class="form-control"
            maxlength="100"
            placeholder="프로젝트명"
            :aria-label="`${item.name} 프로젝트명`"
          />
        </div>
        <div class="col-5">
          <input
            v-model="row.value"
            type="number"
            step="any"
            class="form-control"
            placeholder="값"
            :aria-label="`${item.name} 값`"
          />
        </div>
        <div class="col-2">
          <button type="button" class="btn btn-outline-danger w-100" @click="emit('remove-row', index)">삭제</button>
        </div>
      </div>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="emit('add-row')">+ 프로젝트 행 추가</button>
    </template>
    <input v-else :id="`item-${item.id}`" v-model="state.value" type="number" step="any" class="form-control" />

    <div v-if="item.help_text" class="form-text">↳ {{ item.help_text }}</div>
  </div>
</template>
