import RequestService from '../httpRequest';

// 语料库管理接口(Java 后端)
export default {
    // 语料列表(分页+筛选)
    getCorpusList(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取语料列表失败:', err)
            })
            .send()
    },
    // 单条语料详情
    getCorpusDetail(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取语料详情失败:', err)
            })
            .send()
    },
    // 人工标注
    annotateDialog(id, data, callback) {
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs/${id}/annotate`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('标注语料失败:', err)
            })
            .send()
    },
    // 批量标注
    batchLabel(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs/batch-label`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('批量标注失败:', err)
            })
            .send()
    },
    // 导出训练集
    exportCorpus(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs/export?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('导出语料失败:', err)
            })
            .send()
    },
    // 删除语料
    deleteCorpus(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/corpus/dialogs/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('删除语料失败:', err)
            })
            .send()
    },
    // 语料统计
    getCorpusStats(callback) {
        RequestService.sendRequest()
            .url(`/resona/corpus/stats`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取语料统计失败:', err)
            })
            .send()
    }
}
