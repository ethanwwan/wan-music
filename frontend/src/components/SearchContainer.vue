<template>
  <el-card class="main-card" shadow="hover">
    <!-- 输入头部 -->
    <div v-if="currentMode !== 'rank'" class="input-header">
      <div>
        <h2 class="input-title">{{ title }}</h2>
        <p class="input-desc">{{ description }}</p>
      </div>
    </div>

    <!-- 榜单选择器 -->
    <div v-if="currentMode === 'rank'" class="charts-select-container">
      <el-select v-model="selectedChart" placeholder="选择榜单" size="large" style="width: 100%">
        <el-option label="飙升榜" value="19723756" />
        <el-option label="新歌榜" value="3779629" />
        <el-option label="原创榜" value="2884035" />
        <el-option label="热歌榜" value="3778678" />
      </el-select>
    </div>

    <!-- 标准输入区 -->
    <div v-if="currentMode !== 'rank'" class="input-section">
      <div class="input-row">
        <el-input
          v-model="inputValue"
          :placeholder="placeholder"
          size="large"
          clearable
          @keyup.enter="handleParse"
        >
          <template #prefix>
            <el-icon><Link /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          size="large"
          @click="handleParse"
          :loading="loading"
          :disabled="!inputValue.trim()"
        >
          开始解析
        </el-button>
      </div>

      <!-- 示例数据 -->
      <div class="example-section">
        <span class="example-label">{{ exampleTitle }}</span>
        <div class="example-tags">
          <el-tag
            v-for="link in exampleLinks"
            :key="link.name"
            class="example-tag"
            @click="handleExampleClick(link)"
            effect="plain"
          >
            {{ link.name }}
          </el-tag>
        </div>
      </div>

      <!-- 历史解析 -->
      <div v-if="historyRecords.length > 0" class="history-section">
        <div class="history-header">
          <span class="history-label">历史解析</span>
          <span class="history-clear" @click="handleClearHistory">清除历史</span>
        </div>
        <div class="history-tags">
          <el-tag
            v-for="record in historyRecords"
            :key="record.name"
            class="history-tag"
            @click="handleHistoryClick(record)"
            effect="plain"
          >
            {{ record.name }}
          </el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, defineProps, defineEmits, onMounted, watch, computed } from 'vue'
import { Link } from '@element-plus/icons-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'

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
  exampleLinks: {
    type: Array,
    default: () => []
  },
  exampleTitle: {
    type: String,
    default: '示例歌曲'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'parse',
  'example-click',
  'chart-change',
  'history-click'
])

const inputValue = ref('')
const selectedChart = ref('19723756')
const historyRecords = ref([])

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

const handleHistoryClick = (record) => {
  inputValue.value = record.name
  emit('history-click', record)
}

const handleParse = () => {
  if (inputValue.value.trim()) {
    emit('parse', {
      url: inputValue.value,
      quality: selectedQuality.value
    })
  }
}

const handleExampleClick = (link) => {
  inputValue.value = link.name
  emit('example-click', link)
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
}

@media (min-width: 768px) {
  .input-row {
    flex-direction: row;
  }
}

.input-row :deep(.el-input) {
  flex-grow: 1;
  height: 48px;
}

.input-row :deep(.el-input__wrapper) {
  border-radius: 0.5rem;
  border: 1px solid var(--color-border-subtle);
  padding: 0 1.5rem;
}

.input-row :deep(.el-input__wrapper:hover) {
  border-color: var(--color-border-subtle);
}

.input-row :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(0, 87, 194, 0.2);
  border-color: var(--color-primary);
}

.input-row :deep(.el-input__placeholder) {
  color: #8C8C8C;
}

.input-row :deep(.el-button--primary) {
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

.input-row :deep(.el-button--primary:hover) {
  background: var(--color-primary);
  opacity: 0.9;
}

.input-row :deep(.el-button--primary:active) {
  transform: scale(0.95);
}

.input-row :deep(.el-button--primary:disabled) {
  opacity: 0.5;
  transform: none;
}

.input-row :deep(.el-button--primary.is-loading) {
  background: var(--color-primary);
  opacity: 0.8;
}

.input-row :deep(.el-button--primary.is-loading .el-loading-spinner) {
  color: white;
}

.example-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.example-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-body-sm);
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding-left: 0;
  margin-left: 0;
}

.example-tag {
  cursor: pointer;
  transition: all 0.2s;
  padding: var(--spacing-xs) var(--spacing-lg);
  background: transparent;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-label);
  color: var(--color-secondary);
  margin-left: 0 !important;
}

.example-tag:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
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
  margin-left: 0 !important;
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
