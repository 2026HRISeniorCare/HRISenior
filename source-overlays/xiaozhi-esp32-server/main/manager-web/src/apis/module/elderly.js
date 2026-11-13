import RequestService from '../httpRequest';

// 老人健康档案接口(Java 后端)
export default {
    // 老人列表
    getElderlyList(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/elderly/profiles?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取老人列表失败:', err)
            })
            .send()
    },
    // 老人详情(含情绪摘要、关联设备、关怀提醒)
    getElderlyDetail(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/elderly/profiles/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取老人详情失败:', err)
            })
            .send()
    },
    // 新增/编辑老人档案
    saveElderlyProfile(data, callback) {
        const isEdit = data.id;
        RequestService.sendRequest()
            .url(isEdit ? `/resona/elderly/profiles/${data.id}` : `/resona/elderly/profiles`)
            .method(isEdit ? 'PUT' : 'POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('保存老人档案失败:', err)
            })
            .send()
    },
    // 删除老人档案
    deleteElderlyProfile(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/elderly/profiles/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('删除老人档案失败:', err)
            })
            .send()
    }
}
