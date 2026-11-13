<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">老人健康档案</div>
      <div class="page-sub">管理每位老人的基本信息、关联设备、情绪趋势和关怀提醒</div>

      <!-- 老人列表 -->
      <el-row :gutter="20">
        <el-col :span="7">
          <el-card class="list-card" shadow="never">
            <div class="card-header">
              <span class="card-title">老人列表</span>
              <el-button type="primary" size="mini" icon="el-icon-plus" circle @click="openProfileDialog()" />
            </div>
            <div v-if="elderlyList.length === 0" class="empty-list">暂无老人档案，点击 + 新建</div>
            <div v-for="item in elderlyList" :key="item.id" class="elderly-item"
              :class="{ 'item-active': selectedId === item.id }" @click="selectElderly(item)">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-sub">{{ item.age ? item.age + '岁' : '--' }} · {{ item.gender || '--' }}</div>
              <div class="item-device" v-if="item.device_id">📱 {{ item.device_id }}</div>
            </div>
          </el-card>
        </el-col>

        <!-- 详情区 -->
        <el-col :span="17" v-if="selectedProfile">
          <el-card class="detail-card" shadow="never">
            <div class="card-header">
              <span class="card-title">{{ selectedProfile.name }} 的档案</span>
              <div>
                <el-button size="small" @click="openProfileDialog(selectedProfile)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteProfile">删除</el-button>
              </div>
            </div>

            <el-row :gutter="16">
              <!-- 基本信息 -->
              <el-col :span="12">
                <div class="info-block">
                  <div class="info-title">基本信息</div>
                  <div class="info-row"><span class="info-lbl">姓名</span><span>{{ selectedProfile.name || '--' }}</span></div>
                  <div class="info-row"><span class="info-lbl">年龄</span><span>{{ selectedProfile.age || '--' }} 岁</span></div>
                  <div class="info-row"><span class="info-lbl">性别</span><span>{{ selectedProfile.gender || '--' }}</span></div>
                  <div class="info-row"><span class="info-lbl">紧急联系人</span><span>{{ selectedProfile.emergency_contact || '--' }}</span></div>
                  <div class="info-row"><span class="info-lbl">紧急电话</span><span style="color:#ff5e5e">{{ selectedProfile.emergency_phone || '--' }}</span></div>
                  <div class="info-row"><span class="info-lbl">病史</span>
                    <el-tag v-for="tag in (selectedProfile.medical_tags || [])" :key="tag" size="mini" style="margin-right:4px">{{ tag }}</el-tag>
                  </div>
                </div>
              </el-col>

              <!-- 关联设备 + 情绪摘要 -->
              <el-col :span="12">
                <div class="info-block">
                  <div class="info-title">关联设备</div>
                  <div class="info-row"><span class="info-lbl">设备ID</span><span>{{ selectedProfile.device_id || '未绑定' }}</span></div>
                  <div class="info-row"><span class="info-lbl">在线状态</span>
                    <el-tag v-if="selectedProfile.online" type="success" size="mini">在线</el-tag>
                    <el-tag v-else type="info" size="mini">离线</el-tag>
                  </div>
                </div>
                <div class="info-block mt-12">
                  <div class="info-title">情绪趋势摘要</div>
                  <div ref="emotionMiniPie" class="mini-pie"></div>
                </div>
              </el-col>
            </el-row>

            <!-- 关怀提醒列表 -->
            <div class="info-block mt-16">
              <div class="info-title">关怀提醒</div>
              <el-table :data="elderlyReminders" size="small" stripe v-if="elderlyReminders.length > 0">
                <el-table-column label="类型" width="80"><template slot-scope="s">{{ s.row.type }}</template></el-table-column>
                <el-table-column label="时间" width="160" prop="schedule_time" />
                <el-table-column label="备注" min-width="160" prop="note" />
                <el-table-column label="状态" width="80">
                  <template slot-scope="s"><el-tag v-if="s.row.status==='sent'" type="success" size="mini">已发</el-tag><el-tag v-else type="info" size="mini">待发</el-tag></template>
                </el-table-column>
              </el-table>
              <div v-else class="no-data">暂无提醒</div>
            </div>
          </el-card>
        </el-col>

        <!-- 未选中时 -->
        <el-col :span="17" v-else>
          <div class="no-select">👈 请从左侧列表选择一位老人查看详情</div>
        </el-col>
      </el-row>

      <!-- 编辑档案弹窗 -->
      <el-dialog :title="profileForm.id ? '编辑档案' : '新建档案'" :visible.sync="profileDialogVisible" width="480px">
        <el-form label-width="90px">
          <el-form-item label="姓名"><el-input v-model="profileForm.name" /></el-form-item>
          <el-form-item label="年龄"><el-input-number v-model="profileForm.age" :min="40" :max="120" /></el-form-item>
          <el-form-item label="性别">
            <el-select v-model="profileForm.gender"><el-option label="男" value="男" /><el-option label="女" value="女" /></el-select>
          </el-form-item>
          <el-form-item label="紧急联系人"><el-input v-model="profileForm.emergency_contact" /></el-form-item>
          <el-form-item label="紧急电话"><el-input v-model="profileForm.emergency_phone" /></el-form-item>
          <el-form-item label="病史标签">
            <el-select v-model="profileForm.medical_tags" multiple filterable allow-create placeholder="输入病史标签，回车添加">
              <el-option label="高血压" value="高血压" /><el-option label="糖尿病" value="糖尿病" />
              <el-option label="心脏病" value="心脏病" /><el-option label="关节炎" value="关节炎" />
              <el-option label="阿尔茨海默" value="阿尔茨海默" /><el-option label="抑郁症" value="抑郁症" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联设备"><el-input v-model="profileForm.device_id" placeholder="设备ID" /></el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="profileDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveProfile">保存</el-button>
        </span>
      </el-dialog>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

