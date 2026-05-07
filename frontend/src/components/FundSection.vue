<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ExtractionResult } from '@/stores/bill'
import { useBillStore } from '@/stores/bill'

const props = defineProps<{
  data: ExtractionResult[]
}>()

const billStore = useBillStore()

// 基金及附加相关字段
const fundFields = [
  '基金及附加电费单价(元/kWh)',
  '基金及代理购电价格(元/kWh)',
  '输配电价-电度电价(元/kWh)',
  '上网环节线损电价(元/kWh)',
  '系统运行费单价(元/kWh)',
  '重大水利工程建设基金(元/kWh)',
  '农网还贷基金(元/kWh)',
  '大中型水库移民后期扶持资金(元/kWh)',
  '可再生能源附加(元/kWh)'
]

// Mapping for backend update
const fieldMapping: Record<string, string> = {
  '基金及附加电费单价(元/kWh)': 'fund_surcharge_price',
  '基金及代理购电价格(元/kWh)': 'fund_proxy_price',
  '输配电价-电度电价(元/kWh)': 'transmission_price',
  '上网环节线损电价(元/kWh)': 'loss_price',
  '系统运行费单价(元/kWh)': 'system_operation_price',
  '重大水利工程建设基金(元/kWh)': 'water_fund_price',
  '农网还贷基金(元/kWh)': 'rural_loan_fund_price',
  '大中型水库移民后期扶持资金(元/kWh)': 'reservoir_fund_price',
  '可再生能源附加(元/kWh)': 'renewable_energy_price'
}

const getTotal = (row: any) => {
  const prices = fundFields.map(field => parseFloat(row[field] || 0))
  const total = prices.reduce((a, b) => a + b, 0)
  return total.toFixed(4)
}

const saveEdit = async (row: any, field: string, newValue: any) => {
   const originalVal = row[field]
   
   let val = parseFloat(newValue)
   if (isNaN(val) || val < 0) {
       alert('请输入有效数值')
       row[field] = originalVal
       return
   }
   
   // Update local model
   row[field] = val.toFixed(4)
   
   try {
       // Construct payload
       const fundPayload: any = { month: row['电费年月'] }
       for (const [cnKey, enKey] of Object.entries(fieldMapping)) {
           fundPayload[enKey] = parseFloat(row[cnKey] || 0)
       }
       
       await billStore.updateBill(row._id, row['电费年月'], {
           month: row['电费年月'],
           fund_price: fundPayload
       })
   } catch (e) {
       alert('保存失败')
       row[field] = originalVal
   }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">基金及附加</h2>
    </div>
    
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th style="min-width: 100px;">电费年月</th>
            <th v-for="field in fundFields" :key="field" style="min-width: 180px;">{{ field }}</th>
            <th style="min-width: 120px; font-weight: bold;">合计单价</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in data" :key="index">
            <td>{{ row['电费年月'] }}</td>
            <td v-for="field in fundFields" :key="field">
               <input 
                  type="number"
                  step="0.0001"
                  :value="row[field]"
                  @change="(e) => saveEdit(row, field, (e.target as HTMLInputElement).value)"
                  class="editable-input"
                />
            </td>
            <td style="font-weight: bold; color: #165DFF;">
              {{ getTotal(row) }}
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

.table-wrapper {
  overflow-x: auto;
}
.data-table th, .data-table td {
  padding: 12px 16px;
  text-align: right;
}
.data-table th:first-child, .data-table td:first-child {
  text-align: left;
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 1;
  box-shadow: 2px 0 5px rgba(0,0,0,0.05);
}
.data-table th:first-child {
  background: #f7f8fa;
}
</style>
