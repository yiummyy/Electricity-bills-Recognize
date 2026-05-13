<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()

const provider = ref('deepseek')
const model = ref('deepseek-chat')
const apiKey = ref('')
const apiBase = ref('')
const embeddingPath = ref('./models/embedding/default')

const localModels = ref<string[]>([])

const tokenBuckets = ref<any[]>([])
const tokenTotal = ref({ total_prompt_tokens: 0, total_completion_tokens: 0, total_tokens: 0, total_llm_calls: 0 })
const tokenHours = ref(24)
const tokenLoading = ref(false)

const activeTab = ref('config')

interface UserItem {
  username: string
  role: string
  created_at: string | null
  updated_at: string | null
}

const users = ref<UserItem[]>([])
const usersLoading = ref(false)
const showAddForm = ref(false)
const editTarget = ref<string | null>(null)
const userForm = ref({ username: '', password: '', role: 'user' })
const userFormError = ref('')
const userFormSaving = ref(false)

async function loadSettings() {
  if (authStore.token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${authStore.token}`
  }
  try {
    const res = await api.get('/config/system')
    const data = res.data
    provider.value = data.llm.provider
    model.value = data.llm.model
    apiBase.value = data.llm.api_base || ''
  } catch (e) {
    console.error('Failed to load settings', e)
  }
  loadLocalModels()
  loadTokenUsage()
}

async function loadLocalModels() {
  try {
    const res = await api.get('/config/models')
    localModels.value = res.data.local_models || []
  } catch (e) {
    console.error('Failed to load local models', e)
  }
}

async function loadTokenUsage() {
  tokenLoading.value = true
  try {
    const res = await api.get('/config/token-usage', { params: { hours: tokenHours.value } })
    tokenBuckets.value = res.data.buckets || []
    tokenTotal.value = {
      total_prompt_tokens: res.data.total_prompt_tokens || 0,
      total_completion_tokens: res.data.total_completion_tokens || 0,
      total_tokens: res.data.total_tokens || 0,
      total_llm_calls: res.data.total_llm_calls || 0,
    }
  } catch (e) {
    console.error('Failed to load token usage', e)
  } finally {
    tokenLoading.value = false
  }
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function maxTokens(): number {
  let max = 0
  for (const b of tokenBuckets.value) {
    if (b.total_tokens > max) max = b.total_tokens
  }
  return max || 1
}

function hourLabel(hourKey: string): string {
  try {
    const t = new Date(hourKey.replace('Z', '+00:00').replace('T', ' '))
    return t.getHours().toString().padStart(2, '0') + ':00'
  } catch {
    return hourKey
  }
}

function formatTime(isoStr: string | null): string {
  if (!isoStr) return '—'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return isoStr
  }
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const res = await api.get('/users')
    users.value = res.data
  } catch (e) {
    console.error('Failed to load users', e)
  } finally {
    usersLoading.value = false
  }
}

function startAdd() {
  showAddForm.value = true
  editTarget.value = null
  userForm.value = { username: '', password: '', role: 'user' }
  userFormError.value = ''
}

function startEdit(u: UserItem) {
  showAddForm.value = false
  editTarget.value = u.username
  userForm.value = { username: u.username, password: '', role: u.role }
  userFormError.value = ''
}

function cancelForm() {
  showAddForm.value = false
  editTarget.value = null
  userFormError.value = ''
}

async function submitUserForm() {
  userFormError.value = ''
  userFormSaving.value = true
  try {
    if (editTarget.value) {
      const body: any = { role: userForm.value.role }
      if (userForm.value.password) body.password = userForm.value.password
      await api.put(`/users/${editTarget.value}`, body)
    } else {
      await api.post('/users', {
        username: userForm.value.username,
        password: userForm.value.password,
        role: userForm.value.role,
      })
    }
    cancelForm()
    await loadUsers()
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.message || '操作失败'
    userFormError.value = detail
  } finally {
    userFormSaving.value = false
  }
}

async function deleteUser(username: string) {
  if (!confirm(`确认删除用户「${username}」？`)) return
  try {
    await api.delete(`/users/${username}`)
    await loadUsers()
  } catch (e: any) {
    alert(e.response?.data?.detail || e.message || '删除失败')
  }
}

async function save() {
  // Ensure auth header is set before API call
  if (authStore.token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${authStore.token}`
  } else {
    alert('请先以管理员身份登录后再修改配置')
    return
  }

  if (!authStore.isAdmin) {
    alert('仅管理员可修改系统配置。当前角色：' + authStore.role)
    return
  }

  const formData = new FormData()
  formData.append('provider', provider.value)
  formData.append('model', model.value)
  if (apiKey.value) formData.append('api_key', apiKey.value)
  if (apiBase.value) formData.append('api_base', apiBase.value)

  try {
    await api.post('/config/llm', formData)
    
    if (embeddingPath.value) {
      const embForm = new FormData()
      embForm.append('model_type', 'embedding')
      embForm.append('model_path', embeddingPath.value)
      try {
        await api.post('/config/embedding', embForm)
      } catch (e) {
        console.warn('Embedding config failed', e)
      }
    }
    
    alert('配置已保存')
    close()
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.message
    if (e.response?.status === 401) {
      alert('保存失败: 登录已过期，请重新登录后再试')
    } else if (e.response?.status === 403) {
      alert('保存失败: 仅管理员可修改系统配置，请使用管理员账号登录')
    } else {
      alert('保存失败: ' + detail)
    }
  }
}

