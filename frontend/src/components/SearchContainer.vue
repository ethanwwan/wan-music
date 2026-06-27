<template>
  <a-card class="main-card" :hoverable="true">
    <div class="input-header">
      <div class="header-text">
        <h2 class="input-title">{{ title }}</h2>
      </div>
      <div class="header-actions">
        <!-- 下载队列按钮（设置按钮左侧） -->
        <button
          class="icon-btn queue-btn"
          @click="openDownloadDrawer"
          title="下载队列"
        >
          <svg focusable="false" data-icon="download" width="1em" height="1em" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span
            v-if="totalBadge > 0"
            class="badge"
            :class="{ 'badge-pulse': activeCount > 0 }"
          >
            {{ totalBadge > 99 ? '99+' : totalBadge }}
          </span>
        </button>
        <!-- 设置按钮 -->
        <button
          class="icon-btn settings-btn"
          @click="$emit('open-settings')"
          title="设置"
        >
          <svg focusable="false" data-icon="setting" width="1em" height="1em" fill="currentColor" aria-hidden="true" viewBox="64 64 896 896"><path d="M924.8 625.7l-65.5-56c3.1-19 4.7-38.4 4.7-57.8s-1.6-38.8-4.7-57.8l65.5-56a32.03 32.03 0 009.3-35.2l-.9-2.6a443.74 443.74 0 00-79.7-137.9l-1.8-2.1a32.12 32.12 0 00-35.1-9.5l-81.3 28.9c-30-24.6-63.5-44-99.7-57.6l-15.7-85a32.05 32.05 0 00-25.8-25.7l-2.7-.5c-52.1-9.4-106.9-9.4-159 0l-2.7.5a32.05 32.05 0 00-25.8 25.7l-15.8 85.4a351.86 351.86 0 00-99 57.4l-81.9-29.1a32 32 0 00-35.1 9.5l-1.8 2.1a446.02 446.02 0 00-79.7 137.9l-.9 2.6c-4.5 12.5-.8 26.5 9.3 35.2l66.3 56.6c-3.1 18.8-4.6 38-4.6 57.1 0 19.2 1.5 38.4 4.6 57.1L99 625.5a32.03 32.03 0 00-9.3 35.2l.9 2.6c18.1 50.4 44.9 96.9 79.7 137.9l1.8 2.1a32.12 32.12 0 0035.1 9.5l81.9-29.1c29.8 24.5 63.1 43.9 99 57.4l15.8 85.4a32.05 32.05 0 0025.8 25.7l2.7.5a449.4 449.4 0 00159 0l2.7-.5a32.05 32.05 0 0025.8-25.7l15.7-85a350 350 0 0099.7-57.6l81.3 28.9a32 32 0 0035.1-9.5l1.8-2.1c34.8-41.1 61.6-87.5 79.7-137.9l.9-2.6c4.5-12.3.8-26.3-9.3-35zM788.3 465.9c2.5 15.1 3.8 30.6 3.8 46.1s-1.3 31-3.8 46.1l-6.6 40.1 74.7 63.9a370.03 370.03 0 01-42.6 73.6L721 702.8l-31.4 25.8c-23.9 19.6-50.5 35-79.3 45.8l-38.1 14.3-17.9 97a377.5 377.5 0 01-85 0l-17.9-97.2-37.8-14.5c-28.5-10.8-55-26.2-78.7-45.7l-31.4-25.9-93.4 33.2c-17-22.9-31.2-47.6-42.6-73.6l75.5-64.5-6.5-40c-2.4-14.9-3.7-30.3-3.7-45.5 0-15.3 1.2-30.6 3.7-45.5l6.5-40-75.5-64.5c11.3-26.1 25.6-50.7 42.6-73.6l93.4 33.2 31.4-25.9c23.7-19.5 50.2-34.9 78.7-45.7l37.9-14.3 17.9-97.2c28.1-3.2 56.8-3.2 85 0l17.9 97 38.1 14.3c28.7 10.8 55.4 26.2 79.3 45.8l31.4 25.8 92.8-32.9c17 22.9 31.2 47.6 42.6 73.6L781.8 426l6.5 39.9zM512 326c-97.2 0-176 78.8-176 176s78.8 176 176 176 176-78.8 176-176-78.8-176-176-176zm79.2 255.2A111.6 111.6 0 01512 614c-29.9 0-58-11.7-79.2-32.8A111.6 111.6 0 01400 502c0-29.9 11.7-58 32.8-79.2C454 401.6 482.1 390 512 390c29.9 0 58 11.6 79.2 32.8A111.6 111.6 0 01624 502c0 29.9-11.7 58-32.8 79.2z"></path></svg>
        </button>
      </div>
    </div>

    <div class="input-section">
      <div class="input-row">
        <a-input
          v-model:value="inputValue"
          :placeholder="placeholder"
          size="large"
          allow-clear
          @keyup.enter="handleParse"
          prefix-icon="link"
        />
        <a-select
          v-model:value="selectedDataSource"
          placeholder="数据源"
          size="large"
          style="width: 160px"
          :loading="platforms === null"
          :disabled="!platforms || platforms.length === 0"
          @change="handleDataSourceChange"
        >
          <a-select-option
            v-for="p in platforms || []"
            :key="p.id"
            :value="p.id"
          >
            {{ p.name }}
          </a-select-option>
        </a-select>
        <a-button
          type="primary"
          size="large"
          @click="handleParse"
          :loading="loading"
        >
          搜索
        </a-button>
      </div>

      <div v-if="historyRecords.length > 0" class="history-section">
        <div class="history-header">
          <span class="history-label">历史解析</span>
          <a-button
            class="clear-action-btn"
            type="text"
            danger
            size="small"
            @click="handleClearHistory"
          >
            清除历史
          </a-button>
        </div>
        <div class="history-tags">
          <span
            v-for="record in historyRecords"
            :key="record.name"
            class="history-tag"
            @click="handleTagClick(record)"
          >
            {{ record.name }}
          </span>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'
