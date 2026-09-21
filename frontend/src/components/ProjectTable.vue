<script setup>
import { formatMoney, formatPercent } from '../utils/format'

// 프로젝트별 원가/이익률 표 [04 §3.3]
defineProps({
  rows: { type: Array, required: true },
})
</script>

<template>
  <table class="table table-sm align-middle mb-0">
    <thead>
      <tr>
        <th>프로젝트</th>
        <th class="text-end">매출액</th>
        <th class="text-end">총원가</th>
        <th class="text-end">매출총이익</th>
        <th class="text-end">이익률</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.project_name">
        <td>{{ row.project_name }}</td>
        <td class="text-end">{{ formatMoney(row.revenue) }}</td>
        <td class="text-end">{{ formatMoney(row.total_cost) }}</td>
        <td class="text-end">{{ formatMoney(row.gross_profit) }}</td>
        <td class="text-end">{{ formatPercent(row.gross_margin) }}</td>
      </tr>
      <tr v-if="!rows.length">
        <td colspan="5" class="text-center text-muted">프로젝트 데이터가 없습니다.</td>
      </tr>
    </tbody>
  </table>
</template>
