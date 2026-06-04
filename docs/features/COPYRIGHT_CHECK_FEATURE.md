# 歌曲版权检查功能

## 📋 功能概述

本次更新为专辑/歌单解析添加了歌曲版权检查功能，能够识别并标记因版权问题无法播放的歌曲。

## ✨ 新增功能

### 1. 自动版权检查
- 解析歌单/专辑时自动检查每首歌曲的版权状态
- 后台运行，不影响主流程
- 显示检查进度

### 2. 版权标记显示
- 无版权歌曲显示为灰色
- 显示"🚫"图标替代序号
- 显示"无版权"标签
- 封面图片变为灰度

### 3. 操作限制
- 播放按钮禁用
- 下载按钮禁用
- 点击整行时显示提示

### 4. 用户提示
- 检查完成后显示通知
- 提示有多少首歌曲无法播放
- 点击无版权歌曲时显示具体提示

---

## 🛠️ 技术实现

### 新增函数

#### 1. `checkMusicAvailability(musicId, quality)`
检查单个歌曲是否有版权

**参数**：
- `musicId`: 歌曲ID
- `quality`: 音质（默认：'standard'）

**返回**：
```javascript
{
  available: true,  // 或 false
  url: '...'         // 如果有版权，返回URL
  reason: '...'      // 如果无版权，返回原因
}
```

#### 2. `batchCheckAvailability(musicIds, quality, onProgress)`
批量检查多首歌曲的版权

**参数**：
- `musicIds`: 歌曲ID数组
- `quality`: 音质（默认：'standard'）
- `onProgress`: 进度回调函数

**返回**：
```javascript
Map<musicId, {
  available: boolean,
  url?: string,
  reason?: string
}>
```

#### 3. `checkTrackAvailability()`
检查当前歌单/专辑所有歌曲的版权

在 `parseManager.js` 中实现，会自动：
- 获取当前设置的音质
- 批量检查所有歌曲
- 更新歌曲的 `unavailable` 字段
- 显示通知提示

---

## 🎨 界面变化

### 歌曲列表显示

| 元素 | 正常歌曲 | 无版权歌曲 |
|------|---------|-----------|
| 序号 | 数字（1, 2, 3...） | 🚫 图标 |
| 封面 | 彩色 | 灰度 + 半透明 |
| 歌名 | 黑色 | 灰色 + "无版权"标签 |
| 歌手 | 灰色 | 灰色 |
| 播放按钮 | 可点击 | 禁用（灰色） |
| 下载按钮 | 可点击 | 禁用（灰色） |

### 样式

```css
/* 无版权歌曲行样式 */
.track-row.unavailable {
  background-color: #f5f5f5 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.track-row.unavailable .track-name {
  color: #999 !important;
}

.track-cover.grayscale {
  filter: grayscale(100%);
  opacity: 0.5;
}

.unavailable-reason {
  color: #ff4d4f;
  background: #fff1f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
}
```

---

## 🔄 工作流程

### 解析歌单/专辑流程

```
1. 用户输入歌单/专辑链接
   ↓
2. 调用 musicApi.getPlaylistDetail() 或 getAlbumDetail()
   ↓
3. 解析返回数据，创建 tracks 数组
   ↓
4. 立即显示第一页歌曲（此时没有版权标记）
   ↓
5. 显示成功通知
   ↓
6. 后台调用 checkTrackAvailability()
   ↓
7. 批量检查每首歌曲的版权状态
   ↓
8. 更新 tracks 数组，标记 unavailable 字段
   ↓
9. 重新渲染歌曲列表
   ↓
10. 显示版权提示通知
```

---

## 📝 使用示例

### 解析专辑

```javascript
// 输入专辑链接
albumUrl.value = 'https://music.163.com/album?id=123456'

// 调用解析
await parseAlbum()

// 自动执行：
// 1. 获取专辑信息
// 2. 显示歌曲列表
// 3. 后台检查版权
// 4. 标记无版权歌曲
```

### 前端调用

```javascript
// 手动检查版权
import { checkMusicAvailability } from './services/musicApi.js'

const result = await checkMusicAvailability('33894312', 'standard')
console.log(result)
// { available: true, url: '...' }
// 或
// { available: false, reason: 'no_url' }
```

---

## ⚙️ 配置说明

### 音质选择

版权检查使用当前设置的音质（默认：'standard'）

支持的音质：
- `standard` - 标准音质
- `exhigh` - 极高音质
- `lossless` - 无损音质
- `hires` - Hi-Res
- 其他音质...

### 请求间隔

为避免请求过快，每个请求之间延迟 50ms

```javascript
// 在 batchCheckAvailability 中
if (i < musicIds.length - 1) {
  await new Promise(resolve => setTimeout(resolve, 50))
}
```

---

## 🎯 注意事项

1. **版权状态是动态的**
   - 歌曲版权可能随时变化
   - 建议每次解析都重新检查

2. **性能考虑**
   - 大量歌曲的版权检查可能需要较长时间
   - 检查在后台运行，不影响使用

3. **缓存影响**
   - 版权检查不依赖 URL 缓存
   - 使用 `bypassCache: false`，允许使用已有的缓存

4. **暗色模式支持**
   - 已为暗色模式添加对应样式
   - 无版权歌曲在暗色模式下也有明显的视觉提示

---

## 🐛 已知问题

1. **检查耗时**
   - 100首歌曲的专辑可能需要 5-10 秒检查
   - 解决方案：显示检查进度

2. **部分歌曲可能检查失败**
   - 网络问题可能导致部分检查失败
   - 解决方案：标记为 unavailable，并显示原因

3. **版权判定标准**
   - 当前通过获取播放URL判断
   - 可能存在URL获取失败但实际有版权的情况

---

## 📈 后续优化建议

### 短期优化
1. ✅ 添加检查进度显示
2. ✅ 支持手动刷新版权状态
3. ✅ 添加"仅显示可播放歌曲"筛选

### 中期优化
1. 优化检查速度（并行请求）
2. 添加缓存机制
3. 支持 VIP 歌曲判断

### 长期优化
1. 与网易云音乐官方 API 对接
2. 实时版权状态更新
3. 跨平台版权信息库

---

## 📚 相关文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/services/musicApi.js` | 新增版权检查函数 |
| `frontend/src/utils/parseManager.js` | 集成版权检查逻辑 |
| `frontend/src/components/SearchResultList.vue` | 添加版权标记样式和交互 |

---

## ✅ 测试清单

- [x] 检查单个歌曲版权
- [x] 批量检查歌曲版权
- [x] 解析专辑时自动检查
- [x] 解析歌单时自动检查
- [x] 界面正确显示无版权歌曲
- [x] 无版权歌曲点击提示
- [x] 无版权歌曲播放/下载按钮禁用
- [x] 暗色模式适配
- [x] 进度显示
- [x] 通知提示

---

**最后更新**: 2026-06-04  
**版本**: v1.0.0  
**状态**: ✅ 已完成
