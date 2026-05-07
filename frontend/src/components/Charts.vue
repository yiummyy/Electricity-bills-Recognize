<script setup lang="ts">
import { computed } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { Bar, Pie } from 'vue-chartjs'
import type { ExtractionResult } from '@/stores/bill'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps<{
  data: ExtractionResult[]
}>()

const labels = computed(() => props.data.map(d => d['电费年月']))

const costChartData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '总电费 (元)',
      data: props.data.map(d => parseFloat(d['总电费(元)'] || 0)),
      backgroundColor: '#165DFF',
      borderRadius: 4,
      maxBarThickness: 48
    }
  ]
}))

const usagePieData = computed(() => {
  const peak = props.data.reduce((sum, d) => sum + (parseFloat(d['尖时电量(kWh)']) || 0), 0)
  const shoulder = props.data.reduce((sum, d) => sum + (parseFloat(d['峰段电量(kWh)']) || 0), 0)
  const flat = props.data.reduce((sum, d) => sum + (parseFloat(d['平段电量(kWh)']) || 0), 0)
  const valley = props.data.reduce((sum, d) => sum + (parseFloat(d['谷段电量(kWh)']) || 0), 0)

  const total = peak + shoulder + flat + valley
  const getPercent = (val: number) => total ? ((val / total) * 100).toFixed(1) + '%' : '0%'

  return {
    labels: [
      `尖时 (${getPercent(peak)})`,
      `峰段 (${getPercent(shoulder)})`,
      `平段 (${getPercent(flat)})`,
      `谷段 (${getPercent(valley)})`
    ],
    datasets: [
      {
        backgroundColor: ['#F53F3F', '#FF7D00', '#165DFF', '#00B42A'],
        data: [peak, shoulder, flat, valley]
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    }
  }
}

const pieChartOptions = {
  ...chartOptions,
  plugins: {
    ...chartOptions.plugins,
    tooltip: {
      callbacks: {
        label: (context: any) => {
          return `${context.label}: ${context.parsed} KWh`
        }
      }
    }
  }
}
</script>

<template>
  <div class="charts-grid">
    <div class="chart-wrapper">
      <h3 class="chart-title">电费趋势分析</h3>
      <div style="height: 300px;">
        <Bar :data="costChartData" :options="chartOptions" />
      </div>
    </div>
    <div class="chart-wrapper">
      <h3 class="chart-title">用电结构分析</h3>
      <div style="height: 300px; display: flex; justify-content: center;">
        <Pie :data="usagePieData" :options="pieChartOptions" />
      </div>
    </div>
  </div>
</template>
