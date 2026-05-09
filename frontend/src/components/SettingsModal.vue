<script setup lang="ts">
import { ref, watch, computed } from 'vue'
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
}

watch(() => props.modelValue, (val) => {
  if (val) loadSettings()
})
</script>

<template>
  <div v-if="modelValue" class="modal active">
    <div class="modal-content" style="max-width: 680px; max-height: 85vh; overflow-y: auto;">
      <div class="modal-header">
        <h3 class="modal-title">系统设置</h3>
      </div>
      
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
</style>
