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
        <span class="stat-item">
          <span class="stat-dot stat-running"></span>
          进行中 {{ store.activeCount.value }}
        </span>
        <span class="stat-item">
          <span class="stat-dot stat-done"></span>
          已完成 {{ store.completedCount.value }}
        </span>
      </div>
      <a-button
        v-if="hasCompleted"
        size="small"
        type="text"
        @click="handleClearCompleted"
        :disabled="clearing"
      >
        清理已完成
      </a-button>
    </div>

    <!-- 任务列表 -->
    <div v-if="store.taskList.value.length === 0" class="empty-state">
      <div class="empty-icon">📥</div>
      <p class="empty-text">暂无下载任务</p>
      <p class="empty-hint">批量下载时会显示在这里</p>
    </div>

    <div v-else class="task-list">
      <div
        v-for="task in store.taskList.value"
        :key="task.task_id"
        class="task-item"
        :class="`status-${task.status}`"
      >
        <!-- 任务头部：名称 + 状态 -->
        <div class="task-head">
          <div class="task-name" :title="task.name">
            {{ task.name || '未命名任务' }}
          </div>
          <div class="task-status-badge" :class="`badge-${task.status}`">
            {{ statusLabel(task.status) }}
          </div>
        </div>

        <!-- 进度条 -->
        <a-progress
          v-if="task.total > 0"
          :percent="getPercentage(task)"
          :status="getProgressStatus(task.status)"
          :stroke-color="getProgressColor(task.status)"
          size="small"
        />
        <a-progress
          v-else
          :percent="0"
          :show-info="false"
          size="small"
        />

        <!-- 进度详情 -->
        <div class="task-detail">
          <span class="detail-item">
            ✅ {{ task.completed }} / {{ task.total }}
          </span>
          <span v-if="task.failed > 0" class="detail-item failed">
            ❌ {{ task.failed }} 失败
          </span>
          <span v-if="task.current && task.status === 'running'" class="detail-item current">
            🎵 {{ task.current }}
          </span>
        </div>

        <!-- 错误信息 -->
        <div v-if="task.errors && task.errors.length > 0" class="task-errors">
          <a-collapse ghost>
            <a-collapse-panel :header="`${task.errors.length} 首失败`">
              <div
                v-for="(err, i) in task.errors.slice(0, 10)"
                :key="i"
                class="error-item"
              >
                <span class="error-name">{{ err.name }}</span>
                <span class="error-reason">{{ err.reason }}</span>
              </div>
              <div v-if="task.errors.length > 10" class="error-more">
                还有 {{ task.errors.length - 10 }} 首...
              </div>
            </a-collapse-panel>
          </a-collapse>
        </div>

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
              💾 下载 zip
            </a-button>
            <a-button
              size="small"
              @click="handleRemove(task)"
            >
              删除
            </a-button>
          </template>

          <!-- 失败/取消：删除 + 重试 -->
          <template v-else>
            <a-button
              size="small"
              @click="handleRemove(task)"
            >
              删除
            </a-button>
          </template>

          <!-- 错误信息：显示在右侧 -->
          <span v-if="task.error" class="error-msg" :title="task.error">
            {{ task.error }}
          </span>
        </div>
      </div>
    </div>

    <!-- 底部：关闭按钮 -->
    <template #footer>
      <div class="drawer-footer">
        <a-button @click="store.closeDrawer()">关闭</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
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
    cancelled: '已取消',
    pending: '同步中...'
  }
  return labels[status] || status
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
  return undefined  // 使用默认主题色
}

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
  // 抽屉打开时主动同步一次（确保最新状态）
  store.syncWithBackend()
})
</script>

<style scoped>
.download-drawer :deep(.ant-drawer-body) {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-subtle, #e5e7eb);
}

.stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.stat-running {
  background: #3b82f6;
  animation: pulse 1.5s ease-in-out infinite;
}

.stat-done {
  background: #10b981;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted, #9ca3af);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  margin: 4px 0;
  color: var(--color-text-secondary, #6b7280);
}

.empty-hint {
  font-size: 12px;
  margin: 4px 0;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.task-item {
  background: var(--color-surface-container, #f9fafb);
  border: 1px solid var(--color-border-subtle, #e5e7eb);
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s;
}

.task-item:hover {
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.task-item.status-running {
  border-left: 3px solid #3b82f6;
}

.task-item.status-done {
  border-left: 3px solid #10b981;
}

.task-item.status-error,
.task-item.status-cancelled {
  border-left: 3px solid #9ca3af;
  opacity: 0.85;
}

.task-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface, #111827);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.task-status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.badge-running {
  background: #dbeafe;
  color: #1e40af;
}

.badge-done {
  background: #d1fae5;
  color: #065f46;
}

.badge-error,
.badge-cancelled {
  background: #f3f4f6;
  color: #6b7280;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.task-detail {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-muted, #6b7280);
  margin-top: 6px;
  flex-wrap: wrap;
}

.detail-item.failed {
  color: #ef4444;
}

.detail-item.current {
  color: #3b82f6;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-errors {
  margin-top: 8px;
}

.task-errors :deep(.ant-collapse) {
  background: transparent;
  border: none;
}

.task-errors :deep(.ant-collapse-header) {
  padding: 4px 0 !important;
  font-size: 12px;
  color: #ef4444;
}

.error-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 2px 0;
  color: var(--color-text-secondary, #6b7280);
}

.error-name {
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.error-reason {
  color: #ef4444;
  font-size: 11px;
  max-width: 50%;
  text-align: right;
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
  margin-top: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.error-msg {
  font-size: 11px;
  color: #ef4444;
  flex: 1;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
