<script setup lang="ts">
import { useBillStore } from '@/stores/bill'
import { useAuthStore } from '@/stores/auth'
import { useGlobalStore } from '@/stores/global'
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const billStore = useBillStore()
const authStore = useAuthStore()
const globalStore = useGlobalStore()
const router = useRouter()
const fileInput = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files) {
    billStore.addFiles(target.files)
  }
}

function onDrop(e: DragEvent) {
  isDragOver.value = false
  if (e.dataTransfer?.files) {
    billStore.addFiles(e.dataTransfer.files)
  }
}

function triggerFileInput() {
  fileInput.value?.click()
}

function removeFile(id: string) {
  billStore.removeFile(id)
}

function previewImage(src: string) {
  globalStore.openPreview(src)
}

async function handleAnalyze() {
    // Use direct /extract endpoint (OCR + LLM in one call)
    // The two-step layout flow (/layout/analyze + /layout/extract) is available
    // via the /layout-review route for cases needing manual layout correction
    await billStore.processAll()

    // Scroll to results
    await nextTick()
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    })
}
</script>

<template>
  <div class="card" id="uploadCard">
    <div class="card-header">
      <h1 class="card-title">上传电费单</h1>
      <p class="card-subtitle">批量上传电费单图片，系统将自动识别并分析数据</p>
    </div>

    <div 
      class="upload-area" 
      :class="{ dragover: isDragOver, disabled: !authStore.isLoggedIn }"
      @click="authStore.isLoggedIn && triggerFileInput()"
      @dragover.prevent="authStore.isLoggedIn && (isDragOver = true)"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="authStore.isLoggedIn && onDrop($event)"
    >
      <div class="upload-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M40 18L24 6L8 18V40H40V18Z" stroke="#8f959e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M24 34V20M18 26L24 20L30 26" stroke="#8f959e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="upload-title">点击或拖拽上传电费单</div>
      <div class="upload-subtitle">支持 JPG、PNG、PDF 格式，可同时上传多个文件</div>
      <div class="login-overlay" v-if="!authStore.isLoggedIn">
        <span>请先登录后再上传文件</span>
      </div>
      <input 
        type="file" 
        ref="fileInput" 
        multiple 
        accept="image/*,.pdf" 
        style="display: none;"
        @change="onFileChange"
      >
    </div>

    <div class="preview-grid" v-if="billStore.uploadedFiles.length > 0">
      <div 
        v-for="file in billStore.uploadedFiles" 
        :key="file.id" 
        class="preview-item"
      >
        <button class="remove-btn" @click.stop="removeFile(file.id)">×</button>
        
        <div v-if="file.isPdf" style="width: 100%; height: 120px; display: flex; align-items: center; justify-content: center; background: #f7f8fa;">
           <span style="font-size: 24px;">PDF</span>
        </div>
        <img 
          v-else 
          :src="file.previewSrc" 
          class="preview-image" 
          @click.stop="file.previewSrc && previewImage(file.previewSrc)"
        >
        
        <div class="preview-info">
          <div class="preview-name">{{ file.file.name }}</div>
          <span class="preview-badge" :class="`badge-${file.status}`">
            {{ file.status === 'pending' ? '待处理' : file.status === 'processing' ? '识别中' : file.status === 'success' ? '完成' : '失败' }}
          </span>
        </div>
      </div>
    </div>

    <div class="action-group">
      <button 
        class="btn btn-primary" 
        :disabled="billStore.uploadedFiles.length === 0 || !authStore.isLoggedIn" 
        @click="handleAnalyze"
      >
        {{ authStore.isLoggedIn ? '开始识别' : '请先登录' }}
      </button>
      <button class="btn btn-secondary" @click="billStore.clearAll()">
        清空文件
      </button>
    </div>
  </div>
</template>
