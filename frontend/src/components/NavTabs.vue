<template>
  <nav class="nav-tabs">
    <el-button
      v-for="mode in modes"
      :key="mode.key"
      :class="['nav-btn', { active: modelValue === mode.key }]"
      @click="handleTabClick(mode.key)"
    >
      {{ mode.label }}
    </el-button>
  </nav>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  modes: {
    type: Array,
    default: () => [
      { key: 'music', label: '单曲' },
      { key: 'album', label: '专辑' },
      { key: 'playlist', label: '歌单' },
      { key: 'search', label: '搜索' },
      { key: 'rank', label: '榜单' }
    ]
  },
  modelValue: {
    type: String,
    default: 'music'
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const handleTabClick = (key) => {
  emit('update:modelValue', key)
  emit('change', key)
}
</script>

<style scoped>
.nav-tabs {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-2xl);
}

.nav-btn {
  padding: var(--spacing-md) var(--spacing-lg) !important;
  height: auto !important;
  border: 1px solid var(--color-border-subtle) !important;
  border-radius: var(--radius-md) !important;
  background: var(--color-surface-white) !important;
  font-weight: 600 !important;
  font-size: var(--font-size-body-md) !important;
  line-height: var(--line-height-body-md) !important;
  text-align: center !important;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-secondary) !important;
  box-shadow: none !important;
}

.nav-btn:hover {
  background: var(--color-surface-container-low) !important;
  border-color: var(--color-border-subtle) !important;
  color: var(--color-secondary) !important;
}

.nav-btn.active {
  border-color: var(--color-primary) !important;
  color: var(--color-primary) !important;
  background: var(--color-primary-light) !important;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent) !important;
}

@media (max-width: 768px) {
  .nav-tabs {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
