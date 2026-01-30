/**
 * 系统公告弹窗管理
 * 处理公告的显示、隐藏和用户交互
 */

// 公告管理对象
const AnnouncementManager = {
    // 配置选项
    config: {
        apiUrl: './api/get_announcement.php',
        storageKey: 'announcement_dismissed',
        announcementInfoKey: 'announcement_info',
        autoShow: false
    },

    // 初始化
    init() {
        this.bindEvents();
        if (this.config.autoShow) {
            this.loadAndShowAnnouncement();
        }
    },

    // 绑定事件
    bindEvents() {
        const confirmBtn = document.getElementById('confirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (!confirmBtn.disabled) {
                    this.hideAnnouncement();
                }
            });
        }

        // 公告必须通过点击"我已阅读并同意"按钮才能关闭
    },

    // 加载并显示公告
    async loadAndShowAnnouncement() {
        try {
            const response = await fetch(this.config.apiUrl);
            const data = await response.json();

            if (data.success && data.data) {
                // 检查是否已经关闭过（传入公告数据进行检查）
                if (this.isDismissed(data.data)) {
                    return;
                }

                this.showAnnouncement(data.data);
            } else {
                Logger.warn('获取公告失败:', data.message);
            }
        } catch (error) {
            Logger.error('加载公告时出错:', error);
        }
    },

    // 显示公告
    showAnnouncement(announcementData) {
        const modal = document.getElementById('announcementModal');
        const systemAnnouncement = document.getElementById('systemAnnouncement');
        const disclaimerContent = document.getElementById('disclaimerContent');
        const confirmBtn = document.getElementById('confirmBtn');

        if (!modal || !systemAnnouncement || !disclaimerContent || !confirmBtn) {
            Logger.error('公告弹窗元素未找到');
            return;
        }

        // 存储当前公告数据供后续使用
        this.currentAnnouncementData = announcementData;

        // 更新内容（支持HTML）
        systemAnnouncement.innerHTML = announcementData.content || '暂无公告内容';
        disclaimerContent.innerHTML = announcementData.disclaimer_content || '暂无免责声明';

        // 显示弹窗
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // 防止背景滚动

        // 启动10秒倒计时
        this.startCountdown(confirmBtn);

        // 添加显示动画
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    },

    // 隐藏公告
    hideAnnouncement() {
        const modal = document.getElementById('announcementModal');
        if (!modal) return;

        // 添加隐藏动画
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.style.display = 'none';
            modal.style.opacity = '1';
            document.body.style.overflow = ''; // 恢复背景滚动
        }, 300);

        // 记录用户已关闭
        this.markAsDismissed(this.currentAnnouncementData);
    },

    // 检查是否可见
    isVisible() {
        const modal = document.getElementById('announcementModal');
        return modal && modal.style.display !== 'none';
    },

    // 检查是否已关闭
    isDismissed(announcementData) {
        const dismissed = localStorage.getItem(this.config.storageKey);
        const today = new Date().toDateString();

        // 如果今天没有关闭过，直接返回false
        if (dismissed !== today) {
            return false;
        }

        // 检查公告信息是否有变化
        const storedInfo = localStorage.getItem(this.config.announcementInfoKey);
        if (!storedInfo || !announcementData) {
            return false;
        }

        try {
            const parsedInfo = JSON.parse(storedInfo);
            // 如果公告ID或更新时间发生变化，则需要重新显示
            if (parsedInfo.id !== announcementData.id ||
                parsedInfo.updated_at !== announcementData.updated_at) {
                return false;
            }
        } catch (error) {
            Logger.error('解析存储的公告信息失败:', error);
            return false;
        }

        return true;
    },

    // 标记为已关闭
    markAsDismissed(announcementData) {
        const today = new Date().toDateString();
        localStorage.setItem(this.config.storageKey, today);

        // 存储当前公告信息
        if (announcementData) {
            const announcementInfo = {
                id: announcementData.id,
                updated_at: announcementData.updated_at
            };
            localStorage.setItem(this.config.announcementInfoKey, JSON.stringify(announcementInfo));
        }
    },

    // 强制显示公告（忽略已关闭状态）
    forceShow() {
        this.loadAndShowAnnouncement();
    },

    // 清除已关闭状态
    clearDismissed() {
        localStorage.removeItem(this.config.storageKey);
        localStorage.removeItem(this.config.announcementInfoKey);
    },

    // 启动倒计时
    startCountdown(confirmBtn) {
        let countdown = 3;
        const originalText = confirmBtn.textContent;

        // 禁用按钮并显示倒计时
        confirmBtn.disabled = true;
        confirmBtn.style.opacity = '0.5';
        confirmBtn.style.cursor = 'not-allowed';

        const updateButton = () => {
            confirmBtn.textContent = `请阅读完整内容 (${countdown}秒)`;
        };

        updateButton();

        const timer = setInterval(() => {
            countdown--;
            if (countdown > 0) {
                updateButton();
            } else {
                // 倒计时结束，启用按钮
                clearInterval(timer);
                confirmBtn.disabled = false;
                confirmBtn.style.opacity = '1';
                confirmBtn.style.cursor = 'pointer';
                confirmBtn.textContent = originalText;
            }
        }, 1000);
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        AnnouncementManager.init();
    });
} else {
    AnnouncementManager.init();
}

// 导出到全局作用域（可选）
window.AnnouncementManager = AnnouncementManager;