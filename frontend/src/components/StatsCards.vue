<script setup lang="ts">
import { computed } from 'vue'
import type { ExtractionResult } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

const stats = computed(() => {
  if (props.data.length === 0) return { totalCost: 0, totalUsage: 0, avgPrice: 0 }
  
  const totalCost = props.data.reduce((sum, item) => sum + (parseFloat(item['总电费(元)']) || 0), 0)
  const totalUsage = props.data.reduce((sum, item) => sum + (parseFloat(item['总电量(kWh)']) || 0), 0)
  const avgPrice = totalUsage ? totalCost / totalUsage : 0
  
  return {
    totalCost: totalCost.toFixed(2),
    totalUsage: totalUsage.toFixed(2),
    avgPrice: avgPrice.toFixed(4)
  }
})
</script>

<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(22, 93, 255, 0.1); color: #165DFF;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">累计电费支出</div>
          <div class="stat-value">¥ {{ stats.totalCost }}</div>
        </div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(0, 180, 42, 0.1); color: #00B42A;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">累计用电量</div>
          <div class="stat-value">{{ stats.totalUsage }} KWh</div>
        </div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(255, 125, 0, 0.1); color: #FF7D00;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M2 20h20M4 4l16 16" />
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">平均电价</div>
          <div class="stat-value">¥ {{ stats.avgPrice }} /KWh</div>
        </div>
      </div>
    </div>
  </div>
</template>
