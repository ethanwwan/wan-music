<template>
  <div v-if="visible" class="notice-bar">
    <div class="notice-content">
      <el-icon :size="24" :color="primaryColor">
        <InfoFilled />
      </el-icon>
      <div class="notice-text">
        <span class="notice-title">{{ title }}</span>
        <p class="notice-desc">{{ message }}</p>
      </div>
    </div>
    <button class="notice-close" @click="handleClose">
      <el-icon><Close /></el-icon>
    </button>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { InfoFilled, Close } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    default: '系统公告'
  },
  message: {
    type: String,
    default: '欢迎使用网易云音乐解析工具！'
  },
  modelValue: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = ref(props.modelValue)

const handleClose = () => {
  visible.value = false
  emit('update:modelValue', false)
  emit('close')
}
</script>

<style scoped>
.notice-bar {
  background: var(--color-notice-bg);
  border: 1px solid var(--color-notice-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-2xl);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.notice-content {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
}

.notice-text {
  flex: 1;
}

.notice-title {
  font-weight: 700;
  color: var(--color-primary);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.notice-desc {
  color: var(--color-on-surface-variant);
  font-size: var(--font-size-body-sm);
  margin: 0;
  line-height: var(--line-height-body-md);
}

.notice-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-outline);
  transition: color 0.2s;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notice-close:hover {
  color: var(--color-on-surface);
}
</style>
