# Frontend

> Vue 3 + Vite 前端应用

详细文档见根目录 [README.md](../README.md)。

## 启动

```bash
npm install
npm run dev        # 仅前端 (http://localhost:5175)
npm run dev:full   # 前端 + 后端
npm run build      # 生产构建
```

## 配置

端口由根目录 [`../config.json`](../config.json) 的 `frontend` 节点配置：

- `devPort` - 开发模式端口（默认 5175）
- `prodPort` - 生产构建端口（默认 6175）
- `apiBase` - 跨域部署时的 API 基础路径（默认空 = 同源）

## 目录

- `src/components/` - 业务组件
- `src/composables/` - 组合式 API
- `src/stores/` - Pinia 状态
- `src/services/` - API 服务
- `src/utils/` - 工具函数

## 许可证

MIT
