<template>
  <div class="pagination-container">
    <div class="pagination">
      <button 
        class="pagination-btn" 
        :disabled="currentPage === 1"
        @click="prevPage"
      >
        ←
      </button>
      
      <template v-for="page in visiblePages" :key="page">
        <span 
          v-if="page === '...'" 
          class="pagination-ellipsis"
        >...</span>
        <button 
          v-else
          class="pagination-btn"
          :class="{ active: currentPage === page }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
      </template>
      
      <button 
        class="pagination-btn" 
        :disabled="currentPage === totalPages"
        @click="nextPage"
      >
        →
      </button>
    </div>
    <div class="pagination-info">
      共 {{ totalCount }} 条，第 {{ currentPage }}/{{ totalPages }} 页
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  totalCount: {
    type: Number,
    default: 0
  },
  pageSize: {
    type: Number,
    default: 10
  },
  modelValue: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['update:modelValue', 'page-change'])

const currentPage = ref(props.modelValue)

watch(() => props.modelValue, (newVal) => {
  currentPage.value = newVal
})

watch(currentPage, (newVal) => {
  emit('update:modelValue', newVal)
  emit('page-change', newVal)
})

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(props.totalCount / props.pageSize))
})

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      pages.push(1, 2, 3, 4, '...', total)
    } else if (current >= total - 2) {
      pages.push(1, '...', total - 3, total - 2, total - 1, total)
    } else {
      pages.push(1, '...', current - 1, current, current + 1, '...', total)
    }
  }
  
  return pages
})

const goToPage = (page) => {
  console.log('Pagination: goToPage called with page:', page)
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    console.log('Pagination: currentPage updated to', currentPage.value)
  }
}

const prevPage = () => {
  console.log('Pagination: prevPage called')
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  console.log('Pagination: nextPage called')
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const reset = () => {
  currentPage.value = 1
}

defineExpose({
  reset
})
</script>

<style scoped>
.pagination-container {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1.5rem;
  padding: 1rem;
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-surface-container-low);
}

.pagination {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.pagination-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--color-surface-container);
  color: var(--color-on-surface);
}

.pagination-btn.active {
  background: var(--color-primary);
  color: white;
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-ellipsis {
  color: var(--color-text-muted);
  padding: 0 4px;
}

.pagination-info {
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>