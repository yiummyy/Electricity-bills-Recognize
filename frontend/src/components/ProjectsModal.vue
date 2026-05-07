<script setup lang="ts">
import { ref, watch } from 'vue'
import { useBillStore } from '@/stores/bill'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue'])
const billStore = useBillStore()
const authStore = useAuthStore()
const projects = ref<any[]>([])

function getProjectsKey() {
  return `electricityProjects_${authStore.username || 'anonymous'}`
}

function loadProjects() {
  projects.value = JSON.parse(localStorage.getItem(getProjectsKey()) || '[]')
}

function loadProject(project: any) {
  billStore.extractedData = project.data
  billStore.uploadedFiles = []
  emit('update:modelValue', false)
}

function deleteProject(id: number) {
  if (confirm('确定要删除这个项目吗？')) {
    projects.value = projects.value.filter(p => p.id !== id)
    localStorage.setItem(getProjectsKey(), JSON.stringify(projects.value))
  }
}

function close() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, (val) => {
  if (val) loadProjects()
})
</script>

<template>
  <div v-if="modelValue" class="modal active">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">历史项目</h3>
      </div>
      <div class="project-list">
        <div v-if="projects.length === 0" class="empty-state">
          <div class="empty-state-text">暂无历史项目</div>
        </div>
        <div v-else v-for="p in projects" :key="p.id" class="project-item">
          <div class="project-info">
            <div class="project-name">{{ p.name }}</div>
            <div class="project-meta">{{ p.date }} · {{ p.data.length }} 个月</div>
          </div>
          <div class="project-actions">
            <button class="btn btn-primary" @click="loadProject(p)">加载</button>
            <button class="btn btn-secondary" @click="deleteProject(p.id)">删除</button>
          </div>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" @click="close">关闭</button>
      </div>
    </div>
  </div>
</template>
