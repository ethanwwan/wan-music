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
        <div class="section-title">
          <BgColorsOutlined />
          <span>主题设置</span>
        </div>
        
        <!-- 主题模式 -->
        <div class="theme-mode-section">
          <div class="subsection-title">主题模式</div>
          <div class="theme-mode-options">
            <div 
              class="theme-mode-option"
              :class="{ active: themeMode === 'light' }"
              @click="handleThemeModeChange('light')"
            >
              <StarFilled class="mode-icon" />
              <span class="mode-name">亮色</span>
            </div>
            <div 
              class="theme-mode-option"
              :class="{ active: themeMode === 'dark' }"
              @click="handleThemeModeChange('dark')"
            >
              <CloudFilled class="mode-icon" />
              <span class="mode-name">深色</span>
            </div>
            <div 
              class="theme-mode-option"
              :class="{ active: themeMode === 'auto' }"
              @click="handleThemeModeChange('auto')"
            >
              <MonitorOutlined class="mode-icon" />
              <span class="mode-name">跟随系统</span>
            </div>
          </div>
        </div>

        <!-- 主题色 -->
        <div class="theme-color-section">
          <div class="subsection-title">主题色</div>
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
      </div>

      <!-- 音质设置 -->
      <div class="setting-section">
        <div class="section-title">
          <AudioOutlined />
          <span>音质设置</span>
        </div>
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
              <a-tag color="blue" bordered>解析和下载时使用的默认音质（默认：无损）</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- 下载设置 -->
      <div class="setting-section">
        <div class="section-title">
          <DownloadOutlined />
          <span>下载配置</span>
        </div>
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
              <a-tag color="blue" bordered>写入歌曲名、歌手、专辑、封面、歌词等信息（默认开启）</a-tag>
            </div>
          </a-form-item>

          <a-form-item label="下载LRC歌词文件">
            <a-switch
              v-model:checked="settings.downloadLrcFile"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <a-tag color="blue" bordered>批量下载时同时生成独立的LRC歌词文件（默认开启）</a-tag>
            </div>
          </a-form-item>
        </a-form>
      </div>

      <!-- 解析设置 -->
      <div class="setting-section">
        <div class="section-title">
          <LinkOutlined />
          <span>解析配置</span>
        </div>
        <a-form :model="settings" layout="horizontal" class="settings-form">
          <a-form-item label="启用缓存">
            <a-switch
              v-model:checked="settings.enableCache"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <a-tag color="blue" bordered>减少重复搜索和解析，提升相同内容再次访问速度（默认开启）</a-tag>
            </div>
          </a-form-item>

          <a-form-item label="缓存大小">
            <div class="cache-info">
              <div class="cache-size">
                <FolderOpenOutlined class="cache-icon" />
                <span class="size-text">{{ cacheSize }}</span>
              </div>
              <a-button 
                type="danger" 
                size="small" 
                @click="handleClearCache"
                :loading="clearingCache"
                class="clear-cache-btn"
              >
                <DeleteOutlined />
                <span>清除缓存</span>
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
import { 
  CloseOutlined, 
  BgColorsOutlined, 
  StarFilled, 
  CloudFilled, 
  MonitorOutlined, 
  AudioOutlined, 
  DownloadOutlined, 
  LinkOutlined, 
  FolderOpenOutlined, 
  DeleteOutlined 
} from '@ant-design/icons-vue'

import { settings, saveSettings } from '../utils/settingsManager.js'
import { isDark, toggleTheme, setTheme, initThemeFromLocalStorage } from '../utils/themeManager.js'

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

const themeMode = ref('light')
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
  const savedThemeMode = localStorage.getItem('themeMode')
  const savedThemeColor = localStorage.getItem('themeColor')
  
  if (savedThemeMode) {
    themeMode.value = savedThemeMode
  }
  
  if (savedThemeColor) {
    const color = themeColors.find(c => c.value === savedThemeColor)
    if (color) {
      selectedThemeColor.value = color.hex
    }
  }
}

initThemeSettings()

const handleThemeModeChange = (mode) => {
  themeMode.value = mode
  localStorage.setItem('themeMode', mode)
  
  if (mode === 'auto') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    setTheme(prefersDark ? 'dark' : 'light')
    message.success('已设置为跟随系统')
  } else if (mode === 'dark') {
    setTheme('dark')
    message.success('已切换到深色主题')
  } else {
    setTheme('light')
    message.success('已切换到亮色主题')
  }
}

const handleThemeColorChange = (colorValue) => {
  const color = themeColors.find(c => c.value === colorValue)
  if (!color) return
  
  selectedThemeColor.value = color.hex
  localStorage.setItem('themeColor', colorValue)
  
  document.documentElement.style.setProperty('--color-primary', color.hex)
  
  if (themeMode.value === 'dark') {
    setTheme('dark')
  } else {
    setTheme('light')
  }
  
  // 通知父组件主题色变化
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
  padding: 16px 20px;
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
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin-bottom: 16px;
}

.section-title svg {
  font-size: 18px;
  color: var(--color-primary);
}

.settings-form {
  padding: 0 8px;
}

.settings-form :deep(.ant-form-item) {
  margin-bottom: 16px;
}

.settings-form :deep(.ant-form-item:last-child) {
  margin-bottom: 0;
}

.form-item-hint {
  margin-top: 4px;
}

.form-item-hint :deep(.ant-tag) {
  font-size: 12px;
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

.theme-mode-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 8px;
  border: 2px solid var(--color-border-subtle);
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-surface-white);
}

.theme-mode-option:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.theme-mode-option.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light, rgba(0, 87, 194, 0.08));
}

.mode-icon {
  font-size: 24px;
  color: var(--color-on-surface-variant);
}

.theme-mode-option.active .mode-icon {
  color: var(--color-primary);
}

.mode-name {
  font-size: 13px;
  color: var(--color-on-surface-variant);
  font-weight: 500;
}

.theme-mode-option.active .mode-name {
  color: var(--color-primary);
  font-weight: 600;
}

.theme-color-section {
  margin-top: 20px;
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

.cache-size {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-surface-container-low);
  border-radius: 8px;
}

.cache-icon {
  font-size: 16px;
  color: var(--color-primary);
}

.size-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
}

.clear-cache-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
}
</style>