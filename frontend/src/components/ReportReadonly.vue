<script setup>
import { formatNumber } from '../utils/format'

// 부서 보고서 입력값을 읽기 전용 표로 보여준다 (항목, 프로젝트명, 값, 단위) [04 §3.5]
defineProps({
  report: { type: Object, required: true },
})
</script>

<template>
  <table class="table table-sm align-middle">
    <thead>
      <tr>
        <th>항목</th>
        <th>프로젝트명</th>
        <th class="text-end">값</th>
        <th>단위</th>
      </tr>
    </thead>
    <tbody>
      <template v-for="item in report.items" :key="item.id">
        <template v-if="report.values.some((v) => v.item_id === item.id)">
          <tr v-for="(value, index) in report.values.filter((v) => v.item_id === item.id)" :key="`${item.id}-${index}`">
            <td>{{ index === 0 ? item.name : '' }}</td>
            <td>{{ value.project_name || '-' }}</td>
            <td class="text-end">{{ formatNumber(value.value) }}</td>
            <td>{{ item.unit || '-' }}</td>
          </tr>
        </template>
        <tr v-else>
          <td>
            {{ item.name }}
            <span v-if="item.is_required" class="text-danger small">★필수</span>
          </td>
          <td>-</td>
          <td class="text-end text-muted">미입력</td>
          <td>{{ item.unit || '-' }}</td>
        </tr>
      </template>
      <tr v-if="!report.items.length">
        <td colspan="4" class="text-center text-muted">입력 항목이 없습니다.</td>
      </tr>
    </tbody>
  </table>
</template>
