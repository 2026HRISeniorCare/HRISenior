import RequestService from '../httpRequest';

// 用户反馈收集接口(Java 后端)
export default {
    // 反馈列表
    getFeedbackList(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/feedback/list?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取反馈列表失败:', err)
            })
            .send()
    },
    // 提交反馈
    submitFeedback(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/feedback`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('提交反馈失败:', err)
            })
            .send()
    },
    // 反馈统计
    getFeedbackStats(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/feedback/stats?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取反馈统计失败:', err)
            })
            .send()
    },
    // 试用会话管理
    getSessions(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/feedback/sessions?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取试用会话失败:', err)
            })
            .send()
    },
    createSession(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/feedback/sessions`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('创建试用会话失败:', err)
            })
            .send()
    }
}
