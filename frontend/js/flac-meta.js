/**
 * FLAC Metadata Editor
 * 用于为FLAC无损音乐文件添加/提取元数据
 * 功能：添加标题、艺术家、专辑、歌词等标签；嵌入封面图片
 */

class FLACMetadata {
    /**
     * 检查是否为有效的FLAC文件
     * @param {Uint8Array} data - 文件字节数据
     * @returns {boolean}
     */
    static isValidFLAC(data) {
        return data[0] === 0x66 &&  // 'f'
               data[1] === 0x4C &&  // 'L'
               data[2] === 0x61 &&  // 'a'
               data[3] === 0x43;    // 'C'
    }

    /**
     * 添加元数据到FLAC文件
     * @param {ArrayBuffer} audioData - FLAC文件数据
     * @param {Object} metadata - 元数据对象
     * @param {string} metadata.title - 标题
     * @param {string} metadata.artist - 艺术家
     * @param {string} metadata.album - 专辑
     * @param {string} metadata.lyrics - 歌词
     * @param {Blob} [metadata.cover] - 封面图片
     * @returns {Promise<Blob>}
     */
    static async addMetadata(audioData, metadata) {
        Logger.debug('开始为FLAC文件添加元数据:', metadata);

        const uint8Array = new Uint8Array(audioData);
        if (!this.isValidFLAC(uint8Array)) {
            throw new Error('无效的FLAC文件');
        }

        const vorbisComment = {};
        vorbisComment['TITLE'] = metadata.title || '';
        vorbisComment['ARTIST'] = metadata.artist || '';
        vorbisComment['ALBUM'] = metadata.album || '';
        vorbisComment['DATE'] = metadata.year || '';
        vorbisComment['LYRICS'] = metadata.lyrics || '';

        const commentData = this.createVorbisComment(vorbisComment);
        let resultData = this.insertVorbisCommentBlock(uint8Array, commentData);

        if (metadata.cover) {
            resultData = await this.addCoverImage(resultData, metadata.cover);
        }

        const blobInfo = {
            mimeType: 'audio/flac',
            title: metadata.title,
            artist: metadata.artist,
            album: metadata.album,
            originalSize: audioData.byteLength,
            newSize: resultData.length
        };

        Logger.debug('✅ FLAC元数据写入成功!', blobInfo);

        return new Blob([resultData], { type: 'audio/flac' });
    }

    /**
     * 从FLAC文件中提取元数据
     * @param {ArrayBuffer} audioData - FLAC文件数据
     * @returns {Promise<Object>}
     */
    static async extractMetadata(audioData) {
        return new Promise((resolve, reject) => {
            try {
                const uint8Array = new Uint8Array(audioData);
                if (!this.isValidFLAC(uint8Array)) {
                    reject(new Error('无效的FLAC文件'));
                    return;
                }

                const vorbisComment = this.extractVorbisComment(uint8Array);
                const coverImage = this.extractCoverImage(uint8Array);
                const techInfo = this.extractTechInfo(uint8Array);

                const metadata = {
                    title: vorbisComment['TITLE'] || '',
                    artist: vorbisComment['ARTIST'] || '',
                    album: vorbisComment['ALBUM'] || '',
                    year: vorbisComment['DATE'] || '',
                    lyrics: vorbisComment['LYRICS'] || '',
                    cover: coverImage,
                    ...techInfo
                };

                resolve(metadata);
            } catch (error) {
                Logger.error('提取FLAC元数据失败:', error);
                reject(error);
            }
        });
    }

