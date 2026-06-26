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

## 环境变量

- `.env.dev` - 开发环境（端口 5175，后端 5005）
- `.env.prod` - 生产环境（端口 6175，后端 6005）

## 目录

- `src/components/` - 业务组件
- `src/composables/` - 组合式 API
- `src/stores/` - Pinia 状态
- `src/services/` - API 服务
- `src/utils/` - 工具函数

## 许可证

MIT
