/**
 * 网易云音乐无损解析 - 主入口文件
 * 负责初始化各个模块和协调它们之间的交互
 */

// 页面加载完成后执行
$(document).ready(function() {
    // 初始化各个模块
    initModules();
    
    // 绑定解析方式切换事件
    bindParseMethodSwitch();
    
    // 绑定表单提交事件
    bindFormSubmit();
    
    // 绑定其他按钮事件
    bindOtherEvents();
});

/**
 * 初始化各个模块
 */
function initModules() {
    // 初始化音质选择模块
    if (typeof QualitySelector !== 'undefined') {
        QualitySelector.init();
    }
    
    // 初始化历史记录管理模块
    if (typeof HistoryManager !== 'undefined') {
        HistoryManager.init();
        HistoryManager.bindEvents();
    }
    
    // 初始化歌单解析模块
    if (typeof PlaylistParser !== 'undefined') {
        PlaylistParser.init();
    }
    
    console.log('所有模块初始化完成');
}

/**
 * 绑定解析方式切换事件
 */
function bindParseMethodSwitch() {
    // 监听input的change事件
    $('.parse-method-input').on('change', function() {
        const method = $(this).val();
        console.log('解析方式切换:', method);
        
        // 隐藏所有解析方式容器
        $('.card-form').addClass('d-none');
        
        // 显示对应解析方式的容器
        const cardId = `#${method}-parse-card`;
        console.log('显示卡片:', cardId);
        $(cardId).removeClass('d-none');
        
        // 验证卡片是否存在
        if (!$(cardId).length) {
            console.error('卡片不存在:', cardId);
        }
    });
    
    // 默认显示搜索解析
    $('.card-form').addClass('d-none');
    $('#search-parse-card').removeClass('d-none');
    console.log('默认显示搜索解析');
}

/**
 * 绑定表单提交事件
 */
