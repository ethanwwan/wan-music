<template>
  <el-card class="main-card" shadow="hover">
    <!-- 输入头部 -->
    <div v-if="currentMode !== 'rank'" class="input-header">
      <div>
        <h2 class="input-title">{{ title }}</h2>
        <p class="input-desc">{{ description }}</p>
      </div>
      <div class="quality-select">
        <el-select v-model="selectedQuality" placeholder="选择音质" size="default">
          <el-option
            v-for="option in qualityOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
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

      <!-- 示例歌曲 -->
      <div class="example-section">
        <span class="example-label">示例歌曲</span>
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
        <span class="history-label">历史解析</span>
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
import { ref, defineProps, defineEmits } from 'vue'
import { Link } from '@element-plus/icons-vue'

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
  qualityOptions: {
    type: Array,
    default: () => []
  },
  exampleLinks: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'parse',
  'quality-change',
  'example-click',
  'chart-change',
  'history-click'
])

const inputValue = ref('')
const selectedQuality = ref('lossless')
const selectedChart = ref('19723756')
const historyRecords = ref([])

const addHistoryRecord = (songName) => {
  const exists = historyRecords.value.some(item => item.name === songName)
  if (!exists) {
    historyRecords.value.unshift({
      name: songName,
      url: songName
    })
    if (historyRecords.value.length > 10) {
      historyRecords.value.pop()
    }
  }
}

const handleHistoryClick = (record) => {
  inputValue.value = record.url
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
  inputValue.value = link.url
  emit('example-click', link)
}

const handleChartChange = () => {
  emit('chart-change', selectedChart.value)
}

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
  gap: var(--spacing-lg);
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
  
  .quality-select {
    width: 100%;
  }
  
  .main-card {
    padding: var(--spacing-lg);
  }
}
</style>
