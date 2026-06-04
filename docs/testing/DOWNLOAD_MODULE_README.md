# 增强版音乐下载模块

## 📋 功能概述

本次对万能音乐项目的下载模块进行了全面升级，添加了以下核心功能：

### 🎯 核心功能

1. **下载队列管理** - 支持多任务管理、优先级设置
2. **断点续传** - 下载中断后可以继续，无需重新开始
3. **智能重试 & 音质降级** - 失败自动重试，高音质不可用时自动降级
4. **封面图片缓存** - 减少重复请求，提高效率
5. **实时进度追踪** - 显示下载速度、剩余时间等详细信息
6. **暂停/恢复/取消** - 完整的任务控制功能
7. **前端下载管理器** - 可视化队列管理界面

---

## 📁 新增/修改的文件

### 后端文件

| 文件 | 说明 |
|------|------|
| `backend/api/music_downloader.py` | 完全重写，新增所有增强功能 |
| `backend/main.py` | 新增下载管理API接口 |

### 前端文件

| 文件 | 说明 |
|------|------|
| `frontend/src/services/downloadManager.js` | 新增，前端下载管理服务 |
| `frontend/src/components/DownloadQueue.vue` | 新增，下载队列UI组件 |

### 测试文件

| 文件 | 说明 |
|------|------|
| `backend/test_downloader.py` | 后端完整测试套件 |
| `frontend/src/services/downloadManager.test.js` | 前端测试文件 |
| `test_download_module.py` | 测试运行器 |
| `backend/requirements-test.txt` | 测试依赖 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 后端测试依赖
cd backend
pip install -r requirements-test.txt
```

### 2. 运行测试

```bash
# 运行所有测试
python3 test_download_module.py

# 或者分别运行
cd backend
python3 -m pytest test_downloader.py -v
```

### 3. 启动服务

```bash
# 启动完整服务
npm run dev

# 或者分别启动
npm run dev:api      # 后端（端口 5002）
npm run dev:frontend # 前端（端口 5173）
```

---

## 📡 API 文档

### 新增的下载管理接口

#### 1. 添加单个任务到队列
```
POST /api/download/queue
Content-Type: application/x-www-form-urlencoded

id=<音乐ID>&quality=<音质>&priority=<优先级>
```

**响应：**
```json
{
  "success": true,
  "message": "任务已添加到队列",
  "data": {
    "task_id": "abc123def456"
  }
}
```

#### 2. 批量添加任务
```
POST /api/download/queue/batch
Content-Type: application/json

{
  "ids": [123, 456, 789],
  "quality": "lossless"
}
```

#### 3. 获取队列状态
```
GET /api/download/queue
```

**响应：**
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "abc123",
        "music_id": 123,
        "status": "downloading",
        "progress": {
          "downloaded": 1024000,
          "total": 5120000,
          "percentage": 20,
          "speed": 102400,
          "eta_seconds": 40
        }
      }
    ]
  }
}
```

#### 4. 暂停任务
```
POST /api/download/task/<task_id>/pause
```

#### 5. 恢复任务
```
POST /api/download/task/<task_id>/resume
```

#### 6. 取消任务
```
POST /api/download/task/<task_id>/cancel
```

#### 7. 删除任务
```
DELETE /api/download/task/<task_id>
```

---

## 🎨 前端使用

### 下载管理器服务

```javascript
import {
  addToQueue,
  addBatchToQueue,
  getAllTasks,
  pauseTask,
  resumeTask,
  cancelTask,
  removeTask,
  startTaskPolling,
  stopTaskPolling,
  setOnTasksUpdate
} from './services/downloadManager.js'

// 添加任务
const taskId = await addToQueue(123, 'lossless', 1)

// 批量添加
const taskIds = await addBatchToQueue([1, 2, 3], 'lossless')

// 控制任务
await pauseTask(taskId)
await resumeTask(taskId)
await cancelTask(taskId)
await removeTask(taskId)

// 实时更新
setOnTasksUpdate((tasks) => {
  console.log('任务更新:', tasks)
})
startTaskPolling(1000) // 每1秒更新一次
```

### 下载队列组件

```vue
<template>
  <div>
    <DownloadQueue />
  </div>
</template>

<script setup>
import DownloadQueue from './components/DownloadQueue.vue'
</script>
```

---

## 🧪 测试说明

### 测试覆盖范围

| 测试类别 | 说明 |
|----------|------|
| 单元测试 | 测试各个独立组件的功能 |
| 集成测试 | 测试模块间的协作（可选，需要网络） |
| 性能测试 | 测试并发下载性能 |

### 运行特定测试

```bash
# 只运行后端测试
cd backend
python3 -m pytest test_downloader.py -v

# 运行性能测试
python3 -m pytest test_downloader.py -v -m benchmark

# 运行集成测试（需要网络）
python3 -m pytest test_downloader.py -v --runintegration
```

---

## 🔧 架构说明

### 后端架构

```
EnhancedMusicDownloader (主下载器)
├── DownloadQueue (队列管理器)
│   ├── 任务添加/移除
│   ├── 暂停/恢复
│   └── 工作协程管理
├── CoverCache (封面缓存)
│   ├── 内存缓存
│   └── 文件缓存
└── 任务执行
    ├── 断点续传下载
    ├── 元数据写入
    └── 进度追踪
```

### 前端架构

```
DownloadQueue.vue (UI组件)
└── downloadManager.js (服务层)
    ├── API调用
    ├── 状态管理
    └── 轮询更新
```

---

## 📊 状态说明

### 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待中，尚未开始 |
| `downloading` | 正在下载 |
| `paused` | 已暂停 |
| `completed` | 已完成 |
| `failed` | 失败（超过重试次数） |
| `cancelled` | 已取消 |

### 音质等级（优先级从高到低）

1. `dolby` - 杜比全景声
2. `jymaster` - 超清母带
3. `jyeffect` - 高清臻音
4. `hires` - 高清晰度无损
5. `sky` - 沉浸环绕声
6. `lossless` - 无损（默认）
7. `exhigh` - 极高
8. `standard` - 标准

---

## 🎯 优化细节

### 1. 断点续传

- 使用 `Range` 请求头
- 临时文件保存下载进度
- 支持从任意断点继续

### 2. 智能降级

- 如果指定音质不可用，自动尝试低一级音质
- 持续降级直到找到可用音质或达到标准音质

### 3. 封面缓存

- 两级缓存：内存 + 文件
- 减少重复网络请求
- 提高元数据写入速度

### 4. 并发控制

- 可配置最大并发数
- 优先级队列
- 防止服务器过载

---

## ⚠️ 注意事项

1. **后端服务状态** - 下载器需要后端服务运行
2. **网络连接** - 需要稳定的网络连接
3. **磁盘空间** - 确保有足够的下载空间
4. **Cookie配置** - 下载需要有效的网易云音乐Cookie

---

## 📝 更新日志

### v2.0.0 (当前)
- ✅ 完全重写下载模块
- ✅ 添加队列管理功能
- ✅ 实现断点续传
- ✅ 添加智能重试和降级
- ✅ 实现封面缓存
- ✅ 添加完整API接口
- ✅ 编写完整测试套件

---

## 🤝 贡献指南

如需添加新功能或修复问题，请：

1. 确保所有测试通过
2. 添加相应的测试用例
3. 更新文档
4. 提交PR

---

## 📄 许可证

与项目保持一致的许可证。
