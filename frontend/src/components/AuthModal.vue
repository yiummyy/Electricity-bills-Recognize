<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const authStore = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const user = ref('')
const pass = ref('')
const error = ref('')
const loading = ref(false)

watch(() => props.visible, (v) => {
  if (v) { user.value = ''; pass.value = ''; error.value = '' }
})

async function submit() {
  if (!user.value || !pass.value) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'login') {
      await authStore.login(user.value, pass.value)
    } else {
      await authStore.register(user.value, pass.value)
    }
    emit('close')
  } catch (e: any) {
    let msg = e.response?.data?.detail || e.message || '操作失败'
    if (msg === 'Incorrect username or password') msg = '用户名或密码错误'
    if (msg === 'Username already exists') msg = '用户名已存在'
    error.value = msg
  } finally {
    loading.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <h2>{{ mode === 'login' ? '登录' : '注册' }}</h2>
        <button class="modal-close" @click="emit('close')">✕</button>
      </div>
      <form @submit.prevent="submit" class="modal-body">
        <div class="field">
          <label>用户名</label>
          <input v-model="user" type="text" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="pass" type="password" placeholder="请输入密码（至少6位）" autocomplete="current-password" />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? '请稍候...' : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>
      <div class="modal-footer">
        <span v-if="mode === 'login'">还没有账号？</span>
        <span v-else>已有账号？</span>
        <a href="#" @click.prevent="switchMode">
          {{ mode === 'login' ? '立即注册' : '去登录' }}
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  background: #fff;
  border-radius: 12px;
  width: 380px;
  max-width: 90vw;
  box-shadow: 0 8px 30px rgba(0,0,0,0.15);
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid #f1f5f9;
}
.modal-header h2 { font-size: 18px; font-weight: 600; margin: 0; }
.modal-close {
  background: none; border: none; font-size: 18px; cursor: pointer;
  color: #94a3b8; padding: 4px 8px; border-radius: 4px;
}
.modal-close:hover { color: #475569; background: #f1f5f9; }
.modal-body { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 500; color: #374151; }
.field input {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.field input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
.error-msg {
  font-size: 13px; color: #dc2626; background: #fef2f2;
  padding: 8px 12px; border-radius: 6px; border: 1px solid #fecaca;
}
.btn-submit {
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 10px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-submit:hover { background: #1d4ed8; }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
.modal-footer {
  padding: 14px 24px;
  border-top: 1px solid #f1f5f9;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}
.modal-footer a { color: #2563eb; text-decoration: none; font-weight: 500; }
.modal-footer a:hover { text-decoration: underline; }
</style>
