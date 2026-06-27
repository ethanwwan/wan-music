/**
 * 下载队列 Store
 * 管理所有批量下载任务的状态、订阅 SSE
 */

import { ref, computed } from 'vue'
import {
  startBatchTask,
  getBatchList,
  cancelBatchTask,
  subscribeBatchTask,
  downloadBatchAsZip
} from '../services/musicApi.js'

// ==================== State ====================

/** 所有任务列表：Map<taskId, task> */
const tasks = ref(new Map())

/** 抽屉显示状态 */
const drawerOpen = ref(false)

/** 任务订阅句柄：Map<taskId, unsubscribeFn> */
const subscriptions = new Map()

// ==================== 任务管理 ====================

/**
 * 添加新任务并启动订阅
 * @param {Array} items 歌曲列表
 * @param {string} name 任务名
 * @param {Object} settings 下载设置
 * @returns {Promise<{task_id, total}>}
 */
const addTask = async (items, name = 'playlist', settings = {}) => {
  const result = await startBatchTask(items, name, settings)
  const taskId = result.data.task_id
  const task = {
    task_id: taskId,
    name: name,
    status: 'running',
    total: result.data.total,
    completed: 0,
    failed: 0,
    current: '准备中...',
    file_size: result.data.file_size || 0,
    errors: [],
    error: '',
    created_at: Date.now() / 1000,
    completed_at: 0,
    _items: items,  // 暂存用于重试
    _settings: settings
  }
  tasks.value.set(taskId, task)
  // 触发响应式更新（Map 需要重新赋值）
  tasks.value = new Map(tasks.value)

  // 启动 SSE 订阅
  subscribeTask(taskId)
  return { task_id: taskId, total: result.data.total }
}

/**
 * 订阅任务的进度更新
 */
const subscribeTask = (taskId) => {
  // 避免重复订阅
  if (subscriptions.has(taskId)) return

  const unsubscribe = subscribeBatchTask(taskId, {
    onProgress: (data) => {
      updateTask(taskId, {
        status: data.status,
        completed: data.completed,
        failed: data.failed,
        current: data.current,
        file_size: data.file_size || 0
      })
    },
    onComplete: (data) => {
      updateTask(taskId, {
        status: data.status,
        completed: data.completed,
        failed: data.failed,
        errors: data.errors || [],
        current: data.status === 'done' ? '完成' : '已取消',
        completed_at: Date.now() / 1000,
        file_size: data.file_size || 0,
        // 实际格式信息（仅在 done 时才有值）
        actual_format: data.actual_format,
        degraded: data.degraded || false,
        degraded_count: data.degraded_count || 0,
        format_breakdown: data.format_breakdown || {},
      })
      subscriptions.delete(taskId)
    },
    onError: (err) => {
      // SSE 错误时，从后端拉取最新状态
      console.warn(`[downloadQueue] 任务 ${taskId} SSE 错误:`, err.message)
      refreshTask(taskId)
    }
  })

  subscriptions.set(taskId, unsubscribe)
}

/**
 * 更新任务状态
 */
const updateTask = (taskId, patch) => {
  const task = tasks.value.get(taskId)
  if (!task) return
  Object.assign(task, patch)
  // 触发响应式
  tasks.value = new Map(tasks.value)
}

/**
 * 从后端拉取单个任务最新状态（用于重连）
 */
const refreshTask = async (taskId) => {
  try {
    const result = await getBatchList()
    if (result.success) {
      const found = result.data.find(t => t.task_id === taskId)
      if (found) {
        updateTask(taskId, {
          status: found.status,
          total: found.total,
          completed: found.completed,
          failed: found.failed,
          current: found.current || '',
          errors: found.errors || [],
          error: found.error || '',
          completed_at: found.completed_at || 0,
          file_size: found.file_size || 0,
          // 实际格式信息
          actual_format: found.actual_format,
          degraded: found.degraded || false,
          degraded_count: found.degraded_count || 0,
          format_breakdown: found.format_breakdown || {},
        })
        // 如果是进行中，重新订阅
        if (found.status === 'running') {
          if (subscriptions.has(taskId)) {
            subscriptions.get(taskId)()
            subscriptions.delete(taskId)
          }
          subscribeTask(taskId)
        } else {
          // 已完成/失败/取消，清理订阅
          if (subscriptions.has(taskId)) {
            subscriptions.get(taskId)()
            subscriptions.delete(taskId)
          }
        }
      } else {
        // 后端已无此任务（重启/清理）
        removeTask(taskId)
      }
    }
  } catch (e) {
    console.error(`[downloadQueue] 刷新任务 ${taskId} 失败:`, e)
  }
}

/**
 * 同步后端所有任务（启动时调用）
 * - 把后端有但前端没有的加进来
 * - 把后端没有但前端有的清掉
 * - 重新订阅进行中的任务
 */
