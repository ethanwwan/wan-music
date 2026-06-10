<template>
  <a-drawer
    v-model:open="drawerVisible"
    width="450px"
    placement="right"
    :closable="true"
    :mask-closable="true"
    :header-style="{ display: 'none' }"
    class="settings-drawer"
  >
    <!-- 自定义头部 -->
    <div class="custom-header">
      <span class="header-title">设置</span>
      <CloseOutlined class="close-icon" @click="drawerVisible = false" />
    </div>
    
    <div class="settings-content">
      <!-- 主题设置 -->
      <div class="setting-section">
        <div class="section-title">主题设置</div>
        
        <div class="theme-color-options">
          <div 
            v-for="color in themeColors" 
            :key="color.value"
            class="theme-color-option"
            :class="{ active: selectedThemeColor === color.value }"
            @click="handleThemeColorChange(color.value)"
            :style="{ '--theme-color': color.hex }"
          >
            <div class="color-preview" :style="{ background: color.hex }"></div>
            <span class="color-name">{{ color.name }}</span>
          </div>
        </div>
      </div>

      <!-- 数据源设置 -->
      <div class="setting-section">
        <div class="section-title">数据源设置</div>
        <a-form :model="settings" layout="horizontal" class="settings-form">
          <a-form-item label="数据源">
            <a-select
              v-model:value="settings.dataSource"
              @change="handleSave"
              :style="{ width: '180px' }"
            >
              <a-select-option value="official">官方API</a-select-option>
              <a-select-option value="xuanluoge">xuanluoge</a-select-option>
              <a-select-option value="haitangw">haitangw</a-select-option>
            </a-select>
            <div class="form-item-hint">
              <a-tag color="blue" bordered>选择解析音乐链接的数据源，优先使用官方API</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- 音质设置 -->
      <div class="setting-section">
        <div class="section-title">音质设置</div>
        <a-form :model="settings" layout="horizontal" class="settings-form">
          <a-form-item label="默认音质">
            <a-select
              v-model:value="settings.selectedQuality"
              @change="handleSave"
              :style="{ width: '160px' }"
            >
              <a-select-option value="standard">标准 (128kbps)</a-select-option>
              <a-select-option value="exhigh">极高 (320kbps)</a-select-option>
              <a-select-option value="lossless">无损 (FLAC)</a-select-option>
              <a-select-option value="hires">Hi-Res (FLAC 24bit)</a-select-option>
              <a-select-option value="sky">沉浸 (Dolby Atmos)</a-select-option>
              <a-select-option value="jyeffect">环绕 (Sony 360RA)</a-select-option>
              <a-select-option value="jymaster">母带 (FLAC 24bit/96kHz)</a-select-option>
            </a-select>
            <div class="form-item-hint">
              <a-tag color="blue" bordered>解析和下载时使用的默认音质</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- 下载设置 -->
      <div class="setting-section">
        <div class="section-title">下载配置</div>
        <a-form :model="settings" layout="horizontal" class="settings-form">
          <a-form-item label="文件命名格式">
            <a-select
              v-model:value="settings.filenameFormat"
              @change="handleSave"
              :style="{ width: '160px' }"
            >
              <a-select-option value="song-artist">歌曲名 - 歌手名</a-select-option>
              <a-select-option value="artist-song">歌手名 - 歌曲名</a-select-option>
              <a-select-option value="song-only">仅歌曲名</a-select-option>
            </a-select>
            <div class="form-item-hint">
              <a-tag color="blue" bordered>
                示例：{{ settings.filenameFormat === 'artist-song' ? '歌手 - 歌曲' : (settings.filenameFormat === 'song-only' ? '歌曲' : '歌曲 - 歌手') }}
              </a-tag>
            </div>
          </a-form-item>

          <a-form-item label="自动写入元数据">
            <a-switch
              v-model:checked="settings.writeMetadata"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <a-tag color="blue" bordered>写入歌曲名、歌手、专辑、封面、歌词等信息</a-tag>
            </div>
          </a-form-item>

          <a-form-item label="下载LRC歌词文件">
            <a-switch
              v-model:checked="settings.downloadLrcFile"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <a-tag color="blue" bordered>批量下载时同时生成独立的LRC歌词文件</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- 解析设置 -->
      <div class="setting-section">
        <div class="section-title">解析配置</div>
        <a-form :model="settings" layout="horizontal" class="settings-form">
          <a-form-item label="启用缓存">
            <a-switch
              v-model:checked="settings.enableCache"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <a-tag color="blue" bordered>减少重复搜索和解析，提升相同内容再次访问速度</a-tag>
            </div>
          </a-form-item>

          <a-form-item label="缓存大小">
            <div class="cache-info">
              <span class="size-text">{{ cacheSize }}</span>
              <a-button 
                type="primary" 
                danger
                size="small" 
                :loading="clearingCache"
                class="clear-cache-btn"
                @click="handleClearCache"
              >
                <template #icon><DeleteOutlined /></template>
                清除缓存
              </a-button>
            </div>
            <div class="form-item-hint">
              <a-tag color="blue" bordered>缓存包括搜索结果、歌曲信息等，清除后下次访问会重新获取</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { CloseOutlined, DeleteOutlined } from '@ant-design/icons-vue'

