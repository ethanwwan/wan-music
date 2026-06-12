/**
 * API接口测试用例
 */

import { test, expect } from '@playwright/test'
import {
  apiRequest,
  verifyApiSuccess,
  verifyApiError,
} from './utils/helpers.js'

test.describe('API接口测试', () => {
  test('TC-API-001: 健康检查', async () => {
    const response = await apiRequest('GET', '/health')
    verifyApiSuccess(response)
    expect(response.json.data.service).toBe('running')
  })

  test('TC-API-010: API信息', async () => {
    const response = await apiRequest('GET', '/api/info')
    verifyApiSuccess(response)
    expect(response.json.data.name).toBe('网易云音乐API服务')
  })

  test('TC-API-011: 搜索API - 空关键词', async () => {
    const response = await apiRequest('POST', '/search', {
      keyword: '',
    })
    verifyApiError(response, 400)
  })

  test('TC-API-003: 搜索歌单API', async () => {
    const response = await apiRequest('POST', '/search/playlist', {
      keyword: '华语经典',
      limit: 5,
    })
    verifyApiSuccess(response)
  })

  test('TC-API-004: 搜索专辑API', async () => {
    const response = await apiRequest('POST', '/search/album', {
      keyword: '范特西',
      limit: 5,
    })
    verifyApiSuccess(response)
  })

  test('TC-API-005: 搜索歌手API', async () => {
    const response = await apiRequest('POST', '/search/artist', {
      keyword: '周杰伦',
      limit: 5,
    })
    verifyApiSuccess(response)
  })
})