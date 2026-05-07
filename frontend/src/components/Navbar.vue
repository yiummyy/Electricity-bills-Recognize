<script setup lang="ts">
import { useGlobalStore } from '@/stores/global'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const globalStore = useGlobalStore()
const authStore = useAuthStore()
const router = useRouter()
</script>

<template>
  <nav class="navbar">
    <div class="navbar-content">
      <div class="navbar-brand cursor-pointer" @click="router.push('/')">
        <div class="brand-icon">⚡</div>
        <span>电费单智能分析系统</span>
      </div>
      <div class="navbar-actions">
        <button v-if="authStore.isAdmin" class="btn btn-text" @click="globalStore.showSettings = true">
          <span style="font-size: 16px; margin-right: 4px;">⚙️</span> 设置
        </button>
        <button class="btn btn-text" @click="globalStore.showProjects = true">
          历史项目
        </button>

        <!-- Logged in -->
        <template v-if="authStore.isLoggedIn">
          <span class="user-badge">
            <span class="user-role-dot" :class="authStore.isAdmin ? 'dot-admin' : 'dot-user'"></span>
            {{ authStore.username }}
            <span class="role-tag">{{ authStore.isAdmin ? '管理员' : '用户' }}</span>
          </span>
          <button class="btn btn-secondary btn-sm" @click="authStore.logout()">退出</button>
        </template>

        <!-- Not logged in -->
        <button v-else class="btn btn-primary btn-sm" @click="globalStore.showAuth = true">登录</button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.user-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}
.user-role-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-admin { background: #f59e0b; }
.dot-user { background: #22c55e; }
.role-tag {
  font-size: 11px;
  font-weight: 400;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #6b7280;
}
.btn-sm {
  padding: 5px 14px;
  font-size: 13px;
}
</style>
