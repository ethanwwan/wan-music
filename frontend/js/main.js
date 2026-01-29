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
    // 解析方式切换按钮
    $('.parse-method-btn').on('click', function() {
        const method = $(this).data('method');
        
        // 移除所有按钮的激活状态
        $('.parse-method-btn').removeClass('active');
        
        // 添加当前按钮的激活状态
        $(this).addClass('active');
        
        // 隐藏所有解析方式容器
        $('.parse-method-container').hide();
        
        // 显示对应解析方式的容器
        $(`#${method}-parse-container`).show();
    });
}

/**
 * 绑定表单提交事件
 */
function bindFormSubmit() {
    // 搜索表单提交
    $('#search-form').on('submit', function(e) {
        e.preventDefault();
        const keyword = $('#search-keyword').val().trim();
        const quality = $('#search-quality').val();
        
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
            MusicParser.searchMusic(keyword, quality);
        }
    });
    
    // ID解析表单提交
    $('#query-form').on('submit', function(e) {
        e.preventDefault();
        const songIds = $('#song_ids').val().trim();
        const quality = $('#quality').val();
        
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
            MusicParser.parseMusicById(songIds, quality);
        }
    });
    
    // 歌单解析表单提交
    $('#playlist-form').on('submit', function(e) {
        e.preventDefault();
        const playlistId = $('#playlist_id').val().trim();
        
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
            PlaylistParser.parsePlaylist();
        }
    });
}

/**
 * 绑定其他按钮事件
 */
function bindOtherEvents() {
    // 清空搜索框按钮
    $('#clear-search').on('click', function() {
        $('#search-keyword').val('');
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
}

/**
 * 处理快捷键
 */
$(document).on('keydown', function(e) {
    // Ctrl + /: 切换解析方式
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        const activeMethod = $('.parse-method-btn.active').data('method');
        const methods = ['search', 'id', 'playlist'];
        const currentIndex = methods.indexOf(activeMethod);
        const nextIndex = (currentIndex + 1) % methods.length;
        $(`[data-method="${methods[nextIndex]}"]`).click();
    }
    
    // Ctrl + K: 聚焦搜索框
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        $('#search-keyword').focus();
    }
    
    // Esc: 清空当前输入框
    if (e.key === 'Escape') {
        const activeMethod = $('.parse-method-btn.active').data('method');
        if (activeMethod === 'search') {
            $('#search-keyword').val('');
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
    // 设置默认解析方式
    $(`[data-method="search"]`).click();
    
    // 加载页面时的动画效果
    $('.container').fadeIn(500);
    
    console.log('页面初始化完成');
}

// 页面加载完成后初始化
$(window).on('load', function() {
    initPage();
});
