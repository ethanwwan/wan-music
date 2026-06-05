<template>
  <aside class="floating-actions">
    <!-- 切换主题 -->
    <button 
      class="action-btn" 
      @click="handleToggleTheme" 
      :title="isDark ? '切换亮色主题' : '切换深色主题'"
    >
      <component :is="isDark ? StarFilled : CloudFilled" class="action-icon" />
    </button>
    <!-- 回到顶部 -->
    <button 
      v-show="showScrollTop" 
      class="action-btn" 
      @click="handleScrollTop" 
      title="回到顶部"
    >
      <ArrowUpOutlined class="action-icon" />
    </button>
    <!-- 设置 -->
    <button 
      class="action-btn" 
      @click="handleOpenSettings" 
      title="设置"
    >
      <SettingOutlined class="action-icon" />
    </button>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { CloudFilled, StarFilled, SettingOutlined, ArrowUpOutlined } from '@ant-design/icons-vue'
import { isDark, toggleTheme } from '../utils/themeManager.js'

const emit = defineEmits(['open-settings'])

const showScrollTop = ref(false)

const handleScroll = () => {
  showScrollTop.value = window.scrollY > 200
}

const handleToggleTheme = () => {
  toggleTheme()
}

const handleScrollTop = () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

const handleOpenSettings = () => {
  emit('open-settings')
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
  handleScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.floating-actions {
  position: fixed;
  right: 1.5rem;
  bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 40;
}

.action-btn {
  width: 2.5rem;
  height: 2.5rem;
  background: var(--color-surface-white, #ffffff);
  border: 1px solid var(--color-border-subtle, #e5e5e5);
  border-radius: 0.25rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

.action-btn:hover {
  background: var(--color-surface-container, #eeeeee);
  border-color: var(--color-border-subtle, #e5e5e5);
}

.action-btn:active {
  transform: scale(0.95);
}

.action-icon {
  color: var(--color-on-surface-variant, #414755);
  font-size: 1.25rem;
  width: 1.25rem;
  height: 1.25rem;
}
</style>