import { downloadQueueStore as queueStore } from '../stores/downloadQueue.js'
import { platforms, loadPlatforms } from '../utils/platformsManager.js'

const HISTORY_STORAGE_KEY = 'wan-music-history-records'

const loadHistoryFromStorage = () => {
  try {
    const stored = localStorage.getItem(HISTORY_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch (e) {
    console.error('Failed to load history from storage:', e)
    return []
  }
}

const saveHistoryToStorage = (records) => {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(records))
  } catch (e) {
    console.error('Failed to save history to storage:', e)
  }
}

defineProps({
  title: {
    type: String,
    default: '输入搜索关键词'
  },
  placeholder: {
    type: String,
    default: '请输入歌曲名或歌单名'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['parse', 'open-settings'])

const openDownloadDrawer = () => {
  queueStore.openDrawer()
}
const activeCount = computed(() => queueStore.activeCount.value)
const completedCount = computed(() => queueStore.completedCount.value)
const totalBadge = computed(() => activeCount.value + completedCount.value)

const inputValue = ref('')
const historyRecords = ref([])

// 从 localStorage 读取上次选择的数据源（兜底为 'netease'，加载到平台列表后再校验）
const savedDataSource = localStorage.getItem('wan-music-selected-data-source')
const selectedDataSource = ref(savedDataSource || 'netease')
const selectedSources = ref([selectedDataSource.value])

// 平台列表加载完成后，若上次选择已失效则回退到第一个可用平台
watch(platforms, (list) => {
  if (list && list.length > 0 && !list.some(p => p.id === selectedDataSource.value)) {
    const fallback = list[0].id
    selectedDataSource.value = fallback
    selectedSources.value = [fallback]
    localStorage.setItem('wan-music-selected-data-source', fallback)
  }
})

const selectedQuality = computed({
  get: () => settings.selectedQuality || 'lossless',
  set: (value) => {
    settings.selectedQuality = value
    saveSettings()
  }
})

const loadHistoryRecords = () => {
  historyRecords.value = loadHistoryFromStorage()
}

const addHistoryRecord = (songName) => {
  const exists = historyRecords.value.some(item => item.name === songName)
  if (!exists) {
    historyRecords.value.unshift({ name: songName, url: songName, type: 'search' })
    if (historyRecords.value.length > 50) historyRecords.value.pop()
    saveHistoryToStorage(historyRecords.value)
  }
}

const handleTagClick = (item) => {
  inputValue.value = item.name
}

const handleDataSourceChange = (value) => {
  selectedDataSource.value = value
  selectedSources.value = [value]
  localStorage.setItem('wan-music-selected-data-source', value)
}

const handleParse = () => {
  const value = inputValue.value.trim()
  if (!value) {
    message.warning('请输入歌曲名或歌单名')
    return
  }
  emit('parse', {
    url: value,
    quality: selectedQuality.value,
    sources: [...selectedSources.value]
  })
}

const handleClearHistory = () => {
  historyRecords.value = []
  saveHistoryToStorage([])
}

onMounted(() => {
  loadHistoryRecords()
  loadPlatforms()
})

defineExpose({ addHistoryRecord })
</script>

<style scoped>
.main-card {
  background: var(--color-surface-white);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  padding: var(--spacing-md);
}

.input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.header-text {
  flex: 1;
}

.input-title {
  font-size: var(--font-size-headline-md);
  font-weight: 600;
  line-height: var(--line-height-headline-md);
  margin: 0;
  color: var(--color-on-surface);
  font-family: var(--font-family);
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.input-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: stretch;
}

@media (min-width: 768px) {
  .input-row {
    flex-direction: row;
    align-items: center;
  }
}

.input-row :deep(.ant-input-affix-wrapper) {
  flex-grow: 1;
  height: 48px;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border-subtle);
  transition: all 0.2s;
}

.input-row :deep(.ant-input-affix-wrapper:focus-within) {
  box-shadow: 0 0 0 2px rgba(0, 87, 194, 0.2);
  border-color: var(--color-primary);
}

.input-row :deep(.ant-input) {
  border: none;
  box-shadow: none;
}

.input-row :deep(.ant-select-selector) {
  height: 48px !important;
  display: flex;
  align-items: center;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border-subtle);
}

