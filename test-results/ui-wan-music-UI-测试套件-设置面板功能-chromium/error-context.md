# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui.spec.js >> wan-music UI 测试套件 >> 设置面板功能
- Location: tests/ui.spec.js:51:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('button').filter({ has: locator('.el-icon-setting') }).first()

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - heading "网易云音乐解析" [level=1] [ref=e7]
      - generic [ref=e8]:
        - button [ref=e9] [cursor=pointer]:
          - img [ref=e12]
        - button [ref=e14] [cursor=pointer]:
          - img [ref=e16]
    - main [ref=e18]:
      - generic [ref=e21]:
        - generic [ref=e24]: 🎵 歌曲解析
        - generic [ref=e25]:
          - generic [ref=e29]:
            - img [ref=e32]
            - textbox "请输入网易云音乐歌曲链接" [ref=e35]
            - button "解析" [ref=e38] [cursor=pointer]:
              - generic [ref=e39]: 解析
          - generic [ref=e40]:
            - generic [ref=e41]: 音质选择：
            - radiogroup "radio-group":
              - generic: "{ \"value\": \"standard\", \"label\": \"标准\", \"bitrate\": \"128kbps\" }"
              - generic: "{ \"value\": \"exhigh\", \"label\": \"极高\", \"bitrate\": \"320kbps\" }"
              - generic: "{ \"value\": \"lossless\", \"label\": \"无损\", \"bitrate\": \"FLAC\" }"
              - generic: "{ \"value\": \"hires\", \"label\": \"Hi-Res\", \"bitrate\": \"FLAC 24bit\" }"
              - generic: "{ \"value\": \"sky\", \"label\": \"沉浸\", \"bitrate\": \"Dolby Atmos\" }"
              - generic: "{ \"value\": \"jyeffect\", \"label\": \"环绕\", \"bitrate\": \"Sony 360RA\" }"
              - generic: "{ \"value\": \"jymaster\", \"label\": \"母带\", \"bitrate\": \"FLAC 24bit/96kHz\" }"
              - generic: "{ \"value\": \"dolby\", \"label\": \"杜比\", \"bitrate\": \"Dolby Atmos\" }"
    - paragraph [ref=e45]: 基于 Vue 3 + Element Plus 构建
  - dialog "欢迎使用" [ref=e47]:
    - generic [active] [ref=e48]:
      - banner [ref=e49]:
        - heading "欢迎使用" [level=2] [ref=e50]
        - button "Close this dialog" [ref=e51] [cursor=pointer]:
          - img [ref=e53]
      - generic [ref=e56]:
        - alert [ref=e57]:
          - generic [ref=e58]:
            - generic [ref=e59]: 功能说明
            - paragraph [ref=e60]: 本工具可以解析网易云音乐的歌曲、歌单和专辑，支持多种音质下载。
        - heading "示例链接" [level=4] [ref=e61]
        - generic [ref=e62]:
          - link "-" [ref=e64] [cursor=pointer]:
            - /url: https://music.163.com/song?id=1454730043
            - generic [ref=e65]: "-"
          - link "-" [ref=e67] [cursor=pointer]:
            - /url: https://music.163.com/song?id=1335942780
            - generic [ref=e68]: "-"
          - link "-" [ref=e70] [cursor=pointer]:
            - /url: https://music.163.com/song?id=110191
            - generic [ref=e71]: "-"
      - contentinfo [ref=e72]:
        - button "开始使用" [ref=e73] [cursor=pointer]:
          - generic [ref=e74]: 开始使用
