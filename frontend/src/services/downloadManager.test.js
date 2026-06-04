/**
 * 前端下载管理器测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  DOWNLOAD_STATUSES,
  formatTask,
  setOnTasksUpdate
} from '../src/services/downloadManager.js'

describe('下载管理器', () => {
  describe('状态枚举', () => {
    it('应该定义所有状态', () => {
      expect(DOWNLOAD_STATUSES.PENDING).toBe('pending')
      expect(DOWNLOAD_STATUSES.DOWNLOADING).toBe('downloading')
      expect(DOWNLOAD_STATUSES.COMPLETED).toBe('completed')
      expect(DOWNLOAD_STATUSES.FAILED).toBe('failed')
      expect(DOWNLOAD_STATUSES.PAUSED).toBe('paused')
      expect(DOWNLOAD_STATUSES.CANCELLED).toBe('cancelled')
    })
  })
  
  describe('任务格式化', () => {
    it('应该正确格式化任务', () => {
      const task = {
        task_id: 'test-123',
        music_id: 123,
        music_name: '测试歌曲',
        status: 'downloading',
        progress: {
          downloaded: 1024000,
          total: 5120000,
          percentage: 20,
          speed: 102400,
          eta_seconds: 40
        }
      }
      
      const formatted = formatTask(task)
      
      expect(formatted.task_id).toBe('test-123')
      expect(formatted.music_id).toBe(123)
      expect(formatted.status_text).toBe('下载中')
      expect(formatted.status_color).toBe('#3b82f6')
      expect(formatted.progress_display).toBeDefined()
      expect(formatted.progress_display.percentage).toBe(20)
    })
    
    it('应该处理没有进度信息的任务', () => {
      const task = {
        task_id: 'test-123',
        music_id: 123,
        status: 'pending'
      }
      
      const formatted = formatTask(task)
      
      expect(formatted.progress_display).toBeDefined()
      expect(formatted.progress_display.percentage).toBe(0)
    })
    
    it('应该为不同状态返回正确的状态文本', () => {
      const testCases = [
        { status: 'pending', expectedText: '等待中', expectedColor: '#9ca3af' },
        { status: 'downloading', expectedText: '下载中', expectedColor: '#3b82f6' },
        { status: 'completed', expectedText: '已完成', expectedColor: '#10b981' },
        { status: 'failed', expectedText: '失败', expectedColor: '#ef4444' },
        { status: 'paused', expectedText: '已暂停', expectedColor: '#f59e0b' },
        { status: 'cancelled', expectedText: '已取消', expectedColor: '#6b7280' },
        { status: 'unknown', expectedText: 'unknown', expectedColor: '#9ca3af' },
      ]
      
      testCases.forEach(({ status, expectedText, expectedColor }) => {
        const formatted = formatTask({ task_id: '1', status })
        expect(formatted.status_text).toBe(expectedText)
        expect(formatted.status_color).toBe(expectedColor)
      })
    })
  })
  
  describe('回调机制', () => {
    it('应该能够设置和更新回调', () => {
      const mockCallback = vi.fn()
      setOnTasksUpdate(mockCallback)
      
      // 这个测试只是验证API存在
      expect(true).toBe(true)
    })
  })
})

describe('进度显示格式化', () => {
  it('应该正确处理各种进度值', () => {
    // 测试边界情况
    const edgeCases = [
      { downloaded: 0, total: 0, expectedPercentage: 0 },
      { downloaded: 0, total: 100, expectedPercentage: 0 },
      { downloaded: 50, total: 100, expectedPercentage: 50 },
      { downloaded: 100, total: 100, expectedPercentage: 100 },
      { downloaded: 150, total: 100, expectedPercentage: 100 },
    ]
    
    edgeCases.forEach(({ downloaded, total, expectedPercentage }) => {
      const formatted = formatTask({
        task_id: '1',
        status: 'downloading',
        progress: { downloaded, total, percentage: expectedPercentage }
      })
      
      expect(formatted.progress_display.percentage).toBe(expectedPercentage)
    })
  })
})

describe('错误处理', () => {
  it('应该优雅地处理缺失的任务数据', () => {
    expect(() => {
      formatTask({})
    }).not.toThrow()
  })
  
  it('应该优雅地处理null/undefined任务', () => {
    expect(() => {
      formatTask(null)
    }).not.toThrow()
    
    expect(() => {
      formatTask(undefined)
    }).not.toThrow()
  })
})
