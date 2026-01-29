/**
 * 网易云音乐无损解析 - API安全模块
 * 负责提供安全的API请求方法，确保API调用的安全性
 * 合并了 api-fix.js 的功能，使用相对路径调用后端API
 */

// 后端API地址（使用相对路径）
const backendApiUrl = '';

/**
 * 从文本中提取纯数字ID
 * @param {string} text - 包含ID或链接的文本
 * @returns {string} 纯数字ID，无效则返回原值
 */
function extractPureId(text) {
    if (!text) return text;
    
    const textStr = text.toString();
    
    // 如果已经是纯数字，直接返回
    if (/^\d+$/.test(textStr)) {
        return text;
    }
    
    // 尝试从链接中提取ID参数 - 支持多种格式
    // 1. 普通参数格式: id=123456
    let idMatch = textStr.match(/[?&]id=(\d+)/);
    if (idMatch && idMatch[1]) {
        return idMatch[1]; // 返回纯数字ID
    }
    
    // 2. 编码参数格式: id%3D123456 (即 id= 被编码为 %3D)
    // 更精确的正则表达式，避免捕获额外字符
    idMatch = textStr.match(/[?&]id%3D(\d+)(?:%26|&|$)/i);
    if (idMatch && idMatch[1]) {
        return idMatch[1]; // 返回纯数字ID
    }
    
    // 通用格式：支持 = 或 %3D
    idMatch = textStr.match(/[?&]id(?:%3D|=)(\d+)(?:%26|&|$)/i);
    if (idMatch && idMatch[1]) {
        return idMatch[1]; // 返回纯数字ID
    }
    
    // 作为备用方案，尝试找到独立的长数字序列
    const longNumbers = textStr.match(/\d{6,}/g);
    if(longNumbers && longNumbers.length > 0) {
        return longNumbers[0]; // 返回第一个长数字序列
    }
    
    // 3. 路径格式: /playlist/123456 或 /song/123456
    idMatch = textStr.match(/\/(?:playlist|song)\/(\d+)/i);
    if (idMatch && idMatch[1]) {
        return idMatch[1]; // 返回纯数字ID
    }
    
    // 4. 从原始文本中提取所有数字，取第一个6位以上的数字（通常是ID）
    const allNumbers = textStr.match(/\d{6,}/g);
    if (allNumbers && allNumbers.length > 0) {
        return allNumbers[0];
    }
    
    // 5. 从原始文本中提取所有数字
    const idRegex = /\b(\d+)\b/;
    const matches = textStr.match(idRegex);
    if (matches && matches[1]) {
        return matches[1];
    }
    
    // 如果都找不到，返回原文本
    return text;
}

/**
 * API安全模块
 * 提供安全的API请求方法
 */
const ApiSecurity = (function() {
    /**
     * 安全的API请求方法
     * @param {string} url - API请求地址（会被忽略，使用相对路径）
     * @param {Object} data - 请求数据
     * @param {Object} options - 请求选项
     * @returns {Promise} 返回Promise对象
     */
    async function secureApiRequest(url, data, options = {}) {
        try {
            // 构建完整的后端API URL
            let apiUrl = backendApiUrl;
            
            // 处理不同的action
            if (data.action === 'music') {
                apiUrl += '/song';
            } else if (data.action === 'search') {
                apiUrl += '/search';
            } else if (data.action === 'playlist') {
                apiUrl += '/playlist';
            }
            
            // 添加查询参数
            const params = [];
            if (data.id) {
                // 清理ID参数，确保发送纯数字ID
                const cleanId = extractPureId(data.id);
                params.push(`id=${encodeURIComponent(cleanId)}`);
            } else if (data.url) {
                // 如果使用url参数，也尝试清理
                const cleanId = extractPureId(data.url);
                params.push(`id=${encodeURIComponent(cleanId)}`);
            }
            if (data.name) {
                params.push(`keyword=${encodeURIComponent(data.name)}`);
            }
            if (data.level) {
                params.push(`level=${encodeURIComponent(data.level)}`);
            }
            if (data.limit) {
                params.push(`limit=${encodeURIComponent(data.limit)}`);
            }
            if (data.type) {
                params.push(`type=${encodeURIComponent(data.type)}`);
            }
            
            const queryString = params.join('&');
            if (queryString) {
                apiUrl += '?' + queryString;
            }
            
            // 发送请求
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // 解析响应
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }
    
    /**
     * 生成安全的请求参数
     * @param {Object} params - 原始请求参数
     * @returns {Object} 安全的请求参数
     */
    function generateSecureParams(params) {
        // 这里可以添加一些加密处理逻辑
        // 例如：对参数进行签名、添加时间戳等
        const timestamp = Date.now();
        return {
            ...params,
            timestamp,
            // 可以添加其他安全参数
        };
    }
    
    /**
     * 验证API响应的安全性
     * @param {Object} response - API响应数据
     * @returns {boolean} 验证结果
     */
    function validateApiResponse(response) {
        // 这里可以添加一些响应验证逻辑
        // 例如：验证签名、检查时间戳等
        if (!response) {
            return false;
        }
        return true;
    }
    
    /**
     * 处理API错误
     * @param {Error} error - 错误对象
     */
    function handleApiError(error) {
        console.error('API错误:', error);
        // 这里可以添加一些错误处理逻辑
        // 例如：显示错误提示、记录错误日志等
    }
    
    /**
     * 检查API请求频率
     * @returns {boolean} 是否允许请求
     */
    function checkRequestRate() {
        // 这里可以添加请求频率限制逻辑
        // 例如：记录请求时间，限制每分钟的请求次数
        return true;
    }
    
    // 公开的API
    return {
        secureApiRequest: secureApiRequest,
        generateSecureParams: generateSecureParams,
        validateApiResponse: validateApiResponse,
        handleApiError: handleApiError,
        checkRequestRate: checkRequestRate
    };
})();

// 确保ApiSecurity对象在全局可用
if (typeof window !== 'undefined') {
    window.ApiSecurity = ApiSecurity;
}

// 导出模块（如果在CommonJS环境中）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApiSecurity;
}

console.log('API安全模块加载完成');

// 防止任何形式的重定向
window.addEventListener('beforeunload', function(e) {
    // 取消事件
    e.preventDefault();
    // Chrome需要设置returnValue
    e.returnValue = '';
});

// 监控location变化，防止重定向
const originalAssign = window.location.assign;
window.location.assign = function(url) {
    if (url.includes('kanxizai.cn')) {
        console.warn('阻止了到kanxizai.cn的重定向:', url);
        return;
    }
    originalAssign.call(window.location, url);
};

// 监控replace方法，防止重定向
const originalReplace = window.location.replace;
window.location.replace = function(url) {
    if (url.includes('kanxizai.cn')) {
        console.warn('阻止了到kanxizai.cn的重定向:', url);
        return;
    }
    originalReplace.call(window.location, url);
};
