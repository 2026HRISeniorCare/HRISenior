<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">关怀提醒 · 家属联系 · 安全预警</div>
      <div class="page-sub">用药提醒 / 复诊安排 / 家属紧急联系 / 老人安全实时监测</div>

      <el-tabs v-model="activeTab">
        <!-- ===== 用药提醒 Tab ===== -->
        <el-tab-pane label="💊 用药提醒" name="reminders">
          <el-row class="action-row">
            <el-button type="primary" size="small" @click="openReminderDialog()">+ 新增提醒</el-button>
            <el-select v-model="reminderTypeFilter" placeholder="类型筛选" size="small" clearable style="width:130px;margin-left:8px">
              <el-option label="用药" value="medication" />
              <el-option label="复诊" value="checkup" />
              <el-option label="生日" value="birthday" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-row>
          <el-table :data="reminders" stripe class="mt-12">
            <el-table-column label="类型" width="80">
              <template slot-scope="scope">{{ typeLabel(scope.row.type) }}</template>
            </el-table-column>
            <el-table-column label="时间" width="140" prop="schedule_time" />
            <el-table-column label="关联老人" width="100" prop="elderly_name" />
            <el-table-column label="备注" min-width="160" prop="note" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template slot-scope="scope">
                <el-tag v-if="scope.row.status === 'sent'" type="success" size="small">已发送</el-tag>
                <el-tag v-else-if="scope.row.status === 'confirmed'" type="primary" size="small">已确认</el-tag>
                <el-tag v-else type="info" size="small">待发送</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template slot-scope="scope">
                <el-button type="text" size="small" @click="openReminderDialog(scope.row)">编辑</el-button>
                <el-button type="text" size="small" style="color:#ff5e5e" @click="deleteReminder(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" background layout="prev, pager, next" :total="reminderTotal" :page-size="10" :current-page.sync="reminderPage" @current-change="fetchReminders" />

          <!-- 提醒日志 -->
          <div class="section-title mt-20">提醒发送日志</div>
          <el-table :data="reminderLogs" size="small" stripe>
            <el-table-column label="时间" width="160" prop="sent_time" />
            <el-table-column label="提醒内容" min-width="200" prop="content" />
            <el-table-column label="结果" width="80">
              <template slot-scope="scope">
                <span v-if="scope.row.confirmed">✅</span>
                <span v-else>📤</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ===== 家属联系 Tab ===== -->
        <el-tab-pane label="📞 家属联系" name="contacts">
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="section-title">紧急联系人</div>
              <el-table :data="contacts" size="small" stripe>
                <el-table-column label="姓名" width="80" prop="name" />
                <el-table-column label="电话" width="130" prop="phone" />
                <el-table-column label="关系" width="80" prop="relation" />
                <el-table-column label="关联老人" width="80" prop="elderly_name" />
                <el-table-column label="操作" width="60">
                  <template slot-scope="scope">
                    <el-button type="text" size="small" style="color:#ff5e5e" @click="deleteContact(scope.row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-button type="primary" size="small" class="mt-8" @click="openContactDialog()">+ 添加联系人</el-button>
            </el-col>
            <el-col :span="12">
              <div class="section-title">联系记录</div>
              <el-table :data="contactLogs" size="small" stripe max-height="280">
                <el-table-column label="时间" width="160" prop="time" />
                <el-table-column label="方式" width="60" prop="method" />
                <el-table-column label="摘要" min-width="160" prop="summary" show-overflow-tooltip />
              </el-table>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- ===== 安全预警 Tab ===== -->
        <el-tab-pane label="🚨 安全预警" name="safety">
          <!-- 实时安全状态 -->
          <div class="safety-status" :class="'safety-' + safetyLevel">
            <span class="safety-icon">{{ safetyIcon }}</span>
            <span class="safety-text">{{ safetyText }}</span>
            <span class="safety-time">最近更新: {{ safetyUpdateTime }}</span>
          </div>

          <!-- 危险级别说明 -->
          <el-row :gutter="12" class="mt-12">
            <el-col :span="8"><div class="level-card level-green">🟢 正常<br><small>无异常信号</small></div></el-col>
            <el-col :span="8"><div class="level-card level-yellow">🟡 关注级<br><small>情绪持续低落</small></div></el-col>
            <el-col :span="8"><div class="level-card level-orange">🟠 警告级<br><small>出现负面关键词</small></div></el-col>
          </el-row>
          <el-row :gutter="12" class="mt-8">
            <el-col :span="8"><div class="level-card level-red">🔴 危险级<br><small>明确轻生/自伤表述</small></div></el-col>
          </el-row>

          <!-- 安全事件列表 -->
          <div class="section-title mt-20">安全预警事件</div>
          <el-table :data="safetyAlerts" stripe>
            <el-table-column label="时间" width="160">
              <template slot-scope="scope">{{ scope.row.created_at || '--' }}</template>
            </el-table-column>
            <el-table-column label="级别" width="80">
              <template slot-scope="scope">
                <el-tag v-if="scope.row.level === 'danger'" type="danger" size="small">🔴 危险</el-tag>
                <el-tag v-else-if="scope.row.level === 'warning'" type="warning" size="small">🟠 警告</el-tag>
                <el-tag v-else type="info" size="small">🟡 关注</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="设备" width="120" prop="device_id" />
            <el-table-column label="老人" width="80" prop="elderly_name" />
            <el-table-column label="触发语句" min-width="220" prop="trigger_text" show-overflow-tooltip />
            <el-table-column label="状态" width="110">
              <template slot-scope="scope">
                <el-select v-model="scope.row.handle_status" size="mini" @change="updateSafetyStatus(scope.row)">
                  <el-option label="待处理" value="pending" />
                  <el-option label="已联系家属" value="contacted" />
                  <el-option label="已解除" value="resolved" />
                </el-select>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" background layout="prev, pager, next" :total="safetyTotal" :page-size="10" :current-page.sync="safetyPage" @current-change="fetchSafetyAlerts" />
        </el-tab-pane>
      </el-tabs>

      <!-- 新增/编辑提醒弹窗 -->
      <el-dialog :title="reminderForm.id ? '编辑提醒' : '新增提醒'" :visible.sync="reminderDialogVisible" width="460px">
        <el-form label-width="80px">
          <el-form-item label="类型">
            <el-select v-model="reminderForm.type">
              <el-option label="用药" value="medication" />
              <el-option label="复诊" value="checkup" />
              <el-option label="生日" value="birthday" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item label="时间">
            <el-date-picker v-model="reminderForm.schedule_time" type="datetime" placeholder="选择时间" value-format="yyyy-MM-dd HH:mm:ss" />
          </el-form-item>
          <el-form-item label="重复">
            <el-select v-model="reminderForm.repeat_type">
              <el-option label="一次性" value="once" />
              <el-option label="每天" value="daily" />
              <el-option label="每周" value="weekly" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联老人">
            <el-input v-model="reminderForm.elderly_name" placeholder="老人姓名" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="reminderForm.note" type="textarea" rows="2" placeholder="如：阿司匹林 1 片" />
          </el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="reminderDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveReminder">保存</el-button>
        </span>
      </el-dialog>

      <!-- 新增紧急联系人弹窗 -->
      <el-dialog title="添加紧急联系人" :visible.sync="contactDialogVisible" width="400px">
        <el-form label-width="80px">
          <el-form-item label="姓名"><el-input v-model="contactForm.name" /></el-form-item>
          <el-form-item label="电话"><el-input v-model="contactForm.phone" /></el-form-item>
          <el-form-item label="关系"><el-input v-model="contactForm.relation" placeholder="如：女儿" /></el-form-item>
          <el-form-item label="关联老人"><el-input v-model="contactForm.elderly_name" /></el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="contactDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveContact">保存</el-button>
        </span>
      </el-dialog>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'CareReminders',
  components: { HeaderBar },
  data() {
    return {
      activeTab: 'reminders',
      // 用药提醒
      reminders: [], reminderTotal: 0, reminderPage: 1, reminderTypeFilter: '',
      reminderLogs: [],
      reminderDialogVisible: false,
      reminderForm: { id: '', type: 'medication', schedule_time: '', repeat_type: 'once', elderly_name: '', note: '' },
      // 家属联系
      contacts: [], contactLogs: [],
      contactDialogVisible: false,
      contactForm: { name: '', phone: '', relation: '', elderly_name: '' },
      // 安全预警
      safetyLevel: 'normal', safetyUpdateTime: '--',
      safetyAlerts: [], safetyTotal: 0, safetyPage: 1,
      safetyTimer: null
    }
  },
  computed: {
    safetyIcon() {
      const m = { normal: '🟢', attention: '🟡', warning: '🟠', danger: '🔴' };
      return m[this.safetyLevel] || '🟢';
    },
    safetyText() {
      const m = { normal: '所有老人情绪正常', attention: '有老人情绪持续低落，建议关注', warning: '检测到负面关键词，请及时查看', danger: '⚠ 检测到危险信号，请立即联系家属！' };
      return m[this.safetyLevel] || '正常';
    }
  },
  mounted() {
    this.fetchReminders();
    this.fetchContacts();
    this.fetchSafetyAlerts();
    this.safetyTimer = setInterval(this.fetchSafetyStatus, 3000);
  },
  beforeDestroy() {
    if (this.safetyTimer) clearInterval(this.safetyTimer);
  },
  methods: {
    typeLabel(t) {
      const m = { medication: '💊用药', checkup: '🏥复诊', birthday: '🎂生日', custom: '📋自定义' };
      return m[t] || t;
    },
    // 用药提醒
    fetchReminders() {
      Api.care.getReminders({ page: this.reminderPage, size: 10, type: this.reminderTypeFilter }, ({ data }) => {
        if (data && data.code === 0) {
          this.reminders = (data.data && data.data.records) || [];
          this.reminderTotal = (data.data && data.data.total) || 0;
        }
      });
      Api.care.getReminderLogs({ page: 1, size: 10 }, ({ data }) => {
        if (data && data.code === 0) this.reminderLogs = (data.data && data.data.records) || [];
      });
    },
    openReminderDialog(row) {
      this.reminderForm = row ? { ...row } : { id: '', type: 'medication', schedule_time: '', repeat_type: 'once', elderly_name: '', note: '' };
      this.reminderDialogVisible = true;
    },
    saveReminder() {
      const api = this.reminderForm.id ? Api.care.updateReminder : Api.care.createReminder;
      const payload = this.reminderForm.id ? [this.reminderForm.id, this.reminderForm] : [this.reminderForm];
      api(...payload, ({ data }) => {
        if (data && data.code === 0) {
          this.$message.success('保存成功');
          this.reminderDialogVisible = false;
          this.fetchReminders();
        }
      });
    },
    deleteReminder(row) {
      this.$confirm('确定删除吗？', '提示', { type: 'warning' }).then(() => {
        Api.care.deleteReminder(row.id, ({ data }) => {
          if (data && data.code === 0) { this.$message.success('已删除'); this.fetchReminders(); }
        });
      }).catch(() => {});
    },
    // 家属联系
    fetchContacts() {
      Api.care.getEmergencyContacts('', ({ data }) => {
        if (data && data.code === 0) this.contacts = (data.data && data.data.records) || [];
      });
      Api.care.getContactLogs({ page: 1, size: 15 }, ({ data }) => {
        if (data && data.code === 0) this.contactLogs = (data.data && data.data.records) || [];
      });
    },
    openContactDialog() { this.contactForm = { name: '', phone: '', relation: '', elderly_name: '' }; this.contactDialogVisible = true; },
    saveContact() {
      Api.care.saveEmergencyContact(this.contactForm, ({ data }) => {
        if (data && data.code === 0) { this.$message.success('已添加'); this.contactDialogVisible = false; this.fetchContacts(); }
      });
    },
    deleteContact(row) {
      // 复用 save 接口或走 delete
      this.$confirm('确定删除吗？').then(() => {
        Api.care.saveEmergencyContact({ id: row.id, _delete: true }, ({ data }) => {
          if (data && data.code === 0) { this.$message.success('已删除'); this.fetchContacts(); }
        });
      }).catch(() => {});
    },
    // 安全预警
    fetchSafetyStatus() {
      Api.care.getSafetyStatus(({ data }) => {
        if (data && data.code === 0) {
          this.safetyLevel = (data.data && data.data.level) || 'normal';
          this.safetyUpdateTime = new Date().toLocaleTimeString();
        }
      });
    },
    fetchSafetyAlerts() {
      Api.care.getSafetyAlerts({ page: this.safetyPage, size: 10 }, ({ data }) => {
        if (data && data.code === 0) {
          this.safetyAlerts = (data.data && data.data.records) || [];
          this.safetyTotal = (data.data && data.data.total) || 0;
        }
      });
    },
    updateSafetyStatus(row) {
      Api.care.updateSafetyAlert(row.id, { handle_status: row.handle_status }, () => {
        this.$message.success('状态已更新');
      });
    }
  }
}
</script>

