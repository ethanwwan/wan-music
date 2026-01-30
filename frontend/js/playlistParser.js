/**
 * 网易云音乐无损解析 - 歌单解析模块
 * @author kanxizai
 * @version 1.0
 * @description 负责歌单解析相关功能
 */

/**
 * 歌单解析模块
 * @namespace PlaylistParser
 */
const PlaylistParser = (function () {
    // 当前歌单数据
    let currentPlaylist = null;
    // 当前选择的音质
    let currentQuality = 'standard';
    // 下载队列
    let downloadQueue = [];
    // 是否正在批量下载
    let isBatchDownloading = false;

    /**
     * 初始化歌单解析模块
     * @function init
     */
    function init() {
        // 绑定一键下载全部按钮事件
        $('#download-all').on('click', function () {
            downloadAllSongs();
        });
    }

    /**
     * 解析歌单
     * @function parsePlaylist
     * @async
     * @param {string} playlistInput - 歌单ID或链接
     * @param {string} quality - 音质级别
     */
    // 从文本中提取ID或链接的辅助函数
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
     * 获取歌手名称 - 兼容新旧数据格式
     * @function getArtistNames
     * @param {Object|string} track - 歌曲对象或歌手名称字符串
     * @returns {string} 歌手名称
     */
    function getArtistNames(track) {
        if (!track) return '';
        // 如果是字符串直接返回
        if (typeof track.artists === 'string') {
            return track.artists;
        }
        if (typeof track === 'string') {
            return track;
        }
        // 如果有ar数组，映射获取名称
        if (Array.isArray(track.ar)) {
            return track.ar.map(a => a.name).join(', ');
        }
        // 如果有artist字段
        if (track.artist) {
            return track.artist;
        }
        return '';
    }

    // 检查链接是否为有效的网易云音乐链接
    function checkValidLink(link) {
        if (link.indexOf("http") === -1 ||
            (link.indexOf("music.163.com") === -1 && link.indexOf("163cn.tv") === -1)) {
            return false;
        }
        return true;
    }

    // 从文本中提取纯数字ID
    function extractAndCheckId(text) {
        if (!text) return '';
        
        var link = extractLinks(text);
        if (checkValidLink(link)) {
            // 从链接中提取ID参数 - 支持多种格式
            // 1. 普通参数格式: id=123456
            var idMatch = link.match(/[?&]id=(\d+)/);
            if (idMatch && idMatch[1]) {
                return idMatch[1]; // 返回纯数字ID
            }
            
            // 2. 编码参数格式: id%3D123456 (即 id= 被编码为 %3D)
            // 更精确的正则表达式，避免捕获额外字符
            idMatch = link.match(/[?&]id%3D(\d+)(?:%26|&|$)/i);
            if (idMatch && idMatch[1]) {
                return idMatch[1]; // 返回纯数字ID
            }
            
            // 通用格式：支持 = 或 %3D
            idMatch = link.match(/[?&]id(?:%3D|=)(\d+)(?:%26|&|$)/i);
            if (idMatch && idMatch[1]) {
                return idMatch[1]; // 返回纯数字ID
            }
            
            // 3. 路径格式: /playlist/123456 或 /song/123456
            idMatch = link.match(/\/(?:playlist|song)\/(\d+)/i);
            if (idMatch && idMatch[1]) {
                return idMatch[1]; // 返回纯数字ID
            }
            
            // 4. 从原始文本中提取所有数字，取第一个6位以上的数字（通常是ID）
            var allNumbers = text.match(/\d{6,}/g);
            if (allNumbers && allNumbers.length > 0) {
                return allNumbers[0];
            }
            
            // 5. 从原始文本中提取所有数字
            var idRegex = /\b\d+\b/g;
            var ids = text.match(idRegex);
            if (ids && ids.length > 0) {
                return ids[0];
            }
            return '';
        } else {
            var idRegex = /\b\d+\b/g;
            var ids = text.match(idRegex);
            if (ids && ids.length > 0) {
                return ids[0];
            }
            return '';
        }
    }

    async function parsePlaylist(playlistInput, quality) {
        if (!playlistInput) {
            playlistInput = $('#playlist_id').val().trim();
            if (!playlistInput) {
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
        }

        // 保存当前选择的音质
        currentQuality = quality || $('#playlist_level').val() || 'standard';

        // 显示加载提示
        Swal.fire({
            title: '正在解析歌单',
            html: '请稍候...',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            // 提取并验证歌单ID（支持完整URL或纯ID）
            const validId = extractAndCheckId(playlistInput);
            if (!validId) {
                throw new Error('请输入有效的歌单ID或链接');
            }
            
            // 使用新的安全API请求方法调用歌单解析API
            const response = await ApiSecurity.secureApiRequest('./api/api.php', {
                action: 'playlist',
                id: validId
            }, { useEncryption: true });

            // 关闭加载提示
            Swal.close();

            if (response.status === 200 && response.data && response.data.playlist) {
                currentPlaylist = response.data.playlist;
                displayPlaylistInfo(response.data.playlist);
            } else {
                throw new Error(response.error || '歌单解析失败');
            }
        } catch (error) {
            console.error('歌单解析错误:', error);
            Swal.fire({
                icon: 'error',
                title: '解析失败',
                text: error.message || '歌单解析失败，请检查ID或链接是否正确',
                confirmButtonText: '确定'
            });
        }
    }

    /**
     * 显示歌单信息
     * @function displayPlaylistInfo
     * @param {Object} playlist - 歌单数据
     */
    function displayPlaylistInfo(playlist) {
        // 显示歌单基本信息
        $('#playlist-cover').attr('src', playlist.coverImgUrl);
        $('#playlist-name').text(playlist.name);

        // 处理creator字段 - 可能是对象或字符串
        const creatorName = typeof playlist.creator === 'string'
            ? playlist.creator
            : (playlist.creator.nickname || playlist.creator.name || '');
        $('#playlist-creator').text(creatorName);

        $('#playlist-track-count').text(playlist.trackCount);

        // 格式化创建时间
        if (playlist.createTime) {
            const createDate = new Date(playlist.createTime);
            if (!isNaN(createDate.getTime())) {
                $('#playlist-create-time').text(createDate.toLocaleDateString());
            } else {
                $('#playlist-create-time').text('未知');
            }
        } else {
            $('#playlist-create-time').text('未知');
        }

        // 清空并填充歌曲列表
        const $tracksList = $('#playlist-tracks-list');
        $tracksList.empty();

        if (playlist.tracks && playlist.tracks.length > 0) {
            // 显示所有歌曲，滚动条会自动处理超过容器高度的内容
            playlist.tracks.forEach((track, index) => {
                // 获取歌手名称 - 可能是字符串或数组
                let artistNames;
                if (typeof track.artists === 'string') {
                    artistNames = track.artists;
                } else if (Array.isArray(track.ar)) {
                    artistNames = getArtistNames(track);
                } else {
                    artistNames = track.artists || '';
                }

                // 获取封面图片 - 可能是track.al.picUrl或track.picUrl
                let picUrl;
                if (track.al && track.al.picUrl) {
                    picUrl = track.al.picUrl;
                } else {
                    picUrl = track.picUrl || '';
                }

                // 创建歌曲卡片
                const $card = $(`
                    <div class="track-card">
                    <div class="track-number">${index + 1}</div>
                    <div class="track-image">
                        <img src="${picUrl}?param=100y100" alt="${track.name}" referrerpolicy="no-referrer">
                    </div>
                    <div class="track-info">
                        <div class="track-name">${track.name}</div>
                        <div class="track-artist">${artistNames}</div>
                    </div>
                    <div class="track-actions">
                        <button class="btn btn-sm btn-outline-primary rounded-circle play-song" data-id="${track.id}" title="播放">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success rounded-circle download-song" data-id="${track.id}" title="下载">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </div>
                `);

                // 绑定播放按钮事件
                $card.find('.play-song').on('click', function () {
                    const songId = $(this).data('id');
                    playSong(songId);
                });

                // 绑定下载按钮事件
                $card.find('.download-song').on('click', function () {
                    const songId = $(this).data('id');
                    downloadSong(songId);
                });

                $tracksList.append($card);
            });

            // 添加歌单总数信息
            if (playlist.tracks.length > 20) {
                $tracksList.append(`
                    <div class="text-center py-2 text-muted small">
                        <i class="fas fa-info-circle me-1"></i>共 ${playlist.tracks.length} 首歌曲，可滚动查看全部
                    </div>
                `);
            }
        } else {
            $tracksList.html(`
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-info-circle me-2"></i>歌单中没有歌曲
                </div>
            `);
        }

        // 显示歌单结果区域
        $('#playlist-result').removeClass('d-none');

        // 滚动到结果区域
        $('html, body').animate({
            scrollTop: $('#playlist-result').offset().top - 20
        }, 500);
    }

    /**
     * 播放歌曲
     * @function playSong
     * @param {string} songId - 歌曲ID
     * @async
     */
    async function playSong(songId) {
        try {
            // 显示加载提示
            Swal.fire({
                title: '正在解析歌曲',
                html: '请稍候...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // 调用音乐解析API - 确保songId是字符串类型
            const songData = await MusicParser.parseSongById(String(songId), currentQuality);

            // 关闭加载提示
            Swal.close();

            // 更新UI并播放歌曲
            MusicParser.updateUIWithParsedSong(songData, HistoryManager.add);

            // 滚动到播放器区域
            $('html, body').animate({
                scrollTop: $('#song-info').offset().top - 20
            }, 500);
        } catch (error) {
            console.error('播放歌曲错误:', error);
            Swal.fire({
                icon: 'error',
                title: '播放失败',
                text: error.message || '歌曲解析失败，请稍后再试',
                confirmButtonText: '确定'
            });
        }
    }

    /**
     * 下载单首歌曲
     * @function downloadSong
     * @param {string} songId - 歌曲ID
     * @async
     */
    async function downloadSong(songId) {
        try {
            // 添加下载中的懒加载图标
            const $downloadBtn = $(`.download-song[data-id="${songId}"]`);
            const originalContent = $downloadBtn.html();
            $downloadBtn.html('<i class="fas fa-spinner fa-spin"></i>');
            $downloadBtn.prop('disabled', true);

            // 显示加载提示
            Swal.fire({
                title: '正在解析歌曲',
                html: '准备下载...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // 调用音乐解析API - 确保songId是字符串类型
            const songData = await MusicParser.parseSongById(String(songId), currentQuality);

            // 关闭加载提示
            Swal.close();

            // 获取文件扩展名
            let fileExt = getFileExtension(songData.url) || 'mp3';
            // 如果是mp4则改为m4a
            if (fileExt.toLowerCase() === 'mp4') {
                fileExt = 'm4a';
            }

            // 准备文件名 
            const fileNameWithoutExt = sanitizeFilename(formatMusicFilename(songData.name, songData.ar_name));
            // 完整文件名（用于显示）
            const fileName = `${fileNameWithoutExt}.${fileExt}`;

            // 创建进度条UI元素
            const $progressContainer = $('<div class="progress mt-3"></div>');
            const $progressBar = $('<div class="progress-bar" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>');
            const $progressText = $progressBar;
            const $status = $('<div class="small text-muted mt-1">准备下载...</div>');

            // 添加进度条到页面
            const $downloadStatus = $('<div class="download-status mt-2"></div>');
            $downloadStatus.append($progressContainer.append($progressBar));
            $downloadStatus.append($status);

            // 添加速度信息元素
            const $speedInfo = $('<div id="speed-info" class="small text-muted mt-1"></div>');
            $downloadStatus.append($speedInfo);

            // 显示进度条
            const swalInstance = Swal.fire({
                title: `下载中 - ${songData.name}`,
                html: $downloadStatus[0].outerHTML,
                allowOutsideClick: false,
                showConfirmButton: false,
                didOpen: (popup) => {
                    // 在弹窗打开后获取实际DOM元素的引用
                    window.$currentProgressBar = $(popup).find('.progress-bar');
                    window.$currentStatus = $(popup).find('.small.text-muted').first();
                    window.$currentSpeedInfo = $(popup).find('#speed-info');

                    // 初始状态
                    window.$currentStatus.text('开始下载文件...');
                }
            });

            // 更新进度条显示函数 - 使用全局引用
            function updateProgress(percent, statusText) {
                if (window.$currentProgressBar && window.$currentProgressBar.length) {
                    window.$currentProgressBar.css('width', `${percent}%`).attr('aria-valuenow', percent);
                    window.$currentProgressBar.text(`${percent}%`);
                }

                if (statusText && window.$currentStatus && window.$currentStatus.length) {
                    window.$currentStatus.text(statusText);
                }
            }

            // 更新下载速度显示函数 - 使用全局引用
            function updateSpeedInfo(speed, timeRemaining) {
                if (window.$currentSpeedInfo && window.$currentSpeedInfo.length) {
                    window.$currentSpeedInfo.html(`<i class="fas fa-tachometer-alt me-1"></i>速度: ${speed}${timeRemaining ? ` <i class="fas fa-clock ms-2 me-1"></i>剩余: ${timeRemaining}` : ''}`);
                }
            }

            // 直接下载音频文件，不打包
            updateProgress(5, '开始下载文件...');

            // 添加下载超时处理
            const downloadTimeout = setTimeout(() => {
                console.warn('下载似乎没有进度更新，可能是服务器不支持分片下载');
                updateProgress(10, '下载中，请耐心等待...');
                // 每10秒更新一次进度，防止用户认为下载卡住
                let fakeProgress = 15;
                const fakeProgressInterval = setInterval(() => {
                    if (fakeProgress < 90) {
                        fakeProgress += 5;
                        updateProgress(fakeProgress, '下载中，请耐心等待...');
                    } else {
                        clearInterval(fakeProgressInterval);
                    }
                }, 10000);

                // 保存引用以便在下载完成时清除
                window.currentFakeProgressInterval = fakeProgressInterval;
            }, 15000); // 15秒没有进度更新则触发

            try {
                const audioBlob = await MusicDownloader.downloadWithChunks(
                    songData.url,
                    1024 * 1024,
                    5,
                    (progress) => {
                        // 清除超时处理
                        if (downloadTimeout) clearTimeout(downloadTimeout);
                        if (window.currentFakeProgressInterval) {
                            clearInterval(window.currentFakeProgressInterval);
                            window.currentFakeProgressInterval = null;
                        }
                        updateProgress(progress, '下载文件中...');
                    },
                    (speed, timeRemaining) => {
                        updateSpeedInfo(speed, timeRemaining);
                    }
                );

                // 清除超时处理
                clearTimeout(downloadTimeout);
                if (window.currentFakeProgressInterval) {
                    clearInterval(window.currentFakeProgressInterval);
                    window.currentFakeProgressInterval = null;
                }

                // 下载完成，保存文件
                updateProgress(100, '下载完成！');
                // 创建具有正确MIME类型的Blob
                const mimeType = getMimeTypeFromExtension(fileExt);

                // 添加元数据
                updateProgress(95, '正在写入元数据...');
                
                // 合并歌词
                const mergedLyrics = mergeLyricsWithTranslation(songData.lyric, songData.tlyric);

                // 创建一个新的ArrayBuffer来存储音频数据和元数据
                const audioArrayBuffer = await audioBlob.arrayBuffer();

                // 检查是否启用元数据写入
                const enableMetadata = typeof settingsManager !== 'undefined' ? 
                    settingsManager.getSetting('enableMetadata') : true;

                // 根据文件类型处理元数据
                if (fileExt.toLowerCase() === 'flac') {
                    if (enableMetadata) {
                        try {
                            // 使用 FLACMetadata 库写入元数据
                            let coverBlob = null;
                            if (songData.pic) {
                                try {
                                    // 获取封面图片
                                    const coverResponse = await fetch(songData.pic, {
                                        headers: {
                                            Referer: 'http://music.163.com/'
                                        }
                                    });
                                    coverBlob = await coverResponse.blob();
                                } catch (coverError) {
                                    console.error('获取封面图片失败:', coverError);
                                }
                            }

                            const blobWithMetadata = await FLACMetadata.addMetadata(audioArrayBuffer, {
                                title: songData.name,
                                artist: songData.ar_name,
                                album: songData.al_name,
                                lyrics: mergedLyrics, // 使用合并后的歌词
                                cover: coverBlob
                            });

                            saveAs(blobWithMetadata, fileName);
                        } catch (metadataError) {
                            console.error('写入FLAC元数据失败:', metadataError);
                            // 如果写入元数据失败，仍然保存原始文件
                            const blobWithMime = new Blob([audioBlob], { type: mimeType });
                            saveAs(blobWithMime, fileName);
                        }
                    } else {
                        // 不写入元数据，直接保存原始文件
                        const blobWithMime = new Blob([audioBlob], { type: mimeType });
                        saveAs(blobWithMime, fileName);
                    }
                } else if (fileExt.toLowerCase() === 'mp3' || fileExt.toLowerCase() === 'm4a') {
                    if (enableMetadata) {
                        try {
                            // 使用ID3Writer库写入元数据
                            const writer = new ID3Writer(audioArrayBuffer);
                            writer.setFrame('TIT2', songData.name) // 歌曲名
                                .setFrame('TPE1', [songData.ar_name]) // 歌手
                                .setFrame('TALB', songData.al_name) // 专辑
                                .setFrame('USLT', { description: '', lyrics: mergedLyrics }) // 使用合并后的歌词

                                // 如果有封面图片，添加封面
                                if (songData.pic) {
                                    try {
                                        // 获取封面图片
                                        const coverResponse = await fetch(songData.pic, {
                                            headers: {
                                                Referer: 'http://music.163.com/'
                                            }
                                        });
                                        const coverArrayBuffer = await coverResponse.arrayBuffer();
                                        writer.setFrame('APIC', {
                                            type: 3, // 封面图片
                                            data: coverArrayBuffer,
                                            description: 'Cover'
                                        });
                                    } catch (coverError) {
                                        console.error('获取封面图片失败:', coverError);
                                    }
                                }

                            writer.addTag();
                            const taggedArrayBuffer = writer.arrayBuffer;
                            const blobWithMime = new Blob([taggedArrayBuffer], { type: mimeType });
                            saveAs(blobWithMime, fileName);
                        } catch (metadataError) {
                            console.error('写入元数据失败:', metadataError);
                            // 如果写入元数据失败，仍然保存原始文件
                            const blobWithMime = new Blob([audioBlob], { type: mimeType });
                            saveAs(blobWithMime, fileName);
                        }
                    } else {
                        // 不写入元数据，直接保存原始文件
                        const blobWithMime = new Blob([audioBlob], { type: mimeType });
                        saveAs(blobWithMime, fileName);
                    }
                } else {
                    // 对于不支持的格式，直接保存原始文件
                    const blobWithMime = new Blob([audioBlob], { type: mimeType });
                    saveAs(blobWithMime, fileName);
                }

                // 下载完成提示
                setTimeout(() => {
                    Swal.fire({
                        icon: 'success',
                        title: '下载完成',
                        text: `歌曲《${songData.name}》已成功下载`,
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                }, 1000);

            } catch (downloadError) {
                console.error('下载过程出错:', downloadError);

                // 清除超时处理
                clearTimeout(downloadTimeout);
                if (window.currentFakeProgressInterval) {
                    clearInterval(window.currentFakeProgressInterval);
                    window.currentFakeProgressInterval = null;
                }

                // 尝试使用普通XHR下载作为备选方案
                updateProgress(15, '正在尝试备用下载方式...');

                try {
                    const xhr = new XMLHttpRequest();
                    xhr.open('GET', songData.url);
                    xhr.responseType = 'blob';

                    xhr.onprogress = (event) => {
                        if (event.lengthComputable) {
                            const progress = Math.floor((event.loaded / event.total) * 100);
                            updateProgress(progress, '下载文件中...');
                        } else {
                            // 如果无法计算进度，至少更新状态文本
                            updateProgress(30, `已下载 ${(event.loaded / (1024 * 1024)).toFixed(2)} MB...`);
                        }
                    };

                    xhr.onload = () => {
                        if (xhr.status === 200) {
                            updateProgress(100, '下载完成！');
                            saveAs(xhr.response, fileName);

                            // 下载完成提示
                            Swal.fire({
                                icon: 'success',
                                title: '下载完成',
                                text: `歌曲《${songData.name}》已成功下载`,
                                toast: true,
                                position: 'top-end',
                                showConfirmButton: false,
                                timer: 3000,
                                timerProgressBar: true
                            });
                        } else {
                            throw new Error(`下载失败: ${xhr.statusText || '服务器错误'}`);
                        }
                    };

                    xhr.onerror = () => {
                        throw new Error('网络错误');
                    };

                    xhr.send();
                } catch (fallbackError) {
                    console.error('备用下载也失败:', fallbackError);
                    throw fallbackError; // 继续向外抛出错误
                }
            }

            // 恢复按钮原始状态
            $downloadBtn.html(originalContent);
            $downloadBtn.prop('disabled', false);

        } catch (error) {
            console.error('下载歌曲错误:', error);

            // 恢复按钮原始状态（如果存在）
            const $downloadBtn = $(`.download-song[data-id="${songId}"]`);
            if ($downloadBtn.length) {
                $downloadBtn.html('<i class="fas fa-download"></i>');
                $downloadBtn.prop('disabled', false);
            }

            Swal.fire({
                icon: 'error',
                title: '下载失败',
                text: error.message || '歌曲解析失败，请稍后再试',
                confirmButtonText: '确定'
            });
        }
    }

    /**
     * 下载所有歌曲
     * @function downloadAllSongs
     * @async
     */
    async function downloadAllSongs() {
        if (!currentPlaylist || !currentPlaylist.tracks || currentPlaylist.tracks.length === 0) {
            Swal.fire({
                icon: 'warning',
                title: '没有可下载的歌曲',
                text: '当前歌单中没有歌曲可供下载',
                confirmButtonText: '确定'
            });
            return;
        }

        // 如果已经在下载中，则不重复下载
        if (isBatchDownloading) {
            Swal.fire({
                icon: 'info',
                title: '下载进行中',
                text: '批量下载任务正在进行，请等待完成',
                confirmButtonText: '确定'
            });
            return;
        }

        // 确认是否下载
        const result = await Swal.fire({
            icon: 'question',
            title: '批量下载确认',
            html: `确定要下载歌单中的 <b>${currentPlaylist.tracks.length}</b> 首歌曲吗？<br>这可能需要一些时间。`,
            showCancelButton: true,
            confirmButtonText: '确定下载',
            cancelButtonText: '取消'
        });

        if (!result.isConfirmed) {
            return;
        }

        // 准备下载队列
        downloadQueue = [...currentPlaylist.tracks];
        isBatchDownloading = true;

        // 显示批量下载进度区域
        $('#batch-download-progress').removeClass('d-none');
        $('#batch-progress-bar').css('width', '0%').attr('aria-valuenow', 0).text('0%');
        $('#batch-status').text('准备下载...');
        $('#batch-details').empty();

        // 滚动到进度区域
        $('html, body').animate({
            scrollTop: $('#batch-download-progress').offset().top - 20
        }, 500);

        // 开始下载队列
        await processDownloadQueue();
    }

    /**
     * 处理下载队列
     * @function processDownloadQueue
     * @async
     */
    async function processDownloadQueue() {
        const totalSongs = currentPlaylist.tracks.length;
        const completedSongs = totalSongs - downloadQueue.length;
        const progressPercent = Math.round((completedSongs / totalSongs) * 100);

        // 更新进度条
        $('#batch-progress-bar').css('width', `${progressPercent}%`).attr('aria-valuenow', progressPercent).text(`${progressPercent}%`);
        $('#batch-status').text(`已完成 ${completedSongs}/${totalSongs} 首歌曲下载`);

        // 如果队列为空，表示下载完成
        if (downloadQueue.length === 0) {
            isBatchDownloading = false;
            $('#batch-status').text(`全部下载完成！共 ${totalSongs} 首歌曲`);

            Swal.fire({
                icon: 'success',
                title: '批量下载完成',
                text: `成功下载 ${totalSongs} 首歌曲`,
                confirmButtonText: '确定'
            });

            // 使用requestAnimationFrame延迟隐藏进度条，提高性能
            requestAnimationFrame(() => {
                setTimeout(() => {
                    $('#batch-download-progress').addClass('d-none');
                    $('#batch-details').empty(); // 清空下载详情
                    console.info('批量下载流程结束，UI已重置');
                }, 3000); // 延长时间让用户看到完成状态
            });

            return;
        }

        // 取出队列中的第一首歌
        const song = downloadQueue.shift();

        try {
            // 更新状态
            $('#batch-status').text(`正在下载 (${completedSongs + 1}/${totalSongs}): ${song.name}`);
            $('#batch-details').prepend(`<div id="current-download-item"><i class="fas fa-spinner fa-spin me-2"></i>${song.name} - ${getArtistNames(song)}</div>`);

            // 调用音乐解析API - 确保song.id是字符串类型
            const songData = await MusicParser.parseSongById(String(song.id), currentQuality);

            // 获取文件扩展名
            let fileExt = getFileExtension(songData.url) || 'mp3';
            // 如果是mp4则改为m4a
            if (fileExt.toLowerCase() === 'mp4') {
                fileExt = 'm4a';
            }

            // 准备文件名
            const fileName = sanitizeFilename(`${formatMusicFilename(songData.name, songData.ar_name)}.${fileExt}`);

            // 使用普通下载方式替代分片下载
            const response = await fetch(songData.url, {
                headers: {
                    Referer: 'http://music.163.com/'
                }
            });
            if (!response.ok) {
                throw new Error(`下载失败: ${response.status} ${response.statusText}`);
            }
            const audioBlob = await response.blob();



            // 创建具有正确MIME类型的Blob
            const mimeType = getMimeTypeFromExtension(fileExt);

            // 添加元数据
            $('#current-download-item').html(`<i class="fas fa-cog fa-spin me-2"></i>${song.name} - ${getArtistNames(song)} (写入元数据中...)`);
            
            // 合并歌词
            const mergedLyrics = mergeLyricsWithTranslation(songData.lyric, songData.tlyric);

            // 创建一个新的ArrayBuffer来存储音频数据和元数据
            const audioArrayBuffer = await audioBlob.arrayBuffer();

            // 根据文件类型处理元数据
            if (fileExt.toLowerCase() === 'flac') {
                try {
                    // 使用 FLACMetadata 库写入元数据
                    let coverBlob = null;
                    if (songData.pic) {
                        try {
                            // 获取封面图片
                            const coverResponse = await fetch(songData.pic, {
                                headers: {
                                    Referer: 'http://music.163.com/'
                                }
                            });
                            coverBlob = await coverResponse.blob();
                        } catch (coverError) {
                            console.error('获取封面图片失败:', coverError);
                        }
                    }

                    const blobWithMetadata = await FLACMetadata.addMetadata(audioArrayBuffer, {
                        title: songData.name,
                        artist: songData.ar_name,
                        album: songData.al_name,
                        lyrics: mergedLyrics, // 使用合并后的歌词
                        cover: coverBlob
                    });

                    saveAs(blobWithMetadata, fileName);
                } catch (metadataError) {
                    console.error('写入FLAC元数据失败:', metadataError);
                    // 如果写入元数据失败，仍然保存原始文件
                    const blobWithMime = new Blob([audioBlob], { type: mimeType });
                    saveAs(blobWithMime, fileName);
                }
            } else if (fileExt.toLowerCase() === 'mp3' || fileExt.toLowerCase() === 'm4a') {
                try {
                    // 使用ID3Writer库写入元数据
                    const writer = new ID3Writer(audioArrayBuffer);
                    writer.setFrame('TIT2', songData.name) // 歌曲名
                        .setFrame('TPE1', [songData.ar_name]) // 歌手
                        .setFrame('TALB', songData.al_name) // 专辑
                        .setFrame('USLT', { description: '', lyrics: mergedLyrics }) // 使用合并后的歌词

                    // 如果有封面图片，添加封面
                    if (songData.pic) {
                        try {
                            // 获取封面图片
                            const coverResponse = await fetch(songData.pic, {
                                headers: {
                                    Referer: 'http://music.163.com/'
                                }
                            });
                            const coverArrayBuffer = await coverResponse.arrayBuffer();
                            writer.setFrame('APIC', {
                                type: 3, // 封面图片
                                data: coverArrayBuffer,
                                description: 'Cover'
                            });
                        } catch (coverError) {
                            console.error('获取封面图片失败:', coverError);
                        }
                    }

                    writer.addTag();
                    const taggedArrayBuffer = writer.arrayBuffer;
                    const blobWithMime = new Blob([taggedArrayBuffer], { type: mimeType });
                    saveAs(blobWithMime, fileName);
                } catch (metadataError) {
                    console.error('写入元数据失败:', metadataError);
                    // 如果写入元数据失败，仍然保存原始文件
                    const blobWithMime = new Blob([audioBlob], { type: mimeType });
                    saveAs(blobWithMime, fileName);
                }
            } else {
                // 对于不支持的格式，直接保存原始文件
                const blobWithMime = new Blob([audioBlob], { type: mimeType });
                saveAs(blobWithMime, fileName);
            }

            // 更新下载状态
            $('#current-download-item').html(`<i class="fas fa-check-circle text-success me-2"></i>${song.name} - ${getArtistNames(song)}`);
            $('#current-download-item').removeAttr('id');

            // 延迟一段时间再下载下一首，避免请求过于频繁
            await new Promise(resolve => setTimeout(resolve, 1500));

            // 递归处理下一首
            await processDownloadQueue();
        } catch (error) {
            console.error('批量下载错误:', error, song);

            // 更新失败状态
            $('#current-download-item').html(`<i class="fas fa-times-circle text-danger me-2"></i>${song.name} - ${getArtistNames(song)} (失败: ${error.message || '未知错误'})`);
            $('#current-download-item').removeAttr('id');

            // 继续处理下一首
            await processDownloadQueue();
        }
    }

    /**
     * 检查是否正在进行批量下载
     * @function isDownloading
     * @returns {boolean} 是否正在下载
     */
    function isDownloading() {
        return isBatchDownloading;
    }

    // 返回公共API
    return {
        init: init,
        parsePlaylist: parsePlaylist,
        isDownloading: isDownloading
    };
})();

// 确保DOM加载完成后初始化
$(document).ready(function () {
    // 初始化歌单解析模块
    PlaylistParser.init();
});

/**
 * 根据文件扩展名获取MIME类型
 * @function getMimeTypeFromExtension
 * @param {string} extension - 文件扩展名
 * @returns {string} MIME类型
 */
function getMimeTypeFromExtension(extension) {
    const ext = extension.toLowerCase();
    const mimeTypes = {
        'mp3': 'audio/mpeg',
        'flac': 'audio/flac',
        'wav': 'audio/wav',
        'm4a': 'audio/m4a',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'wma': 'audio/x-ms-wma',
        'alac': 'audio/alac'
    };

    return mimeTypes[ext] || 'audio/mpeg'; // 默认返回audio/mpeg
}

    /**
     * 合并原文歌词和翻译歌词
     * @param {string} originalLyric - 原文歌词
     * @param {string} translatedLyric - 翻译歌词
     * @returns {string} 合并后的歌词
     */
    function mergeLyricsWithTranslation(originalLyric, translatedLyric) {
        if (!originalLyric) return '';
        if (!translatedLyric) return originalLyric;
        
        // 解析原文歌词
        const originalLines = originalLyric.split('\n');
        const translatedLines = translatedLyric.split('\n');
        
        // 创建时间戳到翻译的映射，支持多种时间戳格式
        const translationMap = new Map();
        translatedLines.forEach(line => {
            // 支持 [mm:ss.xx] 和 [mm:ss.xxx] 格式
            const match = line.match(/\[(\d{2}:\d{2}\.\d{2,3})\](.*)/);
            if (match) {
                const timestamp = match[1];
                const text = match[2].trim();
                // 清理翻译文本中的斜杠和其他特殊字符
                const cleanText = text.replace(/^\/+|\/+$/g, '').trim();
                if (cleanText) {
                    translationMap.set(timestamp, cleanText);
                }
            }
        });
        
        // 合并歌词
        const mergedLines = [];
        originalLines.forEach(line => {
            // 支持多种时间戳格式
            const match = line.match(/\[(\d{2}:\d{2}\.\d{2,3})\](.*)/);
            if (match) {
                const timestamp = match[1];
                const originalText = match[2].trim();
                const translatedText = translationMap.get(timestamp);
                
                // 添加原文
                if (originalText) {
                    mergedLines.push(`[${timestamp}]${originalText}`);
                }
                
                // 如果有翻译，添加翻译
                if (translatedText) {
                    mergedLines.push(`[${timestamp}]${translatedText}`);
                }
            } else {
                // 非时间戳行（如作词作曲信息）直接添加
                if (line.trim()) {
                    mergedLines.push(line);
                }
            }
        });
        
        return mergedLines.join('\n');
    }


