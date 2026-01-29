/**
 * 网易云音乐无损解析 - 历史记录管理模块
 * @author kanxizai
 * @version 1.0
 */

/**
 * 历史记录管理模块
 * 负责管理用户的歌曲播放历史记录
 */
const HistoryManager = (function() {
    // 私有变量
    let songHistory = [];
    
    /**
     * 初始化历史记录
     * 从本地存储中加载历史记录数据
     */
    function init() {
        songHistory = JSON.parse(localStorage.getItem('songHistory') || '[]');
    }
    
    /**
     * 获取所有历史记录
     * @returns {Array} 历史记录数组
     */
    function getAll() {
        return songHistory;
    }
    
    /**
     * 添加歌曲到历史记录
     * @param {Object} songData - 歌曲数据对象
     */
    function add(songData) {
        // 检查是否已存在相同ID的记录
        const existingIndex = songHistory.findIndex(item => item.id === songData.id);
        
        // 如果存在，先删除旧记录
        if (existingIndex !== -1) {
            songHistory.splice(existingIndex, 1);
        }
        
        // 限制历史记录最多保存100条
        if (songHistory.length >= 100) {
            songHistory.pop(); // 移除最旧的一条
        }
        
        // 添加新记录到开头
        songHistory.unshift(songData);
        
        // 保存到本地存储
        save();
    }
    
    /**
     * 删除单个历史记录
     * @param {string|number} songId - 歌曲ID
     */
    function remove(songId) {
        // 确保类型一致性，将songId转换为字符串进行比较
        const targetId = String(songId);
        const index = songHistory.findIndex(item => String(item.id) === targetId);
        if (index !== -1) {
            songHistory.splice(index, 1);
            save();
            console.log(`已删除歌曲ID: ${targetId}, 剩余记录数: ${songHistory.length}`);
        } else {
            console.warn(`未找到要删除的歌曲ID: ${targetId}`);
        }
    }
    
    /**
     * 清空历史记录
     */
    function clear() {
        songHistory = [];
        localStorage.removeItem('songHistory');
    }
    
    /**
     * 保存历史记录到本地存储
     * @private
     */
    function save() {
        localStorage.setItem('songHistory', JSON.stringify(songHistory));
    }
    
    /**
     * 更新历史记录列表显示
     * 在DOM中渲染历史记录列表
     */
    function updateHistoryList() {
        const $historyList = $('#history-list');
        const $noHistory = $('#no-history');
        const $historyCount = $('#history-count');
        
        // 更新记录总数
        $historyCount.text(songHistory.length);
        
        if (songHistory.length === 0) {
            $historyList.hide();
            $noHistory.show();
            return;
        }
        
        $historyList.empty().show();
        $noHistory.hide();
        
        // 按时间倒序排列，最新的在前面
        songHistory.sort((a, b) => b.timestamp - a.timestamp);
        
        songHistory.forEach(song => {
            // 检查是否为会员歌曲
            const isVip = song.fee === 1;
            
            const historyItem = $(`
                <div class="list-group-item history-item">
                    <div class="d-flex align-items-center">
                        <div class="flex-shrink-0 position-relative">
                            <img src="${song.pic}" alt="${song.name}" class="history-cover" width="60" height="60" referrerpolicy="no-referrer">
                            ${isVip ? '<span class="vip-badge">VIP</span>' : ''}
                        </div>
                        <div class="flex-grow-1 ms-3 overflow-hidden">
                            <h6 class="mb-0 text-truncate" title="${song.name}">${song.name}</h6>
                            <p class="mb-0 small text-muted text-truncate" title="歌手: ${song.artist} | 专辑: ${song.album}">
                                <i class="fas fa-microphone-alt me-1"></i>${song.artist}
                                <span class="mx-2">|</span>
                                <i class="fas fa-compact-disc me-1"></i>${song.album}
                            </p>
                            <p class="mb-0 small text-muted">
                                <i class="fas fa-clock me-1"></i>${new Date(song.timestamp).toLocaleString()}
                            </p>
                        </div>
                        <div class="ms-3 flex-shrink-0 d-flex gap-2">
                            <button class="btn btn-sm btn-success play-history" data-id="${song.id}" title="播放">
                                <i class="fas fa-play"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-history" data-id="${song.id}" title="删除">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `);
            
            $historyList.append(historyItem);
        });
        
    }
    
    /**
     * 绑定历史记录相关的事件处理
     */
    function bindEvents() {
        // 清空历史记录
        $('#clear-history-btn').on('click', function() {
            Swal.fire({
                title: '确认清空',
                html: '确定要清空所有播放历史吗？<br/><span style="color: #d33;">此操作不可恢复！</span>',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: '确定清空',
                cancelButtonText: '取消'
            }).then((result) => {
                if (result.isConfirmed) {
                    clear();
                    updateHistoryList();
                    Swal.fire({
                        icon: 'success',
                        title: '已清空',
                        text: '播放历史已清空',
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                }
            });
        });
        
        // 显示历史记录弹窗
        $('#history-btn').on('click', function() {
            updateHistoryList();
            $('#historyModal').modal('show');
        });
        
        // 使用事件委托绑定播放按钮事件
        $('#history-list').on('click', '.play-history', function() {
            const songId = $(this).data('id');
            $('#song_ids').val(songId);
            $('#historyModal').modal('hide');
            $('#query-form').trigger('submit');
        });
        
        // 使用事件委托绑定删除按钮事件
        $('#history-list').on('click', '.delete-history', function(e) {
            e.stopPropagation();
            const songId = $(this).data('id');
            const songName = $(this).closest('.history-item').find('h6').text();
            
            console.log('准备删除歌曲:', { songId, songName, type: typeof songId });
            console.log('删除前历史记录数量:', songHistory.length);
            
            Swal.fire({
                title: '确认删除',
                html: `确定要删除 "<strong>${songName}</strong>" 吗？`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: '确定删除',
                cancelButtonText: '取消'
            }).then((result) => {
                if (result.isConfirmed) {
                    console.log('用户确认删除，调用remove函数');
                    remove(songId);
                    console.log('删除后历史记录数量:', songHistory.length);
                    updateHistoryList();
                    Swal.fire({
                        icon: 'success',
                        title: '已删除',
                        text: '历史记录已删除',
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 2000,
                        timerProgressBar: true
                    });
                }
            });
        });
    }
    
    // 公开的API
    return {
        init: init,
        getAll: getAll,
        add: add,
        remove: remove,
        clear: clear,
        updateHistoryList: updateHistoryList,
        bindEvents: bindEvents
    };
})();