export default {
  name: 'ElderlyProfile',
  components: { HeaderBar },
  data() {
    return {
      elderlyList: [],
      selectedId: null,
      selectedProfile: null,
      elderlyReminders: [],
      profileDialogVisible: false,
      profileForm: { id: '', name: '', age: 70, gender: '男', emergency_contact: '', emergency_phone: '', medical_tags: [], device_id: '' },
      emotionMiniPie: null
    }
  },
  mounted() { this.fetchList(); },
  beforeDestroy() { if (this.emotionMiniPie) this.emotionMiniPie.dispose(); },
  methods: {
    fetchList() {
      Api.elderly.getElderlyList({ page: 1, size: 50 }, ({ data }) => {
        if (data && data.code === 0) this.elderlyList = (data.data && data.data.records) || [];
      });
    },
    selectElderly(item) {
      this.selectedId = item.id;
      Api.elderly.getElderlyDetail(item.id, ({ data }) => {
        if (data && data.code === 0) {
          this.selectedProfile = data.data || {};
          this.elderlyReminders = (data.data && data.data.reminders) || [];
          this.$nextTick(() => this.renderMiniPie(data.data));
        }
      });
    },
    renderMiniPie(d) {
      if (!this.$refs.emotionMiniPie) return;
      if (!this.emotionMiniPie) this.emotionMiniPie = echarts.init(this.$refs.emotionMiniPie);
      const dist = (d && d.emotion_distribution) || { happy: 0, sad: 0, neutral: 0, anger: 0 };
      this.emotionMiniPie.setOption({
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie', radius: ['40%', '70%'],
          data: [
            { value: dist.happy || 0, name: '快乐', itemStyle: { color: '#FF7A59' } },
            { value: dist.sad || 0, name: '悲伤', itemStyle: { color: '#6f9cff' } },
            { value: dist.neutral || 0, name: '平静', itemStyle: { color: '#9aa5c4' } },
            { value: dist.anger || 0, name: '生气', itemStyle: { color: '#ff5e5e' } }
          ]
        }]
      });
    },
    openProfileDialog(row) {
      this.profileForm = row ? { ...row, medical_tags: row.medical_tags || [] } : { id: '', name: '', age: 70, gender: '男', emergency_contact: '', emergency_phone: '', medical_tags: [], device_id: '' };
      this.profileDialogVisible = true;
    },
    saveProfile() {
      Api.elderly.saveElderlyProfile(this.profileForm, ({ data }) => {
        if (data && data.code === 0) { this.$message.success('保存成功'); this.profileDialogVisible = false; this.fetchList(); }
      });
    },
    deleteProfile() {
      this.$confirm('确定删除该老人档案吗？相关数据将被清除', '警告', { type: 'warning' }).then(() => {
        Api.elderly.deleteElderlyProfile(this.selectedId, ({ data }) => {
          if (data && data.code === 0) { this.$message.success('已删除'); this.selectedId = null; this.selectedProfile = null; this.fetchList(); }
        });
      }).catch(() => {});
    }
  }
}
</script>

<style scoped>
.emotion-page { min-height: 100vh; display: flex; flex-direction: column; background: linear-gradient(145deg, #fff2ec, #fff8f5); }
.page-main { padding: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #3d4566; }
.page-sub { color: #818cae; margin: 6px 0 18px; }
.list-card, .detail-card { border-radius: 14px; border: none; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.card-title { font-weight: 600; color: #3d4566; }
.elderly-item { padding: 12px 14px; border-radius: 10px; cursor: pointer; margin-bottom: 6px; transition: background .2s; }
.elderly-item:hover { background: #fff2ec; }
.elderly-item.item-active { background: #FF7A59; color: #fff; }
.item-name { font-weight: 600; font-size: 15px; }
.item-sub { font-size: 12px; margin-top: 2px; }
.item-device { font-size: 11px; margin-top: 2px; opacity: 0.8; }
.empty-list, .no-select, .no-data { text-align: center; color: #818cae; padding: 40px 0; }
.info-block { background: #fdf7f4; border-radius: 10px; padding: 14px; }
.info-title { font-weight: 600; color: #3d4566; margin-bottom: 8px; font-size: 14px; }
.info-row { display: flex; padding: 3px 0; font-size: 13px; }
.info-lbl { color: #818cae; width: 80px; flex-shrink: 0; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.mini-pie { width: 100%; height: 180px; }

@media (max-width: 768px) {
  .el-row { flex-direction: column; }
  .el-col { width: 100% !important; margin-bottom: 10px; }
  .list-card { max-height: 200px; overflow-y: auto; }
  .elderly-item { padding: 8px 10px; font-size: 13px; }
  .info-row { font-size: 12px; }
  .info-lbl { width: 65px; }
  .mini-pie { height: 150px; }
  .mt-16 { margin-top: 8px; }
}
</style>
