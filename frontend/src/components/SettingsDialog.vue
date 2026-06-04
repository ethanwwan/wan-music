<template>
  <el-drawer
    v-model="drawerVisible"
    width="450px"
    direction="rtl"
    :close-on-click-modal="true"
    :show-close="true"
    :with-header="false"
    class="settings-drawer"
  >
    <!-- 自定义头部 -->
    <div class="custom-header">
      <span class="header-title">设置</span>
      <el-icon class="close-icon" @click="drawerVisible = false"><Close /></el-icon>
    </div>
    
    <div class="settings-content">
      <!-- 主题设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Brush /></el-icon>
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
              <el-icon class="mode-icon"><Sunny /></el-icon>
              <span class="mode-name">亮色</span>
            </div>
            <div 
              class="theme-mode-option"
              :class="{ active: themeMode === 'dark' }"
              @click="handleThemeModeChange('dark')"
            >
              <el-icon class="mode-icon"><Moon /></el-icon>
              <span class="mode-name">深色</span>
            </div>
            <div 
              class="theme-mode-option"
              :class="{ active: themeMode === 'auto' }"
              @click="handleThemeModeChange('auto')"
            >
              <el-icon class="mode-icon"><Monitor /></el-icon>
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
          <el-icon><Headset /></el-icon>
          <span>音质设置</span>
        </div>
        <el-form :model="settings" label-width="120px" label-position="left" class="settings-form">
          <el-form-item label="默认音质">
            <el-select
              v-model="settings.selectedQuality"
              @change="handleSave"
              style="width: 160px"
            >
              <el-option label="标准 (128kbps)" value="standard" />
              <el-option label="极高 (320kbps)" value="exhigh" />
              <el-option label="无损 (FLAC)" value="lossless" />
              <el-option label="Hi-Res (FLAC 24bit)" value="hires" />
              <el-option label="沉浸 (Dolby Atmos)" value="sky" />
              <el-option label="环绕 (Sony 360RA)" value="jyeffect" />
              <el-option label="母带 (FLAC 24bit/96kHz)" value="jymaster" />
            </el-select>
            <div class="form-item-hint">
              <el-text type="info" size="small">解析和下载时使用的默认音质（默认：无损）</el-text>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 下载设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Download /></el-icon>
          <span>下载配置</span>
        </div>
        <el-form :model="settings" label-width="120px" label-position="left" class="settings-form">
          <el-form-item label="文件命名格式">
            <el-select
              v-model="settings.filenameFormat"
              @change="handleSave"
              style="width: 160px"
            >
              <el-option label="歌曲名 - 歌手名" value="song-artist" />
              <el-option label="歌手名 - 歌曲名" value="artist-song" />
              <el-option label="仅歌曲名" value="song-only" />
            </el-select>
            <div class="form-item-hint">
              <el-text type="info" size="small">
                示例：{{ settings.filenameFormat === 'artist-song' ? '歌手 - 歌曲' : (settings.filenameFormat === 'song-only' ? '歌曲' : '歌曲 - 歌手') }}
              </el-text>
            </div>
          </el-form-item>

          <el-form-item label="自动写入元数据">
            <el-switch
              v-model="settings.writeMetadata"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">写入歌曲名、歌手、专辑、封面、歌词等信息（默认开启）</el-text>
            </div>
          </el-form-item>

          <el-form-item label="下载LRC歌词文件">
            <el-switch
              v-model="settings.downloadLrcFile"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">批量下载时同时生成独立的LRC歌词文件（默认开启）</el-text>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 解析设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Link /></el-icon>
          <span>解析配置</span>
        </div>
        <el-form :model="settings" label-width="120px" label-position="left" class="settings-form">
          <el-form-item label="启用缓存">
            <el-switch
              v-model="settings.enableCache"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">减少重复搜索和解析，提升相同内容再次访问速度（默认开启）</el-text>
            </div>
          </el-form-item>

          <el-form-item label="缓存大小">
            <div class="cache-info">
              <div class="cache-size">
                <el-icon class="cache-icon"><Database /></el-icon>
                <span class="size-text">{{ cacheSize }}</span>
              </div>
              <el-button 
                type="danger" 
                size="small" 
                @click="handleClearCache"
                :loading="clearingCache"
                class="clear-cache-btn"
              >
                <el-icon><Trash /></el-icon>
                <span>清除缓存</span>
              </el-button>
            </div>
            <div class="form-item-hint">
              <el-text type="info" size="small">缓存包括搜索结果、歌曲信息等，清除后下次访问会重新获取</el-text>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage, ElConfirm } from 'element-plus'
