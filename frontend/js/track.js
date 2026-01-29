/**
 * PV/UV统计跟踪脚本
 * 自动记录网站访问数据
 */

(function() {
    'use strict';
    
    // 配置项
    const config = {
        apiUrl: './api/track_visit.php',
        retryTimes: 3,
        retryDelay: 1000,
        timeout: 5000
    };
    
    // 防止重复统计
    let hasTracked = false;
    
    /**
     * 发送统计请求
     */
    function sendTrackingRequest(retryCount = 0) {
        if (hasTracked) {
            return;
        }
        
        // 创建XMLHttpRequest对象
        const xhr = new XMLHttpRequest();
        
        // 设置超时
        xhr.timeout = config.timeout;
        
        // 监听状态变化
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            hasTracked = true;
                            console.log('访问统计记录成功');
                        } else {
                            console.warn('访问统计失败:', response.message);
                            handleRetry(retryCount);
                        }
                    } catch (e) {
                        console.error('解析统计响应失败:', e);
                        handleRetry(retryCount);
                    }
                } else {
                    console.warn('统计请求失败，状态码:', xhr.status);
                    handleRetry(retryCount);
                }
            }
        };
        
        // 监听超时
        xhr.ontimeout = function() {
            console.warn('统计请求超时');
            handleRetry(retryCount);
        };
        
        // 监听错误
        xhr.onerror = function() {
            console.warn('统计请求出错');
            handleRetry(retryCount);
        };
        
        // 发送POST请求
        xhr.open('POST', config.apiUrl, true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        
        // 收集页面信息
        const pageData = {
            url: window.location.href,
            title: document.title,
            referrer: document.referrer,
            timestamp: new Date().getTime()
        };
        
        // 发送数据
        const postData = Object.keys(pageData)
            .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(pageData[key]))
            .join('&');
            
        xhr.send(postData);
    }
    
    /**
     * 处理重试逻辑
     */
    function handleRetry(retryCount) {
        if (retryCount < config.retryTimes) {
            setTimeout(() => {
                sendTrackingRequest(retryCount + 1);
            }, config.retryDelay * (retryCount + 1));
        } else {
            console.error('统计请求重试次数已达上限');
        }
    }
    
    /**
     * 检测页面是否可见
     */
    function isPageVisible() {
        return !document.hidden && document.visibilityState === 'visible';
    }
    
    /**
     * 初始化统计
     */
    function initTracking() {
        // 检查是否为搜索引擎爬虫
        const userAgent = navigator.userAgent.toLowerCase();
        const bots = ['googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider', 'yandexbot', 'facebookexternalhit'];
        
        for (let bot of bots) {
            if (userAgent.includes(bot)) {
                console.log('检测到搜索引擎爬虫，跳过统计');
                return;
            }
        }
        
        // 检查页面是否可见
        if (!isPageVisible()) {
            // 等待页面变为可见时再统计
            document.addEventListener('visibilitychange', function() {
                if (isPageVisible() && !hasTracked) {
                    sendTrackingRequest();
                }
            }, { once: true });
        } else {
            // 页面已可见，直接统计
            sendTrackingRequest();
        }
    }
    
    /**
     * 页面卸载时的处理
     */
    function handlePageUnload() {
        // 使用sendBeacon API发送最后的统计数据（如果支持）
        if (navigator.sendBeacon && !hasTracked) {
            const pageData = {
                url: window.location.href,
                title: document.title,
                referrer: document.referrer,
                timestamp: new Date().getTime(),
                unload: true
            };
            
            const formData = new FormData();
            Object.keys(pageData).forEach(key => {
                formData.append(key, pageData[key]);
            });
            
            navigator.sendBeacon(config.apiUrl, formData);
            hasTracked = true;
        }
    }
    
    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTracking);
    } else {
        // 页面已加载完成
        initTracking();
    }
    
    // 监听页面卸载事件
    window.addEventListener('beforeunload', handlePageUnload);
    window.addEventListener('pagehide', handlePageUnload);
    
    // 导出到全局（用于调试）
    if (typeof window !== 'undefined') {
        window.PVUVTracker = {
            track: sendTrackingRequest,
            hasTracked: () => hasTracked,
            config: config
        };
    }
    
})();