function bindFormSubmit() {
    // 搜索表单提交
    $('#search_btn').on('click', function() {
        const keyword = $('#search_input').val().trim();
        const quality = $('#search_level').val();
        
        if (!keyword) {
            Swal.fire({
                icon: 'warning',
                title: '请输入搜索关键词',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            return;
        }
        
        // 调用MusicParser进行搜索
        if (typeof MusicParser !== 'undefined') {
            MusicParser.performSearch();
        }
    });
    
    // ID解析表单提交
    $('#query-form').on('submit', function(e) {
        e.preventDefault();
        const songIds = $('#song_ids').val().trim();
        const quality = $('#level').val();
        
        if (!songIds) {
            Swal.fire({
                icon: 'warning',
                title: '请输入歌曲ID或链接',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            return;
        }
        
        // 调用MusicParser进行解析
        if (typeof MusicParser !== 'undefined') {
            MusicParser.parseSongById(songIds, quality).then(songData => {
                // 调用HistoryManager添加到历史记录
                if (typeof HistoryManager !== 'undefined') {
                    HistoryManager.add({
                        id: songData.id || songData.validId,
                        name: songData.name,
                        artist: songData.ar_name,
                        album: songData.al_name,
                        pic: songData.pic,
                        fee: songData.fee || 0,
                        timestamp: Date.now()
                    });
                }
                
                // 更新UI显示解析结果
                MusicParser.updateUIWithParsedSong(songData, function(songInfo) {
                    if (typeof HistoryManager !== 'undefined') {
                        HistoryManager.add(songInfo);
                    }
                });
            }).catch(error => {
                MusicParser.handleParseError(error);
            });
        }
    });
    
    // 歌单解析表单提交
    $('#playlist-form').on('submit', function(e) {
        e.preventDefault();
        const playlistId = $('#playlist_id').val().trim();
        const quality = $('#playlist_level').val();
        
        if (!playlistId) {
            Swal.fire({
                icon: 'warning',
                title: '请输入歌单ID或链接',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            return;
        }
        
        // 调用PlaylistParser进行解析
        if (typeof PlaylistParser !== 'undefined') {
            PlaylistParser.parsePlaylist(playlistId, quality);
        }
    });
}

/**
 * 绑定其他按钮事件
 */
function bindOtherEvents() {
    // 清空搜索框按钮
    $('#clear-search').on('click', function() {
        $('#search_input').val('');
    });
    
    // 清空ID输入框按钮
    $('#clear-ids').on('click', function() {
        $('#song_ids').val('');
    });
    
    // 清空歌单输入框按钮
    $('#clear-playlist').on('click', function() {
        $('#playlist_id').val('');
    });
    
    // 显示快捷键帮助
    $('#shortcut-help-btn').on('click', function() {
        Swal.fire({
            title: '快捷键帮助',
            html: `
                <div class="text-left">
                    <p><kbd>Ctrl</kbd> + <kbd>/</kbd>: 切换解析方式</p>
                    <p><kbd>Ctrl</kbd> + <kbd>K</kbd>: 聚焦搜索框</p>
                    <p><kbd>Enter</kbd>: 提交当前表单</p>
                    <p><kbd>Esc</kbd>: 清空当前输入框</p>
                </div>
            `,
            icon: 'info',
            confirmButtonText: '确定'
        });
    });
    
    // 显示关于页面
    $('#about-btn').on('click', function() {
        Swal.fire({
            title: '关于网易云音乐无损解析',
            html: `
                <div class="text-center">
                    <h5>版本: v5.2.0</h5>
                    <p>一个免费的网易云音乐无损解析工具</p>
                    <p>支持歌曲搜索、ID解析、歌单解析</p>
                    <p>支持无损音质下载</p>
                </div>
            `,
            icon: 'info',
            confirmButtonText: '确定'
        });
    });
    
    // 绑定下载按钮事件
    $('#download-pack').on('click', function() {
        const songData = window.currentSongData;
        if (!songData || !songData.url) {
            Swal.fire({
                icon: 'warning',
                title: '没有可下载的歌曲',
                text: '请先解析一首歌曲',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000
            });
            return;
        }
        
        const uiElements = {
            $progressContainer: $('#download-progress-container'),
            $progressBar: $('#download-progress-bar'),
            $progressText: $('#download-progress-text'),
            $status: $('#download-status')
        };
        
        const downloadData = {
            name: songData.name,
            url: songData.url,
            pic: songData.pic,
            lyric: songData.processedLyrics || songData.lyric,
            tlyric: songData.tlyric,
            ar_name: songData.ar_name,
            al_name: songData.al_name,
            fee: songData.fee,
            id: songData.id,
            ext: songData.ext || { audio: 'mp3' }
        };
        
        if (typeof MusicDownloader !== 'undefined') {
            MusicDownloader.downloadAndPackSong(downloadData, uiElements);
        } else {
            Swal.fire({
                icon: 'error',
                title: '下载模块未加载',
                text: '请刷新页面后重试',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000
            });
        }
    });
}

/**
 * 处理快捷键
 */
$(document).on('keydown', function(e) {
    // Ctrl + /: 切换解析方式
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        const activeMethod = $('.parse-method-input:checked').val();
        const methods = ['search', 'id', 'playlist'];
        const currentIndex = methods.indexOf(activeMethod);
        const nextIndex = (currentIndex + 1) % methods.length;
        $(`#parseMethod${methods[nextIndex].charAt(0).toUpperCase() + methods[nextIndex].slice(1)}`).prop('checked', true).trigger('change');
    }
    
    // Ctrl + K: 聚焦搜索框
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        $('#search_input').focus();
    }
    
    // Esc: 清空当前输入框
    if (e.key === 'Escape') {
        const activeMethod = $('.parse-method-input:checked').val();
        if (activeMethod === 'search') {
            $('#search_input').val('');
        } else if (activeMethod === 'id') {
            $('#song_ids').val('');
        } else if (activeMethod === 'playlist') {
            $('#playlist_id').val('');
        }
    }
});

/**
 * 显示加载状态
 */
function showLoading(message = '加载中...') {
    Swal.fire({
        title: message,
        html: '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>',
        allowOutsideClick: false,
        showConfirmButton: false
    });
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    Swal.close();
}

/**
 * 显示消息提示
 */
function showMessage(message, type = 'info') {
    Swal.fire({
        icon: type,
        title: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
    });
}

/**
 * 验证输入
 */
function validateInput(input, minLength = 1) {
    if (!input || input.trim().length < minLength) {
        return false;
    }
    return true;
}

/**
 * 清理结果区域
 */
function clearResults() {
    $('#result-container').empty();
    $('#playlist-result-container').empty();
}

/**
 * 初始化页面
 */
function initPage() {
    // 隐藏所有解析方式容器
    $('.card-form').addClass('d-none');
    
    // 默认显示搜索解析
    $('#search-parse-card').removeClass('d-none');
    
    // 加载页面时的动画效果
    $('.container').fadeIn(500);
    
    console.log('页面初始化完成');
}

// 页面加载完成后初始化
$(window).on('load', function() {
    initPage();
});
