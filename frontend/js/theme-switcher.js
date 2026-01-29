/**
 * 主题切换脚本
 * 负责处理网站的暗黑/浅色模式切换功能
 * 现在通过设置管理器统一管理
 * @author kanxizai
 */

// 主题切换工具类
class ThemeSwitcher {
    constructor() {
        this.init();
    }

    init() {
        // 等待设置管理器初始化完成
        document.addEventListener('DOMContentLoaded', () => {
            // 延迟执行，确保settingsManager已经初始化
            setTimeout(() => {
                this.applyThemeFromSettings();
                this.migrateOldThemeSettings();
                this.setupSystemThemeListener();
                // 添加初始系统主题检查
                this.checkSystemPreference();
            }, 100);
        });
    }

    /**
     * 从设置管理器应用主题
     */
    applyThemeFromSettings() {
        if (typeof settingsManager !== 'undefined') {
            const themeMode = settingsManager.getSetting('themeMode');
            this.applyTheme(themeMode);
        }
    }

    /**
     * 应用主题
     */
    applyTheme(theme) {
        const body = document.body;
        let actualTheme = theme;
        
        // 如果设置为跟随系统，检测系统偏好
        if (theme === 'system') {
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
     * 迁移旧的主题设置
     * 将localStorage中的theme设置迁移到新的设置系统
     */
    migrateOldThemeSettings() {
        const oldTheme = localStorage.getItem('theme');
        if (oldTheme && typeof settingsManager !== 'undefined') {
            // 如果存在旧的主题设置，迁移到新系统
            const currentSettings = settingsManager.getSettings();
            if (currentSettings.themeMode === 'light' && oldTheme === 'dark') {
                settingsManager.updateSetting('themeMode', 'dark');
            }
            
            // 清除旧的主题设置
            localStorage.removeItem('theme');
        }
    }

    /**
     * 设置系统主题监听器
     */
    setupSystemThemeListener() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            // 监听系统主题变化
            mediaQuery.addEventListener('change', (e) => {
                if (typeof settingsManager !== 'undefined') {
                    const currentTheme = settingsManager.getSetting('themeMode');
                    
                    // 只有当设置为跟随系统时才自动切换
                    if (currentTheme === 'system') {
                        // 直接应用新的系统主题
                        this.applyTheme('system');
                    }
                }
            });
        }
    }

    /**
     * 检查系统偏好并设置默认主题
     */
    checkSystemPreference() {
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (typeof settingsManager !== 'undefined') {
            const currentTheme = settingsManager.getSetting('themeMode');
            
            // 如果当前是默认的system主题，应用系统偏好
            if (currentTheme === 'system') {
                settingsManager.applyTheme();
            }
        }
    }

    /**
     * 手动切换主题
     */
    toggleTheme() {
        if (typeof settingsManager !== 'undefined') {
            const currentTheme = settingsManager.getSetting('themeMode');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            settingsManager.updateSetting('themeMode', newTheme);
        }
    }
}

// 创建主题切换器实例
const themeSwitcher = new ThemeSwitcher();

// 系统主题监听已移至ThemeSwitcher类内部

// 导出主题切换器
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSwitcher;
}