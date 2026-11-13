import RequestService from '../httpRequest';

// 情绪数据接口(来自 Python 语音服务 8003,经 devServer 代理 /resona/emotion)
export default {
    // 所有在线设备的当前情绪快照
    getCurrentEmotion(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/current`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取当前情绪失败:', err)
            })
            .send()
    },
    // 最近高冲突预警事件
    getEmotionAlerts(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alerts`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取情绪预警失败:', err)
            })
            .send()
    },
    // 情绪历史查询(需后端 DB 支持)
    getEmotionHistory(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/emotion/history?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取情绪历史失败:', err)
            })
            .send()
    },
    // 情绪统计数据(按天/周/月聚合)
    getEmotionStats(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/emotion/stats?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取情绪统计失败:', err)
            })
            .send()
    },
    // 情绪元数据(支持的类别列表)
    getEmotionMeta(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/meta`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail(() => {
                // 降级：使用默认4类
                if (callback) {
                    callback({
                        data: {
                            code: 0,
                            data: {
                                emotions: [
                                    { key: 'happy', label: '快乐', emoji: '😊', color: '#FF7A59' },
                                    { key: 'sad', label: '悲伤', emoji: '😢', color: '#6f9cff' },
                                    { key: 'neutral', label: '平静', emoji: '😌', color: '#9aa5c4' },
                                    { key: 'anger', label: '生气', emoji: '😠', color: '#ff5e5e' }
                                ]
                            }
                        }
                    })
                }
            })
            .send()
    },
    // 系统监控统计(来自 Python 8003)
    getMonitorStats(callback) {
        RequestService.sendRequest()
            .url(`/resona/monitor/stats`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取系统监控数据失败:', err)
            })
            .send()
    },
    // D-S 融合蒙特卡洛仿真
    runSimulation(params, callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/simulate`)
            .method('POST')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('仿真请求失败:', err)
            })
            .send()
    }
}