.input-row :deep(.ant-btn-primary) {
  height: 48px;
  padding: 0 2rem;
  background: var(--color-primary);
  border-radius: 0.5rem;
  font-weight: 700;
  font-size: 16px;
  line-height: 1.5;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  border: none;
  transition: all 0.2s;
}

.input-row :deep(.ant-btn-primary:hover) {
  background: var(--color-primary);
  opacity: 0.9;
}

.input-row :deep(.ant-btn-primary:active) {
  transform: scale(0.95);
}

.input-row :deep(.ant-btn-primary:disabled) {
  opacity: 0.5;
  transform: none;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.icon-btn {
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--color-border-subtle);
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-on-surface);
  transition: all 0.2s;
  padding: 0;
  font-size: 20px;
  position: relative;
}

.icon-btn svg {
  display: block;
}

.icon-btn:hover {
  background: var(--color-surface-container);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  box-shadow: 0 0 0 2px #fff;
}

.badge-pulse {
  animation: badge-pulse 1.5s ease-in-out infinite;
}

@keyframes badge-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 2px #fff, 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 2px #fff, 0 0 0 6px rgba(239, 68, 68, 0);
  }
}

.queue-btn:hover .badge {
  background: var(--color-primary);
}

.history-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-body-sm);
}


.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding-left: 0;
  margin-left: 0;
}

.history-tag {
  cursor: pointer;
  transition: all 0.2s;
  padding: var(--spacing-xs) var(--spacing-lg);
  background: transparent;
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-label);
  color: var(--color-primary);
}

.history-tag:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

@media (max-width: 768px) {
  .input-row {
    flex-direction: column;
  }

  .input-header {
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .main-card {
    padding: var(--spacing-lg);
  }
}
</style>
