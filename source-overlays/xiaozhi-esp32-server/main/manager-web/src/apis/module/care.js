import RequestService from '../httpRequest';

// 关怀提醒 + 安全预警接口(Java 后端)
export default {
    // ===== 用药提醒 =====
    getReminders(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/care/reminders?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取提醒列表失败:', err)
            })
            .send()
    },
    createReminder(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/reminders`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('创建提醒失败:', err)
            })
            .send()
    },
    updateReminder(id, data, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/reminders/${id}`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('更新提醒失败:', err)
            })
            .send()
    },
    deleteReminder(id, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/reminders/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('删除提醒失败:', err)
            })
            .send()
    },
    getReminderLogs(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/care/reminder-logs?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取提醒日志失败:', err)
            })
            .send()
    },

    // ===== 家属联系 =====
    getEmergencyContacts(elderlyId, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/emergency-contacts?elderlyId=${elderlyId || ''}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取紧急联系人失败:', err)
            })
            .send()
    },
    saveEmergencyContact(data, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/emergency-contacts`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('保存紧急联系人失败:', err)
            })
            .send()
    },
    getContactLogs(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/care/contact-logs?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取联系记录失败:', err)
            })
            .send()
    },

    // ===== 安全预警 =====
    getSafetyAlerts(params, callback) {
        const query = new URLSearchParams(params).toString();
        RequestService.sendRequest()
            .url(`/resona/care/safety-alerts?${query}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取安全预警失败:', err)
            })
            .send()
    },
    updateSafetyAlert(id, data, callback) {
        RequestService.sendRequest()
            .url(`/resona/care/safety-alerts/${id}`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('更新安全预警失败:', err)
            })
            .send()
    },
    // 获取最新安全状态(用于 HealthOverview 指示器)
    getSafetyStatus(callback) {
        RequestService.sendRequest()
            .url(`/resona/care/safety-status`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取安全状态失败:', err)
            })
            .send()
    }
}
