<script setup lang="ts">
import { useBillStore } from '@/stores/bill'
import { useAuthStore } from '@/stores/auth'
import StatsCards from './StatsCards.vue'
import Charts from './Charts.vue'
import DataTable from './DataTable.vue'
import PowerFactorSection from './PowerFactorSection.vue'
import FundSection from './FundSection.vue'
import ComplexBillSection from './ComplexBillSection.vue'
import * as XLSX from 'xlsx'

const billStore = useBillStore()

function exportExcel() {
  if (billStore.extractedData.length === 0) return

  const wb = XLSX.utils.book_new()
  
  // 1. 月度电量电价数据 (Main Sheet)
  // 排除已移动到其他区块的列
  const excludeCols = [
    '功率因数标准', '实际功率因数', '调整电费(元)',
    '基金及附加电费单价(元/kWh)', '基金及代理购电价格(元/kWh)',
    '输配电价-电度电价(元/kWh)', '上网环节线损电价(元/kWh)',
    '系统运行费单价(元/kWh)', '重大水利工程建设基金(元/kWh)',
    '农网还贷基金(元/kWh)', '大中型水库移民后期扶持资金(元/kWh)',
    '可再生能源附加(元/kWh)'
  ]
  
  const mainData = billStore.extractedData.map(row => {
    const newRow: any = { ...row }
    excludeCols.forEach(col => delete newRow[col])
    return newRow
  })
  
  const wsMain = XLSX.utils.json_to_sheet(mainData)
  XLSX.utils.book_append_sheet(wb, wsMain, "月度电量电价数据")

  // 2. 功率因数 Sheet
  const pfData = billStore.extractedData.map(row => ({
    '电费年月': row['电费年月'],
    '功率因数标准': row['功率因数标准'],
    '实际功率因数': row['实际功率因数'],
    '调整电费(元)': row['调整电费(元)']
  }))
  const wsPF = XLSX.utils.json_to_sheet(pfData)
  XLSX.utils.book_append_sheet(wb, wsPF, "功率因数")

  // 3. 基金及附加 Sheet
  const fundData = billStore.extractedData.map(row => {
    // Collect all fund fields dynamically or statically
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
    const res: any = { '电费年月': row['电费年月'] }
    let total = 0
    fundFields.forEach(f => {
      res[f] = row[f]
      total += parseFloat(row[f] || 0)
    })
    res['合计单价'] = total.toFixed(4)
    return res
  })
  const wsFund = XLSX.utils.json_to_sheet(fundData)
  XLSX.utils.book_append_sheet(wb, wsFund, "基金及附加")

  XLSX.writeFile(wb, `电费单数据导出_${new Date().toISOString().slice(0,10)}.xlsx`)
}

const authStore = useAuthStore()

function getProjectsKey() {
  return `electricityProjects_${authStore.username || 'anonymous'}`
}

function saveProject() {
  const name = prompt('请输入项目名称', `项目_${new Date().toLocaleDateString()}`)
  if (name) {
    const project = {
      id: Date.now(),
      name,
      date: new Date().toLocaleDateString(),
      data: billStore.extractedData
    }
    const key = getProjectsKey()
    const projects = JSON.parse(localStorage.getItem(key) || '[]')
    projects.push(project)
    localStorage.setItem(key, JSON.stringify(projects))
    alert('项目保存成功')
  }
}
</script>

<template>
  <div v-if="billStore.extractedData.length > 0">
    <StatsCards :data="billStore.extractedData" />
    
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">数据分析图表</h2>
      </div>
      <Charts :data="billStore.extractedData" />
    </div>

    <!-- 月度电量电价数据 (原详细数据表) -->
    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
        <h2 class="card-title">月度电量电价数据</h2>
        <div class="action-group" style="margin-top: 0;">
          <button class="btn btn-secondary" @click="saveProject">保存项目</button>
          <button class="btn btn-primary" @click="exportExcel">导出 Excel</button>
        </div>
      </div>
      <DataTable :data="billStore.extractedData" />
    </div>

    <!-- 功率因数区块 -->
    <PowerFactorSection :data="billStore.extractedData" />

    <!-- 基金及附加区块 -->
    <FundSection :data="billStore.extractedData" />

    <!-- 复杂账单分时电价区块 -->
    <ComplexBillSection :data="billStore.extractedData" />
  </div>
</template>
