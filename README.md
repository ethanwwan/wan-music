# 🎵 万能音乐 - 网易云音乐解析下载工具

一个基于Vue 3 + Node.js的网易云音乐解析下载工具，支持歌曲、歌单、专辑解析和无损音乐下载。

## ✨ 功能特性

- 🎵 **歌曲解析** - 支持单曲链接解析
- 📋 **歌单解析** - 批量解析歌单中的歌曲
- 💿 **专辑解析** - 解析专辑中的所有歌曲
- 🔍 **音乐搜索** - 关键词搜索歌曲
- 🎛️ **音质选择** - 支持多种音质（标准、高品、无损、Hi-Res、杜比等）
- 📥 **批量下载** - 批量下载歌曲并自动嵌入元数据
- 💾 **歌词下载** - 自动下载歌词文件
- 🎨 **现代化UI** - 简洁美观的界面设计

## 🛠️ 技术栈

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **Pinia** - 状态管理
- **Element Plus** - UI组件库
- **Vite** - 构建工具

### 后端
- **Node.js** - JavaScript运行时
- **Express** - Web框架
- **Axios** - HTTP客户端
- **EAPI加密** - 网易云音乐API加密协议

## 📁 项目结构（Monorepo）

```
wan-music/                          # 根目录 - 项目根目录
├── package.json                    # 根NPM配置（workspace配置）
├── workspaces/
│   ├── frontend/                  # 前端workspace
│   │   ├── package.json           # 前端依赖
│   │   ├── vite.config.js        # Vite配置
│   │   ├── public/               # 静态资源
│   │   ├── src/                  # 前端源码
│   │   │   ├── App.vue
│   │   │   ├── main.js
│   │   │   ├── index.js
│   │   │   ├── test.js
│   │   │   ├── components/       # Vue组件
│   │   │   ├── composables/      # Vue组合式API
│   │   │   ├── config/          # 配置文件
│   │   │   ├── services/        # API服务
│   │   │   ├── stores/          # Pinia状态管理
│   │   │   ├── styles/          # 样式文件
│   │   │   └── utils/           # 工具函数
│   │   └── tests/               # 前端测试
│   │       ├── ui.spec.js       # Playwright测试
│   │       ├── test-ui-*.mjs    # UI交互测试
│   │       ├── check-*.mjs     # 检查脚本
│   │       └── results/         # 测试结果
│   │
│   └── backend/                  # 后端workspace
│       ├── package.json         # 后端依赖
│       ├── cookie.txt          # 网易云Cookie
│       ├── src/                # 后端源码
│       │   ├── server.js       # Express服务器
│       │   ├── server-crypto.js # EAPI加密
│       │   └── server-cookie.js # Cookie管理
│       └── tests/              # 后端测试
│           ├── test-api*.mjs   # API测试
│           ├── test-eapi.mjs   # EAPI测试
│           └── monitor-*.mjs   # 监控脚本
│
├── docs/                         # 文档目录
│   ├── README.md
│   ├── architecture/            # 架构文档
│   ├── development/            # 开发文档
│   ├── maintenance/            # 维护文档
│   └── testing/               # 测试文档
│
├── playwright.config.js         # Playwright配置
└── Dockerfile                  # Docker配置
```

## 🚀 快速开始

### 环境要求

- Node.js >= 18.0.0
- npm >= 9.0.0

### 安装依赖

```bash
# 安装所有依赖（包括frontend和backend）
npm install
```

### 启动开发服务器

```bash
# 启动完整应用（前端 + 后端）
npm run dev

# 或分开启动
npm run dev:frontend    # 启动前端（端口5173）
npm run dev:api         # 启动后端（端口3000）
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
npm run preview
```

## 📝 使用说明

### 1. 歌曲解析

1. 打开应用
2. 选择"单曲解析"选项卡
3. 输入网易云音乐歌曲链接，如：
   - `https://music.163.com/song?id=33894312`
   - `https://y.music.163.com/m/song/33894312`
4. 点击"开始解析"
5. 选择音质并下载

### 2. 歌单解析

1. 切换到"歌单解析"选项卡
2. 输入歌单链接，如：
   - `https://music.163.com/playlist?id=225001`
