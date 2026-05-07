import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useGlobalStore = defineStore('global', () => {
  const loading = ref(false)
  const loadingText = ref('')
  const loadingDetail = ref('')
  
  const showSettings = ref(false)
  const showProjects = ref(false)
  const showPreview = ref(false)
  const showAuth = ref(false)
  const previewImageSrc = ref('')

  function showLoading(text: string, detail: string = '') {
    loading.value = true
    loadingText.value = text
    loadingDetail.value = detail
  }

  function hideLoading() {
    loading.value = false
  }

  function openPreview(src: string) {
    previewImageSrc.value = src
    showPreview.value = true
  }

  return {
    loading,
    loadingText,
    loadingDetail,
    showSettings,
    showProjects,
    showPreview,
    showAuth,
    previewImageSrc,
    showLoading,
    hideLoading,
    openPreview
  }
})
