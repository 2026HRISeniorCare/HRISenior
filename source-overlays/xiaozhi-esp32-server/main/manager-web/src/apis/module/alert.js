import RequestService from '../httpRequest';

// 情绪预警规则配置接口(Java 后端 + Python 端点)
export default {
    // 获取当前预警配置
    getAlertConfig(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/config`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取预警配置失败:', err)
            })
            .send()
    },
    // 更新预警配置
    updateAlertConfig(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/config`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('更新预警配置失败:', err)
            })
            .send()
    },
    // 预警规则列表
    getAlertRules(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/rules`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取预警规则失败:', err)
            })
            .send()
    },
    // 新增规则
    createAlertRule(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/rules`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('创建预警规则失败:', err)
            })
            .send()
    },
    // 删除规则
    deleteAlertRule(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/rules/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('删除预警规则失败:', err)
            })
            .send()
    },
    // 推送配置到在线设备
    pushConfigToDevices(callback) {
        RequestService.sendRequest()
            .url(`/resona/emotion/alert/config/push`)
            .method('POST')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('推送配置失败:', err)
            })
            .send()
    }
}
