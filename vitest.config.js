/**
 * 自动化测试脚本
 * 测试 wan-music 项目的各个功能模块
 */

import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/**/*.test.js'],
    coverage: {
      reporter: ['text', 'json', 'html']
    }
  }
})
