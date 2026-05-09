<script setup lang="ts">
import { computed } from 'vue'
import type { ExtractionResult } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

const stats = computed(() => {
  if (props.data.length === 0) return { months: 0, totalCost: '0.00', totalUsage: '0', avgPrice: '0.0000' }
  
  const totalCost = props.data.reduce((sum, item) => sum + (parseFloat(item['总电费(元)']) || 0), 0)
  const totalUsage = props.data.reduce((sum, item) => sum + (parseFloat(item['总电量(kWh)']) || 0), 0)
  const avgPrice = totalUsage ? totalCost / totalUsage : 0
  
  return {
    months: props.data.length,
    totalCost: totalCost.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    totalUsage: totalUsage.toLocaleString('zh-CN'),
    avgPrice: avgPrice.toFixed(4)
  }
})
</script>

<template>
  <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(22, 93, 255, 0.08);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="18" rx="2" stroke="#165DFF" stroke-width="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9" stroke="#165DFF" stroke-width="2"></line>
            <line x1="7" y1="1" x2="7" y2="4" stroke="#165DFF" stroke-width="2" stroke-linecap="round"></line>
            <line x1="17" y1="1" x2="17" y2="4" stroke="#165DFF" stroke-width="2" stroke-linecap="round"></line>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">电费单月份（月）</div>
          <div class="stat-value">{{ stats.months }}</div>
        </div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(20, 201, 201, 0.08);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" stroke="#14C9C9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">总用电量</div>
          <div class="stat-value">{{ stats.totalUsage }} <span style="font-size: 14px; font-weight: normal; color: #6b7280;">kWh</span></div>
        </div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(247, 186, 30, 0.08);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="#F7BA1E" stroke-width="2"></circle>
            <path d="M12 6v3m0 6v3m-4-6h8" stroke="#F7BA1E" stroke-width="2" stroke-linecap="round"></path>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">总电费</div>
          <div class="stat-value"><span style="font-size: 16px; font-weight: normal; color: #6b7280;">¥</span> {{ stats.totalCost }}</div>
        </div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-content">
        <div class="stat-icon" style="background: rgba(239, 74, 66, 0.08);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M3 3v18h18" stroke="#EF4A42" stroke-width="2" stroke-linecap="round"></path>
            <path d="M7 14l4-4 3 3 5-7" stroke="#EF4A42" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <circle cx="7" cy="14" r="2" fill="#EF4A42"></circle>
            <circle cx="11" cy="10" r="2" fill="#EF4A42"></circle>
            <circle cx="14" cy="13" r="2" fill="#EF4A42"></circle>
            <circle cx="19" cy="6" r="2" fill="#EF4A42"></circle>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">平均电价</div>
          <div class="stat-value">{{ stats.avgPrice }} <span style="font-size: 14px; font-weight: normal; color: #6b7280;">元/kWh</span></div>
        </div>
      </div>
    </div>
  </div>
</template>
