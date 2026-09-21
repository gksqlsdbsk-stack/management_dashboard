<script setup>
import { formatByKind } from '../utils/format'

// 지표 표: 행 정의(`rows`, utils/sections.js)와 열(`blocks`: [{ label, data }])로 그린다.
// 계산 불가(null)는 '-' 로, 이월된 stock 값은 '(n월 기준)' 을 덧붙인다 [A-26, A-36]
defineProps({
  rows: { type: Array, required: true },
  blocks: { type: Array, required: true },
  baseMonth: { type: Number, required: true },
})
</script>

<template>
  <table class="table table-sm align-middle mb-0">
    <thead>
      <tr>
        <th></th>
        <th v-for="block in blocks" :key="block.label" class="text-end">{{ block.label }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.field">
        <td>{{ row.label }}</td>
        <td v-for="block in blocks" :key="block.label" class="text-end text-nowrap">
          {{ formatByKind(row.kind, block.data?.[row.field]) }}
          <span
            v-if="row.asField && block.data?.[row.asField] && block.data[row.asField] !== baseMonth"
            class="small text-muted"
          >
            ({{ block.data[row.asField] }}월 기준)
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</template>
