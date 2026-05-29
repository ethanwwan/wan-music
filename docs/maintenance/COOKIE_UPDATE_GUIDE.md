# Cookie更新指南

## 问题说明

如果您遇到"未找到歌曲详情"或"获取歌曲URL失败"的错误，很可能是Cookie已过期。

## 如何更新Cookie

### 方法1：从浏览器获取

1. 打开浏览器，登录网易云音乐：https://music.163.com
2. 按 `F12` 打开开发者工具
3. 切换到 **Network（网络）** 标签
4. 刷新页面，点击任意一个请求
5. 在 **Request Headers** 中找到 `Cookie` 字段
6. 复制整个Cookie值

### 方法2：使用浏览器扩展

安装 "EditThisCookie" 或 "Cookie Editor" 扩展，直接导出Cookie。

### 更新Cookie

1. 打开 `backend/cookie.txt` 文件
2. 将新的Cookie值粘贴进去
3. 保存文件
4. 重启后端服务

## 验证Cookie

访问 http://localhost:3000/health 查看Cookie状态：

```json
{
  "cookie": {
    "valid": true,
    "cookieCount": 21,
    "hasMusicU": true,
    "hasNmtid": true,
    "hasCsrf": true
  }
}
```

## 必需字段

确保Cookie包含以下关键字段：
- `MUSIC_U` - 登录凭证（最重要）
- `NMTID` - 客户端ID
- `__csrf` - CSRF令牌

## 注意事项

- Cookie通常有有效期，到期后需要重新获取
- 请勿分享您的Cookie给他人
- 某些VIP歌曲可能需要VIP账号的Cookie