import { settings, saveSettings } from '../utils/settingsManager.js'

const emit = defineEmits(['theme-color-change', 'update:open'])

const cacheSize = ref('0 KB')
const clearingCache = ref(false)

const calculateCacheSize = () => {
  let totalSize = 0
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      const value = localStorage.getItem(key)
      if (value) {
        totalSize += key.length + value.length
      }
    }
  } catch (e) {
    console.warn('读取 localStorage 失败:', e)
  }
  
  if (totalSize < 1024) {
    return `${totalSize} B`
  } else if (totalSize < 1024 * 1024) {
    return `${(totalSize / 1024).toFixed(2)} KB`
  } else {
    return `${(totalSize / (1024 * 1024)).toFixed(2)} MB`
  }
}

const refreshCacheSize = () => {
  cacheSize.value = calculateCacheSize()
}

const handleClearCache = async () => {
  Modal.confirm({
    title: '确认清除缓存？',
    content: '清除后所有缓存数据将被删除，下次访问需要重新加载',
    okText: '确认清除',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      clearingCache.value = true
      
      try {
        localStorage.clear()
        sessionStorage.clear()
        refreshCacheSize()
        message.success('缓存已清除')
      } catch (e) {
        message.error('清除缓存失败')
      } finally {
        clearingCache.value = false
      }
    }
  })
}

onMounted(() => {
  refreshCacheSize()
})

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const drawerVisible = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

const selectedThemeColor = ref('#0057c2')

const themeColors = [
  { name: '默认蓝', value: 'blue', hex: '#0057c2' },
  { name: '活力红', value: 'red', hex: '#e53935' },
  { name: '优雅紫', value: 'purple', hex: '#8e24aa' },
  { name: '清新绿', value: 'green', hex: '#43a047' },
  { name: '温暖橙', value: 'orange', hex: '#fb8c00' },
  { name: '深邃青', value: 'cyan', hex: '#00acc1' }
]

const initThemeSettings = () => {
  const savedThemeColor = localStorage.getItem('themeColor')
  
  if (savedThemeColor) {
    const color = themeColors.find(c => c.value === savedThemeColor)
    if (color) {
      selectedThemeColor.value = color.hex
    }
  }
}

initThemeSettings()

const handleThemeColorChange = async (colorValue) => {
  const color = themeColors.find(c => c.value === colorValue)
  if (!color) return
  
  selectedThemeColor.value = color.hex
  localStorage.setItem('themeColor', colorValue)
  
  emit('theme-color-change', color.hex)
  
  message.success(`已切换到${color.name}`)
}

const handleSave = () => {
  saveSettings()
  message.success('设置已保存')
}

const handleClose = () => {
  handleSave()
  drawerVisible.value = false
}
</script>

<style scoped>
.custom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-on-surface);
}

.close-icon {
  font-size: 20px;
  color: var(--color-on-surface-variant);
  cursor: pointer;
  transition: color 0.2s;
}

.close-icon:hover {
  color: var(--color-on-surface);
}

.settings-content {
  padding: 16px 0;
  height: calc(100% - 57px);
  overflow-y: auto;
}

.settings-content::-webkit-scrollbar {
  display: none;
}

.settings-content {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.setting-section {
  margin-bottom: 24px;
}

.setting-section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin-bottom: 16px;
}

.settings-form {
  padding: 0;
}

.settings-form :deep(.ant-form-item) {
  margin-bottom: 16px;
  padding-left: 0 !important;
}

.settings-form :deep(.ant-form-item:last-child) {
  margin-bottom: 0;
}

.settings-form :deep(.ant-col) {
  padding-left: 0 !important;
}

.settings-form :deep(.ant-form-item-label) {
  padding-left: 0 !important;
}

.form-item-hint {
  margin-top: 4px;
}

.form-item-hint :deep(.ant-tag) {
  font-size: 12px;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  color: var(--color-on-surface-variant);
}

.subsection-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface-variant);
  margin-bottom: 12px;
  padding-left: 4px;
}

.theme-mode-section {
  margin-bottom: 20px;
}

.theme-mode-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 0 8px;
}

.theme-color-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 0 8px;
}

.theme-color-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-surface-container-low);
}

.theme-color-option:hover {
  border-color: var(--theme-color);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.theme-color-option.active {
  border-color: var(--theme-color);
  background: var(--color-surface-white);
}

.color-preview {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.color-name {
  font-size: 12px;
  color: var(--color-on-surface-variant);
  text-align: center;
  font-weight: 500;
}

.theme-color-option.active .color-name {
  color: var(--theme-color);
  font-weight: 600;
}

.cache-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.size-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
  line-height: 32px;
}

.clear-cache-btn {
  margin-left: auto;
}

.clear-cache-btn :deep(.ant-btn-icon) {
  font-size: 14px;
}
</style>