<style scoped>
.emotion-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(145deg, #fff2ec, #fff8f5);
}
.page-main { padding: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #3d4566; }
.page-sub { color: #818cae; margin: 6px 0 18px; }
.action-row { margin-bottom: 8px; }
.section-title { font-weight: 600; color: #3d4566; margin-bottom: 8px; font-size: 15px; }
.mt-8 { margin-top: 8px; }
.mt-12 { margin-top: 12px; }
.mt-20 { margin-top: 20px; }
.pager { margin-top: 10px; text-align: right; }
.safety-status {
  padding: 16px 20px; border-radius: 12px; display: flex; align-items: center; gap: 12px;
  font-size: 18px; font-weight: 600;
}
.safety-normal { background: #ecfdf5; color: #059669; }
.safety-attention { background: #fffbeb; color: #d97706; }
.safety-warning { background: #fff7ed; color: #ea580c; }
.safety-danger { background: #fef2f2; color: #dc2626; }
.safety-time { font-size: 13px; font-weight: 400; color: #818cae; margin-left: auto; }
.level-card {
  padding: 14px; border-radius: 10px; text-align: center; font-weight: 600;
  background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.level-green { border-left: 3px solid #10B981; }
.level-yellow { border-left: 3px solid #F59E0B; }
.level-orange { border-left: 3px solid #f97316; }
.level-red { border-left: 3px solid #ef4444; }
</style>
