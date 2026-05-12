<script setup lang="ts">
import UploadZone from '@/components/UploadZone.vue'
import ResultsSection from '@/components/ResultsSection.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <main>
    <UploadZone />
    <ResultsSection />
  </main>
</template>

<style scoped>
</style>
