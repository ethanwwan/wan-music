<template>
  <aside class="floating-actions" :style="{ bottom: bottomOffset + 'px' }">
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const playerHeight = ref(0)

const bottomOffset = computed(() => {
  return playerHeight.value + 32
})

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
</style>
