<script setup lang="ts">
import { computed } from 'vue'
import type { ExtractionResult } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

const basicInfo = computed(() => {
  if (props.data.length === 0) return {
    userId: '-',
    settlementName: '-',
    voltage: '-',
    category: '-'
  }
  // take from the first item
  const first = props.data[0]
  return {
    userId: first['用户编号'] || '-',
    settlementName: first['结算户名'] || '-',
    voltage: first['供电电压'] || '-',
    category: first['用电类别'] || '-'
  }
})
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">基本信息</h2>
    </div>
    
    <div class="info-card">
      <div class="info-grid" id="commonInfo">
        <div class="info-item">
          <div class="info-label">用户编号</div>
          <div class="info-value">{{ basicInfo.userId }}</div>
        </div>
    
        <div class="info-item">
          <div class="info-label">结算户名</div>
          <div class="info-value">{{ basicInfo.settlementName }}</div>
        </div>
    
        <div class="info-item">
          <div class="info-label">供电电压</div>
          <div class="info-value">{{ basicInfo.voltage }}</div>
        </div>
    
        <div class="info-item">
          <div class="info-label">用电类别</div>
          <div class="info-value">{{ basicInfo.category }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
