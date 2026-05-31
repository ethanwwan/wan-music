<template>
  <el-drawer
    v-model="drawerVisible"
    title="设置"
    width="450px"
    direction="rtl"
    :close-on-click-modal="true"
    :show-close="true"
    class="settings-drawer"
  >
    <div class="settings-content">
      <!-- 主题设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Palette /></el-icon>
          <span>主题设置</span>
        </div>
        <div class="theme-options">
          <div 
            v-for="theme in themes" 
            :key="theme.id"
            class="theme-option"
            :class="{ active: currentTheme === theme.id }"
            @click="handleThemeChange(theme.id)"
          >
            <div class="theme-preview">
              <div class="preview-primary" :style="{ background: theme.primary }"></div>
              <div class="preview-secondary" :style="{ background: theme.secondary }"></div>
              <div class="preview-accent" :style="{ background: theme.accent }"></div>
            </div>
            <span class="theme-name">{{ theme.name }}</span>
          </div>
        </div>
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
              <el-text type="info" size="small">写入歌曲名、歌手、专辑、封面等信息</el-text>
            </div>
          </el-form-item>

          <el-form-item label="启用ZIP打包">
            <el-switch
              v-model="settings.zipDownload"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">打包音频、歌词、封面等为一个压缩包</el-text>
            </div>
          </el-form-item>

          <el-form-item label="歌词格式">
            <el-switch
              v-model="settings.srtLyricsDownload"
              @change="handleSave"
              active-text="SRT"
              inactive-text="LRC"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">开启为 SRT 字幕；关闭为 LRC 歌词</el-text>
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
          <el-form-item label="启用链接缓存">
            <el-switch
              v-model="settings.enableUrlCache"
              @change="handleSave"
            />
            <div class="form-item-hint">
              <el-text type="info" size="small">减少重复解析，提升相同歌曲再次播放速度</el-text>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Link, Palette } from '@element-plus/icons-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'
import { isDark, toggleTheme, setTheme } from '../utils/themeManager.js'

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

const themes = [
  {
    id: 'light',
    name: '简约白',
    primary: '#0057c2',
    secondary: '#f5f5f5',
    accent: '#ffffff'
  },
  {
    id: 'dark',
    name: '深邃黑',
    primary: '#1a1a1a',
    secondary: '#2d2d2d',
    accent: '#3d3d3d'
  },
  {
    id: 'blue',
    name: '海洋蓝',
    primary: '#1e88e5',
    secondary: '#e3f2fd',
    accent: '#90caf9'
  },
  {
    id: 'purple',
    name: '优雅紫',
    primary: '#7c4dff',
    secondary: '#f3e5f5',
    accent: '#ce93d8'
  },
  {
    id: 'green',
    name: '清新绿',
    primary: '#43a047',
    secondary: '#e8f5e9',
    accent: '#81c784'
  }
]

const currentTheme = computed(() => {
  return isDark.value ? 'dark' : 'light'
})

const handleThemeChange = (themeId) => {
  if (themeId === 'dark') {
    setTheme('dark')
  } else if (themeId === 'light') {
    setTheme('light')
  } else {
    setTheme('light')
    document.documentElement.style.setProperty('--color-primary', themes.find(t => t.id === themeId)?.primary || '#0057c2')
  }
  ElMessage.success('主题已切换')
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
.settings-drawer {
  width: 450px !important;
}

.settings-drawer :deep(.el-drawer) {
  width: 450px !important;
}

.settings-content {
  padding: 20px 0;
  height: 100%;
  overflow-y: auto;
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

/* 主题选项样式 */
.theme-options {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  padding: 0 8px;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-surface-container-low);
}

.theme-option:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.theme-option.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.theme-preview {
  display: flex;
  gap: 3px;
  margin-bottom: 8px;
}

.preview-primary {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.preview-secondary {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  margin-top: 8px;
}

.preview-accent {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 12px;
}

.theme-name {
  font-size: 12px;
  color: var(--color-on-surface-variant);
  text-align: center;
}

.theme-option.active .theme-name {
  color: var(--color-primary);
  font-weight: 600;
}
</style>