/**
 * 音质等级配置
 * 前后端共享的音质定义
 */

export const QUALITY_LEVELS = {
  standard: {
    value: 'standard',
    label: '标准',
    description: '128kbps',
    priority: 8
  },
  exhigh: {
    value: 'exhigh',
    label: '极高',
    description: '320kbps',
    priority: 7
  },
  lossless: {
    value: 'lossless',
    label: '无损',
    description: 'FLAC',
    priority: 6
  },
  hires: {
    value: 'hires',
    label: 'Hi-Res',
    description: 'FLAC 24bit',
    priority: 5
  },
  sky: {
    value: 'sky',
    label: '沉浸环绕声',
    description: 'Surround Audio',
    priority: 4
  },
  jyeffect: {
    value: 'jyeffect',
    label: '高清臻音',
    description: 'Spatial Audio',
    priority: 3
  },
  jymaster: {
    value: 'jymaster',
    label: '超清母带',
    description: 'FLAC 24bit/96kHz',
    priority: 2
  },
  dolby: {
    value: 'dolby',
    label: '杜比全景声',
    description: 'Dolby Atmos',
    priority: 1
  }
}

export const getQualityOptions = () => {
  return Object.values(QUALITY_LEVELS)
    .sort((a, b) => a.priority - b.priority)
    .map(q => ({
      value: q.value,
      label: `${q.label} (${q.description})`
    }))
}

export const getQualityLabel = (value) => {
  return QUALITY_LEVELS[value]?.label || value
}

export const isValidQuality = (value) => {
  return Object.prototype.hasOwnProperty.call(QUALITY_LEVELS, value)
}

export const getAllQualityValues = () => {
  return Object.keys(QUALITY_LEVELS)
}

export const getDefaultQuality = () => {
  return 'lossless'
}