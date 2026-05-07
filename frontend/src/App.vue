<script setup lang="ts">
import { RouterView } from 'vue-router'
import Navbar from './components/Navbar.vue'
import LoadingOverlay from './components/LoadingOverlay.vue'
import SettingsModal from './components/SettingsModal.vue'
import ProjectsModal from './components/ProjectsModal.vue'
import ImagePreviewModal from './components/ImagePreviewModal.vue'
import AuthModal from './components/AuthModal.vue'
import { useGlobalStore } from './stores/global'

const globalStore = useGlobalStore()
</script>

<template>
  <Navbar />
  <div class="container">
    <RouterView />
  </div>

  <SettingsModal v-model="globalStore.showSettings" />
  <ProjectsModal v-model="globalStore.showProjects" />
  <ImagePreviewModal
    v-model="globalStore.showPreview"
    :src="globalStore.previewImageSrc"
  />
  <AuthModal :visible="globalStore.showAuth" @close="globalStore.showAuth = false" />
  <LoadingOverlay
    :visible="globalStore.loading" 
    :text="globalStore.loadingText" 
    :detail="globalStore.loadingDetail" 
  />
</template>

<style scoped>
.container {
  max-width: 1400px;
  margin: 24px auto;
  padding: 0 24px;
}
</style>
