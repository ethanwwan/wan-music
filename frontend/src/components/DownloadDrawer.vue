<template>
  <a-drawer
    :open="store.drawerOpen.value"
    @update:open="(v) => v ? store.openDrawer() : store.closeDrawer()"
    title="下载队列"
    placement="right"
    :width="420"
    :destroy-on-close="false"
    class="download-drawer"
  >
    <!-- 头部：统计 + 清理按钮 -->
    <div class="drawer-header">
      <div class="stats">
        <a-tag color="blue">
          <component :is="CloudDownloadOutlined" class="mr-1" />
          进行中 {{ store.activeCount.value }}
        </a-tag>
        <a-tag color="green">
          <component :is="CheckCircleOutlined" class="mr-1" />
          已完成 {{ store.completedCount.value }}
        </a-tag>
      </div>
      <a-button
        v-if="hasCompleted"
        size="small"
        type="text"
        danger
        class="clear-task-btn"
        @click="handleClearCompleted"
        :loading="clearing"
      >
        清理已完成
      </a-button>
    </div>

    <!-- 任务列表 -->
    <div v-if="store.taskList.value.length === 0" class="empty-state">
      <div class="empty-container">
        <div class="empty-icon-wrapper">
          <div class="empty-icon-bg"></div>
          <component :is="DownloadOutlined" class="empty-icon" />
        </div>
        <div class="empty-content">
          <h3 class="empty-title">暂无下载任务</h3>
          <p class="empty-desc">批量下载歌曲时，任务会显示在这里</p>
        </div>
      </div>
    </div>

    <div v-else class="task-list">
      <a-card
        v-for="task in store.taskList.value"
        :key="task.task_id"
        :class="`task-card status-${task.status}`"
        hoverable
        :bordered="false"
      >
        <!-- 任务头部：名称 + 状态 -->
        <div class="task-head">
          <div class="task-name-wrapper">
            <component :is="MusicOutlined" class="task-icon" />
            <span class="task-name" :title="task.name">
              {{ task.name || '未命名任务' }}
            </span>
          </div>
          <a-tag :color="getStatusColor(task.status)">
            {{ statusLabel(task.status) }}
          </a-tag>
        </div>

        <!-- 进度条 -->
        <a-progress
          v-if="task.total > 0"
          :percent="getPercentage(task)"
          :status="getProgressStatus(task.status)"
          :stroke-color="getProgressColor(task.status)"
          :show-info="false"
          class="task-progress"
        />

        <!-- 进度详情 -->
        <div class="task-detail">
          <a-space :size="12">
            <span class="detail-item">
              <component :is="CheckCircleOutlined" class="success-icon" />
              {{ task.completed }} / {{ task.total }}
            </span>
            <span v-if="task.failed > 0" class="detail-item failed">
              <component :is="CloseCircleOutlined" class="error-icon" />
              {{ task.failed }} 失败
            </span>
            <span v-if="task.file_size > 0" class="detail-item">
              {{ formatFileSize(task.file_size) }}
            </span>
            <span v-if="task.current && task.status === 'running'" class="detail-item current">
              <component :is="HeadphonesOutlined" class="current-icon" />
              {{ task.current }}
            </span>
          </a-space>
        </div>

        <!-- 格式信息（单文件显示实际格式；ZIP 显示格式分布；降级时显示警告） -->
        <div v-if="task.status === 'done' && getFormatInfo(task).tags.length > 0" class="task-format">
          <component
            v-if="task.degraded"
            :is="WarningOutlined"
            class="degraded-icon"
          />
          <template v-for="(tag, idx) in getFormatInfo(task).tags" :key="idx">
            <a-tag :color="tag.color" class="format-tag">
              {{ tag.text }}
            </a-tag>
          </template>
        </div>

        <!-- 错误信息 -->
        <a-collapse
          v-if="task.errors && task.errors.length > 0"
          :default-active-key="['errors-' + task.task_id]"
          :bordered="false"
          class="task-errors"
        >
          <a-collapse-panel :key="'errors-' + task.task_id" :header="`${task.errors.length} 首失败`">
            <a-list
              :data-source="task.errors.slice(0, 10)"
              size="small"
              class="error-list"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <span class="error-name">{{ item.name }}</span>
                    </template>
                    <template #description>
                      <span class="error-reason">{{ item.reason }}</span>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
            <div v-if="task.errors.length > 10" class="error-more">
              还有 {{ task.errors.length - 10 }} 首...
            </div>
          </a-collapse-panel>
        </a-collapse>

        <!-- 操作按钮 -->
        <div class="task-actions">
          <!-- 进行中：取消 -->
          <a-button
            v-if="task.status === 'running'"
            size="small"
            danger
            @click="handleCancel(task)"
            :loading="cancellingId === task.task_id"
          >
            <component :is="StopOutlined" class="mr-1" />
            取消
          </a-button>

          <!-- 已完成：下载 + 删除 -->
          <template v-else-if="task.status === 'done'">
            <a-button
              size="small"
              type="primary"
              @click="handleDownload(task)"
              :loading="downloadingId === task.task_id"
            >
              下载
            </a-button>
            <a-button
              size="small"
              class="action-delete-btn"
              @click="handleRemove(task)"
            >
              删除
            </a-button>
          </template>

          <!-- 失败/取消：删除 -->
          <template v-else>
            <a-button
              size="small"
              class="action-delete-btn"
              @click="handleRemove(task)"
            >
              删除
            </a-button>
          </template>

          <!-- 错误信息：显示在右侧 -->
          <span v-if="task.error" class="error-msg" :title="task.error">
            <component :is="AlertCircleOutlined" class="error-icon" />
            {{ task.error }}
          </span>
        </div>
      </a-card>
    </div>

    <!-- 底部：关闭按钮 -->
    <template #footer>
      <div class="drawer-footer">
        <a-button @click="store.closeDrawer()">
          <component :is="CloseOutlined" class="mr-1" />
          关闭
        </a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import * as icons from '@ant-design/icons-vue'