    /**
     * 创建Vorbis Comment元数据块
     * @param {Object} metadata - 元数据对象
     * @returns {Uint8Array}
     */
    static createVorbisComment(metadata) {
        const vendor = 'FLAC Metadata Editor';
        const vendorEncoded = new TextEncoder().encode(vendor);
        const commentData = [];

        for (const [key, value] of Object.entries(metadata)) {
            if (value) {
                const entry = key + '=' + value;
                commentData.push(new TextEncoder().encode(entry));
            }
        }

        let totalLength = 4 + vendorEncoded.length + 4;
        for (const data of commentData) {
            totalLength += 4 + data.length;
        }

        const result = new Uint8Array(totalLength);
        let offset = 0;

        result[offset++] = vendorEncoded.length & 0xFF;
        result[offset++] = (vendorEncoded.length >> 8) & 0xFF;
        result[offset++] = (vendorEncoded.length >> 16) & 0xFF;
        result[offset++] = (vendorEncoded.length >> 24) & 0xFF;
        result.set(vendorEncoded, offset);
        offset += vendorEncoded.length;

        result[offset++] = commentData.length & 0xFF;
        result[offset++] = (commentData.length >> 8) & 0xFF;
        result[offset++] = (commentData.length >> 16) & 0xFF;
        result[offset++] = (commentData.length >> 24) & 0xFF;

        for (const data of commentData) {
            result[offset++] = data.length & 0xFF;
            result[offset++] = (data.length >> 8) & 0xFF;
            result[offset++] = (data.length >> 16) & 0xFF;
            result[offset++] = (data.length >> 24) & 0xFF;
            result.set(data, offset);
            offset += data.length;
        }

        return result;
    }

    /**
     * 插入Vorbis Comment块到FLAC文件
     * @param {Uint8Array} flacData - FLAC文件数据
     * @param {Uint8Array} commentData - Vorbis Comment数据
     * @returns {Uint8Array}
     */
    static insertVorbisCommentBlock(flacData, commentData) {
        let pos = 4;
        let foundCommentBlock = false;
        let commentBlockStart = 0;
        let commentBlockEnd = 0;

        while (pos < flacData.length) {
            const blockType = flacData[pos];
            const isLast = (blockType & 0x80) !== 0;
            const type = blockType & 0x7F;
            const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

            if (type === 4) {
                foundCommentBlock = true;
                commentBlockStart = pos;
                commentBlockEnd = pos + 4 + blockLength;
                break;
            }

            pos += 4 + blockLength;
            if (isLast) break;
        }

        const headerLength = 4;
        const commentBlockHeader = new Uint8Array(4);
        commentBlockHeader[0] = 4;
        commentBlockHeader[1] = commentData.length >> 16 & 0xFF;
        commentBlockHeader[2] = commentData.length >> 8 & 0xFF;
        commentBlockHeader[3] = commentData.length & 0xFF;

        if (foundCommentBlock) {
            const newData = new Uint8Array(
                flacData.length - (commentBlockEnd - commentBlockStart) + 4 + commentData.length
            );
            newData.set(flacData.slice(0, commentBlockStart), 0);
            newData.set(commentBlockHeader, commentBlockStart);
            newData.set(commentData, commentBlockStart + 4);
            newData.set(flacData.slice(commentBlockEnd), commentBlockStart + 4 + commentData.length);
            return newData;
        } else {
            let vorbisCommentPos = 4;
            for (let i = 0; i < 10; i++) {
                const blockType = flacData[vorbisCommentPos];
                const isLast = (blockType & 0x80) !== 0;
                const type = blockType & 0x7F;
                const blockLength = (flacData[vorbisCommentPos + 1] << 16) |
                                   (flacData[vorbisCommentPos + 2] << 8) |
                                   flacData[vorbisCommentPos + 3];

                if (type === 4) {
                    vorbisCommentPos += 4 + blockLength;
                    break;
                }

                vorbisCommentPos += 4 + blockLength;
                if (isLast) break;
            }

            const newData = new Uint8Array(flacData.length + 4 + commentData.length);
            newData.set(flacData.slice(0, vorbisCommentPos), 0);
            newData.set(commentBlockHeader, vorbisCommentPos);
            newData.set(commentData, vorbisCommentPos + 4);
            newData.set(flacData.slice(vorbisCommentPos), vorbisCommentPos + 4 + commentData.length);
            return newData;
        }
    }

