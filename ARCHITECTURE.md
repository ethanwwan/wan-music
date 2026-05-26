/**
 * 项目架构文档
 *
 * 本项目完全采用 JavaScript 实现，不再依赖 Python 后端
 *
 * ## 模块架构
 *
 * ### 1. 配置模块 (src/config/)
 *
 * - **index.js** - 应用配置管理
 *   - APP_CONFIG: 应用全局配置对象
 *   - ConfigManager: 配置管理器类
 *
 * ### 2. 服务层 (src/services/)
 *
 * - **neteaseApi.js** - 网易云音乐 API 核心
 *   - NeteaseAPI: API 调用类
 *   - 支持: 歌曲 URL、详情、歌词、搜索、歌单、专辑
 *
 * - **crypto.js** - 加密工具
 *   - CryptoUtils: EAPI 加密实现
 *   - MD5、AES-CBC 加密
 *
 * - **musicApi.js** - 音乐服务封装
 *   - parseUrl(): URL 解析
 *   - getMusicInfo(): 获取音乐信息
 *   - downloadMusic(): 下载音乐
 *   - QUALITY_LEVELS: 音质等级常量
 *
 * - **metadataWriter.js** - 元数据写入
 *   - embedMetadata(): 写入 FLAC/MP3 元数据
 *
 * - **downloadManager.js** - 下载管理
 *   - DownloadManager: 下载管理器
 *   - 支持批量下载、并发控制
 *
 * ### 3. 工具模块 (src/utils/)
 *
 * - **logger.js** - 日志管理
 *   - Logger: 日志类
 *   - 支持分级日志 (DEBUG, INFO, WARN, ERROR)
 *   - 开发环境全打印，生产环境只打印警告和错误
 *
 * - **errors.js** - 异常处理
 *   - APIError, NetworkError, DownloadError 等
 *   - handleError(): 全局异常处理器
 *
 * - **cookieManager.js** - Cookie 管理
 *   - CookieManager: Cookie 管理类
 *   - localStorage 存储
 *
 * - **downloadHelper.js** - 下载辅助
 *   - saveBlob(): 保存文件
 *   - sanitizeFilename(): 文件名清理
 *
 * - **settingsManager.js** - 设置管理
 *   - settings: 全局设置对象
 *
 * - **themeManager.js** - 主题管理
 *   - 浅色/深色模式切换
 *
 * - **parseManager.js** - 解析管理
 *   - 解析状态管理
 *
 * - **paginationManager.js** - 分页管理
 *   - 歌单分页显示
 *
 * ### 4. 组件层 (src/components/)
 *
 * - **MusicPlayer.vue** - 音乐播放器
 * - **PlaylistDetail.vue** - 歌单详情
 *
 * ### 5. 入口文件
 *
 * - **main.js** - Vue 应用入口
 * - **App.vue** - 根组件
 * - **index.js** - 模块统一导出
 *
 * ## 依赖关系
 *
 * ```
 * App.vue
 *   ├── MusicPlayer.vue
 *   ├── PlaylistDetail.vue
 *   └── parseManager.js
 *         ├── musicApi.js
 *         │     ├── neteaseApi.js
 *         │     │     └── crypto.js
 *         │     ├── metadataWriter.js
 *         │     └── downloadHelper.js
 *         └── downloadManager.js
 *               ├── logger.js
 *               ├── errors.js
 *               └── metadataWriter.js
 *
 * config/index.js
 *   ├── logger.js
 *   ├── errors.js
 *   └── cookieManager.js
 * ```
 *
 * ## 功能对应表
 *
 * | Python 模块 | JavaScript 模块 | 功能 |
 * |------------|----------------|------|
 * | music_api.py | neteaseApi.js | API 调用 |
 * | music_api.py | crypto.js | EAPI 加密 |
 * | music_downloader.py | downloadManager.js | 下载管理 |
 * | music_downloader.py | metadataWriter.js | 元数据写入 |
 * | cookie_manager.py | cookieManager.js | Cookie 管理 |
 * | logger.py | logger.js | 日志管理 |
 * | exceptions.py | errors.js | 异常处理 |
 * | config.py | config/index.js | 配置管理 |
 *
 * ## 注意事项
 *
 * 1. **跨域问题**: 浏览器直接调用网易云音乐 API 会遇到跨域限制
 *    - 开发环境可使用 Vite 代理
 *    - 生产环境需要配置反向代理或使用 Edge Functions
 *
 * 2. **下载限制**: 浏览器无法直接访问文件系统
 *    - 使用 Blob + saveBlob() 实现浏览器端下载
 *    - 无法实现服务器端下载（需要后端）
 *
 * 3. **Cookie 安全**: Cookie 存储在 localStorage
 *    - 存在 XSS 攻击风险
 *    - 生产环境建议使用 HTTPS + HttpOnly Cookie
 *
 * ## 部署建议
 *
 * ### 开发环境
 * ```bash
 * npm run dev
 * ```
 *
 * ### 生产环境
 * ```bash
 * npm run build
 * ```
 * 部署 dist/ 目录到静态服务器
 *
 * ### 反向代理配置 (Nginx)
 * ```nginx
 * location /api/ {
 *     proxy_pass https://interface3.music.163.com/;
 *     proxy_set_header Host interface3.music.163.com;
 *     proxy_set_header Referer https://music.163.com;
 * }
 * ```
 */
