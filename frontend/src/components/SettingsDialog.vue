<template>
  <el-dialog
    v-model="dialogVisible"
    title="设置"
    width="450px"
    :close-on-click-modal="true"
    :show-close="true"
    class="settings-dialog"
  >
    <div class="settings-content">
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
    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleClose">完成</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Link } from '@element-plus/icons-vue'
import { settings, saveSettings } from '../utils/settingsManager.js'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const handleSave = () => {
  saveSettings()
  ElMessage.success('设置已保存')
}

const handleClose = () => {
  handleSave()
  dialogVisible.value = false
}
</script>

<style scoped>
.settings-content {
  padding: 0;
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
</style>