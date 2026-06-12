# 网易云音乐前端应用（Vue版）

## 📁 目录结构

```
frontend/
├── public/           # 静态资源
│   └── favicon.svg
├── src/              # 源代码
│   ├── components/   # Vue组件
│   ├── composables/  # 组合式函数
│   ├── config/       # 配置文件
│   ├── services/     # API服务
│   ├── stores/       # Pinia状态管理
│   ├── styles/       # 样式文件
│   ├── utils/        # 工具函数
│   ├── App.vue       # 主应用组件
│   ├── main.js       # 入口文件
│   └── index.js      # 导出文件
├── index.html        # HTML模板
├── vite.config.js    # Vite配置
├── package.json      # 依赖配置
├── LICENSE           # 许可证
├── .gitignore        # Git忽略配置
└── README.md         # 本文件
```

## 🔧 技术栈

- **Vue 3** - 前端框架
- **Vite** - 构建工具
- **Pinia** - 状态管理
- **Ant Design Vue** - UI组件库
- **Axios** - HTTP客户端

## 🎯 核心功能

### 1. 音乐搜索
支持多平台音乐搜索（网易云、QQ、波点、酷狗）。

### 2. 音乐播放
支持在线播放和下载音乐。

### 3. 歌单管理
支持查看和解析歌单详情。

### 4. 下载管理
支持批量下载音乐，自动添加ID3标签。

## 🚀 启动方式

### 安装依赖
```bash
cd frontend
npm install
```

### 开发模式
```bash
# 仅启动前端
npm run dev

# 同时启动前后端
npm run dev:full
```

### 生产构建
```bash
npm run build
```

### 预览构建结果
```bash
npm run preview
```

## 🔧 配置说明

### Vite代理配置
前端通过 Vite 代理将 API 请求转发到后端：
- `/api` → `http://localhost:5002`
- `/song` → `http://localhost:5002`
- `/playlist` → `http://localhost:5002`
- `/search` → `http://localhost:5002`

### 环境变量
可通过 `.env` 文件配置：
```env
VITE_API_BASE_URL=http://localhost:5002
```

## 🧪 测试

```bash
# UI测试
npm run test:ui

# UI测试（带界面）
npm run test:ui:headed

# UI测试（调试模式）
npm run test:ui:debug

# 安装测试依赖
npm run test:install
```

## 📄 许可证

MIT License