<script setup lang="ts">
defineProps<{
  visible: boolean
  text?: string
  detail?: string
}>()
</script>

<template>
  <div v-if="visible" class="loading-overlay">
    <div class="loading-content">
      <div class="spinner"></div>
      <div class="loading-text">{{ text || '正在处理...' }}</div>
      <div class="loading-detail" v-if="detail">{{ detail }}</div>
    </div>
  </div>
</template>