const {
  DownloadOutlined,
  CheckCircleOutlined,
  MusicOutlined,
  CloseCircleOutlined,
  HeadphonesOutlined,
  StopOutlined,
  CloudDownloadOutlined,
  AlertCircleOutlined = icons.WarningOutlined,
  WarningOutlined,
  CloseOutlined,
  TrashOutlined
} = icons
import { downloadQueueStore as store } from '../stores/downloadQueue.js'

const cancellingId = ref(null)
const downloadingId = ref(null)
const clearing = ref(false)

const hasCompleted = computed(() => {
  return store.taskList.value.some(t =>
    ['done', 'error', 'cancelled'].includes(t.status)
  )
})

const statusLabel = (status) => {
  const labels = {
    running: '进行中',
    done: '已完成',
    error: '失败',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getStatusColor = (status) => {
  const colors = {
    running: 'blue',
    done: 'green',
    error: 'error',
    cancelled: 'default'
  }
  return colors[status] || 'default'
}

const getPercentage = (task) => {
  if (task.total === 0) return 0
  return Math.round((task.completed / task.total) * 100)
}

const getProgressStatus = (status) => {
  if (status === 'error') return 'exception'
  if (status === 'done') return 'success'
  if (status === 'cancelled') return 'normal'
  return 'active'
}

const getProgressColor = (status) => {
  if (status === 'cancelled') return '#999'
  return undefined
}

const formatFileSize = (bytes) => {
  if (!bytes || bytes <= 0) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

// 格式颜色映射
const FORMAT_COLORS = {
  flac: 'green',
  ogg: 'orange',
  mp3: 'blue',
  m4a: 'cyan',
  wav: 'purple',
}

// 格式显示名称
const FORMAT_LABELS = {
  flac: 'FLAC',
  ogg: 'OGG',
  mp3: 'MP3',
  m4a: 'M4A',
  wav: 'WAV',
}

// 根据 task 生成格式 tag 列表
// 单文件：[{text: 'FLAC', color: 'green'}]
// ZIP：[{text: 'FLAC × 10', color: 'green'}, {text: 'OGG × 2', color: 'orange'}]
const getFormatInfo = (task) => {
  const tags = []
  if (task.single_file) {
    // 单文件：直接显示 actual_format
    const fmt = (task.actual_format || 'mp3').toLowerCase()
    tags.push({
      text: FORMAT_LABELS[fmt] || fmt.toUpperCase(),
      color: FORMAT_COLORS[fmt] || 'default'
    })
  } else {
    // ZIP：按格式数量倒序展示
    const breakdown = task.format_breakdown || {}
    const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1])
    for (const [fmt, count] of entries) {
      const f = fmt.toLowerCase()
      tags.push({
        text: `${FORMAT_LABELS[f] || f.toUpperCase()} × ${count}`,
        color: FORMAT_COLORS[f] || 'default'
      })
    }
  }
  return { tags }
}

// 已通知过的降级任务 ID（避免重复弹窗）
const notifiedDegradedIds = new Set()
// 监听新完成的任务，若有降级则弹 notification
watch(() => store.taskList.value, (tasks) => {
  for (const t of tasks) {
    if (t.status === 'done' && t.degraded && !notifiedDegradedIds.has(t.task_id)) {
      notifiedDegradedIds.add(t.task_id)
      const cnt = t.degraded_count || 1
      const total = t.total || cnt
      message.warning(
        `《${t.name}》：${cnt}/${total} 首请求的无损不可用，已降级为有损格式`,
        5
      )
    }
  }
}, { deep: true })

const handleCancel = async (task) => {
  Modal.confirm({
    title: '确认取消',
    content: `取消任务 "${task.name}"？已下载的歌曲将不会保存。`,
    okText: '确认取消',
    cancelText: '继续下载',
    okButtonProps: { danger: true },
    onOk: async () => {
      cancellingId.value = task.task_id
      try {
        await store.cancelTask(task.task_id)
        message.success('已取消')
      } catch (e) {
        message.error(`取消失败: ${e.message}`)
      } finally {
        cancellingId.value = null
      }
    }
  })
}

const handleDownload = async (task) => {
  downloadingId.value = task.task_id
  try {
    const filename = await store.downloadTask(task.task_id)
    message.success(`已下载: ${filename}`)
  } catch (e) {
    message.error(`下载失败: ${e.message}`)
  } finally {
    downloadingId.value = null
  }
}

const handleRemove = async (task) => {
  try {
    await store.removeTask(task.task_id)
  } catch (e) {
    // 忽略
  }
}

const handleClearCompleted = async () => {
  clearing.value = true
  try {
    await store.clearCompleted()
    message.success('已清理')
  } catch (e) {
    message.error(`清理失败: ${e.message}`)
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  store.syncWithBackend()
})
</script>

<style scoped>
.download-drawer :deep(.ant-drawer-body) {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
}

.stats {
  display: flex;
  gap: 8px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-icon-wrapper {
  position: relative;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.empty-icon-bg {
  position: absolute;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.empty-icon {
  font-size: 48px;
  color: #fff;
  z-index: 1;
  animation: float 3s ease-in-out infinite;
}

.empty-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-on-surface, #111827);
  margin: 0;
}

.empty-desc {
  font-size: 14px;
  color: var(--color-text-muted, #9ca3af);
  margin: 0;
  max-width: 280px;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.85;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  overflow-x: visible;       /* 关键：不要水平裁切，让卡片阴影能溢出 */
  flex: 1;
  padding: 6px 4px;          /* 给卡片左右各留 4px 让阴影有空间显示 */
}

/* a-card 内部结构：让 .ant-card-body 也不裁切阴影 */
.task-list :deep(.ant-card) {
  overflow: visible !important;
}
.task-list :deep(.ant-card-body) {
  overflow: visible !important;
}

/* 任务卡片：使用对称彩色辉光阴影（四周均匀分布） */
/* 用 !important 防止 Ant Design Vue 的默认 .ant-card 样式覆盖 */
.task-card {
  transition: all 0.25s ease;
  border-radius: 12px;
  background: var(--color-surface-white, #fff) !important;
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.06),
    0 0 12px rgba(0, 0, 0, 0.06),
    0 2px 4px rgba(0, 0, 0, 0.04),
    0 6px 16px rgba(0, 0, 0, 0.08) !important;
}

.task-card:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.08),
    0 0 16px rgba(0, 0, 0, 0.08),
    0 4px 8px rgba(0, 0, 0, 0.06),
    0 12px 28px rgba(0, 0, 0, 0.12) !important;
}

/* 下载中：蓝色脉冲阴影（核心动画，使用更强的颜色） */
.task-card.status-running {
  position: relative;
  animation: running-shadow-pulse 2s ease-in-out infinite;
}

@keyframes running-shadow-pulse {
  0%, 100% {
    box-shadow:
      0 0 0 1px rgba(59, 130, 246, 0.40),
      0 0 12px rgba(59, 130, 246, 0.32),
      0 0 24px rgba(59, 130, 246, 0.22),
      0 2px 4px rgba(59, 130, 246, 0.22),
      0 6px 18px rgba(59, 130, 246, 0.20) !important;
  }
  50% {
    box-shadow:
      0 0 0 1px rgba(59, 130, 246, 0.55),
      0 0 20px rgba(59, 130, 246, 0.45),
      0 0 40px rgba(59, 130, 246, 0.30),
      0 4px 8px rgba(59, 130, 246, 0.28),
      0 10px 28px rgba(59, 130, 246, 0.25) !important;
  }
}

.task-card.status-running:hover {
  animation-play-state: paused;
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(59, 130, 246, 0.60),
    0 0 20px rgba(59, 130, 246, 0.48),
    0 0 40px rgba(59, 130, 246, 0.32),
    0 4px 8px rgba(59, 130, 246, 0.28),
    0 10px 28px rgba(59, 130, 246, 0.25) !important;
}

/* 已完成：绿色辉光（表示成功） */
.task-card.status-done {
  box-shadow:
    0 0 0 1px rgba(16, 185, 129, 0.35),
    0 0 12px rgba(16, 185, 129, 0.30),
    0 0 24px rgba(16, 185, 129, 0.20),
    0 2px 4px rgba(16, 185, 129, 0.20),
    0 6px 18px rgba(16, 185, 129, 0.18) !important;
}

.task-card.status-done:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(16, 185, 129, 0.50),
    0 0 16px rgba(16, 185, 129, 0.40),
    0 0 32px rgba(16, 185, 129, 0.25),
    0 4px 8px rgba(16, 185, 129, 0.24),
    0 10px 28px rgba(16, 185, 129, 0.20) !important;
}

/* 失败/取消：灰暗阴影 + 透明度 */
.task-card.status-error,
.task-card.status-cancelled {
  opacity: 0.75;
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.06),
    0 0 8px rgba(0, 0, 0, 0.05),
    0 1px 2px rgba(0, 0, 0, 0.04),
    0 2px 6px rgba(0, 0, 0, 0.06) !important;
}

