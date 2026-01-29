/**
 * 网易云音乐无损解析 - 音质选择模块
 * @author kanxizai
 * @version 1.0
 * @description 负责处理音质选择相关功能
 */

/**
 * 音质选择器模块
 * @namespace QualitySelector
 */
const QualitySelector = (function() {
    // 音质配置数据
    const qualityOptions = [
        { value: "standard", text: "标准(看歌曲)", icon: "fas fa-music text-muted", badge: "128kbps" },
        { value: "exhigh", text: "极高(看歌曲)", icon: "fas fa-star text-warning", badge: "HQ" },
        { value: "lossless", text: "无损(VIP)", icon: "fas fa-gem text-info", badge: "SQ" },
        { value: "hires", text: "高解析度无损(VIP)", icon: "fas fa-crown text-warning", badge: "Hi-Res" },
        { value: "jyeffect", text: "高清臻音(VIP)", icon: "fas fa-headphones text-success", badge: "Spatial Audio" },
        { value: "jymaster", text: "超清母带(SVIP)", icon: "fas fa-certificate text-danger", badge: "Master" },
        { value: "sky", text: "沉浸环绕声(SVIP)", icon: "fas fa-cloud text-primary", badge: "Surround Audio" },
        { value: "dolby", text: "杜比全景声(SVIP)", icon: "fas fa-compact-disc text-danger", badge: "Dolby Atmos" }
    ];
    
    /**
     * 初始化音质选择器
     * @function init
     * @memberof QualitySelector
     */
    function init() {
        // 动态生成音质选择器
        generateQualityOptionsHTML('#search-quality-container', 'search-quality-option', 'searchQualityOptions');
        generateQualityOptionsHTML('#id-quality-container', 'quality-option', 'qualityOptions');
        generateQualityOptionsHTML('#playlist-quality-container', 'playlist-quality-option', 'playlistQualityOptions');
        
        // 从本地存储中获取上次选择的音质
        loadSavedQuality();
        
        // 绑定事件处理
        bindEvents();
    }
    
    /**
     * 从本地存储加载保存的音质设置
     * @function loadSavedQuality
     * @memberof QualitySelector
     * @private
     */
    function loadSavedQuality() {
        const savedQuality = localStorage.getItem('selectedQuality');
        if (savedQuality) {
            const savedQualityValue = localStorage.getItem('selectedQualityValue');
            updateQualityUI(savedQualityValue, savedQuality);
        }
    }
    
    /**
     * 更新音质UI显示
     * @function updateQualityUI
     * @memberof QualitySelector
     * @param {string} value - 音质值
     * @param {string} text - 音质显示文本
     */
    function updateQualityUI(value, text) {
        // 更新ID解析卡片中的音质选择
        $('#level').val(value);
        $('#selectedQuality').text(text);
        
        // 更新搜索卡片中的音质选择
        $('#search_level').val(value);
        $('#searchSelectedQuality').text(text);
        
        // 更新歌单解析卡片中的音质选择
        $('#playlist_level').val(value);
        $('#playlistSelectedQuality').text(text);
    }
    
    /**
     * 保存音质选择到本地存储
     * @function saveQualitySelection
     * @memberof QualitySelector
     * @param {string} value - 音质值
     * @param {string} text - 音质显示文本
     */
    function saveQualitySelection(value, text) {
        localStorage.setItem('selectedQuality', text);
        localStorage.setItem('selectedQualityValue', value);
    }
    
    /**
     * 绑定音质选择相关事件
     * @function bindEvents
     * @memberof QualitySelector
     * @private
     */
    function bindEvents() {
        // ID解析卡片中的音质选择处理
        $('.quality-option').on('click', function () {
            const value = $(this).data('value');
            const text = $(this).find('span:first').text();
            
            updateQualityUI(value, text);
            saveQualitySelection(value, text);
            
            $('#qualityOptions').collapse('hide');
        });

        // 搜索卡片中的音质选择处理
        $('.search-quality-option').on('click', function () {
            const value = $(this).data('value');
            const text = $(this).find('span:first').text();
            
            updateQualityUI(value, text);
            saveQualitySelection(value, text);
            
            $('#searchQualityOptions').collapse('hide');
        });
        
        // 歌单解析卡片中的音质选择处理
        $('.playlist-quality-option').on('click', function () {
            const value = $(this).data('value');
            const text = $(this).find('span:first').text();
            
            updateQualityUI(value, text);
            saveQualitySelection(value, text);
            
            $('#playlistQualityOptions').collapse('hide');
        });
    }
    
    /**
     * 动态生成音质选择器HTML
     * @function generateQualityOptionsHTML
     * @memberof QualitySelector
     * @param {string} targetElement - 目标元素选择器
     * @param {string} optionClass - 选项CSS类名
     * @param {string} containerId - 容器ID
     */
    function generateQualityOptionsHTML(targetElement, optionClass, containerId) {
        let html = `
            <div class="card">
                <div class="card-header p-0">
                    <button class="btn btn-link w-100 text-start text-decoration-none d-flex justify-content-between align-items-center p-3"
                        type="button" data-bs-toggle="collapse" data-bs-target="#${containerId}">
                        <span><i class="fas fa-music me-2"></i>当前选择：<span id="${getQualitySpanId(containerId)}"
                                class="fw-bold text-primary">标准音质</span></span>
                        <i class="fas fa-chevron-down"></i>
                    </button>
                </div>
                <div id="${containerId}" class="collapse">
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush">`;
        
        qualityOptions.forEach(option => {
            html += `
                <button type="button"
                    class="list-group-item list-group-item-action d-flex justify-content-between align-items-center ${optionClass}"
                    data-value="${option.value}">
                    <span><i class="${option.icon} me-2"></i>${option.text}</span>
                    <span class="badge bg-light text-dark">${option.badge}</span>
                </button>`;
        });
        
        html += `
                        </div>
                    </div>
                </div>
            </div>
            <input type="hidden" id="${getQualityInputId(containerId)}" value="standard">`;
        
        $(targetElement).html(html);
        
        // 重新绑定事件
        bindEvents();
    }
    
    /**
     * 根据容器ID获取对应的音质显示元素ID
     * @function getQualitySpanId
     * @memberof QualitySelector
     * @private
     * @param {string} containerId - 容器ID
     * @returns {string} 音质显示元素ID
     */
    function getQualitySpanId(containerId) {
        if (containerId === 'qualityOptions') {
            return 'selectedQuality';
        } else if (containerId === 'searchQualityOptions') {
            return 'searchSelectedQuality';
        } else if (containerId === 'playlistQualityOptions') {
            return 'playlistSelectedQuality';
        }
        return 'selectedQuality'; // 默认值
    }
    
    /**
     * 根据容器ID获取对应的音质输入元素ID
     * @function getQualityInputId
     * @memberof QualitySelector
     * @private
     * @param {string} containerId - 容器ID
     * @returns {string} 音质输入元素ID
     */
    function getQualityInputId(containerId) {
        if (containerId === 'qualityOptions') {
            return 'level';
        } else if (containerId === 'searchQualityOptions') {
            return 'search_level';
        } else if (containerId === 'playlistQualityOptions') {
            return 'playlist_level';
        }
        return 'level'; // 默认值
    }
    
    // 公开API
    return {
        init: init,
        updateQualityUI: updateQualityUI,
        generateQualityOptionsHTML: generateQualityOptionsHTML
    };
})();

// 确保DOM加载完成后初始化
$(document).ready(function() {
    // 初始化音质选择器
    QualitySelector.init();
});