    /**
     * 从FLAC中提取Vorbis Comment
     * @param {Uint8Array} flacData - FLAC数据
     * @returns {Object}
     */
    static extractVorbisComment(flacData) {
        let pos = 4;
        const result = {};

        while (pos < flacData.length) {
            const blockType = flacData[pos];
            const isLast = (blockType & 0x80) !== 0;
            const type = blockType & 0x7F;
            const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

            if (type === 4) {
                pos += 4;
                const vendorLength = flacData[pos] | flacData[pos + 1] << 8 |
                                     flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4 + vendorLength;

                const numComments = flacData[pos] | flacData[pos + 1] << 8 |
                                   flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                for (let i = 0; i < numComments; i++) {
                    const commentLength = flacData[pos] | flacData[pos + 1] << 8 |
                                          flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                    pos += 4;

                    const commentData = flacData.slice(pos, pos + commentLength);
                    pos += commentLength;

                    const commentStr = new TextDecoder().decode(commentData);
                    const equalIndex = commentStr.indexOf('=');

                    if (equalIndex > 0) {
                        const key = commentStr.substring(0, equalIndex).toUpperCase();
                        const value = commentStr.substring(equalIndex + 1);
                        result[key] = value;
                    }
                }
                break;
            }

            pos += 4 + blockLength;
            if (isLast) break;
        }

        return result;
    }

    /**
     * 从FLAC中提取封面图片
     * @param {Uint8Array} flacData - FLAC数据
     * @returns {Blob|null}
     */
    static extractCoverImage(flacData) {
        let pos = 4;

        while (pos < flacData.length) {
            const blockType = flacData[pos];
            const isLast = (blockType & 0x80) !== 0;
            const type = blockType & 0x7F;
            const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

            if (type === 6) {
                pos += 4;
                pos += 4;

                const pictureType = flacData[pos] | flacData[pos + 1] << 8 |
                                   flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const mimeLength = flacData[pos] | flacData[pos + 1] << 8 |
                                   flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const mimeType = new TextDecoder().decode(flacData.slice(pos, pos + mimeLength));
                pos += mimeLength;

                const descLength = flacData[pos] | flacData[pos + 1] << 8 |
                                   flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4 + descLength;

                const width = flacData[pos] | flacData[pos + 1] << 8 |
                              flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const height = flacData[pos] | flacData[pos + 1] << 8 |
                               flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const depth = flacData[pos] | flacData[pos + 1] << 8 |
                              flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const colors = flacData[pos] | flacData[pos + 1] << 8 |
                               flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const imageLength = flacData[pos] | flacData[pos + 1] << 8 |
                                    flacData[pos + 2] << 16 | flacData[pos + 3] << 24;
                pos += 4;

                const imageData = flacData.slice(pos, pos + imageLength);
                pos += imageLength;

                return new Blob([imageData], { type: mimeType });
            }

            pos += 4 + blockLength;
            if (isLast) break;
        }

        return null;
    }

