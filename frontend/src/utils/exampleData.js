// 示例链接 - 搜索关键词
export const searchExampleLinks = [
  { url: '周杰伦', name: '周杰伦', type: 'artist' },
  { url: '夜曲', name: '夜曲', type: 'song' },
  { url: '林俊杰', name: '林俊杰', type: 'artist' },
  { url: '稻香', name: '稻香', type: 'song' },
  { url: '五月天', name: '五月天', type: 'artist' }
]

// 示例链接 - 单曲
export const musicExampleLinks = [
  { url: 'https://music.163.com/song?id=1454730043', name: '赤伶', artist: '李玉刚' },
  { url: 'https://music.163.com/song?id=1335942780', name: '九万字', artist: '黄诗扶' },
  { url: 'https://music.163.com/song?id=110191', name: '暗里着迷', artist: '刘德华' },
  { url: 'https://music.163.com/song?id=1390321408', name: '芒种', artist: '音阙诗听' },
  { url: 'https://music.163.com/song?id=1373482286', name: '野狼disco', artist: '宝石Gem' }
]

// 示例链接 - 歌单
export const playlistExampleLinks = [
  { url: 'https://music.163.com/playlist?id=7358627467', name: '华语经典流行', creator: '网易云音乐' },
  { url: 'https://music.163.com/playlist?id=2884035', name: '那些回不去的年少时光', creator: '网易云音乐' },
  { url: 'https://music.163.com/playlist?id=19723756', name: '云音乐飙升榜', creator: '网易云音乐' },
  { url: 'https://music.163.com/playlist?id=3778678', name: '热歌榜', creator: '网易云音乐' },
  { url: 'https://music.163.com/playlist?id=3779629', name: '新歌榜', creator: '网易云音乐' }
]

// 示例链接 - 专辑
export const albumExampleLinks = [
  { url: 'https://music.163.com/#/album?id=10804', name: '第二天堂', artist: '林俊杰' },
  { url: 'https://music.163.com/#/album?id=3056951', name: '新地球 - 人 (Special Edition)', artist: '林俊杰' },
  { url: 'https://music.163.com/#/album?id=74956171', name: '进阶', artist: '林俊杰' },
  { url: 'https://music.163.com/#/album?id=84838576', name: '最伟大的作品', artist: '周杰伦' },
  { url: 'https://music.163.com/#/album?id=122778306', name: '入海', artist: '毛不易' }
]

/**
 * 根据当前视图获取示例链接
 * @param {string} currentView 当前视图类型 ('search', 'music', 'playlist', or 'album')
 * @returns {Array} 示例链接数组
 */
export const getExampleLinks = (currentView) => {
  if (currentView === 'search') {
    return searchExampleLinks
  }
  if (currentView === 'playlist') {
    return playlistExampleLinks
  }
  if (currentView === 'album') {
    return albumExampleLinks
  }
  return musicExampleLinks
}

/**
 * 获取示例标签的标题（用于显示在示例数据上方）
 * @param {string} currentView 当前视图类型 ('search', 'music', 'playlist', or 'album')
 * @returns {string} 示例标签标题
 */
export const getExampleTitle = (currentView) => {
  if (currentView === 'search') {
    return '搜索示例'
  }
  if (currentView === 'playlist') {
    return '歌单示例'
  }
  if (currentView === 'album') {
    return '专辑示例'
  }
  return '示例歌曲'
}

/**
 * 获取历史解析假数据
 * @param {string} type 过滤类型（可选）：'search', 'music', 'playlist', 'album'
 * @returns {Array} 历史记录数组
 */