const syncWithBackend = async () => {
  try {
    const result = await getBatchList()
    if (!result.success) return
    const backendTasks = new Map(result.data.map(t => [t.task_id, t]))
    const localIds = new Set(tasks.value.keys())
    const backendIds = new Set(backendTasks.keys())

    // 1. 后端有，前端没有 → 添加
    for (const [taskId, bt] of backendTasks) {
      if (!localIds.has(taskId)) {
        tasks.value.set(taskId, {
          task_id: taskId,
          name: bt.name,
          status: bt.status,
          total: bt.total,
          completed: bt.completed,
          failed: bt.failed,
          current: bt.current || '',
          errors: bt.errors || [],
          error: bt.error || '',
          created_at: bt.created_at || Date.now() / 1000,
          completed_at: bt.completed_at || 0,
          file_size: bt.file_size || 0,
          // 实际格式信息
          actual_format: bt.actual_format,
          degraded: bt.degraded || false,
          degraded_count: bt.degraded_count || 0,
          format_breakdown: bt.format_breakdown || {},
        })
      } else {
        // 同步最新进度
        const local = tasks.value.get(taskId)
        if (local.status === 'running' && bt.status !== 'running') {
          // 状态有变化，更新
          updateTask(taskId, {
            status: bt.status,
            completed: bt.completed,
            failed: bt.failed,
            current: bt.current || '',
            errors: bt.errors || [],
            error: bt.error || '',
            completed_at: bt.completed_at || 0,
            file_size: bt.file_size || 0,
            // 实际格式信息
            actual_format: bt.actual_format,
            degraded: bt.degraded || false,
            degraded_count: bt.degraded_count || 0,
            format_breakdown: bt.format_breakdown || {},
          })
        }
      }
    }

    // 2. 前端有，后端没有 → 移除
    for (const taskId of localIds) {
      if (!backendIds.has(taskId)) {
        tasks.value.delete(taskId)
      }
    }

    // 3. 重新订阅所有进行中的任务
    for (const [taskId, bt] of backendTasks) {
      if (bt.status === 'running') {
        subscribeTask(taskId)
      }
    }

    tasks.value = new Map(tasks.value)
  } catch (e) {
    console.error('[downloadQueue] 同步后端任务失败:', e)
  }
}

/**
 * 取消/删除任务
 */
const cancelTask = async (taskId) => {
  try {
    // 先取消订阅
    if (subscriptions.has(taskId)) {
      subscriptions.get(taskId)()
      subscriptions.delete(taskId)
    }
    // 调后端
    await cancelBatchTask(taskId)
    // 从列表移除
    removeTask(taskId)
    return { success: true }
  } catch (e) {
    console.error(`[downloadQueue] 取消任务 ${taskId} 失败:`, e)
    throw e
  }
}

/**
 * 从本地列表移除（不调后端）
 */
const removeTask = (taskId) => {
  tasks.value.delete(taskId)
  tasks.value = new Map(tasks.value)
}

/**
 * 下载完成任务的 zip
 */
const downloadTask = async (taskId) => {
  try {
    const filename = await downloadBatchAsZip(taskId)
    // 下载完成后删除任务
    await cancelTask(taskId)
    return filename
  } catch (e) {
    console.error(`[downloadQueue] 下载任务 ${taskId} 失败:`, e)
    throw e
  }
}

/**
 * 清理所有已完成/失败/取消的任务
 */
const clearCompleted = async () => {
  const completedIds = Array.from(tasks.value.entries())
    .filter(([_, t]) => ['done', 'error', 'cancelled'].includes(t.status))
    .map(([id]) => id)
  for (const id of completedIds) {
    try {
      await cancelTask(id)
    } catch (e) {
      // 任务可能已被后端清理
      removeTask(id)
    }
  }
}

// ==================== 抽屉控制 ====================

const openDrawer = () => { drawerOpen.value = true }
const closeDrawer = () => { drawerOpen.value = false }
const toggleDrawer = () => { drawerOpen.value = !drawerOpen.value }

// ==================== Computed ====================

/** 任务列表（按创建时间倒序）*/
const taskList = computed(() => {
  return Array.from(tasks.value.values())
    .sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
})

/** 进行中任务数 */
const activeCount = computed(() => {
  return taskList.value.filter(t => t.status === 'running').length
})

/** 已完成任务数（10 分钟内未下载的）*/
const completedCount = computed(() => {
  return taskList.value.filter(t => t.status === 'done' && !t.downloaded).length
})

// ==================== 初始化 ====================

/**
 * 启动时初始化：从后端同步任务列表
 */
const init = async () => {
  await syncWithBackend()
}

// ==================== 暴露 API ====================

export const downloadQueueStore = {
  // state
  tasks,
  drawerOpen,
  // computed
  taskList,
  activeCount,
  completedCount,
  // actions
  addTask,
  cancelTask,
  removeTask,
  downloadTask,
  refreshTask,
  syncWithBackend,
  clearCompleted,
  init,
  // drawer
  openDrawer,
  closeDrawer,
  toggleDrawer
}
