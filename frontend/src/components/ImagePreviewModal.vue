<script setup lang="ts">
defineProps<{
  modelValue: boolean
  src: string
}>()

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <div v-if="modelValue" class="image-preview-modal active">
    <div class="image-preview-content">
      <button class="image-preview-close" @click="close">×</button>
      <img :src="src" alt="预览">
    </div>
  </div>
</template>
