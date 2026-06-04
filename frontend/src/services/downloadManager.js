/**
 * 增强版下载管理器
 * 使用后端API进行下载队列管理
 */

// 任务状态枚举
export const DOWNLOAD_STATUSES = {
  PENDING: 'pending',
  DOWNLOADING: 'downloading',
  COMPLETED: 'completed',
  FAILED: 'failed',
  PAUSED: 'paused',
  CANCELLED: 'cancelled'
}

// 本地下载队列存储
let taskUpdateInterval = null
let localTasks = new Map()
let onTasksUpdateCallback = null

// 设置任务更新回调
export const setOnTasksUpdate = (callback) => {
  onTasksUpdateCallback = callback
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

// 格式化速度
const formatSpeed = (bytesPerSecond) => {
  if (!bytesPerSecond) return '0 KB/s'
  const kbps = bytesPerSecond / 1024
  if (kbps >= 1024) {
    return `${(kbps / 1024).toFixed(2)} MB/s`
  }
  return `${kbps.toFixed(2)} KB/s`
}

// 格式化ETA
const formatEta = (seconds) => {
  if (!seconds || seconds === Infinity) return '未知'
  if (seconds < 60) return `${Math.round(seconds)} 秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)} 分`
  return `${(seconds / 3600).toFixed(1)} 小时`
}

// 添加单个任务到队列
export const addToQueue = async (musicId, quality = 'lossless', priority = 0) => {
  try {
    const response = await fetch('/api/download/queue', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${musicId}&quality=${quality}&priority=${priority}`
    })
    
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '添加任务失败')
    }
    
    return result.data.task_id
  } catch (error) {
    console.error('添加任务失败:', error)
    throw error
  }
}

// 批量添加任务到队列
export const addBatchToQueue = async (musicIds, quality = 'lossless') => {
  try {
    const response = await fetch('/api/download/queue/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ids: musicIds, quality })
    })
    
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '批量添加任务失败')
    }
    
    return result.data.task_ids
  } catch (error) {
    console.error('批量添加任务失败:', error)
    throw error
  }
}

// 获取所有任务
export const getAllTasks = async () => {
  try {
    const response = await fetch('/api/download/queue')
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '获取队列失败')
    }
    
    const tasks = result.data.tasks || []
    localTasks = new Map(tasks.map(task => [task.task_id, task]))
    
    if (onTasksUpdateCallback) {
      onTasksUpdateCallback(tasks)
    }
    
    return tasks
  } catch (error) {
    console.error('获取队列失败:', error)
    throw error
  }
}

// 获取单个任务状态
export const getTaskStatus = async (taskId) => {
  try {
    const response = await fetch(`/api/download/task/${taskId}`)
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '获取任务状态失败')
    }
    
    const task = result.data
    localTasks.set(taskId, task)
    
    if (onTasksUpdateCallback) {
      const tasks = Array.from(localTasks.values())
      onTasksUpdateCallback(tasks)
    }
    
    return task
  } catch (error) {
    console.error('获取任务状态失败:', error)
    throw error
  }
}

// 暂停任务
export const pauseTask = async (taskId) => {
  try {
    const response = await fetch(`/api/download/task/${taskId}/pause`, {
      method: 'POST'
    })
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '暂停任务失败')
    }
    
    await getAllTasks() // 刷新任务列表
    return true
  } catch (error) {
    console.error('暂停任务失败:', error)
    throw error
  }
}

// 恢复任务
export const resumeTask = async (taskId) => {
  try {
    const response = await fetch(`/api/download/task/${taskId}/resume`, {
      method: 'POST'
    })
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '恢复任务失败')
    }
    
    await getAllTasks() // 刷新任务列表
    return true
  } catch (error) {
    console.error('恢复任务失败:', error)
    throw error
  }
}

// 取消任务
export const cancelTask = async (taskId) => {
  try {
    const response = await fetch(`/api/download/task/${taskId}/cancel`, {
      method: 'POST'
    })
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '取消任务失败')
    }
    
    await getAllTasks() // 刷新任务列表
    return true
  } catch (error) {
    console.error('取消任务失败:', error)
    throw error
  }
}

// 删除任务
export const removeTask = async (taskId) => {
  try {
    const response = await fetch(`/api/download/task/${taskId}`, {
      method: 'DELETE'
    })
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.message || '删除任务失败')
    }
    
    localTasks.delete(taskId)
    await getAllTasks() // 刷新任务列表
    return true
  } catch (error) {
    console.error('删除任务失败:', error)
    throw error
  }
}

// 开始轮询任务更新
export const startTaskPolling = (intervalMs = 1000) => {
  if (taskUpdateInterval) {
    stopTaskPolling()
  }
  
  taskUpdateInterval = setInterval(async () => {
    try {
      await getAllTasks()
    } catch (error) {
      console.error('轮询任务状态失败:', error)
    }
  }, intervalMs)
  
  console.log('开始轮询下载任务状态')
}

// 停止轮询任务更新
export const stopTaskPolling = () => {
  if (taskUpdateInterval) {
    clearInterval(taskUpdateInterval)
    taskUpdateInterval = null
    console.log('停止轮询下载任务状态')
  }
}

// 格式化任务显示
export const formatTask = (task) => {
  return {
    ...task,
    progress_display: {
      downloaded: formatFileSize(task.progress?.downloaded || 0),
      total: formatFileSize(task.progress?.total || 0),
      percentage: Math.round(task.progress?.percentage || 0),
      speed: formatSpeed(task.progress?.speed || 0),
      eta: formatEta(task.progress?.eta_seconds || 0)
    },
    status_text: getStatusText(task.status),
    status_color: getStatusColor(task.status)
  }
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    [DOWNLOAD_STATUSES.PENDING]: '等待中',
    [DOWNLOAD_STATUSES.DOWNLOADING]: '下载中',
    [DOWNLOAD_STATUSES.COMPLETED]: '已完成',
    [DOWNLOAD_STATUSES.FAILED]: '失败',
    [DOWNLOAD_STATUSES.PAUSED]: '已暂停',
    [DOWNLOAD_STATUSES.CANCELLED]: '已取消'
  }
  return statusMap[status] || status
}

// 获取状态颜色
const getStatusColor = (status) => {
  const colorMap = {
    [DOWNLOAD_STATUSES.PENDING]: '#9ca3af',
    [DOWNLOAD_STATUSES.DOWNLOADING]: '#3b82f6',
    [DOWNLOAD_STATUSES.COMPLETED]: '#10b981',
    [DOWNLOAD_STATUSES.FAILED]: '#ef4444',
    [DOWNLOAD_STATUSES.PAUSED]: '#f59e0b',
    [DOWNLOAD_STATUSES.CANCELLED]: '#6b7280'
  }
  return colorMap[status] || '#9ca3af'
}

// 获取本地缓存的任务
export const getLocalTasks = () => {
  return Array.from(localTasks.values())
}
