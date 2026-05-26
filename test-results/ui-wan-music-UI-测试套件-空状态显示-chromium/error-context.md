# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui.spec.js >> wan-music UI 测试套件 >> 空状态显示
- Location: tests/ui.spec.js:132:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.empty-section').locator('.el-icon')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.empty-section').locator('.el-icon')

```

```yaml
- heading "网易云音乐解析" [level=1]
- button:
  - img
- button:
  - img
- main:
  - text: 🎵 歌曲解析
  - img
  - textbox "请输入网易云音乐歌曲链接"
  - button "解析"
  - text: 音质选择：
  - radiogroup "radio-group": "{ \"value\": \"standard\", \"label\": \"标准\", \"bitrate\": \"128kbps\" } { \"value\": \"exhigh\", \"label\": \"极高\", \"bitrate\": \"320kbps\" } { \"value\": \"lossless\", \"label\": \"无损\", \"bitrate\": \"FLAC\" } { \"value\": \"hires\", \"label\": \"Hi-Res\", \"bitrate\": \"FLAC 24bit\" } { \"value\": \"sky\", \"label\": \"沉浸\", \"bitrate\": \"Dolby Atmos\" } { \"value\": \"jyeffect\", \"label\": \"环绕\", \"bitrate\": \"Sony 360RA\" } { \"value\": \"jymaster\", \"label\": \"母带\", \"bitrate\": \"FLAC 24bit/96kHz\" } { \"value\": \"dolby\", \"label\": \"杜比\", \"bitrate\": \"Dolby Atmos\" }"
- paragraph: 基于 Vue 3 + Element Plus 构建
- dialog "欢迎使用":
  - banner:
    - heading "欢迎使用" [level=2]
    - button "Close this dialog":
      - img
  - alert:
    - text: 功能说明
    - paragraph: 本工具可以解析网易云音乐的歌曲、歌单和专辑，支持多种音质下载。
  - heading "示例链接" [level=4]
  - link "-":
    - /url: https://music.163.com/song?id=1454730043
  - link "-":
    - /url: https://music.163.com/song?id=1335942780
  - link "-":
    - /url: https://music.163.com/song?id=110191
  - contentinfo:
    - button "开始使用"
```

# Test source

```ts
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
  54  |     await settingsButton.click()
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
> 139 |       await expect(emptyIcon).toBeVisible()
      |                               ^ Error: expect(locator).toBeVisible() failed
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
  155 |     
  156 |     // 平板视图
  157 |     await page.setViewportSize({ width: 768, height: 1024 })
  158 |     await page.waitForTimeout(500)
  159 |     await expect(container).toBeVisible()
  160 |     
  161 |     // 桌面视图
  162 |     await page.setViewportSize({ width: 1920, height: 1080 })
  163 |     await page.waitForTimeout(500)
  164 |     await expect(container).toBeVisible()
  165 |   })
  166 | 
  167 |   test('错误提示功能', async ({ page }) => {
  168 |     // 输入无效链接
  169 |     const songInput = page.locator('input[placeholder*="歌曲链接"]').first()
  170 |     await songInput.fill('https://example.com/invalid')
  171 |     
  172 |     // 点击解析
  173 |     const parseButton = page.locator('button:has-text("解析")').first()
  174 |     await parseButton.click()
  175 |     
  176 |     // 等待错误提示（如果有）
  177 |     await page.waitForTimeout(1000)
  178 |     
  179 |     // 检查是否有错误消息
  180 |     const errorMessage = page.locator('.el-message--error')
  181 |     // 不强制要求有错误消息，因为可能需要更长的处理时间
  182 |   })
  183 | 
  184 |   test('控制台无错误', async ({ page }) => {
  185 |     const errors = []
  186 |     
  187 |     // 监听控制台错误
  188 |     page.on('console', msg => {
  189 |       if (msg.type() === 'error') {
  190 |         errors.push(msg.text())
  191 |       }
  192 |     })
  193 |     
  194 |     // 等待页面完全加载
  195 |     await page.waitForLoadState('networkidle')
  196 |     await page.waitForTimeout(2000)
  197 |     
  198 |     // 过滤掉已知的非关键错误（如 API 调用失败）
  199 |     const criticalErrors = errors.filter(err => 
  200 |       !err.includes('Failed to fetch') &&
  201 |       !err.includes('Network Error') &&
  202 |       !err.includes('net::ERR')
  203 |     )
  204 |     
  205 |     // 输出错误日志
  206 |     if (criticalErrors.length > 0) {
  207 |       console.log('发现关键错误:', criticalErrors)
  208 |     }
  209 |     
  210 |     // 不强制要求无错误，因为 API 调用失败是预期的
  211 |     console.log(`共发现 ${errors.length} 个错误（包含非关键错误）`)
  212 |   })
  213 | })
  214 | 
  215 | // 性能测试
  216 | test.describe('性能测试', () => {
  217 |   test('页面加载时间', async ({ page }) => {
  218 |     const startTime = Date.now()
  219 |     
  220 |     await page.goto(BASE_URL)
  221 |     await page.waitForLoadState('networkidle')
  222 |     
  223 |     const loadTime = Date.now() - startTime
  224 |     
  225 |     console.log(`页面加载时间: ${loadTime}ms`)
  226 |     
  227 |     // 页面加载时间应该在 5 秒内
  228 |     expect(loadTime).toBeLessThan(5000)
  229 |   })
  230 | })
  231 | 
  232 | // 可访问性测试
  233 | test.describe('可访问性测试', () => {
  234 |   test('图片 alt 文本', async ({ page }) => {
  235 |     await page.goto(BASE_URL)
  236 |     await page.waitForLoadState('networkidle')
  237 |     
  238 |     // 检查所有图片是否有 alt 属性
  239 |     const images = page.locator('img')
```