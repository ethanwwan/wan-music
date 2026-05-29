# 📚 项目文档

本文档目录包含项目的各类文档，按功能分类整理。

## 📁 目录结构

```
docs/
├── README.md              # 文档说明（本文件）
├── architecture/          # 架构文档
│   └── ARCHITECTURE.md    # 系统架构设计
├── development/           # 开发文档
│   ├── COMPARISON_REPORT.md  # Python vs Node.js对比
│   └── JAVASCRIPT_API_INTEGRATION.md  # JavaScript API集成
├── maintenance/           # 维护文档
│   ├── OPTIMIZATION_REPORT.md   # 优化报告
│   ├── OPTIMIZATION_STATUS.md    # 优化状态
│   ├── FIX_REPORT.md           # 修复报告
│   └── RESTORE_REPORT.md       # 恢复报告
└── testing/               # 测试文档
    ├── TEST_REPORT.md        # 测试报告
    └── FINAL_TEST_REPORT.md  # 最终测试报告
```

## 📖 文档说明

### 🔧 architecture/ - 架构文档

**ARCHITECTURE.md**
- 系统整体架构设计
- 模块划分
- 技术选型
- 数据流设计

### 💻 development/ - 开发文档

**COMPARISON_REPORT.md**
- Python后端与Node.js后端对比
- Cookie管理差异
- API响应格式差异
- 建议和结论

**JAVASCRIPT_API_INTEGRATION.md**
- JavaScript API集成方案
- EAPI加密实现
- Cookie认证
- API调用示例

### 🔧 maintenance/ - 维护文档

**OPTIMIZATION_REPORT.md**
- 性能优化报告
- 代码优化建议
- 架构优化方案

**OPTIMIZATION_STATUS.md**
- 当前优化状态
- 已完成的优化
- 待优化的部分

**FIX_REPORT.md**
- 问题修复记录
- Bug修复方案
- 已知问题

**RESTORE_REPORT.md**
- 代码恢复记录
- 版本回退说明
- 数据恢复步骤

### 🧪 testing/ - 测试文档

**TEST_REPORT.md**
- 测试计划
- 测试用例
- 测试结果

**FINAL_TEST_REPORT.md**
- 最终测试报告
- 测试覆盖率
- 性能测试结果

## 📝 编辑指南

### 添加新文档

1. 确定文档类型（架构/开发/维护/测试）
2. 在对应目录下创建 `.md` 文件
3. 使用标准Markdown格式
4. 在本文档中添加链接

### 文档命名规范

- 使用有意义的文件名
- 使用PascalCase或kebab-case
- 避免使用中文文件名
- 添加适当的后缀（Report.md, Guide.md等）

### 文档格式

```markdown
# 文档标题

## 概述
简要说明文档内容

## 详细内容
...

## 相关文档
- [链接1](../other-dir/doc1.md)
- [链接2](./doc2.md)
```

## 🔗 相关链接

- [主README](../README.md)
- [前端文档](../frontend/README.md)
- [后端文档](../backend/README.md)
- [测试文档](../frontend/tests/README.md)

## 📧 联系方式

如有问题，请提交Issue。