function close() {
  emit('update:modelValue', false)
  activeTab.value = 'config'
}

watch(() => props.modelValue, (val) => {
  if (val) {
    loadSettings()
    loadUsers()
  }
})

watch(activeTab, (val) => {
  if (val === 'users') loadUsers()
})
</script>

<template>
  <div v-if="modelValue" class="modal active">
    <div class="modal-content" style="max-width: 720px; max-height: 85vh; overflow-y: auto;">
      <div class="modal-header">
        <h3 class="modal-title">系统设置</h3>
        <button class="modal-close" @click="close">✕</button>
      </div>

      <div class="settings-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'config' }"
          @click="activeTab = 'config'"
        >⚙️ 系统配置</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >👥 账号管理</button>
      </div>

      <!-- Tab: 系统配置 -->
      <div v-show="activeTab === 'config'">
        <div class="form-group">
          <h4 style="margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px;">LLM 模型配置</h4>
          <label class="form-label">供应商 (Provider)</label>
          <select class="form-input" v-model="provider">
            <option value="deepseek">DeepSeek</option>
            <option value="tongyi">通义千问</option>
            <option value="wenxin">文心一言</option>
            <option value="vllm">本地 vLLM</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">模型名称 (Model Name)</label>
          <input type="text" class="form-input" v-model="model" placeholder="e.g. deepseek-chat">
        </div>
        <div class="form-group">
          <label class="form-label">API Key</label>
          <input type="password" class="form-input" v-model="apiKey" placeholder="留空则不修改">
        </div>
        <div class="form-group">
          <label class="form-label">API Base URL</label>
          <input type="text" class="form-input" v-model="apiBase" placeholder="留空则根据供应商自动推断">
        </div>

        <div class="form-group" style="margin-top: 24px;">
          <h4 style="margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px;">Embedding 模型配置</h4>
          <label class="form-label">Embedding 模型</label>
          <select v-if="localModels.length > 0" class="form-input" v-model="embeddingPath">
            <option v-for="m in localModels" :key="m" :value="'./models/embedding/' + m">{{ m }}</option>
          </select>
          <input v-else type="text" class="form-input" v-model="embeddingPath" placeholder="./models/embedding/default">
        </div>

        <div style="margin-top: 28px;">
          <h4 style="margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px;">
            Token 消耗看板
            <span style="font-weight: normal; font-size: 13px; color: #999; margin-left: 8px;">
              24 小时累计: {{ formatTokens(tokenTotal.total_tokens) }} tokens / {{ tokenTotal.total_llm_calls }} 次调用
            </span>
          </h4>
          
          <div v-if="tokenLoading" style="text-align: center; padding: 20px; color: #999;">加载中…</div>
          
          <div v-else-if="tokenBuckets.length === 0" style="text-align: center; padding: 20px; color: #999;">
            暂无 Token 消耗记录
          </div>
          
          <div v-else class="token-dashboard">
            <div class="token-stats-row">
              <div class="token-stat">
                <div class="token-stat-value">{{ formatTokens(tokenTotal.total_prompt_tokens) }}</div>
                <div class="token-stat-label">输入 Tokens</div>
              </div>
              <div class="token-stat">
                <div class="token-stat-value">{{ formatTokens(tokenTotal.total_completion_tokens) }}</div>
                <div class="token-stat-label">输出 Tokens</div>
              </div>
              <div class="token-stat">
                <div class="token-stat-value">{{ formatTokens(tokenTotal.total_tokens) }}</div>
                <div class="token-stat-label">总计 Tokens</div>
              </div>
              <div class="token-stat">
                <div class="token-stat-value">{{ tokenTotal.total_llm_calls }}</div>
                <div class="token-stat-label">LLM 调用次数</div>
              </div>
            </div>
            
            <div class="token-bar-chart">
              <div v-for="b in tokenBuckets" :key="b.hour" class="token-bar-item">
                <div class="token-bar-label">{{ hourLabel(b.hour) }}</div>
                <div class="token-bar-track">
                  <div
                    class="token-bar-fill"
                    :style="{
                      width: (maxTokens() > 0 ? (b.total_tokens / maxTokens()) * 100 : 0) + '%'
                    }"
                    :title="`${b.total_tokens} tokens (${b.llm_calls} 次调用)`"
                  ></div>
                </div>
                <div class="token-bar-value">{{ formatTokens(b.total_tokens) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-actions" style="margin-top: 24px;">
          <button class="btn btn-secondary" @click="close">取消</button>
          <button class="btn btn-primary" @click="save">保存配置</button>
        </div>
      </div>

      <!-- Tab: 账号管理 -->
      <div v-show="activeTab === 'users'">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h4 style="margin: 0;">系统中所有账号</h4>
          <button class="btn btn-primary btn-sm" @click="startAdd" v-if="!showAddForm && !editTarget">+ 添加账号</button>
        </div>

        <!-- Add / Edit Form -->
        <div v-if="showAddForm || editTarget" class="user-form-card">
          <h4>{{ editTarget ? '修改账号' : '添加账号' }}</h4>
          <div class="field" v-if="!editTarget">
            <label>用户名</label>
            <input v-model="userForm.username" type="text" placeholder="2-32 位" class="form-input" />
          </div>
          <div class="field">
            <label>{{ editTarget ? '新密码' : '密码' }} <span style="color:#999;font-weight:400;font-size:12px;">（{{ editTarget ? '留空则不修改' : '至少6位' }}）</span></label>
            <input v-model="userForm.password" type="password" :placeholder="editTarget ? '留空则不修改密码' : '至少6位'" class="form-input" />
          </div>
          <div class="field">
            <label>角色</label>
            <select v-model="userForm.role" class="form-input">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div v-if="userFormError" class="error-msg">{{ userFormError }}</div>
          <div style="display: flex; gap: 8px; margin-top: 12px;">
            <button class="btn btn-primary btn-sm" @click="submitUserForm" :disabled="userFormSaving">
              {{ userFormSaving ? '保存中…' : (editTarget ? '更新' : '创建') }}
            </button>
            <button class="btn btn-secondary btn-sm" @click="cancelForm">取消</button>
          </div>
        </div>

        <!-- Users Table -->
        <div v-if="usersLoading" style="text-align: center; padding: 20px; color: #999;">加载中…</div>

        <div v-else-if="users.length === 0" style="text-align: center; padding: 20px; color: #999;">
          暂无注册账号（默认管理员 admin 通过兜底机制生效）
        </div>

        <table v-else class="users-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>角色</th>
              <th>创建时间</th>
              <th>最后修改</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.username" :class="{ 'row-editing': editTarget === u.username }">
              <td>
                <span class="username-cell">{{ u.username }}</span>
                <span v-if="u.username === 'admin'" class="default-tag">出厂默认</span>
              </td>
              <td>
                <span class="role-badge" :class="u.role === 'admin' ? 'role-admin' : 'role-user'">
                  {{ u.role === 'admin' ? '管理员' : '用户' }}
                </span>
              </td>
              <td class="time-cell">{{ formatTime(u.created_at) }}</td>
              <td class="time-cell">{{ formatTime(u.updated_at) }}</td>
              <td class="action-cell">
                <button class="btn btn-text btn-xs" @click="startEdit(u)">编辑</button>
                <button class="btn btn-text btn-xs btn-danger" @click="deleteUser(u.username)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.token-dashboard {
  margin-top: 8px;
}

.token-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.token-stat {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
}

.token-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}

