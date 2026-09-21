<script setup>
import { onBeforeUnmount, onMounted, ref, toRaw, watch } from 'vue'
import { Chart, registerables } from 'chart.js'

// Chart.js 를 직접 사용하는 캔버스 컴포넌트 (래퍼 라이브러리 없음) [A-38]
Chart.register(...registerables)

const props = defineProps({
  config: { type: Object, required: true },
  height: { type: String, default: '280px' },
})

const canvas = ref(null)
let chart = null

function render() {
  chart?.destroy()
  chart = new Chart(canvas.value, toRaw(props.config))
}

onMounted(render)
watch(() => props.config, render)
onBeforeUnmount(() => chart?.destroy())
</script>

<template>
  <div :style="{ height, position: 'relative' }">
    <canvas ref="canvas"></canvas>
  </div>
</template>