3. 点击"解析歌单"
4. 批量选择歌曲和音质
5. 点击"下载选中"或"下载全部"

### 3. 专辑解析

1. 切换到"专辑解析"选项卡
2. 输入专辑链接，如：
   - `https://music.163.com/album?id=14808721`
3. 点击"解析专辑"
4. 下载专辑中的歌曲

### 4. 音乐搜索

1. 切换到"搜索"选项卡
2. 输入关键词（如歌手名、歌曲名）
3. 点击"搜索"
4. 选择歌曲进行下载

## 🎛️ 音质说明

| 音质等级 | 说明 | 文件格式 |
|---------|------|---------|
| standard | 标准音质 | MP3 |
| exhigh | 高品音质 | MP3 |
| lossless | 无损音质 | FLAC |
| hires | Hi-Res音质 | FLAC |
| sky | 极高音质 | FLAC |
| jyeffect | 鲸云臻音 | FLAC |
| jymaster | 鲸云母带 | FLAC |
| dolby | 杜比全景声 | FLAC |

## 🧪 测试

```bash
# 运行后端核心测试
npm test

# 运行Playwright UI测试
npm run test:ui

# 带UI的Playwright测试
npm run test:ui:headed

# 安装Playwright浏览器
npm run test:install
```

详细测试说明：
- [前端测试文档](frontend/tests/README.md)
- [后端测试文档](backend/tests/README.md)

## 📚 文档

项目文档位于 `docs/` 目录：

- [文档目录](docs/README.md)
- [架构文档](docs/architecture/ARCHITECTURE.md)
- [开发文档](docs/development/)
- [维护文档](docs/maintenance/)
- [测试文档](docs/testing/)

## 🐳 Docker部署

### 构建镜像

```bash
docker build -t wan-music .
```

### 运行容器

```bash
docker run -d -p 5000:3000 wan-music
```

### 使用Docker Compose

```bash
docker-compose up -d
```

## ⚙️ 配置说明

### Cookie配置

Cookie文件位于 `backend/cookie.txt`，包含网易云音乐认证信息。

**重要**：请勿将Cookie文件提交到版本控制系统！

### Vite代理配置

在 `vite.config.js` 中配置API代理：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:3000',
      changeOrigin: true
    },
    '/eapi': {
      target: 'http://localhost:3000',
      changeOrigin: true
    }
  }
}
```

## 🏗️ Monorepo架构

本项目采用npm workspaces实现Monorepo架构：

### 工作区结构

- **根workspace** - 管理所有工作区和共享依赖
- **frontend workspace** - 前端应用
- **backend workspace** - 后端API服务

### 工作区命令

```bash
# 在根目录运行，影响所有工作区
npm install          # 安装所有工作区依赖
npm run dev          # 启动所有工作区

# 在特定工作区运行
npm run dev --workspace=frontend
npm run dev --workspace=backend

# 在特定工作区安装依赖
npm install <package> --workspace=frontend
npm install <package> --workspace=backend
```

### 依赖共享

- **devDependencies** - 放在根目录（如concurrently）
- **frontend依赖** - 放在frontend/package.json
- **backend依赖** - 放在backend/package.json

## 🛠️ 开发指南

### 添加新的API端点

1. 在 `backend/src/server.js` 中添加路由
2. 使用 `neteaseRequest()` 函数发起请求
3. 添加Cookie认证（如需要）
4. 更新API文档

### 前端组件开发

1. 在 `frontend/src/components/` 创建组件
2. 使用Element Plus组件库
3. 添加国际化支持（如需要）

### 测试驱动开发

1. 编写测试用例
2. 运行测试确保通过
3. 实现功能代码

## 📄 许可证

MIT License

## 🙏 致谢

- [网易云音乐](https://music.163.com/) - 音乐平台
- [NeteaseCloudMusicApi](https://github.com/Binaryify/NeteaseCloudMusicApi) - API参考
- [Vue.js](https://vuejs.org/) - 前端框架
- [Element Plus](https://element-plus.org/) - UI组件库

## 📧 联系方式

如有问题或建议，请提交Issue。
