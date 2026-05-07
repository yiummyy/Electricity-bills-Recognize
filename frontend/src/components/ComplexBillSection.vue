<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  data: any[]
}>()

const collapsed = ref(true)

// Parse JSON string from "分时电价明细"
const complexData = computed(() => {
  return props.data.map(row => {
    try {
      if (row['分时电价明细'] && row['分时电价明细'] !== '-') {
        return {
          month: row['电费年月'],
          details: JSON.parse(row['分时电价明细'])
        }
      }
      return null
    } catch (e) {
      return null
    }
  }).filter(item => item !== null)
})

const hasData = computed(() => complexData.value.length > 0)

// Helper to get price by type
function getPrice(details: any[], type: string) {
    const item = details.find((d: any) => d.tou_type === type)
    return item ? item.final_price.toFixed(4) : '-'
}

// Helper to get components tooltip
function getComponents(details: any[], type: string) {
    const item = details.find((d: any) => d.tou_type === type)
    if (!item || !item.components) return ''
    
    return Object.entries(item.components)
        .map(([k, v]) => `${k}: ${Number(v).toFixed(4)}`)
        .join('\n')
}
</script>

<template>
  <div v-if="hasData" class="card mt-6">
    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;" @click="collapsed = !collapsed">
      <div>
        <h2 class="card-title">分时电价明细 (复杂账单计算)</h2>
        <p class="text-sm text-gray-500">
          尖时/峰/平/谷综合电价 = 电能 + 输配 + 损耗 + 基金 + 其它(系统运行/市场化分摊)
        </p>
      </div>
      <span class="text-gray-400 text-lg transition-transform" :style="{ transform: collapsed ? '' : 'rotate(90deg)' }">▶</span>
    </div>

    <div v-show="!collapsed" class="overflow-x-auto">
      <table class="w-full text-sm text-left text-gray-500">
        <thead class="text-xs text-gray-700 uppercase bg-gray-50">
          <tr>
            <th class="px-6 py-3">月份</th>
            <th class="px-6 py-3">尖时电价 (元/kWh)</th>
            <th class="px-6 py-3">峰段电价 (元/kWh)</th>
            <th class="px-6 py-3">平段电价 (元/kWh)</th>
            <th class="px-6 py-3">谷段电价 (元/kWh)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in complexData" :key="idx" class="bg-white border-b hover:bg-gray-50">
            <td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
              {{ item.month }}
            </td>
            <td class="px-6 py-4" :title="getComponents(item.details, 'peak')">
              <span class="cursor-help border-b border-dotted border-gray-400">
                {{ getPrice(item.details, 'peak') }}
              </span>
            </td>
            <td class="px-6 py-4" :title="getComponents(item.details, 'shoulder')">
               <span class="cursor-help border-b border-dotted border-gray-400">
                {{ getPrice(item.details, 'shoulder') }}
               </span>
            </td>
            <td class="px-6 py-4" :title="getComponents(item.details, 'flat')">
               <span class="cursor-help border-b border-dotted border-gray-400">
                {{ getPrice(item.details, 'flat') }}
               </span>
            </td>
            <td class="px-6 py-4" :title="getComponents(item.details, 'valley')">
               <span class="cursor-help border-b border-dotted border-gray-400">
                {{ getPrice(item.details, 'valley') }}
               </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles if needed */
</style>
