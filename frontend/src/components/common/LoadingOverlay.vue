<template>
  <transition name="fade">
    <div v-if="visible" class="loading-overlay" :class="{ 'fullscreen': fullscreen }">
      <div class="loading-content">
        <div class="spinner">
          <div class="circle"></div>
        </div>
        <p v-if="text" class="loading-text">{{ text }}</p>
        <p v-if="subText" class="loading-subtext">{{ subText }}</p>
        <div v-if="progress !== null" class="progress-bar">
          <el-progress 
            :percentage="progress" 
            :status="progressStatus"
            :stroke-width="6"
          />
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  text: {
    type: String,
    default: '加载中...'
  },
  subText: {
    type: String,
    default: ''
  },
  progress: {
    type: Number,
    default: null
  },
  fullscreen: {
    type: Boolean,
    default: false
  }
})

const progressStatus = computed(() => {
  if (props.progress >= 100) return 'success'
  if (props.progress >= 80) return ''
  return 'exception'
})
</script>

<style scoped>
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(var(--color-surface-white-rgb, 255, 255, 255), 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}

.dark .loading-overlay {
  background: rgba(var(--color-surface-dark-rgb, 30, 30, 30), 0.9);
}

.loading-overlay.fullscreen {
  position: fixed;
  z-index: 2000;
}

.loading-content {
  text-align: center;
}

.spinner {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
}

.circle {
  width: 100%;
  height: 100%;
  border: 4px solid var(--el-border-color);
  border-top-color: var(--el-color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 16px;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
  font-weight: 500;
  white-space: nowrap;
}

.loading-subtext {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0;
}

.progress-bar {
  width: 200px;
  margin: 16px auto 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
