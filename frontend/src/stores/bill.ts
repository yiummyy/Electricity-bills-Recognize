import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import { useGlobalStore } from './global'
import { scheduler } from '@/utils/scheduler'

export interface UploadedFile {
  id: string
  file: File
  status: 'pending' | 'processing' | 'success' | 'error'
  previewSrc?: string
  isPdf?: boolean
}

export interface ExtractionResult {
  _id?: string
  // Define based on backend response
  [key: string]: any
}

export interface LayoutItem {
  id: number
  box: number[][] // [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
  text: string
  confidence: number
  type: string
}

export interface LayoutResult {
  file_name: string
  file_token: string
  image_base64: string
  image_width: number
  image_height: number
  regions: LayoutItem[]
  processing_time_ms: number
}

export const useBillStore = defineStore('bill', () => {
  const uploadedFiles = ref<UploadedFile[]>([])
  const extractedData = ref<ExtractionResult[]>([])
  const layoutResults = ref<LayoutResult[]>([])
  const globalStore = useGlobalStore()

  function addFiles(files: FileList | File[]) {
    Array.from(files).forEach((file, index) => {
      if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
        alert(`文件 ${file.name} 格式不支持，已跳过`)
        return
      }

      const fileId = `file_${Date.now()}_${index}`
      const isPdf = file.type === 'application/pdf'
      const fileObj: UploadedFile = {
        id: fileId,
        file: file,
        status: 'pending',
        isPdf
      }

      if (!isPdf) {
        const reader = new FileReader()
        reader.onload = (e) => {
          fileObj.previewSrc = e.target?.result as string
        }
        reader.readAsDataURL(file)
      }

      uploadedFiles.value.push(fileObj)
    })
  }

  function removeFile(fileId: string) {
    uploadedFiles.value = uploadedFiles.value.filter(f => f.id !== fileId)
  }

  function clearAll() {
    uploadedFiles.value = []
    extractedData.value = []
  }

  async function processAll() {
    if (uploadedFiles.value.length === 0) return

    globalStore.showLoading('正在识别电费单数据...', '这可能需要几分钟时间')
    extractedData.value = []
    
    // Reset statuses
    uploadedFiles.value.forEach(f => f.status = 'pending')

    const total = uploadedFiles.value.length
    let completed = 0

    // Use scheduler for concurrent processing
    const tasks = uploadedFiles.value.map((fileObj, index) => {
      return scheduler.submit(async () => {
        fileObj.status = 'processing'
        try {
          const formData = new FormData()
          formData.append('file', fileObj.file)
          
          const response = await api.post('/extract', formData, { timeout: 600000 })
          const data = mapBackendToFrontend(response.data, index)
          
          // Push to extractedData (thread-safe in JS single thread event loop)
          extractedData.value.push(...data)
          fileObj.status = 'success'
        } catch (e) {
          console.error(`File ${index} failed:`, e)
          fileObj.status = 'error'
          extractedData.value.push(getEmptyDataTemplate(index))
          throw e // Re-throw to let scheduler know it failed
        } finally {
          completed++
          globalStore.loadingText = `正在处理... (${completed}/${total})`
        }
      }, {
        id: `extract_${fileObj.id}`,
        priority: 1,
        timeout: 600000, // 10 minutes
        retries: 1
      }).catch(err => {
        // Handled in scheduler, but catch here to prevent Promise.all failure if needed
        console.warn(`Task for ${fileObj.file.name} failed final`, err)
      })
    })

    await Promise.all(tasks)

    globalStore.hideLoading()
  }

  async function analyzeAllFiles() {
    if (uploadedFiles.value.length === 0) return

    globalStore.showLoading('正在进行版面分析...', '识别文本与表格区域')
    layoutResults.value = []
    
    // Reset statuses
    uploadedFiles.value.forEach(f => f.status = 'pending')

    const total = uploadedFiles.value.length
    let completed = 0

    const tasks = uploadedFiles.value.map((fileObj, index) => {
      return scheduler.submit(async () => {
        fileObj.status = 'processing'
        try {
          const formData = new FormData()
          formData.append('file', fileObj.file)
          
          const response = await api.post('/layout/analyze', formData, { timeout: 600000 })
          layoutResults.value.push(response.data)
          fileObj.status = 'success'
        } catch (e) {
          console.error(`Layout Analysis for ${fileObj.file.name} failed:`, e)
          fileObj.status = 'error'
          throw e
        } finally {
          completed++
          globalStore.loadingText = `正在分析... (${completed}/${total})`
        }
      }, {
        id: `analyze_${fileObj.id}`,
        priority: 1,
        timeout: 600000,
        retries: 1
      })
    })

    await Promise.all(tasks)
    globalStore.hideLoading()
  }

  async function extractFromLayouts() {
     if (layoutResults.value.length === 0) return
     
     globalStore.showLoading('正在提取字段...', '调用 LLM 进行结构化提取')
     extractedData.value = []
     
     const total = layoutResults.value.length
     let completed = 0
     
     const tasks = layoutResults.value.map((layout, index) => {
         const task = scheduler.submit(async () => {
              try {
                  const formData = new FormData()
                  formData.append('file_token', layout.file_token)
                  
                  const response = await api.post('/layout/extract', formData, { timeout: 600000 })
                  console.log('Backend response for extract:', response.data) // Debug Log
                  const data = mapBackendToFrontend(response.data, index)
                  console.log('Mapped Frontend Data:', data) // Debug Log
                  extractedData.value.push(...data)
              } catch (e) {
                  console.error(`Extraction failed for ${layout.file_name}`, e)
                  // On failure, push empty template to keep order/count correct?
                  // Or we can just filter out failed ones.
                  // For now, let's push empty template but handle duplicate pushes if retries happen (which we disabled)
                  extractedData.value.push(getEmptyDataTemplate(index))
                  throw e 
              }
         }, {
              id: `extract_${layout.file_token}`,
              priority: 1,
              retries: 0 // Disable retries
         })
         
         // Update progress
         task.finally(() => {
             completed++
             globalStore.loadingText = `正在提取... (${completed}/${total})`
         })
         
         return task
      })
      
      // Use allSettled to ensure we wait for all, even if some fail
      await Promise.allSettled(tasks)
     globalStore.hideLoading()
  }

  async function updateBill(id: string, month: string, data: any) {
    if (!id) {
        console.warn('Cannot update bill without ID');
        return;
    }
    try {
        await api.put(`/bills/${id}/months/${month}`, data);
        console.log('Bill updated successfully');
    } catch (e) {
        console.error('Update failed', e);
        throw e;
    }
  }

  // Helpers (Migrated from HTML)
  function mapBackendToFrontend(data: any, index: number) {
    const processRow = (usage: any, pf: any, fund: any, month: string, detailedPrices: any = null) => {
        const getVal = (val: any) => {
            if (val === null || val === undefined) return 0;
            return parseFloat(val) || 0;
        };

        const fmt = (val: any, decimals = 2) => {
             return getVal(val).toFixed(decimals);
        };
        
        return {
            _id: data.id || data._id,
            '电费年月': month,
            '用户编号': usage.user_id || pf.meter_id || '-',
            '结算户号': usage.settlement_account_no || '-',
            '电表编号': usage.meter_no || '-',
            '结算户名': usage.settlement_name || '-', 
            '供电电压': usage.voltage_level || '-', 
            '用电类别': usage.usage_category || '-',
            '计量点编号': pf.meter_id || '-',
            
            '尖时电量(kWh)': fmt(usage.peak_usage),
            '尖时电价(元/kWh)': fmt(usage.peak_price, 4),
            '峰段电量(kWh)': fmt(usage.shoulder_usage),
            '峰段电价(元/kWh)': fmt(usage.shoulder_price, 4),
            '平段电量(kWh)': fmt(usage.flat_usage),
            '平段电价(元/kWh)': fmt(usage.flat_price, 4),
            '谷段电量(kWh)': fmt(usage.valley_usage),
            '谷段电价(元/kWh)': fmt(usage.valley_price, 4),
            '深谷段电量(kWh)': '0.00',
            '深谷段电价(元/kWh)': '0.0000',

            // Complex Bill Detailed Prices (If available)
            '分时电价明细': detailedPrices ? JSON.stringify(detailedPrices) : '-',

            '总电量(kWh)': fmt(usage.total_usage),
            '总电费(元)': fmt(usage.total_cost),
            
            '功率因数标准': pf.standard_pf || 0,
            '实际功率因数': pf.actual_pf || 0,
            '调整电费(元)': '0.00',
            
            '基金及附加电费单价(元/kWh)': fmt(fund.fund_surcharge_price, 4),
            '基金及代理购电价格(元/kWh)': fmt(fund.fund_proxy_price, 4),
            '输配电价-电度电价(元/kWh)': fmt(fund.transmission_price, 4),
            '上网环节线损电价(元/kWh)': fmt(fund.loss_price, 4),
            '系统运行费单价(元/kWh)': fmt(fund.system_operation_price, 4),
            '重大水利工程建设基金(元/kWh)': fmt(fund.water_fund_price, 4),
            '农网还贷基金(元/kWh)': fmt(fund.rural_loan_fund_price, 4),
            '大中型水库移民后期扶持资金(元/kWh)': fmt(fund.reservoir_fund_price, 4),
            '可再生能源附加(元/kWh)': fmt(fund.renewable_energy_price, 4)
        };
    };

    if (data.monthly_bills && Array.isArray(data.monthly_bills) && data.monthly_bills.length > 0) {
        return data.monthly_bills.map((bill: any) => {
            return processRow(
                bill.usage || {},
                bill.power_factor || {},
                bill.fund_price || {},
                bill.month || "Unknown",
                bill.detailed_prices // Pass detailed_prices explicitly
            );
        });
    } else {
        // Fallback for old format or if monthly_bills is empty
        const usage = data.usage || {};
        const pf = data.power_factor || {};
        const fund = data.fund_price || {};
        const monthStr = pf.month || fund.month || `2024-${String(index + 1).padStart(2, '0')}`;
        // Fallback doesn't support detailed_prices yet unless we extract it from root
        return [processRow(usage, pf, fund, monthStr, data.detailed_prices)];
    }
  }

  function getEmptyDataTemplate(index: number) {
     const monthStr = `${new Date().getFullYear()}-${String(index + 1).padStart(2, '0')}`;
     return {
        '电费年月': monthStr,
        '用户编号': '-',
        '结算户名': '识别失败',
        '总电量(kWh)': '0.00',
        '总电费(元)': '0.00',
        '尖时电量(kWh)': '0.00', '尖时电价(元/kWh)': '0.0000',
        '峰段电量(kWh)': '0.00', '峰段电价(元/kWh)': '0.0000',
        '平段电量(kWh)': '0.00', '平段电价(元/kWh)': '0.0000',
        '谷段电量(kWh)': '0.00', '谷段电价(元/kWh)': '0.0000'
     };
  }

  return {
    uploadedFiles,
    extractedData,
    layoutResults,
    addFiles,
    removeFile,
    clearAll,
    processAll,
    analyzeAllFiles,
    extractFromLayouts,
    updateBill
  }
})