import { Download, Link, Brush, Headset, Sunny, Moon, Monitor, Close, Database, Trash } from '@element-plus/icons-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'
import { isDark, toggleTheme, setTheme, initThemeFromLocalStorage } from '../utils/themeManager.js'

// 缓存大小
const cacheSize = ref('0 KB')
// 清除缓存加载状态
const clearingCache = ref(false)

// 计算 localStorage 缓存大小
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
  
  // 转换为可读格式
  if (totalSize < 1024) {
    return `${totalSize} B`
  } else if (totalSize < 1024 * 1024) {
    return `${(totalSize / 1024).toFixed(2)} KB`
  } else {
    return `${(totalSize / (1024 * 1024)).toFixed(2)} MB`
  }
}

// 刷新缓存大小
const refreshCacheSize = () => {
  cacheSize.value = calculateCacheSize()
}

// 清除缓存
const handleClearCache = async () => {
  await ElConfirm(
    '确认清除缓存？',
    '清除后所有缓存数据将被删除，下次访问需要重新加载',
    {
      confirmButtonText: '确认清除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    clearingCache.value = true
    
    try {
      // 清除 localStorage
      localStorage.clear()
      
      // 清除 sessionStorage
      sessionStorage.clear()
      
      // 清除内存中的缓存（如果有）
      // 这里可以添加其他缓存清理逻辑
      
      // 刷新缓存大小显示
      refreshCacheSize()
      
      ElMessage.success('缓存已清除')
    } catch (e) {
      ElMessage.error('清除缓存失败')
    } finally {
      clearingCache.value = false
    }
  }).catch(() => {
    // 用户取消
  })
}

// 组件挂载时计算缓存大小
onMounted(() => {
  refreshCacheSize()
})

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const drawerVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 主题模式：light, dark, auto
const themeMode = ref('light')
// 选中的主题色
const selectedThemeColor = ref('#0057c2')

// 主题色选项（6种经典色）
const themeColors = [
  { name: '默认蓝', value: 'blue', hex: '#0057c2' },
  { name: '活力红', value: 'red', hex: '#e53935' },
  { name: '优雅紫', value: 'purple', hex: '#8e24aa' },
  { name: '清新绿', value: 'green', hex: '#43a047' },
  { name: '温暖橙', value: 'orange', hex: '#fb8c00' },
  { name: '深邃青', value: 'cyan', hex: '#00acc1' }
]

// 初始化时从 localStorage 读取主题设置
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

// 组件挂载时初始化
initThemeSettings()

// 处理主题模式切换
const handleThemeModeChange = (mode) => {
  themeMode.value = mode
  localStorage.setItem('themeMode', mode)
  
  if (mode === 'auto') {
    // 跟随系统
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    setTheme(prefersDark ? 'dark' : 'light')
    ElMessage.success('已设置为跟随系统')
  } else if (mode === 'dark') {
    setTheme('dark')
    ElMessage.success('已切换到深色主题')
  } else {
    setTheme('light')
    ElMessage.success('已切换到亮色主题')
  }
}

// 处理主题色切换
const handleThemeColorChange = (colorValue) => {
  const color = themeColors.find(c => c.value === colorValue)
  if (!color) return
  
  selectedThemeColor.value = color.hex
  localStorage.setItem('themeColor', colorValue)
  
  // 应用主题色
  document.documentElement.style.setProperty('--color-primary', color.hex)
  
  // 如果是深色模式，确保保持深色
  if (themeMode.value === 'dark') {
    setTheme('dark')
  } else {
    setTheme('light')
  }
  
  ElMessage.success(`已切换到${color.name}`)
}

const handleSave = () => {
  saveSettings()
  ElMessage.success('设置已保存')
}

const handleClose = () => {
  handleSave()
  drawerVisible.value = false
}
</script>

<style scoped>
/* 自定义头部样式 */
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
  height: calc(100% - 57px); /* 减去头部高度 */
  overflow-y: auto;
}

/* 隐藏滚动条 */
.settings-content::-webkit-scrollbar {
  display: none;
}

.settings-content {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
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

.section-title .el-icon {
  font-size: 18px;
  color: var(--color-primary);
}

.settings-form {
  padding: 0 8px;
}

.settings-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.settings-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.settings-form :deep(.el-form-item__content) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.form-item-hint {
  margin-top: 4px;
}

/* 子标题样式 */
.subsection-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface-variant);
  margin-bottom: 12px;
  padding-left: 4px;
}

/* 主题模式选项 */
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

/* 主题色选项 */
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

/* 缓存信息样式 */
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

.clear-cache-btn:hover {
  background: #ff4d4f !important;
}

.clear-cache-btn:deep(.el-icon) {
  font-size: 14px;
}
</style>