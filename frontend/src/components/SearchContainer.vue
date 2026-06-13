<template>
  <a-card class="main-card" :hoverable="true">
    <!-- 输入头部 -->
    <div v-if="currentMode !== 'rank'" class="input-header">
      <div>
        <h2 class="input-title">{{ title }}</h2>
        <p class="input-desc">{{ description }}</p>
      </div>
    </div>

    <!-- 榜单选择器 -->
    <div v-if="currentMode === 'rank'" class="charts-select-container">
      <a-select v-model:value="selectedChart" placeholder="选择榜单" size="large" style="width: 100%">
        <a-select-option value="19723756">飙升榜</a-select-option>
        <a-select-option value="3779629">新歌榜</a-select-option>
        <a-select-option value="2884035">原创榜</a-select-option>
        <a-select-option value="3778678">热歌榜</a-select-option>
      </a-select>
    </div>

    <!-- 标准输入区 -->
    <div v-if="currentMode !== 'rank'" class="input-section">
      <div class="input-row">
        <a-input
          v-model:value="inputValue"
          :placeholder="placeholder"
          size="large"
          allow-clear
          @keyup.enter="handleParse"
          prefix-icon="link"
        />
        <!-- 数据源下拉选择框 -->
        <a-select 
          v-model:value="selectedDataSource" 
          placeholder="数据源" 
          size="large"
          style="width: 140px"
          @change="handleDataSourceChange"
        >
          <a-select-option value="all">全部</a-select-option>
          <a-select-option value="netease">网易云音乐</a-select-option>
          <a-select-option value="qq">QQ音乐</a-select-option>
          <a-select-option value="kugou">酷狗音乐</a-select-option>
          <a-select-option value="bodian">波点音乐</a-select-option>
        </a-select>
        <a-button
          type="primary"
          size="large"
          @click="handleParse"
          :loading="loading"
        >
          开始解析
        </a-button>
      </div>

      <!-- 历史解析 -->
      <div v-if="historyRecords.length > 0" class="history-section">
        <div class="history-header">
          <span class="history-label">历史解析</span>
          <span class="history-clear" @click="handleClearHistory">清除历史</span>
        </div>
        <div class="history-tags">
          <span
            v-for="record in historyRecords"
            :key="record.name"
            class="history-tag"
            @click="handleTagClick(record, 'history-click')"
          >
            {{ record.name }}
          </span>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup>
import { ref, defineProps, onMounted, watch, computed } from 'vue'
import { message } from 'ant-design-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'
import { dataSources, defaultSelectedSources } from '../utils/dataSourceConfig.js'

// 历史记录存储的localStorage key
const HISTORY_STORAGE_KEY = 'wan-music-history-records'

// 从localStorage加载历史记录
const loadHistoryFromStorage = () => {
  try {
    const stored = localStorage.getItem(HISTORY_STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch (e) {
    console.error('Failed to load history from storage:', e)
    return []
  }
}

// 保存历史记录到localStorage
const saveHistoryToStorage = (records) => {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(records))
  } catch (e) {
    console.error('Failed to save history to storage:', e)
  }
}

const props = defineProps({
  currentMode: {
    type: String,
    default: 'music'
  },
  title: {
    type: String,
    default: '输入歌曲 URL 或 ID'
  },
  description: {
    type: String,
    default: '支持单曲分享链接或直接输入数字ID'
  },
  placeholder: {
    type: String,
    default: '在此输入网易云音乐单曲链接或ID'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'parse',
  'chart-change',
  'history-click'
])

const inputValue = ref('')
const selectedChart = ref('19723756')
const historyRecords = ref([])
const selectedSources = ref([...defaultSelectedSources])
const selectedDataSource = ref('all')

// 从设置中读取音质，如果没有则使用默认值 'lossless'
const selectedQuality = computed({
  get: () => settings.selectedQuality || 'lossless',
  set: (value) => {
    settings.selectedQuality = value
    saveSettings()
  }
})

const loadHistoryRecords = (mode) => {
  // 榜单模式不显示历史记录
  if (mode === 'rank') {
    historyRecords.value = []
    return
  }
  // 从localStorage加载历史记录，并过滤当前模式
  const allHistory = loadHistoryFromStorage()
  historyRecords.value = allHistory.filter(record => record.type === mode)
}

const addHistoryRecord = (songName) => {
  // 检查是否已存在
  const exists = historyRecords.value.some(item => item.name === songName)
  if (!exists) {
    // 添加到历史记录开头
    historyRecords.value.unshift({
      name: songName,
      url: songName,
      type: props.currentMode
    })
    // 限制最多10条记录
    if (historyRecords.value.length > 10) {
      historyRecords.value.pop()
    }
    // 保存到localStorage（包含所有模式的历史）
    const allHistory = loadHistoryFromStorage()
    // 移除同一模式的相同记录
    const otherHistory = allHistory.filter(h => h.type !== props.currentMode || h.name !== songName)
    const newHistory = [historyRecords.value[0], ...otherHistory].slice(0, 50) // 总共最多50条
    saveHistoryToStorage(newHistory)
  }
}

const handleTagClick = (item, eventName) => {
  inputValue.value = item.name
  emit(eventName, item)
}

const handleDataSourceChange = (value) => {
  selectedDataSource.value = value
  // 根据选择的数据源更新selectedSources
  if (value === 'all') {
    selectedSources.value = ['netease', 'qq', 'kugou', 'bodian']
  } else {
    selectedSources.value = [value]
  }
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

const handleChartChange = () => {
  emit('chart-change', selectedChart.value)
}

const handleClearHistory = () => {
  historyRecords.value = []
  // 清除localStorage中的历史记录
  saveHistoryToStorage([])
}

onMounted(() => {
  // 初始化时从localStorage加载历史记录
  loadHistoryRecords(props.currentMode)
})

// 监听模式变化，切换历史记录
watch(() => props.currentMode, (newMode) => {
  loadHistoryRecords(newMode)
})

defineExpose({
  addHistoryRecord
})
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
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
}

.input-title {
  font-size: var(--font-size-headline-md);
  font-weight: 600;
  line-height: var(--line-height-headline-md);
  margin: 0 0 var(--spacing-xs) 0;
  color: var(--color-on-surface);
  font-family: var(--font-family);
}

.input-desc {
  font-size: var(--font-size-body-md);
  line-height: var(--line-height-body-md);
  color: var(--color-text-muted);
  margin: 0;
  font-family: var(--font-family);
}

.quality-select {
  min-width: 140px;
}

.charts-select-container {
  margin-bottom: var(--spacing-lg);
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

.data-source-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.data-source-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-body-sm);
}

.data-source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding-left: 0;
  margin-left: 0;
}

.data-source-tag {
  cursor: pointer;
  transition: all 0.2s;
  padding: var(--spacing-xs) var(--spacing-lg);
  background: transparent;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-label);
  color: var(--color-secondary);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.data-source-tag:hover {
  border-color: var(--color-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.data-source-tag.active {
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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

.history-clear {
  cursor: pointer;
  transition: color 0.2s;
  font-size: var(--font-size-body-sm);
  color: var(--color-text-muted);
}

.history-clear:hover {
  color: var(--color-error);
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