/**
 * 网站设置管理器
 * 负责设置的保存、加载和应用
 */
class SettingsManager {
    constructor() {
        this.settings = {
            themeMode: 'system', // 默认跟随系统
            filenameFormat: 'song-artist',
            enableMetadata: true, // 默认开启元数据写入
            enableZipPackage: false
        };
        
        this.init();
    }

    /**
     * 初始化设置管理器
     */
    init() {
        this.loadSettings();
        this.bindEvents();
        this.applySettings();
    }

    /**
     * 从localStorage加载设置
     */
    loadSettings() {
        try {
            const savedSettings = localStorage.getItem('musicSiteSettings');
            if (savedSettings) {
                this.settings = { ...this.settings, ...JSON.parse(savedSettings) };
            }
        } catch (error) {
            console.warn('加载设置失败，使用默认设置:', error);
        }
    }

    /**
     * 保存设置到localStorage
     */
    saveSettings() {
        try {
            localStorage.setItem('musicSiteSettings', JSON.stringify(this.settings));
            this.showMessage('设置已保存', 'success');
        } catch (error) {
            console.error('保存设置失败:', error);
            this.showMessage('保存设置失败', 'error');
        }
    }

    /**
     * 应用当前设置
     */
    applySettings() {
        // 应用主题设置
        this.applyTheme();
        
        // 更新设置弹窗中的选项状态
        this.updateSettingsModal();
    }

    /**
     * 应用主题设置
     */
    applyTheme() {
        const body = document.body;
        let actualTheme = this.settings.themeMode;
        
        // 如果设置为跟随系统，检测系统偏好
        if (actualTheme === 'system') {
            actualTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        
        if (actualTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            body.classList.add('dark-theme');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            body.classList.remove('dark-theme');
        }
    }

    /**
     * 更新设置弹窗中的选项状态
     */
    updateSettingsModal() {
        // 更新主题选择
        const themeRadios = document.querySelectorAll('input[name="themeMode"]');
        themeRadios.forEach(radio => {
            radio.checked = radio.value === this.settings.themeMode;
        });

        // 更新文件命名格式选择
        const formatRadios = document.querySelectorAll('input[name="filenameFormat"]');
        formatRadios.forEach(radio => {
            radio.checked = radio.value === this.settings.filenameFormat;
        });

        // 更新元数据写入选项
        const metadataCheckbox = document.getElementById('enableMetadata');
        if (metadataCheckbox) {
            metadataCheckbox.checked = this.settings.enableMetadata;
        }

        // 更新ZIP打包选项
        const zipCheckbox = document.getElementById('enableZipPackage');
        if (zipCheckbox) {
            zipCheckbox.checked = this.settings.enableZipPackage;
        }
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 设置按钮点击事件
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                const settingsModal = new bootstrap.Modal(document.getElementById('settingsModal'));
                settingsModal.show();
            });
        }

        // 保存设置按钮事件
        const saveBtn = document.getElementById('saveSettings');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.collectAndSaveSettings();
            });
        }

        // 主题切换事件
        const themeRadios = document.querySelectorAll('input[name="themeMode"]');
        themeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.settings.themeMode = e.target.value;
                    this.applyTheme();
                }
            });
        });
    }

    /**
     * 收集并保存设置
     */
    collectAndSaveSettings() {
        // 收集主题设置
        const selectedTheme = document.querySelector('input[name="themeMode"]:checked');
        if (selectedTheme) {
            this.settings.themeMode = selectedTheme.value;
        }

        // 收集文件命名格式设置
        const selectedFormat = document.querySelector('input[name="filenameFormat"]:checked');
        if (selectedFormat) {
            this.settings.filenameFormat = selectedFormat.value;
        }

        // 收集元数据写入设置
        const metadataCheckbox = document.getElementById('enableMetadata');
        if (metadataCheckbox) {
            this.settings.enableMetadata = metadataCheckbox.checked;
        }

        // 收集ZIP打包设置
        const zipCheckbox = document.getElementById('enableZipPackage');
        if (zipCheckbox) {
            this.settings.enableZipPackage = zipCheckbox.checked;
        }

        // 保存设置
        this.saveSettings();
        
        // 应用设置
        this.applySettings();

        // 关闭弹窗
        const settingsModal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
        if (settingsModal) {
            settingsModal.hide();
        }
    }

    /**
     * 获取当前设置
     */
    getSettings() {
        return { ...this.settings };
    }

    /**
     * 获取特定设置项
     */
    getSetting(key) {
        return this.settings[key];
    }

    /**
     * 更新特定设置项
     */
    updateSetting(key, value) {
        this.settings[key] = value;
        this.saveSettings();
        this.applySettings();
    }

    /**
     * 显示消息提示
     */
    showMessage(message, type = 'info') {
        // 创建消息提示元素
        const messageEl = document.createElement('div');
        messageEl.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show position-fixed`;
        messageEl.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 250px;';
        messageEl.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'check-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(messageEl);

        // 3秒后自动移除
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 3000);
    }

    /**
     * 重置设置为默认值
     */
    resetSettings() {
        this.settings = {
            themeMode: 'system', // 默认跟随系统
            filenameFormat: 'song-artist',
            enableMetadata: true, // 默认开启元数据写入
            enableZipPackage: false
        };
        this.saveSettings();
        this.applySettings();
        this.showMessage('设置已重置为默认值', 'success');
    }

    /**
     * 根据设置格式化文件名
     * @param {string} songName - 歌曲名
     * @param {string} artistName - 歌手名
     * @returns {string} 格式化后的文件名（不含扩展名）
     */
    formatFilename(songName, artistName) {
        const format = this.getSetting('filenameFormat');
        const safeArtistName = artistName || '未知歌手';
        
        switch (format) {
            case 'artist-song':
                return `${safeArtistName} - ${songName}`;
            case 'song-artist':
            default:
                return `${songName} - ${safeArtistName}`;
        }
    }
}

// 全局文件名格式化函数，供其他模块使用
function formatMusicFilename(songName, artistName) {
    if (typeof settingsManager !== 'undefined') {
        return settingsManager.formatFilename(songName, artistName);
    }
    // 如果设置管理器未初始化，使用默认格式
    return `${songName} - ${artistName || '未知歌手'}`;
}

// 全局设置管理器实例
let settingsManager;

// 页面加载完成后初始化设置管理器
document.addEventListener('DOMContentLoaded', () => {
    settingsManager = new SettingsManager();
});

// 导出设置管理器类和实例
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SettingsManager, settingsManager };
}