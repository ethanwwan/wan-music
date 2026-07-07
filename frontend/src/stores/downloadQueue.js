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

// ==================== 后端未就绪的容错机制 ====================
//
// 后端启动慢（加载 30+ 数据源 ~ 10s），前端启动时（特别是 Vite HMR 触发）
// 调用 /download/batch/list 会 ECONNREFUSED。
// 这里对 store 内的所有 fetch 提供"静默重试"包装：
// - 失败时指数退避重试 3 次（2s, 4s, 8s），总等待 ~14s，足够后端就绪
// - 重试都失败时用 console.warn（黄色，不刷红色 error）
// - 用户主动操作（addTask/cancelTask/downloadTask）失败仍 throw
// - 后台自动调用（init / refreshTask）失败静默吞掉
//
// 这样开发体验显著提升，不会再看到 1 行 + 0 行的红色 error 错误。
// ====================================================================

/**
 * 静默重试包装（用于后台自动调用的 API）
 * - 不 throw
 * - 重试都失败时 console.warn（不 console.error）
 * - 用户操作场景不要用这个（应该把错误暴露给用户）
 */
const silentFetch = async (fn, { maxRetries = 3, baseDelay = 2000, context = '' } = {}) => {
  let lastErr
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn()
    } catch (e) {
      lastErr = e
      if (i < maxRetries) {
        await new Promise(r => setTimeout(r, baseDelay * (1 << i)))  // 2s, 4s, 8s
      }
    }
  }
  // 重试都失败：静默 warn（不是 error）
  console.warn(`[downloadQueue] ${context} 后端未就绪（已重试 ${maxRetries} 次）: ${lastErr?.message || lastErr}`)
  return null  // 静默吞掉
}

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
    songs: items.map(it => ({  // 立即构造初始 songs 列表（后端会推送真实状态）
      id: it.id,
      name: it.name,
      artist: it.artist || it.artists,
      platform: it.platform || it.source,
      level: it.quality,
      status: 'pending',
      file_size: 0,
      error: '',
    })),
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
      // 前端累计 file_size：所有 done 歌曲的 file_size 之和
      // 这样用户能实时看到累计大小（不用等任务完成才更新）
      const songs = data.songs || []
      const totalSize = songs
        .filter(s => s.status === 'done' && s.file_size > 0)
        .reduce((sum, s) => sum + s.file_size, 0)
      updateTask(taskId, {
        status: data.status,
        completed: data.completed,
        failed: data.failed,
        current: data.current,
        file_size: totalSize,              // 前端累加（覆盖后端估算）
        songs: data.songs || undefined,    // 后端推送 per-song 状态（undefined 时保留本地）
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
        songs: data.songs || undefined,
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
  // 后台静默重试：SSE 错误时自动重连，后端未就绪时静默等待
  const result = await silentFetch(() => getBatchList(), {
    context: `刷新任务 ${taskId}`,
    maxRetries: 2,        // 2s + 4s = 6s（比 syncWithBackend 短，因为这是 SSE 重连）
  })
  if (!result || !result.success) return
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
      songs: found.songs || [],
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

/**
 * 同步后端所有任务（启动时调用）
 * - 把后端有但前端没有的加进来
 * - 把后端没有但前端有的清掉
 * - 重新订阅进行中的任务
 */
const syncWithBackend = async () => {
  // 启动时静默重试：后端需要 ~10s 加载，silentFetch 等到 ~14s
  const result = await silentFetch(() => getBatchList(), {
    context: '同步后端任务',
    maxRetries: 3,        // 2s + 4s + 8s = 14s
  })
  if (!result || !result.success) return
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
        songs: bt.songs || [],            // per-song 状态
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
          songs: bt.songs || [],
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
}

/**
 * 取消/删除任务
 */
const cancelTask = async (taskId) => {
  // 先取消订阅
  if (subscriptions.has(taskId)) {
    subscriptions.get(taskId)()
    subscriptions.delete(taskId)
  }
  // 调后端（用户主动操作，错误要暴露给 UI，但静默重试一次）
  let err
  for (let i = 0; i < 2; i++) {  // 最多重试 1 次
    try {
      await cancelBatchTask(taskId)
      // 从列表移除
      removeTask(taskId)
      return { success: true }
    } catch (e) {
      err = e
      if (i < 1) {
        await new Promise(r => setTimeout(r, 1500))  // 等 1.5s 重试
      }
    }
  }
  // 重试后仍失败：console.warn 而不是 console.error
  console.warn(`[downloadQueue] 取消任务 ${taskId} 失败:`, err?.message || err)
  throw err
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
  // 用户主动操作，错误要暴露给 UI，但 console.warn 而不是 console.error
  let err
  for (let i = 0; i < 2; i++) {
    try {
      const filename = await downloadBatchAsZip(taskId)
      // 下载完成后删除任务
      await cancelTask(taskId)
      return filename
    } catch (e) {
      err = e
      if (i < 1) {
        await new Promise(r => setTimeout(r, 1500))
      }
    }
  }
  console.warn(`[downloadQueue] 下载任务 ${taskId} 失败:`, err?.message || err)
  throw err
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
//
// 关键设计：syncWithBackend 不在 init() 触发，而是 lazy 在 openDrawer 触发。
// 这样启动时**完全零 fetch**（Chrome DevTools 网络层错误无法用 JS 拦截）。
//
// 但 syncWithBackend 自身仍然会做静默重试（silentFetch）——
// 因为用户打开 drawer 时，后端可能仍没就绪（init 时不做 → 用户可能
// 立即点开 drawer，那时后端只启动了 1-2s）。

const openDrawer = () => {
  drawerOpen.value = true
  // 同步放后台，不阻塞抽屉立即展示
  // 下载后的任务已由 addTask() 加入本地 tasks，用户立即可见
  syncWithBackend()
}
const closeDrawer = () => { drawerOpen.value = false }
const toggleDrawer = () => {
  drawerOpen.value = !drawerOpen.value
  if (drawerOpen.value) {
    syncWithBackend()
  }
}

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
 * 启动时初始化：故意不做任何 fetch
 *
 * 原因：Chrome DevTools 对任何 fetch 失败都会自动打印网络层错误
 * （如 ERR_EMPTY_RESPONSE / net::ERR_ABORTED），这是浏览器自身行为，
 * JS 代码无法拦截。
 *
 * 后端启动慢（~10s 加载 30+ 数据源），前端启动时立即调 fetch 几乎必败。
 *
 * 解决方案：
 * 1. App 启动时**不**自动调 syncWithBackend
 * 2. 用户**主动操作**（打开抽屉 / 点击刷新）时调
 * 3. silentFetch 在应用层重试 + 静默
 *
 * 这样启动期间**零**网络层错误，用户体验最佳。
 */
const init = async () => {
  // 故意不做事。syncWithBackend 在 openDrawer / 手动刷新时按需调用
  return
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
