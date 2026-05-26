# Wan Music - 网易云音乐无损解析

基于 Vue 3 的网易云音乐无损解析工具，纯前端实现，无需后端服务。

## 项目结构

```
wan-music/
├── src/
│   ├── components/         # Vue 组件
│   │   ├── MusicPlayer.vue     # 音乐播放器组件
│   │   └── PlaylistDetail.vue # 歌单详情组件
│   ├── services/          # API 服务层
│   │   ├── musicApi.js        # 音乐 API 调用
│   │   └── metadataWriter.js  # 元数据写入
│   ├── utils/             # 工具函数
│   │   ├── cookies.js         # Cookie 管理
│   │   ├── downloadHelper.js  # 下载辅助
│   │   ├── parseManager.js    # 解析管理
│   │   ├── paginationManager.js # 分页管理
│   │   ├── settingsManager.js # 设置管理
│   │   ├── themeManager.js    # 主题管理
│   │   ├── deviceDetector.js  # 设备检测
│   │   ├── exampleData.js     # 示例数据
│   │   └── lyricsConverter.js # 歌词转换
│   ├── styles/            # 样式文件
│   │   └── global.css        # 全局样式
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── public/               # 静态资源
├── index.html           # HTML 入口
├── vite.config.js      # Vite 配置
└── package.json        # 依赖配置
```

## 功能特性

- 🎵 单曲解析 - 支持多种音质（母带、Hi-Res、无损、高品质）
- 📋 歌单解析 - 一键解析整个歌单
- 💿 专辑解析 - 支持专辑解析
- 🎨 主题切换 - 支持浅色/深色模式
- 📱 响应式设计 - 完美适配桌面和移动端
- ⚡ 快速下载 - 支持批量下载和 ZIP 打包
- 🎼 元数据写入 - 自动写入歌曲信息、封面、歌词
- 🔒 安全下载 - 纯前端实现，无需后端

## 技术栈

- Vue 3 - 渐进式 JavaScript 框架
- Element Plus - Vue 3 UI 组件库
- Vite - 新一代前端构建工具
- JavaScript ES6+ - 现代 JavaScript 语法

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:5173/

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 使用说明

1. 打开应用，选择解析模式（单曲/歌单/专辑）
2. 输入网易云音乐链接
3. 选择音质等级
4. 点击解析按钮
5. 解析完成后可在线播放或下载

## 配置说明

应用支持丰富的配置选项：

- 文件命名格式
- 元数据写入开关
- ZIP 打包下载
- 歌词格式选择（LRC/SRT）
- 播放链接缓存
- 主题模式切换
- 布局模式切换（双栏/单栏）

## 注意事项

⚠️ 本工具仅供学习交流使用，请支持正版音乐。

## License

MIT License
