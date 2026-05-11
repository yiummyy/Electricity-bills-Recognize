<script setup lang="ts">
import UploadZone from '@/components/UploadZone.vue'
import ResultsSection from '@/components/ResultsSection.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <main>
    <div class="welcome-banner" v-if="!authStore.isLoggedIn">
      <div class="welcome-icon">⚡</div>
      <h1 class="welcome-title">欢迎使用电费单智能分析系统</h1>
      <p class="welcome-desc">登录后即可上传电费单据，自动识别并分析用电数据</p>
      <p class="welcome-hint">请点击右上角 <strong>「登录」</strong> 按钮开始使用</p>
    </div>
    <UploadZone />
    <ResultsSection />
  </main>
</template>

<style scoped>
.welcome-banner {
  text-align: center;
  padding: 48px 24px 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: #fff;
  margin-bottom: 24px;
}
.welcome-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.welcome-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px 0;
}
.welcome-desc {
  font-size: 16px;
  opacity: 0.9;
  margin: 0 0 8px 0;
}
.welcome-hint {
  font-size: 14px;
  opacity: 0.75;
  margin: 0;
}
</style>
