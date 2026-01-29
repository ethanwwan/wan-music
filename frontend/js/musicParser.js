/**
 * 网易云音乐解析模块
 * @author kanxizai
 * @version 1.0
 * @description 负责搜索和ID/链接解析功能
 */

// 文件扩展名提取函数
const getFileExtension = url => {
    try {
        return new URL(url).pathname.split('.').pop().toLowerCase().replace(/\?.+/, '');
    } catch {
        const parts = url.split('.');
        return parts.length > 1 ? parts.pop().split(/[?#]/)[0] : '';
    }
};

// 文件名安全处理
const sanitizeFilename = name =>
    String(name).replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, ' ').trim();

/**
 * 处理歌词时间戳和文本
 * @function lrctrim
 * @param {string} lyrics - 原始歌词文本
 * @returns {Array} 处理后的歌词数据数组
 */
function lrctrim(lyrics) {
    const lines = lyrics.split('\n');
    const data = [];

    lines.forEach((line, index) => {
        const matches = line.match(/\[(\d{2}):(\d{2}[\.:]?\d*)]/);
        if (matches) {
            const minutes = parseInt(matches[1], 10);
            const seconds = parseFloat(matches[2].replace('.', ':')) || 0;
            const timestamp = minutes * 60000 + seconds * 1000;
            const originalTimeStr = matches[0]; // 保存原始时间戳字符串

            let text = line.replace(/\[\d{2}:\d{2}[\.:]?\d*\]/g, '').trim();
            text = text.replace(/\s\s+/g, ' '); // Replace multiple spaces with a single space

            data.push([timestamp, index, text, originalTimeStr]); // 添加原始时间戳字符串
        }
    });

    data.sort((a, b) => a[0] - b[0]);

    return data;
}

/**
 * 合并原文歌词和翻译歌词
 * @function lrctran
 * @param {string} lyric - 原文歌词
 * @param {string} tlyric - 翻译歌词
 * @returns {string} 合并后的歌词文本
 */
function lrctran(lyric, tlyric) {
    lyric = lrctrim(lyric);
    tlyric = lrctrim(tlyric);

    let len1 = lyric.length;
    let len2 = tlyric.length;
    let result = "";
    
    // 创建翻译映射表，以时间戳为键
    const translationMap = new Map();
    for (let j = 0; j < len2; j++) {
        translationMap.set(tlyric[j][0], tlyric[j]);
    }

    for (let i = 0; i < len1; i++) {
        // 添加原文歌词行
        result += `${lyric[i][3]}${lyric[i][2]}\n`;
        
        // 查找对应的翻译
        const translation = translationMap.get(lyric[i][0]);
        if (translation && translation[2].trim()) {
            // 清理翻译文本中的斜杠
            const cleanTranslation = translation[2].replace('/', '').trim();
            if (cleanTranslation) {
                // 添加翻译歌词行，使用相同的时间戳
                result += `${lyric[i][3]}${cleanTranslation}\n`;
            }
        }
    }

    return result;
}

/**
 * 从文本中提取链接
 * @function extractLinks
 * @param {string} text - 包含可能链接的文本
 * @returns {string} 提取的链接或空字符串
 */
function extractLinks(text) {
    var regex = /https?:\/\/\S+/g;
    var matches = text.match(regex);
    if (matches) {
        return matches[0];
    } else {
        return '';
    }
}

/**
 * 检查链接是否为有效的网易云音乐链接
 * @function checkValidLink
 * @param {string} link - 要检查的链接
 * @returns {boolean} 链接是否有效
 */
function checkValidLink(link) {
    if (link.indexOf("http") === -1 ||
        (link.indexOf("music.163.com") === -1 && link.indexOf("163cn.tv") === -1)) {
        return false;
    }
    return true;
}

/**
 * 从文本中提取并检查ID或链接
 * @function extractAndCheckId
 * @param {string} text - 包含ID或链接的文本
 * @returns {string} 有效的ID或链接，无效则返回空字符串
 */
function extractAndCheckId(text) {
    var link = extractLinks(text);
    if (checkValidLink(link)) {
        return link;
    } else {
        var idRegex = /\b\d+\b/g;
        var ids = text.match(idRegex);
        if (ids && ids.length > 0) {
            return ids[0];
        }
        return '';
    }
}

/**
 * 音乐解析模块 - 负责搜索和ID/链接解析功能
 * @namespace MusicParser
 */
const MusicParser = {
    /**
     * 执行歌曲搜索
     * @async
     * @function performSearch
     * @memberof MusicParser
     * @description 根据用户输入的关键词搜索歌曲
     */
    performSearch: async function() {
        const searchTerm = $('#search_input').val().trim();
        if (!searchTerm) {
            Swal.fire({
                icon: 'warning',
                title: '请输入搜索内容',
                text: '请输入歌曲名称进行搜索',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            return;
        }

        // 显示加载指示器
        $('#loading_indicator').removeClass('d-none');
        $('#search_results').removeClass('d-none');
        $('#results_list').empty();

        try {
            // 使用新的安全API请求方法进行歌曲搜索
            const response = await ApiSecurity.secureApiRequest('./api/api.php', {
                action: 'search',
                name: searchTerm,
                limit: 50
            }, { useEncryption: true });

            // 隐藏加载指示器
            $('#loading_indicator').addClass('d-none');

            if (response.code === 200 && response.data && response.data.length > 0) {
                this.displaySearchResults(response.data);
            } else {
                $('#results_list').html(`
                    <div class="list-group-item text-center text-muted">
                        <i class="fas fa-info-circle me-2"></i>未找到相关歌曲
                    </div>
                `);
            }
        } catch (error) {
            console.error('搜索错误:', error);
            $('#loading_indicator').addClass('d-none');
            $('#results_list').html(`
                <div class="list-group-item text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>搜索失败，请稍后再试
                </div>
            `);
        }
    },

    /**
     * 显示搜索结果
     * @function displaySearchResults
     * @memberof MusicParser
     * @param {Array} results - 搜索结果数组
     * @description 将搜索结果渲染到页面上
     */
    displaySearchResults: function(results) {
        $('#results_list').empty();

        results.forEach(song => {
            // 处理歌手名称
            const artistNames = song.artists.map(artist => artist.name).join(', ');
            
            // 获取封面图片URL (使用新的picUrl字段或回退到album.picUrl)
            const coverUrl = song.picUrl || (song.album && song.album.picUrl) || '';
            
            // 检查是否为会员歌曲 (fee=1表示会员歌曲，fee=0表示免费歌曲)
            const isVip = song.fee === 1;
            
            // 创建结果项
            const resultItem = $(`
                <div class="list-group-item search-result-item" data-id="${song.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex">
                            <div class="song-cover-container flex-shrink-0">
                                <img src="${coverUrl}" alt="${song.name}" class="song-cover">
                                ${isVip ? '<span class="vip-badge"><i class="fas fa-crown"></i>VIP</span>' : ''}
                            </div>
                            <div class="me-auto">
                                <div class="song-title">${song.name}</div>
                                <div class="song-artist"><i class="fas fa-microphone-alt text-muted me-1"></i>${artistNames}</div>
                                <div class="song-album"><i class="fas fa-compact-disc text-muted me-1"></i>${song.album.name}</div>
                            </div>
                        </div>
                        <span class="badge bg-light text-dark">${song.duration}</span>
                    </div>
                </div>
            `);

            // 点击结果项时自动填充ID并触发解析
            resultItem.on('click', function () {
                const songId = $(this).data('id');
                $('#song_ids').val(songId);
                
                // 保存当前歌曲的fee值，用于后续添加到历史记录
                const isSongVip = isVip;
                
                // 使用搜索卡片中选择的音质设置
                const searchQualityValue = $('#search_level').val();
                const searchQuality = $('#searchSelectedQuality').text();
                
                // 同步更新ID解析卡片中的音质选择
                $('#level').val(searchQualityValue);
                $('#selectedQuality').text(searchQuality);
                
                $('#search_results').addClass('d-none');
                
                // 修改提交表单前，先保存fee值到表单的隐藏字段
                // 如果表单中没有该字段，需要先创建
                if ($('#song_fee').length === 0) {
                    $('<input>').attr({
                        type: 'hidden',
                        id: 'song_fee',
                        name: 'song_fee',
                        value: isSongVip ? 1 : 0
                    }).appendTo('#query-form');
                } else {
                    $('#song_fee').val(isSongVip ? 1 : 0);
                }
                
                $('#query-form').trigger('submit');
            });

            $('#results_list').append(resultItem);
        });
    },

    /**
     * 解析歌曲ID或链接
     * @async
     * @function parseSongById
     * @memberof MusicParser
     * @param {string} songIds - 歌曲ID或链接
     * @param {string} level - 音质等级
     * @returns {Promise<Object>} 解析结果
     * @description 根据歌曲ID或链接解析歌曲信息
     */
    parseSongById: async function(songIds, level) {
        const validId = extractAndCheckId(songIds);
        if (!validId) throw new Error('请输入有效的歌曲ID或链接');

        let lastError;
        const maxRetries = 3;
        
        // 重试机制：最多重试3次
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                // 使用新的安全API请求方法进行音乐解析
                const response = await ApiSecurity.secureApiRequest('./api/api.php', {
                    action: 'music',
                    url: validId,
                    level: level,
                    type: 'json'
                }, { useEncryption: true });

                if (response.code !== 200) {
                    // 记录错误信息用于重试
                    lastError = new Error(response.msg);
                    console.warn(`歌曲解析失败 (尝试 ${attempt}/${maxRetries}):`, response.msg);
                    
                    // 如果不是最后一次尝试，则等待后重试
                    if (attempt < maxRetries) {
                        // 指数退避策略：第一次等待1秒，第二次2秒，第三次4秒
                        const delay = Math.pow(2, attempt - 1) * 1000;
                        console.log(`等待 ${delay}ms 后重试...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        continue;
                    }
                    // 最后一次尝试仍然失败，抛出错误
                    throw lastError;
                }

                // 处理歌词
                const processedLyrics = response.tlyric
                    ? lrctran(response.lyric, response.tlyric)
                    : response.lyric;

                // 返回处理后的数据
                return {
                    ...response,
                    processedLyrics,
                    validId
                };
                
            } catch (error) {
                lastError = error;
                
                // 如果是最后一次尝试，直接抛出错误
                if (attempt === maxRetries) {
                    console.error(`歌曲解析最终失败 (${maxRetries}次尝试):`, error.message);
                    throw new Error(`解析失败: ${error.message} (已重试${maxRetries - 1}次)`);
                }
                
                // 网络错误或其他异常，等待后重试
                console.warn(`歌曲解析异常 (尝试 ${attempt}/${maxRetries}):`, error.message);
                const delay = Math.pow(2, attempt - 1) * 1000;
                console.log(`等待 ${delay}ms 后重试...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    },

    /**
     * 更新UI显示解析结果
     * @function updateUIWithParsedSong
     * @memberof MusicParser
     * @param {Object} songData - 解析后的歌曲数据
     * @param {Function} addToHistory - 添加到历史记录的回调函数
     * @description 更新界面显示解析后的歌曲信息
     */
    updateUIWithParsedSong: function(songData, addToHistory) {
        // 更新DOM
        $('#song_name').text(songData.name);
        $('#song_pic').attr('src', songData.pic);
        $('#artist_names').text(songData.ar_name);
        $('#song_alname').text(songData.al_name);
        $('#song_level').text(songData.level);
        $('#song_size').text(songData.size);
        $('#song_url').attr('href', songData.url);
        $('#lyric').html(songData.processedLyrics.replace(/\n/g, '<br>'));

        // 初始化播放器
        if (window.aplayerInstance) window.aplayerInstance.destroy();
        window.aplayerInstance = new APlayer({
            container: document.getElementById('aplayer'),
            mini: false,
            autoplay: true,
            theme: '#1e88e5',
            loop: 'all',
            order: 'list',
            preload: 'auto',
            volume: 0.7,
            mutex: true,
            listFolded: false,
            listMaxHeight: 90,
            lrcType: 1,
            audio: [{
                name: songData.name,
                artist: songData.ar_name,
                url: songData.url,
                cover: songData.pic,
                lrc: songData.processedLyrics
            }]
        });
        
        // 确保循环按钮可见
        setTimeout(() => {
            $('.aplayer-icon-loop').css({
                'display': 'inline-block',
                'visibility': 'visible'
            });
        }, 500);

        $('#song-info').removeClass('d-none');
        $('#download-pack').prop('disabled', false);
        
        // 自动滚动到结果区域
        $('html, body').animate({
            scrollTop: $('#song-info').offset().top - 20
        }, 500);
        
        // 使用 SweetAlert2 显示成功提示
        Swal.fire({
            icon: 'success',
            title: '解析成功',
            text: `成功解析歌曲《${songData.name}》`,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
        
        // 获取fee值，优先使用API返回的值，如果没有则使用表单中保存的值
        const feeValue = songData.fee !== undefined ? songData.fee : ($('#song_fee').length > 0 ? parseInt($('#song_fee').val()) : 0);
        
        // 添加到历史记录
        if (typeof addToHistory === 'function') {
            addToHistory({
                id: songData.id || songData.validId,
                name: songData.name,
                artist: songData.ar_name,
                album: songData.al_name,
                pic: songData.pic,
                fee: feeValue,
                timestamp: Date.now()
            });
        }
        
        // 更新当前歌曲数据
        window.currentSongData = {
            name: sanitizeFilename(songData.name),
            url: songData.url,
            pic: songData.pic,
            lyric: songData.lyric,
            tlyric: songData.tlyric,
            ar_name: songData.ar_name, // 添加歌手名称字段
            al_name: songData.al_name, // 添加专辑名称字段

            ext: {
                audio: getFileExtension(songData.url) || 'mp3',
                image: getFileExtension(songData.pic) || 'jpg'
            }
        };
    },

    /**
     * 处理解析错误
     * @function handleParseError
     * @memberof MusicParser
     * @param {Error} error - 错误对象
     * @description 处理解析过程中的错误并显示给用户
     */
    handleParseError: function(error) {
        console.error('解析错误:', error);
        // 处理API返回的错误信息
        let errorMsg = '未知错误';
        if (error.responseJSON) {
            // jQuery ajax错误
            errorMsg = error.responseJSON.msg || error.codeText;
        } else if (error.response) {
            // axios错误
            errorMsg = error.response.data.msg || error.response.codeText;
        } else if (error.msg) {
            // API直接返回的错误对象
            errorMsg = error.msg;
        } else if (error.message) {
            // 标准JS错误
            errorMsg = error.message;
        }
        // 使用 SweetAlert2 显示错误提示
        Swal.fire({
            icon: 'error',
            title: '解析失败',
            text: errorMsg,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
        $('#download-pack').prop('disabled', false);
    }
};

// 导出模块
window.MusicParser = MusicParser;