.task-card.status-error:hover,
.task-card.status-cancelled:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.task-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-name-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.task-icon {
  font-size: 18px;
  color: #3b82f6;
}

.task-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface, #111827);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-progress {
  margin: 4px 0;
}

/* 进度条更细：从默认 8px 改为 4px */
.task-progress :deep(.ant-progress-outer) {
  height: 4px !important;
}
.task-progress :deep(.ant-progress-bg) {
  height: 4px !important;
}

.task-detail {
  margin-bottom: 12px;
}

/* 实际格式展示（单文件 / ZIP） */
.task-format {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  padding: 6px 8px;
  background: var(--color-bg-muted, #f5f7fa);
  border-radius: 6px;
}

.task-format .degraded-icon {
  color: #fa8c16;
  font-size: 14px;
  margin-right: 2px;
}

.task-format .format-tag {
  margin: 0;
  font-size: 11px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}

.detail-item.failed {
  color: #ef4444;
}

.detail-item.current {
  color: #3b82f6;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.success-icon {
  color: #10b981;
}

.error-icon {
  color: #ef4444;
}

.current-icon {
  color: #3b82f6;
}

.task-errors {
  margin-bottom: 12px;
  background: #fef2f2;
  border-radius: 8px;
  padding: 8px;
}

.task-errors :deep(.ant-collapse-header) {
  padding: 4px 0 !important;
  font-size: 12px;
  color: #ef4444;
}

.task-errors :deep(.ant-collapse-content) {
  padding: 8px 0 !important;
}

.error-list :deep(.ant-list-item) {
  padding: 4px 0 !important;
}

.error-name {
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.error-reason {
  font-size: 11px;
  color: #ef4444;
}

.error-more {
  font-size: 11px;
  color: var(--color-text-muted, #9ca3af);
  text-align: center;
  padding: 4px 0;
}

.task-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding-top: 12px;
}

/* 删除按钮：默认灰文字，hover 时变红（和全局 clear 按钮风格一致） */
.action-delete-btn {
  color: var(--color-text-muted, #6b7280) !important;
  transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.action-delete-btn:hover {
  color: var(--color-error, #d4380d) !important;
  border-color: var(--color-error, #d4380d) !important;
  background: rgba(212, 56, 13, 0.06) !important;
}

.error-msg {
  font-size: 11px;
  color: #ef4444;
  flex: 1;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
