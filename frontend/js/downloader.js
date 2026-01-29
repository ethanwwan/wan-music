/**
 * 网易云音乐无损解析 - 下载功能模块
 * @author kanxizai
 * @version 1.5
 */

// 定义下载模块
const MusicDownloader = (function() {
    // 日志系统配置
    const logger = {
        enabled: false, // 默认关闭日志
        prefix: '[MusicDownloader]',
        
        /**
         * 设置日志开关状态
         * @param {boolean} status - 是否启用日志
         */
        setEnabled: function(status) {
            this.enabled = !!status;
            this.info(`日志系统${this.enabled ? '已启用' : '已禁用'}`);
            return this.enabled;
        },
        
        /**
         * 输出信息日志
         * @param {string} message - 日志信息
         * @param {any} data - 附加数据（可选）
         */
        info: function(message, data) {
            if (!this.enabled) return;
            if (data !== undefined) {
                console.log(`${this.prefix} [INFO] ${message}`, data);
            } else {
                console.log(`${this.prefix} [INFO] ${message}`);
            }
        },
        
        /**
         * 输出调试日志
         * @param {string} message - 日志信息
         * @param {any} data - 附加数据（可选）
         */
        debug: function(message, data) {
            if (!this.enabled) return;
            if (data !== undefined) {
                console.debug(`${this.prefix} [DEBUG] ${message}`, data);
            } else {
                console.debug(`${this.prefix} [DEBUG] ${message}`);
            }
        },
        
        /**
         * 输出警告日志
         * @param {string} message - 日志信息
         * @param {any} data - 附加数据（可选）
         */
        warn: function(message, data) {
            if (!this.enabled) return;
            if (data !== undefined) {
                console.warn(`${this.prefix} [WARN] ${message}`, data);
            } else {
                console.warn(`${this.prefix} [WARN] ${message}`);
            }
        },
        
        /**
         * 输出错误日志
         * @param {string} message - 日志信息
         * @param {any} data - 附加数据（可选）
         */
        error: function(message, data) {
            if (!this.enabled) return;
            if (data !== undefined) {
                console.error(`${this.prefix} [ERROR] ${message}`, data);
            } else {
                console.error(`${this.prefix} [ERROR] ${message}`);
            }
        }
    };
    // 下载状态管理对象
    const downloadState = {
        isDownloading: false,
        currentTask: null,
        
        /**
         * 设置下载状态
         * @param {boolean} status - 是否正在下载
         * @param {Object} task - 当前下载任务信息
         */
        setDownloading: function(status, task = null) {
            this.isDownloading = !!status;
            this.currentTask = task;
            logger.info(`下载状态已更新: ${this.isDownloading ? '下载中' : '空闲'}`);
            if (task) {
                logger.debug('当前任务:', task);
            }
            return this.isDownloading;
        },
        
        /**
         * 获取当前下载状态
         * @returns {boolean} 是否正在下载
         */
        isActive: function() {
            return this.isDownloading;
        },
        
        /**
         * 获取当前下载任务信息
         * @returns {Object|null} 当前下载任务信息
         */
        getCurrentTask: function() {
            return this.currentTask;
        }
    };
    
    /**
     * 计算最优下载参数
     * @param {number} fileSize - 文件大小（字节）
     * @returns {Object} - 返回最优的切片大小和并发数
     */
    const calculateOptimalDownloadParams = (fileSize) => {
        logger.info(`计算最优下载参数，文件大小: ${(fileSize / (1024 * 1024)).toFixed(2)} MB`);
        
        // 基础配置
        let chunkSize = 1024 * 1024; // 默认1MB
        let concurrency = 5; // 默认5个并发
        
        // 根据文件大小动态调整参数
        if (fileSize <= 5 * 1024 * 1024) {
            // 小于5MB的文件
            chunkSize = 512 * 1024; // 512KB
            concurrency = 3;
            logger.debug(`小文件优化: 切片=${(chunkSize/1024).toFixed(0)}KB, 并发=${concurrency}`);
        } else if (fileSize <= 20 * 1024 * 1024) {
            // 5MB-20MB的文件
            chunkSize = 1024 * 1024; // 1MB
            concurrency = 5;
            logger.debug(`中等文件优化: 切片=${(chunkSize/1024/1024).toFixed(1)}MB, 并发=${concurrency}`);
        } else if (fileSize <= 100 * 1024 * 1024) {
            // 20MB-100MB的文件
            chunkSize = 2 * 1024 * 1024; // 2MB
            concurrency = 8;
            logger.debug(`较大文件优化: 切片=${(chunkSize/1024/1024).toFixed(1)}MB, 并发=${concurrency}`);
        } else if (fileSize <= 500 * 1024 * 1024) {
            // 100MB-500MB的文件
            chunkSize = 4 * 1024 * 1024; // 4MB
            concurrency = 20;
            logger.debug(`大文件优化: 切片=${(chunkSize/1024/1024).toFixed(1)}MB, 并发=${concurrency}`);
        } else {
            // 超过500MB的文件
            chunkSize = 8 * 1024 * 1024; // 8MB
            concurrency = 12;
            logger.debug(`超大文件优化: 切片=${(chunkSize/1024/1024).toFixed(1)}MB, 并发=${concurrency}`);
        }
        
        logger.info(`计算完成，最优参数: 切片大小=${(chunkSize/1024/1024).toFixed(2)}MB, 并发数=${concurrency}`);
        return { chunkSize, concurrency };
    };
    
    /**
     * 分片下载函数 - 支持多线程并行下载
     * @param {string} url - 下载地址
     * @param {number} chunkSize - 分片大小（字节）
     * @param {number} concurrency - 并发数
     * @param {function} onProgress - 进度回调
     * @param {function} onSpeed - 速度回调
     * @returns {Promise<Blob>} - 返回完整的文件Blob
     */
    const downloadWithChunks = async (url, chunkSize = 1024 * 1024, concurrency = 5, onProgress, onSpeed) => {
        logger.info(`开始分片下载: ${url}`, { chunkSize, concurrency });
        
        return new Promise(async (resolve, reject) => {
            try {
                // 获取文件大小
                logger.debug(`发送HEAD请求获取文件大小`);
                const headResponse = await fetch(url, { 
                    method: 'HEAD',
                    headers: {
                        Referer: 'http://music.163.com/'
                    }
                });
                if (!headResponse.ok) {
                    logger.error(`获取文件信息失败: ${headResponse.statusText}`);
                    throw new Error(`获取文件信息失败: ${headResponse.statusText}`);
                }
                
                const contentLength = parseInt(headResponse.headers.get('content-length') || '0');
                logger.info(`文件大小: ${contentLength} 字节 (${(contentLength / (1024 * 1024)).toFixed(2)} MB)`);
                
                if (!contentLength) {
                    logger.warn(`无法获取文件大小，回退到普通下载模式`);
                    // 如果无法获取文件大小，回退到普通下载
                    return downloadWithProgress(url, onProgress, onSpeed).then(resolve).catch(reject);
                }
                
                // 计算最优下载参数
                const optimalParams = calculateOptimalDownloadParams(contentLength);
                chunkSize = optimalParams.chunkSize;
                concurrency = optimalParams.concurrency;
                logger.info(`使用最优下载参数: 切片大小=${(chunkSize/1024/1024).toFixed(2)}MB, 并发数=${concurrency}`);
                
                // 计算分片数量
                const chunks = Math.ceil(contentLength / chunkSize);
                logger.info(`分片数量: ${chunks}, 每片大小: ${(chunkSize / 1024).toFixed(2)} KB`);
                
                const chunkArray = new Array(chunks).fill().map((_, index) => {
                    const start = index * chunkSize;
                    const end = Math.min(start + chunkSize - 1, contentLength - 1);
                    return { index, start, end, downloaded: false, data: null };
                });
                
                // 下载状态追踪
                let downloadedSize = 0;
                let startTime = Date.now();
                let lastUpdate = startTime;
                let lastDownloadedSize = 0;
                
                // 速度计算函数
                const calculateSpeed = () => {
                    const now = Date.now();
                    const timeElapsed = (now - lastUpdate) / 1000; // 转换为秒
                    if (timeElapsed > 0) {
                        const bytesDownloaded = downloadedSize - lastDownloadedSize;
                        const speed = bytesDownloaded / timeElapsed; // 字节/秒
                        
                        lastUpdate = now;
                        lastDownloadedSize = downloadedSize;
                        
                        // 格式化速度显示
                        let speedText = '';
                        if (speed >= 1024 * 1024) {
                            speedText = `${(speed / (1024 * 1024)).toFixed(2)} MB/s`;
                        } else if (speed >= 1024) {
                            speedText = `${(speed / 1024).toFixed(2)} KB/s`;
                        } else {
                            speedText = `${Math.round(speed)} B/s`;
                        }
                        
                        // 估计剩余时间
                        const remaining = contentLength - downloadedSize;
                        let timeRemaining = '';
                        if (speed > 0) {
                            const seconds = Math.ceil(remaining / speed);
                            if (seconds < 60) {
                                timeRemaining = `${seconds}秒`;
                            } else {
                                timeRemaining = `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
                            }
                        }
                        
                        logger.debug(`当前下载速度: ${speedText}, 剩余时间: ${timeRemaining}, 已下载: ${(downloadedSize / (1024 * 1024)).toFixed(2)}MB/${(contentLength / (1024 * 1024)).toFixed(2)}MB`);
                        
                        if (onSpeed) onSpeed(speedText, timeRemaining);
                        return { speed, speedText, timeRemaining };
                    }
                    return null;
                };
                
                // 进度更新函数
                const updateChunkProgress = (chunkSize) => {
                    downloadedSize += chunkSize;
                    const progress = Math.floor((downloadedSize / contentLength) * 100);
                    if (onProgress) onProgress(progress);
                    
                    // 每秒更新一次速度
                    if (Date.now() - lastUpdate >= 1000) {
                        calculateSpeed();
                    }
                };
                
                // 下载单个分片
                const downloadChunk = async (chunk) => {
                    try {
                        logger.debug(`开始下载分片 ${chunk.index}/${chunks-1}, 范围: ${chunk.start}-${chunk.end}`);
                        
                        const response = await fetch(url, {
                            headers: {
                                Range: `bytes=${chunk.start}-${chunk.end}`,
                                Referer: 'http://music.163.com/'
                            }
                        });
                        
                        if (!response.ok) {
                            logger.error(`分片 ${chunk.index} 下载失败: ${response.statusText}`);
                            throw new Error(`分片下载失败: ${response.statusText}`);
                        }
                        
                        const blob = await response.blob();
                        logger.debug(`分片 ${chunk.index} 下载完成, 大小: ${(blob.size / 1024).toFixed(2)} KB`);
                        
                        chunk.data = blob;
                        chunk.downloaded = true;
                        updateChunkProgress(blob.size);
                        return chunk;
                    } catch (error) {
                        logger.error(`分片 ${chunk.index} 下载失败:`, error);
                        throw error;
                    }
                };
                
                // 并发控制函数
                const downloadChunksWithConcurrency = async () => {
                    const pendingChunks = [...chunkArray];
                    const inProgress = new Set();
                    const completedChunks = [];
                    
                    logger.info(`开始并发下载, 并发数: ${concurrency}`);
                    
                    // 速度更新定时器
                    const speedInterval = setInterval(() => {
                        calculateSpeed();
                    }, 1000);
                    
                    while (pendingChunks.length > 0 || inProgress.size > 0) {
                        // 填充并发队列
                        while (inProgress.size < concurrency && pendingChunks.length > 0) {
                            const chunk = pendingChunks.shift();
                            const promise = downloadChunk(chunk).then(result => {
                                inProgress.delete(promise);
                                completedChunks.push(result);
                                logger.debug(`分片 ${chunk.index} 已完成, 当前进度: ${completedChunks.length}/${chunks}`);
                                return result;
                            }).catch(error => {
                                inProgress.delete(promise);
                                // 失败的分片重新加入队列
                                pendingChunks.push(chunk);
                                logger.warn(`重试分片 ${chunk.index}`);
                            });
                            
                            inProgress.add(promise);
                        }
                        
                        // 等待任意一个分片完成
                        if (inProgress.size > 0) {
                            await Promise.race(inProgress);
                        }
                    }
                    
                    clearInterval(speedInterval);
                    logger.info(`所有分片下载完成, 总分片数: ${completedChunks.length}`);
                    return completedChunks;
                };
                
                // 开始并发下载
                const completedChunks = await downloadChunksWithConcurrency();
                
                // 按顺序合并分片
                logger.info(`开始合并分片...`);
                completedChunks.sort((a, b) => a.index - b.index);
                const blobs = completedChunks.map(chunk => chunk.data);
                const finalBlob = new Blob(blobs, { type: headResponse.headers.get('content-type') || 'application/octet-stream' });
                logger.info(`分片合并完成, 最终文件大小: ${(finalBlob.size / (1024 * 1024)).toFixed(2)} MB`);
                
                resolve(finalBlob);
            } catch (error) {
                logger.error('分片下载失败:', error);
                // 尝试回退到普通下载
                try {
                    logger.warn('回退到普通下载模式');
                    const blob = await downloadWithProgress(url, onProgress, onSpeed);
                    resolve(blob);
                } catch (fallbackError) {
                    logger.error('普通下载也失败:', fallbackError);
                    reject(fallbackError);
                }
            }
        });
    };
    
    /**
     * 普通下载函数 - 带进度监控
     * @param {string} url - 下载地址
     * @param {function} onProgress - 进度回调
     * @param {function} onSpeed - 速度回调
     * @returns {Promise<Blob>} - 返回文件Blob
     */
    const downloadWithProgress = (url, onProgress, onSpeed) => {
        logger.info(`开始普通下载: ${url}`);
        
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', url);
            xhr.responseType = 'blob';
            xhr.timeout = 60000; // 60秒超时
            
            xhr.setRequestHeader('Referer', 'http://music.163.com/');
            
            let startTime = Date.now();
            let lastUpdate = startTime;
            let lastLoaded = 0;
            
            xhr.onprogress = (event) => {
                if (event.lengthComputable) {
                    const progress = Math.floor((event.loaded / event.total) * 100);
                    if (onProgress) onProgress(progress);
                    
                    // 计算下载速度
                    const now = Date.now();
                    if (now - lastUpdate >= 1000) { // 每秒更新一次
                        const timeElapsed = (now - lastUpdate) / 1000; // 转换为秒
                        const bytesDownloaded = event.loaded - lastLoaded;
                        const speed = bytesDownloaded / timeElapsed; // 字节/秒
                        
                        // 格式化速度显示
                        let speedText = '';
                        if (speed >= 1024 * 1024) {
                            speedText = `${(speed / (1024 * 1024)).toFixed(2)} MB/s`;
                        } else if (speed >= 1024) {
                            speedText = `${(speed / 1024).toFixed(2)} KB/s`;
                        } else {
                            speedText = `${Math.round(speed)} B/s`;
                        }
                        
                        // 估计剩余时间
                        const remaining = event.total - event.loaded;
                        let timeRemaining = '';
                        if (speed > 0) {
                            const seconds = Math.ceil(remaining / speed);
                            if (seconds < 60) {
                                timeRemaining = `${seconds}秒`;
                            } else {
                                timeRemaining = `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
                            }
                        }
                        
                        logger.debug(`普通下载进度: ${progress}%, 速度: ${speedText}, 剩余: ${timeRemaining}`);
                        
                        if (onSpeed) onSpeed(speedText, timeRemaining);
                        
                        lastUpdate = now;
                        lastLoaded = event.loaded;
                    }
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    logger.info(`普通下载完成, 文件大小: ${(xhr.response.size / (1024 * 1024)).toFixed(2)} MB`);
                    resolve(xhr.response);
                } else {
                    logger.error(`下载失败: ${xhr.statusText || '服务器错误'}`);
                    reject(new Error(`下载失败: ${xhr.statusText || '服务器错误'}`));
                }
            };

            xhr.ontimeout = () => {
                logger.error('下载超时');
                reject(new Error('下载超时'));
            };
            
            xhr.onerror = () => {
                logger.error('网络错误');
                reject(new Error('网络错误'));
            };
            
            xhr.send();
            logger.debug('XHR请求已发送');
        });
    };
    
    /**
     * 下载并处理歌曲文件（添加元数据后下载）
     * @param {Object} songData - 歌曲数据对象
     * @param {Object} uiElements - UI元素对象，包含进度条等
     * @returns {Promise<void>} - 下载完成的Promise
     */
    const downloadAndPackSong = async (songData, uiElements) => {
        if (!songData) return Promise.reject(new Error('没有可下载的歌曲数据'));
        
        // 设置下载状态
        downloadState.setDownloading(true, {
            type: 'song',
            name: songData.name,
            artist: songData.artist,
            id: songData.id
        });
        
        logger.info(`开始下载歌曲: ${songData.name}`);
        logger.debug('歌曲数据:', songData);
        
        const { $progressContainer, $progressBar, $progressText, $status } = uiElements;
        
        // 添加速度信息元素
        const $speedInfo = $('<div id="speed-info" class="small text-muted mt-1"></div>');
        if ($('#speed-info').length === 0) {
            $status.after($speedInfo);
        }
        
        // 重置进度条
        $progressContainer.removeClass('d-none');
        $progressBar.removeClass('bg-danger').css('width', '0%').attr('aria-valuenow', 0);
        $progressText.text('0%');
        $status.text('准备下载...');
        $('#speed-info').text('');
        
        try {
            const { name, url, pic, lyric, tlyric, ar_name, al_name, ext } = songData;
            
            // 处理文件扩展名 - 确保是字符串
            let fileExt = 'mp3';
            if (ext && ext.audio) {
                fileExt = String(ext.audio).toLowerCase();
            } else if (typeof ext === 'string') {
                fileExt = ext.toLowerCase();
            }
            
            // 如果是mp4则改为m4a
            if (fileExt === 'mp4') {
                logger.info(`检测到MP4音频文件，将扩展名修改为M4A`);
                fileExt = 'm4a';
            }
            
            // 准备文件名
            const fileNameWithoutExt = formatMusicFilename(name, ar_name);
            // 安全处理文件名（移除不安全字符）
            const safeFileName = fileNameWithoutExt.replace(/[\\/:*?"<>|]/g, '_');
            // 完整文件名
            const fileName = `${safeFileName}.${fileExt}`;
            
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
            
            // 合并歌词
            const mergedLyrics = mergeLyricsWithTranslation(lyric, tlyric);
            
            /**
             * 更新进度条显示
             * @param {number} percent - 百分比进度
             * @param {string} statusText - 状态文本
             */
            function updateProgress(percent, statusText) {
                // 使用requestAnimationFrame优化UI更新
                requestAnimationFrame(() => {
                    $progressBar.css('width', `${percent}%`).attr('aria-valuenow', percent);
                    $progressText.text(`${percent}%`);
                    if (statusText) $status.text(statusText);
                });
            }
            
            /**
             * 更新下载速度显示
             * @param {string} speed - 速度文本
             * @param {string} timeRemaining - 剩余时间
             */
            function updateSpeedInfo(speed, timeRemaining) {
                requestAnimationFrame(() => {
                    $('#speed-info').html(`<i class="fas fa-tachometer-alt me-1"></i>速度: ${speed}${timeRemaining ? ` <i class="fas fa-clock ms-2 me-1"></i>剩余: ${timeRemaining}` : ''}`);
                });
            }
            
            // 开始下载音频
            updateProgress(5, '开始下载文件...');
            logger.info('开始下载音频文件');
            
            // 下载音频文件
            const audioBlob = await downloadWithChunks(
                url, 
                1024 * 1024, 
                5,
                (progress) => {
                    updateProgress(progress, '下载文件中...');
                },
                (speed, timeRemaining) => {
                    updateSpeedInfo(speed, timeRemaining);
                }
            );
            
            // 下载完成，准备处理元数据
            updateProgress(90, '下载完成！');
            logger.info(`音频下载完成: ${fileName}, 大小: ${(audioBlob.size / (1024 * 1024)).toFixed(2)} MB`);
            
            // 创建具有正确MIME类型的Blob
            const mimeType = getMimeTypeFromExtension(fileExt);
            
            // 添加元数据
            updateProgress(95, '正在写入元数据...');
            
            // 创建一个新的ArrayBuffer来存储音频数据和元数据
            const audioArrayBuffer = await audioBlob.arrayBuffer();
            let finalAudioBlob = audioBlob; // 用于存储最终的音频文件
            
            // 检查是否启用ZIP打包
            const enableZipPackage = typeof settingsManager !== 'undefined' ? 
                settingsManager.getSetting('enableZipPackage') : false;
            
            // 检查是否启用元数据写入
            const enableMetadata = typeof settingsManager !== 'undefined' ? 
                settingsManager.getSetting('enableMetadata') : true;
            
            // 根据文件类型处理元数据
            if (fileExt.toLowerCase() === 'flac') {
                if (enableMetadata) {
                    try {
                        // 使用 FLACMetadata 库写入元数据
                        let coverBlob = null;
                        if (pic) {
                            try {
                                // 获取封面图片
                                const coverResponse = await fetch(pic, {
                                    headers: {
                                        Referer: 'http://music.163.com/'
                                    }
                                });
                                coverBlob = await coverResponse.blob();
                            } catch (coverError) {
                                logger.error('获取封面图片失败:', coverError);
                            }
                        }
                        
                        const blobWithMetadata = await FLACMetadata.addMetadata(audioArrayBuffer, {
                            title: name,
                            artist: ar_name,
                            album: al_name,
                            lyrics: mergedLyrics, // 使用合并后的歌词
                            cover: coverBlob
                        });
                        
                        finalAudioBlob = blobWithMetadata;
                        if (!enableZipPackage) {
                            saveAs(blobWithMetadata, fileName);
                        }
                    } catch (metadataError) {
                        logger.error('写入FLAC元数据失败:', metadataError);
                        // 如果写入元数据失败，仍然保存原始文件
                        finalAudioBlob = new Blob([audioBlob], { type: mimeType });
                        if (!enableZipPackage) {
                            saveAs(finalAudioBlob, fileName);
                        }
                    }
                } else {
                    // 不写入元数据，直接保存原始文件
                    finalAudioBlob = new Blob([audioBlob], { type: mimeType });
                    if (!enableZipPackage) {
                        saveAs(finalAudioBlob, fileName);
                    }
                }
            } else if (fileExt.toLowerCase() === 'mp3' || fileExt.toLowerCase() === 'm4a') {
                if (enableMetadata) {
                    try {
                        // 使用ID3Writer库写入元数据
                        const writer = new ID3Writer(audioArrayBuffer);
                        writer.setFrame('TIT2', name) // 歌曲名
                              .setFrame('TPE1', [ar_name]) // 歌手
                              .setFrame('TALB', al_name) // 专辑
                              .setFrame('USLT', {description: '', lyrics: mergedLyrics}) // 使用合并后的歌词
                        
                        // 如果有封面图片，添加封面
                        if (pic) {
                            try {
                                // 获取封面图片
                                const coverResponse = await fetch(pic, {
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
                                logger.error('获取封面图片失败:', coverError);
                            }
                        }
                        
                        writer.addTag();
                        const taggedArrayBuffer = writer.arrayBuffer;
                        finalAudioBlob = new Blob([taggedArrayBuffer], { type: mimeType });
                        if (!enableZipPackage) {
                            saveAs(finalAudioBlob, fileName);
                        }
                    } catch (metadataError) {
                        logger.error('写入元数据失败:', metadataError);
                        // 如果写入元数据失败，仍然保存原始文件
                        finalAudioBlob = new Blob([audioBlob], { type: mimeType });
                        if (!enableZipPackage) {
                            saveAs(finalAudioBlob, fileName);
                        }
                    }
                } else {
                    // 不写入元数据，直接保存原始文件
                    finalAudioBlob = new Blob([audioBlob], { type: mimeType });
                    if (!enableZipPackage) {
                        saveAs(finalAudioBlob, fileName);
                    }
                }
            } else {
                // 对于不支持的格式，直接保存原始文件
                finalAudioBlob = new Blob([audioBlob], { type: mimeType });
                if (!enableZipPackage) {
                    saveAs(finalAudioBlob, fileName);
                }
            }

            if (enableZipPackage) {
                // ZIP打包下载，使用写入元数据后的音频文件
                await createZipPackage(songData, finalAudioBlob, fileExt, safeFileName, mergedLyrics);
            }
            
            // 使用requestAnimationFrame延迟隐藏进度条，提高性能
            requestAnimationFrame(() => {
                setTimeout(() => {
                    $progressContainer.addClass('d-none');
                    $('#speed-info').text(''); // 清空速度显示
                    logger.info('下载流程结束，UI已重置');
                }, 1500);
            });
            
            // 下载完成提示
            Swal.fire({
                icon: 'success',
                title: '下载完成',
                text: `歌曲《${name}》已成功下载`,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            
            return Promise.resolve();
            
        } catch (error) {
            logger.error('下载错误:', error);
            $progressBar.addClass('bg-danger');
            $status.html(`<span class="text-danger">下载失败: ${error.message || '未知错误'}</span>`);
            $('#speed-info').text(''); // 清空速度显示
            
            // 下载失败提示
            Swal.fire({
                icon: 'error',
                title: '下载失败',
                text: error.message || '文件下载过程中发生错误',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            
            return Promise.reject(error);
        }
    };
    
    /**
     * 创建ZIP打包下载
     * @param {Object} songData - 歌曲数据对象
     * @param {Blob} audioBlob - 音频文件Blob
     * @param {string} fileExt - 文件扩展名
     * @param {string} safeFileName - 安全的文件名（不含扩展名）
     * @param {string} lyrics - 歌词内容
     * @returns {Promise<void>}
     */
    const createZipPackage = async (songData, audioBlob, fileExt, safeFileName, lyrics) => {
        try {
            logger.info('开始创建ZIP打包文件');
            
            // 检查JSZip是否可用
            if (typeof JSZip === 'undefined') {
                throw new Error('JSZip库未加载，无法创建ZIP文件');
            }

            const zip = new JSZip();
            const { name, pic, ar_name } = songData;

            // 添加音频文件到ZIP
            const audioFileName = `${safeFileName}.${fileExt}`;
            zip.file(audioFileName, audioBlob);
            logger.info(`已添加音频文件: ${audioFileName}`);

            // 下载并添加封面图片
            if (pic) {
                try {
                    const coverResponse = await fetch(pic, {
                        headers: {
                            Referer: 'http://music.163.com/'
                        }
                    });
                    if (coverResponse.ok) {
                        const coverBlob = await coverResponse.blob();
                        const coverFileName = `${safeFileName}.jpg`;
                        zip.file(coverFileName, coverBlob);
                        logger.info(`已添加封面图片: ${coverFileName}`);
                    }
                } catch (coverError) {
                    logger.error('下载封面图片失败:', coverError);
                }
            }

            // 添加歌词文件
            if (lyrics && lyrics.trim()) {
                const lyricsFileName = `${safeFileName}.lrc`;
                zip.file(lyricsFileName, lyrics);
                logger.info(`已添加歌词文件: ${lyricsFileName}`);
            }

            // 生成ZIP文件并下载
            const zipBlob = await zip.generateAsync({
                type: "blob",
                compression: "STORE", // 不压缩，只打包
                compressionOptions: {
                    level: 0
                }
            });

            const zipFileName = `${safeFileName}.zip`;
            saveAs(zipBlob, zipFileName);
            logger.info(`ZIP打包完成: ${zipFileName}`);

            // 显示ZIP打包完成提示
            Swal.fire({
                icon: 'success',
                title: 'ZIP打包完成',
                text: `歌曲《${name}》已打包为ZIP文件下载`,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });

        } catch (error) {
            logger.error('ZIP打包失败:', error);
            
            // 显示ZIP打包失败提示
            Swal.fire({
                icon: 'error',
                title: 'ZIP打包失败',
                text: error.message || 'ZIP文件创建过程中发生错误',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        }
    };

    /**
     * 根据文件扩展名获取MIME类型
     * @param {string} extension - 文件扩展名
     * @returns {string} MIME类型
     */
    const getMimeTypeFromExtension = (extension) => {
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
    };
    
    // 返回公共API
    return {
        // 下载相关API
        downloadWithChunks,
        downloadWithProgress,
        downloadAndPackSong,
        getMimeTypeFromExtension, // 添加到公共API
        
        // 日志控制API
        enableLogs: function() {
            return logger.setEnabled(true);
        },
        disableLogs: function() {
            return logger.setEnabled(false);
        },
        toggleLogs: function() {
            return logger.setEnabled(!logger.enabled);
        },
        isLogsEnabled: function() {
            return logger.enabled;
        }
    };
})();

// 导出模块
window.MusicDownloader = MusicDownloader;

// 控制台提示信息
console.log("\n %c MusicDownloader v1.1 %c 看戏仔 %c\n", 
    "background:#35495e; padding: 1px; border-radius: 3px 0 0 3px; color: #fff;", 
    "background:#41b883; padding: 1px; border-radius: 0 3px 3px 0; color: #fff;", 
    "background:transparent");
console.log("提示: 可以通过以下命令控制下载日志输出:");
console.log(" - MusicDownloader.enableLogs() - 启用日志");
console.log(" - MusicDownloader.disableLogs() - 禁用日志");
console.log(" - MusicDownloader.toggleLogs() - 切换日志状态");
console.log(" - MusicDownloader.isLogsEnabled() - 检查日志状态");


