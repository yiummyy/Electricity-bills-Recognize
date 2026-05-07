<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ExtractionResult } from '@/stores/bill'
import { useBillStore } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

const billStore = useBillStore()

const columns = [
  { key: '电费年月', label: '电费年月', editable: false },
  { key: '功率因数标准', label: '功率因数标准', editable: true },
  { key: '实际功率因数', label: '实际功率因数', editable: true },
  { key: '调整电费(元)', label: '调整电费(元)', editable: true }
]

function isLowPF(row: any) {
  const standard = parseFloat(row['功率因数标准'] || 0)
  const actual = parseFloat(row['实际功率因数'] || 0)
  return actual < standard
}

const saveEdit = async (row: any, colKey: string, newValue: any) => {
  const originalValue = row[colKey]
  
  // Validation
  let val = parseFloat(newValue)
  if (isNaN(val)) val = 0
  
  // Specific validation for Power Factor (0-1)
  if ((colKey === '功率因数标准' || colKey === '实际功率因数') && (val < 0 || val > 1)) {
    alert('功率因数必须在 0 ~ 1 之间')
    // Reset value (need to force UI update)
    row[colKey] = originalValue
    return
  }

  // Update local model
  row[colKey] = val.toFixed(2)

  try {
    const payload = {
        month: row['电费年月'],
        power_factor: {
            month: row['电费年月'],
            meter_id: row['计量点编号'],
            standard_pf: parseFloat(row['功率因数标准']),
            actual_pf: parseFloat(row['实际功率因数']),
            deviation_alert: parseFloat(row['实际功率因数']) < parseFloat(row['功率因数标准'])
        }
    }
    
    await billStore.updateBill(row._id, row['电费年月'], payload)
  } catch (e) {
    alert('保存失败')
    row[colKey] = originalValue
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <div style="display: flex; align-items: center; gap: 8px;">
        <h2 class="card-title">功率因数</h2>
        <div class="tooltip-container">
          <span class="info-icon">ℹ️</span>
          <div class="tooltip-text">功率因数越低，调整电费越高</div>
        </div>
      </div>
    </div>
    
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in data" :key="index">
            <td v-for="col in columns" :key="col.key">
              <template v-if="col.editable">
                 <input 
                    type="number"
                    step="0.01"
                    :value="row[col.key]"
                    @change="(e) => saveEdit(row, col.key, (e.target as HTMLInputElement).value)"
                    class="editable-input"
                    :class="{ 'text-red': col.key === '实际功率因数' && isLowPF(row) }"
                  />
              </template>
              <template v-else>
                 <span>{{ row[col.key] }}</span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.editable-input {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  padding: 4px;
  border-radius: 4px;
  text-align: right;
  font-family: inherit;
  font-size: inherit;
}
.editable-input:hover {
  border-color: #e5e7eb;
  background: #f9fafb;
}
.editable-input:focus {
  border-color: #165DFF;
  background: #fff;
  outline: none;
}

.info-icon {
  cursor: help;
  font-size: 16px;
}

.tooltip-container {
  position: relative;
  display: inline-block;
}

.tooltip-text {
  visibility: hidden;
  width: 200px;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 6px;
  padding: 5px;
  position: absolute;
  z-index: 1;
  bottom: 125%; /* Position above */
  left: 50%;
  margin-left: -100px;
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 12px;
}

.tooltip-container:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

.text-red {
  color: #F53F3F;
  font-weight: bold;
}
</style>
