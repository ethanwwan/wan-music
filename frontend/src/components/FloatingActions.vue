<template>
  <aside class="floating-actions" :style="{ bottom: bottomOffset + 'px' }">
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
import { SettingOutlined } from '@ant-design/icons-vue'

const emit = defineEmits(['open-settings'])

const playerHeight = ref(0)

const bottomOffset = computed(() => {
  return playerHeight.value + 32
})

const handleOpenSettings = () => {
  emit('open-settings')
}

const updatePlayerHeight = () => {
  const player = document.querySelector('.bottom-player')
  if (player) {
    const rect = player.getBoundingClientRect()
    playerHeight.value = rect.height
  } else {
    playerHeight.value = 0
  }
}

let observer = null
let checkInterval = null

onMounted(() => {
  window.addEventListener('resize', updatePlayerHeight)
  updatePlayerHeight()

  const player = document.querySelector('.bottom-player')
  if (player) {
    observer = new MutationObserver(() => {
      updatePlayerHeight()
    })
    observer.observe(player, {
      attributes: true,
      attributeFilter: ['class', 'style'],
      subtree: true
    })
  }

  checkInterval = setInterval(updatePlayerHeight, 100)
})

onUnmounted(() => {
  window.removeEventListener('resize', updatePlayerHeight)
  if (observer) {
    observer.disconnect()
  }
  if (checkInterval) {
    clearInterval(checkInterval)
  }
})
</script>

<style scoped>
.floating-actions {
  position: fixed;
  right: 1.5rem;
  bottom: 32px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 40;
  transition: bottom 0.3s ease;
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