    /**
     * 添加封面图片到FLAC
     * @param {Uint8Array} flacData - FLAC数据
     * @param {Blob} imageBlob - 封面图片
     * @returns {Promise<Uint8Array>}
     */
    static async addCoverImage(flacData, imageBlob) {
        return new Promise((resolve, reject) => {
            try {
                const maxImageSize = 16 * 1024 * 1024;

                if (imageBlob.size > maxImageSize) {
                    Logger.debug('图片数据过大(' + (imageBlob.size / 1024 / 1024).toFixed(2) + 'MB)，最大支持16MB');
                    this.compressImage(imageBlob, maxImageSize)
                        .then(compressedBlob => this.addCoverImage(flacData, compressedBlob))
                        .then(resolve)
                        .catch(reject);
                    return;
                }

                this.processCoverImage(flacData, imageBlob)
                    .then(resolve)
                    .catch(reject);
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 处理封面图片并插入到FLAC
     * @param {Uint8Array} flacData - FLAC数据
     * @param {Blob} imageBlob - 图片数据
     * @returns {Promise<Uint8Array>}
     */
    static async processCoverImage(flacData, imageBlob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async () => {
                try {
                    const imageData = new Uint8Array(reader.result);

                    if (imageData.length > 16 * 1024 * 1024) {
                        reject(new Error('图片大小超过16MB限制'));
                        return;
                    }

                    const mimeType = 'image/jpeg';
                    const pictureBlock = this.createPictureBlock({
                        type: 3,
                        mimeType: mimeType,
                        description: 'Cover',
                        width: 0,
                        height: 0,
                        depth: 24,
                        colors: 0,
                        data: imageData
                    });

                    const result = this.insertPictureBlock(flacData, pictureBlock);
                    resolve(result);
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsArrayBuffer(imageBlob);
        });
    }

    /**
     * 压缩图片到指定大小以下
     * @param {Blob} imageBlob - 原始图片
     * @param {number} maxSize - 最大大小（字节）
     * @returns {Promise<Blob>}
     */
    static async compressImage(imageBlob, maxSize) {
        return new Promise((resolve, reject) => {
            try {
                const maxDimension = 1024;
                const img = new Image();
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                img.onload = () => {
                    let { width, height } = img;

                    if (width > maxDimension || height > maxDimension) {
                        const scale = Math.min(maxDimension / width, maxDimension / height);
                        width = Math.floor(width * scale);
                        height = Math.floor(height * scale);
                    }

                    canvas.width = width;
                    canvas.height = height;
                    ctx.drawImage(img, 0, 0, width, height);

                    let quality = 0.9;

                    const compress = () => {
                        canvas.toBlob((blob) => {
                            if (!blob) {
                                reject(new Error('图片压缩失败'));
                                return;
                            }

                            if (blob.size <= maxSize || quality <= 0.5) {
                                Logger.debug('图片压缩完成: ' + (blob.size / 1024).toFixed(2) + 'KB');
                                resolve(blob);
                            } else {
                                quality -= 0.1;
                                canvas.toBlob(compress, 'image/jpeg', quality);
                            }
                        }, 'image/jpeg', quality);
                    };

                    compress();
                };

                img.onerror = () => reject(new Error('图片加载失败'));
                img.src = URL.createObjectURL(imageBlob);
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 创建图片元数据块
     * @param {Object} params - 图片参数
     * @returns {Uint8Array}
     */
    static createPictureBlock(params) {
        const mimeTypeEncoded = new TextEncoder().encode(params.mimeType);
        const descriptionEncoded = new TextEncoder().encode(params.description || '');

        const totalLength = 32 + mimeTypeEncoded.length + descriptionEncoded.length + params.data.length;
        const buffer = new ArrayBuffer(totalLength);
        const view = new DataView(buffer);
        let offset = 0;

        view.setUint32(offset, params.type, false);
        offset += 4;

        view.setUint32(offset, mimeTypeEncoded.length, false);
        offset += 4;

        for (let i = 0; i < mimeTypeEncoded.length; i++) {
            view.setUint8(offset, mimeTypeEncoded[i]);
            offset++;
        }

        view.setUint32(offset, descriptionEncoded.length, false);
        offset += 4;

        for (let i = 0; i < descriptionEncoded.length; i++) {
            view.setUint8(offset, descriptionEncoded[i]);
            offset++;
        }

        view.setUint32(offset, params.width, false);
        offset += 4;
        view.setUint32(offset, params.height, false);
        offset += 4;
        view.setUint32(offset, params.depth, false);
        offset += 4;
        view.setUint32(offset, params.colors, false);
        offset += 4;

        const imageData = params.data.data || params.data;
        for (let i = 0; i < imageData.length; i++) {
            view.setUint8(offset, imageData[i]);
            offset++;
        }

        return new Uint8Array(buffer);
    }

    /**
     * 插入图片块到FLAC
     * @param {Uint8Array} flacData - FLAC数据
     * @param {Uint8Array} pictureData - 图片块数据
     * @returns {Uint8Array}
     */
    static insertPictureBlock(flacData, pictureData) {
        let pos = 4;
        let foundPictureBlock = false;
        let pictureBlockStart = 0;
        let pictureBlockEnd = 0;

        while (pos < flacData.length) {
            const blockType = flacData[pos];
            const isLast = (blockType & 0x80) !== 0;
            const type = blockType & 0x7F;
            const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

            if (type === 6) {
                foundPictureBlock = true;
                pictureBlockStart = pos;
                pictureBlockEnd = pos + 4 + blockLength;
                break;
            }

            pos += 4 + blockLength;
            if (isLast) break;
        }

        const headerLength = 4;
        const pictureBlockHeader = new Uint8Array(4);
        pictureBlockHeader[0] = 6;
        pictureBlockHeader[1] = pictureData.length >> 16 & 0xFF;
        pictureBlockHeader[2] = pictureData.length >> 8 & 0xFF;
        pictureBlockHeader[3] = pictureData.length & 0xFF;

        if (foundPictureBlock) {
            const newData = new Uint8Array(
                flacData.length - (pictureBlockEnd - pictureBlockStart) + 4 + pictureData.length
            );
            newData.set(flacData.slice(0, pictureBlockStart), 0);
            newData.set(pictureBlockHeader, pictureBlockStart);
            newData.set(pictureData, pictureBlockStart + 4);
            newData.set(flacData.slice(pictureBlockEnd), pictureBlockStart + 4 + pictureData.length);
            return newData;
        } else {
            let vorbisCommentEnd = 0;

            for (let i = 0; i < 20; i++) {
                if (pos >= flacData.length) break;

                const blockType = flacData[pos];
                const isLast = (blockType & 0x80) !== 0;
                const type = blockType & 0x7F;
                const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

                if (type === 4) {
                    vorbisCommentEnd = pos + 4 + blockLength;
                    break;
                }

                pos += 4 + blockLength;
                if (isLast) {
                    vorbisCommentEnd = pos;
                    break;
                }
            }

            const newData = new Uint8Array(flacData.length + 4 + pictureData.length);
            newData.set(flacData.slice(0, vorbisCommentEnd), 0);
            newData.set(pictureBlockHeader, vorbisCommentEnd);
            newData.set(pictureData, vorbisCommentEnd + 4);
            newData.set(flacData.slice(vorbisCommentEnd), vorbisCommentEnd + 4 + pictureData.length);
            return newData;
        }
    }

    /**
     * 提取FLAC技术信息（采样率、位深、声道数等）
     * @param {Uint8Array} flacData - FLAC数据
     * @returns {Object}
     */
    static extractTechInfo(flacData) {
        let pos = 4;
        const info = {
            sampleRate: 0,
            channels: 0,
            bitDepth: 0,
            duration: 0,
            fileSize: flacData.length
        };

        while (pos < flacData.length) {
            const blockType = flacData[pos];
            const isLast = (blockType & 0x80) !== 0;
            const type = blockType & 0x7F;
            const blockLength = (flacData[pos + 1] << 16) | (flacData[pos + 2] << 8) | flacData[pos + 3];

            if (type === 0) {
                pos += 4;

                const minBlockSize = flacData[pos] << 8 | flacData[pos + 1];
                pos += 2;

                const maxBlockSize = flacData[pos] << 8 | flacData[pos + 1];
                pos += 2;

                const minFrameSize = flacData[pos] << 16 | flacData[pos + 1] << 8 | flacData[pos + 2];
                pos += 3;

                const maxFrameSize = flacData[pos] << 16 | flacData[pos + 1] << 8 | flacData[pos + 2];
                pos += 3;

                const sampleInfo = flacData[pos];
                pos += 1;

                const sampleRate = (sampleInfo & 0xF0) >> 4;
                const channelInfo = (sampleInfo & 0x0E) >> 1;
                const bitDepthInfo = ((sampleInfo & 0x01) << 4) | ((flacData[pos] & 0xF0) >> 4);

                info.sampleRate = sampleRate === 0 ? 0 : [88200, 96000, 192000, 0, 0, 44100, 48000, 176400][sampleRate - 1] || 0;
                info.channels = channelInfo + 1;
                info.bitDepth = bitDepthInfo === 0 ? 0 : [8, 12, 0, 16, 20, 24, 0, 24][bitDepthInfo - 1] || 0;

                pos += 4;

                const totalSamples = ((flacData[pos] & 0x0F) << 32) | (flacData[pos + 1] << 24) |
                                    (flacData[pos + 2] << 16) | (flacData[pos + 3] << 8) | flacData[pos + 4];
                pos += 5;

                if (info.sampleRate > 0) {
                    info.duration = Math.round(totalSamples / info.sampleRate);
                }

                break;
            }

            pos += 4 + blockLength;
            if (isLast) break;
        }

        return info;
    }

    /**
     * 格式化时长
     * @param {number} seconds - 秒数
     * @returns {string}
     */
    static formatDuration(seconds) {
        if (!seconds) return '00:00';
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return String(minutes).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
    }

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string}
     */
    static formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const unitIndex = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, unitIndex) * 100) / 100 + ' ' + units[unitIndex];
    }
}