.token-stat-label {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.token-bar-chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-bar-label {
  width: 42px;
  font-size: 11px;
  color: #666;
  text-align: right;
  flex-shrink: 0;
}

.token-bar-track {
  flex: 1;
  height: 14px;
  background: #eee;
  border-radius: 7px;
  overflow: hidden;
}

.token-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 7px;
  transition: width 0.3s ease;
  min-width: 2px;
}

.token-bar-value {
  width: 48px;
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
}

.settings-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 20px;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover {
  color: #374151;
}

.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #94a3b8;
  padding: 4px 8px;
  border-radius: 4px;
}

.modal-close:hover {
  color: #475569;
  background: #f1f5f9;
}

.user-form-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.user-form-card h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.field label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.field input,
.field select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}

.field input:focus,
.field select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.error-msg {
  font-size: 13px;
  color: #dc2626;
  background: #fef2f2;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #fecaca;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.users-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid #e5e7eb;
  color: #6b7280;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.users-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  color: #374151;
}

.users-table tr.row-editing td {
  background: #eff6ff;
}

.users-table tr:hover td {
  background: #f9fafb;
}

.username-cell {
  font-weight: 600;
  color: #1f2937;
}

.default-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 4px;
  background: #fef3c7;
  color: #92400e;
  margin-left: 6px;
  vertical-align: middle;
}

.role-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.role-admin {
  background: #fef3c7;
  color: #92400e;
}

.role-user {
  background: #e0f2fe;
  color: #0369a1;
}

.time-cell {
  font-size: 12px;
  color: #9ca3af;
  white-space: nowrap;
}

.action-cell {
  white-space: nowrap;
}

.btn-xs {
  font-size: 12px;
  padding: 3px 10px;
}

.btn-danger {
  color: #dc2626;
}

.btn-danger:hover {
  background: #fef2f2;
}

.btn-sm {
  padding: 6px 16px;
  font-size: 13px;
}
</style>
