<script setup lang="ts">
import { computed } from 'vue'
import type { ExtractionResult } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

// Fixed columns that are always shown
const fixedColumns = ['电费年月', '用户编号', '结算户号', '电表编号', '总电量(kWh)', '总电费(元)']

// Potential dynamic columns in order
const dynamicColumnCandidates = [
  '尖时电量(kWh)', '尖时电价(元/kWh)',
  '峰段电量(kWh)', '峰段电价(元/kWh)',
  '平段电量(kWh)', '平段电价(元/kWh)',
  '谷段电量(kWh)', '谷段电价(元/kWh)',
  '深谷段电量(kWh)', '深谷段电价(元/kWh)',
  '功率因数标准', '实际功率因数', '调整电费(元)',
  '基金及附加电费单价(元/kWh)', '基金及代理购电价格(元/kWh)',
  '输配电价-电度电价(元/kWh)', '上网环节线损电价(元/kWh)',
  '系统运行费单价(元/kWh)', '重大水利工程建设基金(元/kWh)',
  '农网还贷基金(元/kWh)', '大中型水库移民后期扶持资金(元/kWh)',
  '可再生能源附加(元/kWh)'
]

const columns = computed(() => {
  if (props.data.length === 0) return [...fixedColumns, ...dynamicColumnCandidates.slice(0, 8)] // Default fallback

  const activeColumns = dynamicColumnCandidates.filter(col => {
    // Check if any row has a non-zero/non-empty value for this column
    return props.data.some(row => {
      const val = row[col]
      return val && val !== '0.00' && val !== '0.0000' && val !== 0 && val !== '-'
    })
  })

  return [...fixedColumns, ...activeColumns]
})
</script>

<template>
  <div class="table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col">{{ col }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in props.data" :key="index">
          <td v-for="col in columns" :key="col">
             <input type="text" v-model="row[col]" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
