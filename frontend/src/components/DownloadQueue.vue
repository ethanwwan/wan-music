<template>
  <div class="download-queue">
    <div class="queue-content">
      <div class="queue-info" v-if="tasks.length > 0">
        <span class="info-text">共 {{ tasks.length }} 个任务</span>
      </div>
      <div v-if="tasks.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <p>暂无下载任务</p>
      </div>
      
      <div v-else class="task-list">
        <div v-for="task in formattedTasks" :key="task.task_id" class="task-item" :class="task.status">
          <div class="task-info">
            <div class="task-name">{{ task.music_name || `歌曲 #${task.music_id}` }}</div>
            <div class="task-meta">
              <span class="task-status" :style="{ color: task.status_color }">
                {{ task.status_text }}
              </span>
              <span v-if="task.progress_display" class="task-progress">
                {{ task.progress_display.percentage }}% · {{ task.progress_display.downloaded }} / {{ task.progress_display.total }}
              </span>
              <span v-if="task.progress_display && task.status === 'downloading'" class="task-speed">
                · {{ task.progress_display.speed }}
              </span>
              <span v-if="task.progress_display && task.status === 'downloading'" class="task-eta">
                · 剩余 {{ task.progress_display.eta }}
              </span>
            </div>
          </div>
          
          <div class="task-progress-bar" v-if="task.progress_display && task.status === 'downloading'">
            <div class="progress-fill" :style="{ width: task.progress_display.percentage + '%' }"></div>
          </div>
          
          <div class="task-actions">
            <button v-if="task.status === 'downloading'" @click="handlePause(task.task_id)" 
                    class="action-btn pause-btn" title="暂停">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            </button>
            
            <button v-else-if="task.status === 'paused' || task.status === 'pending'" 
                    @click="handleResume(task.task_id)" class="action-btn resume-btn" title="继续">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
            </button>
            
            <button @click="handleCancel(task.task_id)" class="action-btn cancel-btn" 
                    :disabled="['completed', 'cancelled'].includes(task.status)" title="取消">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z" />
              </svg>
            </button>
            
            <button @click="handleRemove(task.task_id)" class="action-btn remove-btn" title="删除">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { 
  getAllTasks, 
  pauseTask, 
  resumeTask, 
  cancelTask, 
  removeTask,
  formatTask,
  setOnTasksUpdate,
  startTaskPolling,
  stopTaskPolling
} from '../services/downloadManager.js'

// 响应式数据
const tasks = ref([])
const loading = ref(false)
const error = ref(null)

// 格式化任务
const formattedTasks = computed(() => {
  return tasks.value.map(task => formatTask(task))
})

// 加载任务
const loadTasks = async () => {
  try {
    loading.value = true
    const taskList = await getAllTasks()
    tasks.value = taskList
  } catch (err) {
    error.value = err.message
    console.error('加载任务失败:', err)
  } finally {
    loading.value = false
  }
}

// 处理暂停
const handlePause = async (taskId) => {
  try {
    await pauseTask(taskId)
  } catch (err) {
    console.error('暂停任务失败:', err)
  }
}

// 处理恢复
const handleResume = async (taskId) => {
  try {
    await resumeTask(taskId)
  } catch (err) {
    console.error('恢复任务失败:', err)
  }
}

// 处理取消
const handleCancel = async (taskId) => {
  try {
    await cancelTask(taskId)
  } catch (err) {
    console.error('取消任务失败:', err)
  }
}

// 处理删除
const handleRemove = async (taskId) => {
  try {
    await removeTask(taskId)
  } catch (err) {
    console.error('删除任务失败:', err)
  }
}

// 生命周期
onMounted(() => {
  // 设置任务更新回调
  setOnTasksUpdate((updatedTasks) => {
    tasks.value = updatedTasks
  })
  
  // 初始加载
  loadTasks()
  
  // 开始轮询
  startTaskPolling(1000)
})

onUnmounted(() => {
  // 停止轮询
  stopTaskPolling()
})
</script>

<style scoped>
.download-queue {
  background: var(--color-surface);
  border-radius: 8px;
  overflow: hidden;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.queue-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--color-on-surface);
}

.queue-actions {
  display: flex;
  gap: 8px;
}

.task-count {
  font-size: 14px;
  color: var(--color-text-muted);
}

.queue-content {
  max-height: 400px;
  overflow-y: auto;
}

.queue-content::-webkit-scrollbar {
  display: none;
}

.queue-content {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--color-text-muted);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-muted);
}

.task-list {
  padding: 8px;
}

.queue-info {
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.info-text {
  font-size: 13px;
  color: var(--color-text-muted);
}

.task-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 4px;
  background: var(--color-surface-container-low);
  transition: background 0.2s;
}

.task-item:hover {
  background: var(--color-surface-container-high);
}

.task-item.completed {
  background: rgba(16, 185, 129, 0.1);
}

.task-item.failed {
  background: rgba(239, 68, 68, 0.1);
}

.task-item.paused {
  background: rgba(245, 158, 11, 0.1);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.task-progress-bar {
  height: 4px;
  background: var(--color-border-subtle);
  border-radius: 2px;
  overflow: hidden;
  margin: 0 12px;
  min-width: 100px;
  flex: 0 0 100px;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.task-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  padding: 4px;
}

.action-btn:hover {
  background: var(--color-surface-container-high);
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.action-btn svg {
  width: 16px;
  height: 16px;
  color: var(--color-on-surface-variant);
}

.pause-btn:hover svg,
.resume-btn:hover svg {
  color: var(--color-primary);
}

.cancel-btn:hover svg {
  color: var(--color-primary);
}

.remove-btn:hover svg {
  color: #ef4444;
}
</style>
