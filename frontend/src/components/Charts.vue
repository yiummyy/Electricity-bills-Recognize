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
import { Bar, Doughnut } from 'vue-chartjs'
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
      backgroundColor: 'rgba(22, 93, 255, 0.8)',
      hoverBackgroundColor: 'rgba(22, 93, 255, 1)',
      borderRadius: 6,
      maxBarThickness: 40
    },
    {
      label: '总电量 (kWh)',
      data: props.data.map(d => parseFloat(d['总电量(kWh)'] || 0)),
      backgroundColor: 'rgba(20, 201, 201, 0.8)',
      hoverBackgroundColor: 'rgba(20, 201, 201, 1)',
      borderRadius: 6,
      maxBarThickness: 40
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
        borderWidth: 0,
        hoverOffset: 4,
        data: [peak, shoulder, flat, valley]
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        usePointStyle: true,
        padding: 20,
        font: {
          family: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif",
          size: 13
        }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      titleColor: '#1f2329',
      bodyColor: '#4e5969',
      borderColor: 'rgba(22, 93, 255, 0.1)',
      borderWidth: 1,
      padding: 12,
      boxPadding: 6,
      usePointStyle: true,
      titleFont: { size: 14, weight: 600 as const },
      bodyFont: { size: 13 }
    }
  },
  scales: {
    x: {
      grid: {
        display: false,
        drawBorder: false
      },
      ticks: {
        font: { size: 12 }
      }
    },
    y: {
      grid: {
        color: '#f2f3f5',
        drawBorder: false,
        borderDash: [4, 4]
      },
      ticks: {
        font: { size: 12 },
        padding: 8
      }
    }
  }
}

const pieChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        usePointStyle: true,
        padding: 20,
        font: {
          family: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif",
          size: 13
        }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      titleColor: '#1f2329',
      bodyColor: '#4e5969',
      borderColor: 'rgba(22, 93, 255, 0.1)',
      borderWidth: 1,
      padding: 12,
      usePointStyle: true,
      callbacks: {
        label: (context: any) => {
          return ` ${context.label.split(' ')[0]}: ${context.parsed} KWh`
        }
      }
    }
  }
}
</script>

<template>
  <div class="charts-grid">
    <div class="chart-wrapper">
      <h3 class="chart-title">综合趋势分析</h3>
      <div style="height: 320px;">
        <Bar :data="costChartData" :options="chartOptions" />
      </div>
    </div>
    <div class="chart-wrapper">
      <h3 class="chart-title">用电结构分析</h3>
      <div style="height: 320px; display: flex; justify-content: center; position: relative;">
        <Doughnut :data="usagePieData" :options="pieChartOptions" />
      </div>
    </div>
  </div>
</template>
