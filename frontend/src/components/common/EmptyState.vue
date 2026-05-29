<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <el-icon :size="64"><Document /></el-icon>
      </slot>
    </div>
    <h3 v-if="title" class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<script setup>
import { Document } from '@element-plus/icons-vue'

defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-icon {
  color: var(--el-text-color-placeholder);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}

.empty-description {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0;
  max-width: 300px;
}

.empty-action {
  margin-top: 16px;
}
</style>