```

# Test source

```ts
  1   | /**
  2   |  * Playwright UI 自动化测试
  3   |  * 测试 wan-music 项目的 UI 交互功能
  4   |  */
  5   | 
  6   | import { test, expect } from '@playwright/test'
  7   | 
  8   | // 测试配置
  9   | const BASE_URL = 'http://localhost:5173'
  10  | const TEST_SONG_URL = 'https://music.163.com/song?id=1380946308'
  11  | 
  12  | test.describe('wan-music UI 测试套件', () => {
  13  |   
  14  |   test.beforeEach(async ({ page }) => {
  15  |     await page.goto(BASE_URL)
  16  |     await page.waitForLoadState('networkidle')
  17  |   })
  18  | 
  19  |   test('页面标题和基本元素加载', async ({ page }) => {
  20  |     // 检查页面标题
  21  |     await expect(page).toHaveTitle(/网易云音乐解析/)
  22  | 
  23  |     // 检查主标题
  24  |     const title = page.locator('h1')
  25  |     await expect(title).toContainText('网易云音乐解析')
  26  | 
  27  |     // 检查页脚
  28  |     const footer = page.locator('.app-footer p')
  29  |     await expect(footer).toContainText('Vue 3')
  30  |   })
  31  | 
  32  |   test('主题切换功能', async ({ page }) => {
  33  |     // 查找主题切换按钮
  34  |     const themeButton = page.locator('button').filter({ has: page.locator('.el-icon-moon') }).first()
  35  |     
  36  |     if (await themeButton.isVisible()) {
  37  |       // 点击切换主题
  38  |       await themeButton.click()
  39  |       
  40  |       // 等待主题更新
  41  |       await page.waitForTimeout(1000)
  42  |       
  43  |       // 验证主题已切换（检查是否有 dark 类）
  44  |       const html = page.locator('html')
  45  |       const hasDarkClass = await html.evaluate(el => el.classList.contains('dark'))
  46  |       
  47  |       console.log(`主题切换成功: ${hasDarkClass ? '深色模式' : '浅色模式'}`)
  48  |     }
  49  |   })
  50  | 
  51  |   test('设置面板功能', async ({ page }) => {
  52  |     // 点击设置按钮
  53  |     const settingsButton = page.locator('button').filter({ has: page.locator('.el-icon-setting') }).first()
> 54  |     await settingsButton.click()
      |                          ^ Error: locator.click: Test timeout of 30000ms exceeded.
  55  | 
  56  |     // 检查设置面板是否打开
  57  |     const drawer = page.locator('.el-drawer')
  58  |     await expect(drawer).toBeVisible()
  59  | 
  60  |     // 检查设置项
  61  |     const qualityLabel = page.locator('text=默认音质')
  62  |     await expect(qualityLabel).toBeVisible()
  63  | 
  64  |     // 关闭设置面板
  65  |     const closeButton = drawer.locator('.el-drawer__header button')
  66  |     await closeButton.click()
  67  |     
  68  |     await expect(drawer).not.toBeVisible()
  69  |   })
  70  | 
  71  |   test('歌曲解析表单功能', async ({ page }) => {
  72  |     // 查找歌曲解析输入框
  73  |     const songInput = page.locator('input[placeholder*="歌曲链接"]').first()
  74  |     
  75  |     // 检查输入框存在
  76  |     await expect(songInput).toBeVisible()
  77  |     
  78  |     // 输入测试链接
  79  |     await songInput.fill(TEST_SONG_URL)
  80  |     
  81  |     // 验证输入内容
  82  |     await expect(songInput).toHaveValue(TEST_SONG_URL)
  83  |     
  84  |     // 查找解析按钮
  85  |     const parseButton = page.locator('button:has-text("解析")').first()
  86  |     await expect(parseButton).toBeVisible()
  87  |   })
  88  | 
  89  |   test('音质选择功能', async ({ page }) => {
  90  |     // 查找音质单选按钮组
  91  |     const qualityGroup = page.locator('.quality-selector').first()
  92  |     
  93  |     if (await qualityGroup.isVisible()) {
  94  |       // 检查音质选项
  95  |       const losslessOption = qualityGroup.locator('text=无损').first()
  96  |       await expect(losslessOption).toBeVisible()
  97  |       
  98  |       // 点击无损选项
  99  |       await losslessOption.click()
  100 |       
  101 |       // 验证选中状态
  102 |       const radio = qualityGroup.locator('.el-radio-button__inner').filter({ hasText: '无损' })
  103 |       await expect(radio).toHaveClass(/is-active/)
  104 |     }
  105 |   })
  106 | 
  107 |   test('欢迎对话框功能', async ({ page }) => {
  108 |     // 等待欢迎对话框出现
  109 |     await page.waitForTimeout(1500)
  110 |     
  111 |     const welcomeDialog = page.locator('.el-dialog')
  112 |     
  113 |     // 如果欢迎对话框出现
  114 |     if (await welcomeDialog.isVisible()) {
  115 |       // 检查标题
  116 |       const title = welcomeDialog.locator('.el-dialog__title')
  117 |       await expect(title).toContainText('欢迎使用')
  118 |       
  119 |       // 检查功能说明
  120 |       const alert = welcomeDialog.locator('.el-alert')
  121 |       await expect(alert).toBeVisible()
  122 |       
  123 |       // 点击开始使用按钮
  124 |       const startButton = welcomeDialog.locator('button:has-text("开始使用")')
  125 |       await startButton.click()
  126 |       
  127 |       // 验证对话框关闭
  128 |       await expect(welcomeDialog).not.toBeVisible()
  129 |     }
  130 |   })
  131 | 
  132 |   test('空状态显示', async ({ page }) => {
  133 |     // 检查空状态区域
  134 |     const emptySection = page.locator('.empty-section')
  135 |     
  136 |     if (await emptySection.isVisible()) {
  137 |       // 检查空状态图标
  138 |       const emptyIcon = emptySection.locator('.el-icon')
  139 |       await expect(emptyIcon).toBeVisible()
  140 |       
  141 |       // 检查空状态描述
  142 |       const emptyText = emptySection.locator('.el-empty__description')
  143 |       await expect(emptyText).toContainText('暂无解析结果')
  144 |     }
  145 |   })
  146 | 
  147 |   test('响应式布局', async ({ page }) => {
  148 |     // 移动端视图
  149 |     await page.setViewportSize({ width: 375, height: 667 })
  150 |     await page.waitForTimeout(500)
  151 |     
  152 |     // 检查布局是否正常
  153 |     const container = page.locator('.app-container')
  154 |     await expect(container).toBeVisible()
```