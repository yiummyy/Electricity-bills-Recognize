<template>
  <div class="layout-review-page p-4 bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto">
      <div class="header flex justify-between items-center mb-6 bg-white p-4 rounded-lg shadow-sm sticky top-0 z-50">
        <div>
          <h2 class="text-xl font-bold text-gray-800">版面分析确认</h2>
          <p class="text-gray-500 text-sm mt-1">请确认识别区域（红色方框），确认无误后点击“开始提取”</p>
        </div>
        <div class="actions flex gap-3 items-center">
          <label class="inline-flex items-center cursor-pointer mr-2">
             <input type="checkbox" v-model="showJson" class="sr-only peer">
             <div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
             <span class="ms-3 text-sm font-medium text-gray-900">显示JSON</span>
          </label>
          <el-button @click="handleCancel">重新上传</el-button>
          <el-button type="primary" size="large" @click="handleConfirm" :loading="loading">
            确认并提取 ({{ layoutResults.length }}张)
          </el-button>
        </div>
      </div>

      <div v-if="layoutResults.length === 0" class="text-center py-20 text-gray-400">
        暂无数据，请先上传文件
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div v-for="(result, idx) in layoutResults" :key="idx" class="bg-white rounded-lg shadow-md overflow-hidden flex flex-col">
          <div class="p-3 border-b bg-gray-50 flex justify-between items-center">
            <span class="font-medium text-gray-700 truncate max-w-[70%]" :title="result.file_name">{{ result.file_name }}</span>
            <span class="text-xs text-gray-400">耗时: {{ Math.round(result.processing_time_ms) }}ms</span>
          </div>
          
          <div class="relative w-full bg-gray-100 flex-grow flex items-center justify-center p-2" style="min-height: 300px;">
            <!-- JSON View -->
            <div v-if="showJson" class="w-full h-full bg-gray-50 p-4 overflow-auto text-xs font-mono whitespace-pre text-gray-700" style="max-height: 800px;">
{{ JSON.stringify(result.regions, null, 2) }}
            </div>
            
            <!-- Image View -->
            <div v-else class="relative inline-block">
               <img 
                 :src="`data:image/png;base64,${result.image_base64}`" 
                 class="block max-w-full max-h-[800px] w-auto h-auto" 
                 style="user-select: none;"
               />
               
               <!-- Overlay Boxes -->
               <div v-for="region in result.regions" :key="region.id"
                    class="absolute border border-red-500 hover:bg-red-500 hover:bg-opacity-20 transition-colors duration-200 cursor-help"
                    :style="getBoxStyle(region.box, result.image_width, result.image_height)"
                    :title="region.text">
               </div>
            </div>
          </div>
          
          <div class="p-3 bg-gray-50 text-xs text-gray-500 border-t flex justify-between">
            <span>识别区域: {{ result.regions.length }} 个</span>
            <span>分辨率: {{ result.image_width }}x{{ result.image_height }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBillStore } from '@/stores/bill'
import { useGlobalStore } from '@/stores/global'
import { ElMessage } from 'element-plus'

const router = useRouter()
const billStore = useBillStore()
const globalStore = useGlobalStore()

const layoutResults = computed(() => billStore.layoutResults)
const loading = computed(() => globalStore.loading)
const showJson = ref(false)

// Convert box [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] to style percentages
function getBoxStyle(box: number[][], imgW: number, imgH: number) {
    if (!imgW || !imgH) return {}
    
    // PaddleOCR returns 4 points. We take bounding box of them.
    const xs = box.map(p => p[0])
    const ys = box.map(p => p[1])
    
    const x1 = Math.min(...xs)
    const y1 = Math.min(...ys)
    const x2 = Math.max(...xs)
    const y2 = Math.max(...ys)
    
    const w = x2 - x1
    const h = y2 - y1
    
    return {
        left: `${(x1 / imgW) * 100}%`,
        top: `${(y1 / imgH) * 100}%`,
        width: `${(w / imgW) * 100}%`,
        height: `${(h / imgH) * 100}%`
    }
}

async function handleConfirm() {
    try {
        await billStore.extractFromLayouts()
        if (billStore.extractedData.length > 0) {
            router.push('/')
        } else {
            ElMessage.warning('未能提取到任何有效数据，请检查版面分析结果或重试')
        }
    } catch (e) {
        console.error(e)
        ElMessage.error('提取过程发生错误，请查看控制台')
    }
}

function handleCancel() {
    billStore.clearAll()
    router.push('/')
}
</script>

<style scoped>
/* Optional: specific styles if tailwind is missing some */
</style>