export const getMockHistoryRecords = (type = null) => {
  const allRecords = [
    // 搜索历史
    { name: '周杰伦', url: '周杰伦', type: 'search' },
    { name: '夜曲', url: '夜曲', type: 'search' },
    { name: '林俊杰', url: '林俊杰', type: 'search' },
    { name: '稻香', url: '稻香', type: 'search' },
    { name: '五月天', url: '五月天', type: 'search' },
    // 单曲历史
    { name: '夜曲', url: 'https://music.163.com/song?id=318104', type: 'music' },
    { name: '稻香', url: 'https://music.163.com/song?id=185513', type: 'music' },
    { name: '晴天', url: 'https://music.163.com/song?id=185313', type: 'music' },
    { name: '九万字', url: 'https://music.163.com/song?id=1335942780', type: 'music' },
    { name: '赤伶', url: 'https://music.163.com/song?id=1454730043', type: 'music' },
    // 歌单历史
    { name: '华语经典流行', url: 'https://music.163.com/playlist?id=7358627467', type: 'playlist' },
    { name: '那些回不去的年少时光', url: 'https://music.163.com/playlist?id=2884035', type: 'playlist' },
    { name: '云音乐飙升榜', url: 'https://music.163.com/playlist?id=19723756', type: 'playlist' },
    // 专辑历史
    { name: '最伟大的作品', url: 'https://music.163.com/#/album?id=84838576', type: 'album' },
    { name: '进阶', url: 'https://music.163.com/#/album?id=74956171', type: 'album' },
    { name: '第二天堂', url: 'https://music.163.com/#/album?id=10804', type: 'album' }
  ]
  
  if (type) {
    return allRecords.filter(record => record.type === type)
  }
  
  return allRecords
}

/**
 * 获取当前示例链接（需要在组件中传入currentView）
 * @param {string} currentView 当前视图类型
 * @returns {Array} 示例链接数组
 */
export const getCurrentExampleLinks = (currentView) => {
  return getExampleLinks(currentView)
}

/**
 * 获取随机示例链接
 * @param {string} type 链接类型 ('music', 'playlist', or 'album')
 * @returns {Object} 随机示例链接对象
 */
export const getRandomExampleLink = (type) => {
  let links
  if (type === 'playlist') {
    links = playlistExampleLinks
  } else if (type === 'album') {
    links = albumExampleLinks
  } else {
    links = musicExampleLinks
  }
  const randomIndex = Math.floor(Math.random() * links.length)
  return links[randomIndex]
}

/**
 * 获取所有示例链接
 * @returns {Object} 包含音乐、歌单和专辑示例链接的对象
 */
export const getAllExampleLinks = () => {
  return {
    music: musicExampleLinks,
    playlist: playlistExampleLinks,
    album: albumExampleLinks
  }
}

/**
 * 添加新的示例链接
 * @param {string} type 链接类型 ('music', 'playlist', or 'album')
 * @param {Object} linkData 链接数据对象
 */
export const addExampleLink = (type, linkData) => {
  if (type === 'playlist') {
    playlistExampleLinks.push(linkData)
  } else if (type === 'album') {
    albumExampleLinks.push(linkData)
  } else {
    musicExampleLinks.push(linkData)
  }
}

/**
 * 移除示例链接
 * @param {string} type 链接类型 ('music', 'playlist', or 'album')
 * @param {number} index 要移除的链接索引
 */
export const removeExampleLink = (type, index) => {
  if (type === 'playlist' && index >= 0 && index < playlistExampleLinks.length) {
    playlistExampleLinks.splice(index, 1)
  } else if (type === 'album' && index >= 0 && index < albumExampleLinks.length) {
    albumExampleLinks.splice(index, 1)
  } else if (type === 'music' && index >= 0 && index < musicExampleLinks.length) {
    musicExampleLinks.splice(index, 1)
  }
}

/**
 * 验证示例链接格式
 * @param {Object} linkData 链接数据对象
 * @param {string} type 链接类型 ('music', 'playlist', or 'album')
 * @returns {boolean} 是否为有效格式
 */
export const validateExampleLink = (linkData, type) => {
  if (!linkData || typeof linkData !== 'object') return false
  
  const hasUrl = typeof linkData.url === 'string' && linkData.url.trim() !== ''
  const hasName = typeof linkData.name === 'string' && linkData.name.trim() !== ''
  
  if (type === 'playlist') {
    const hasCreator = typeof linkData.creator === 'string' && linkData.creator.trim() !== ''
    return hasUrl && hasName && hasCreator
  } else { // 'music' or 'album'
    const hasArtist = typeof linkData.artist === 'string' && linkData.artist.trim() !== ''
    return hasUrl && hasName && hasArtist
  }
}