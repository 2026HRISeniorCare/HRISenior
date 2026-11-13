<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">用户反馈收集</div>
      <div class="page-sub">收集老人和家属的试用反馈，评估系统效果，闭环迭代</div>

      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stat-row">
        <el-col :span="6"><div class="stat-card"><div class="stat-num">{{ stats.avgRating || '--' }}</div><div class="stat-lbl">平均评分</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="stat-num">{{ stats.emotionAccuracy || '--' }}%</div><div class="stat-lbl">情绪准确率</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="stat-num">{{ stats.totalFeedbacks || 0 }}</div><div class="stat-lbl">总反馈数</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="stat-num">{{ stats.totalSessions || 0 }}</div><div class="stat-lbl">试用会话数</div></div></el-col>
      </el-row>

      <el-tabs v-model="activeTab">
        <!-- 反馈列表 -->
        <el-tab-pane label="反馈记录" name="list">
          <el-table :data="feedbackList" stripe>
            <el-table-column label="时间" width="160">
              <template slot-scope="scope">{{ scope.row.created_at || '--' }}</template>
            </el-table-column>
            <el-table-column label="试用会话" width="120" prop="session_name" />
            <el-table-column label="老人" width="80" prop="elderly_name" />
            <el-table-column label="评分" width="160">
              <template slot-scope="scope">
                <el-rate :value="scope.row.rating" disabled show-score text-color="#FF7A59" />
              </template>
            </el-table-column>
            <el-table-column label="情绪判断" width="90">
              <template slot-scope="scope">
                <el-tag v-if="scope.row.emotion_accurate" type="success" size="small">准确</el-tag>
                <el-tag v-else type="danger" size="small">不准</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="评价内容" min-width="200" prop="comment" show-overflow-tooltip />
          </el-table>
          <el-pagination class="pager" background layout="prev, pager, next" :total="feedbackTotal" :page-size="10" :current-page.sync="fbPage" @current-change="fetchFeedbacks" />
        </el-tab-pane>

        <!-- 统计分析 -->
        <el-tab-pane label="统计分析" name="stats">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-card class="chart-card" shadow="never">
                <div class="panel-title">评分趋势</div>
                <div ref="ratingTrend" class="chart-box"></div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="chart-card" shadow="never">
                <div class="panel-title">情绪准确率</div>
                <div ref="accuracyPie" class="chart-box"></div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 试用管理 -->
        <el-tab-pane label="试用管理" name="sessions">
          <el-button type="primary" size="small" class="mb-12" @click="openSessionDialog()">+ 新建试用会话</el-button>
          <el-table :data="sessions" stripe>
            <el-table-column label="会话名称" width="140" prop="name" />
            <el-table-column label="老人" width="80" prop="elderly_name" />
            <el-table-column label="设备" width="140" prop="device_id" />
            <el-table-column label="开始时间" width="160" prop="start_time" />
            <el-table-column label="状态" width="90">
              <template slot-scope="scope">
                <el-tag v-if="scope.row.status === 'active'" type="success" size="small">进行中</el-tag>
                <el-tag v-else type="info" size="small">已结束</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template slot-scope="scope">
                <el-button v-if="scope.row.status === 'active'" type="text" size="small" @click="endSession(scope.row)">结束</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <!-- 新建试用会话弹窗 -->
      <el-dialog title="新建试用会话" :visible.sync="sessionDialogVisible" width="420px">
        <el-form label-width="80px">
          <el-form-item label="会话名称"><el-input v-model="sessionForm.name" placeholder="如：张奶奶第一轮试用" /></el-form-item>
          <el-form-item label="老人姓名"><el-input v-model="sessionForm.elderly_name" /></el-form-item>
          <el-form-item label="关联设备"><el-input v-model="sessionForm.device_id" /></el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="sessionDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createSession">创建并开始</el-button>
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
  name: 'FeedbackManagement',
  components: { HeaderBar },
  data() {
    return {
      activeTab: 'list',
      stats: { avgRating: '--', emotionAccuracy: '--', totalFeedbacks: 0, totalSessions: 0 },
      feedbackList: [], feedbackTotal: 0, fbPage: 1,
      sessions: [],
      sessionDialogVisible: false,
      sessionForm: { name: '', elderly_name: '', device_id: '' },
      ratingTrend: null, accuracyPie: null
    }
  },
  mounted() {
    this.fetchFeedbacks();
    this.fetchSessions();
    this.fetchStats();
  },
  beforeDestroy() {
    if (this.ratingTrend) this.ratingTrend.dispose();
    if (this.accuracyPie) this.accuracyPie.dispose();
  },
  methods: {
    fetchFeedbacks() {
      Api.feedback.getFeedbackList({ page: this.fbPage, size: 10 }, ({ data }) => {
        if (data && data.code === 0) {
          this.feedbackList = (data.data && data.data.records) || [];
          this.feedbackTotal = (data.data && data.data.total) || 0;
        }
      });
    },
    fetchStats() {
      Api.feedback.getFeedbackStats({}, ({ data }) => {
        if (data && data.code === 0) {
          const d = data.data || {};
          this.stats.avgRating = d.avg_rating ? Number(d.avg_rating).toFixed(1) : '--';
          this.stats.emotionAccuracy = d.emotion_accuracy ? Math.round(Number(d.emotion_accuracy) * 100) : '--';
          this.stats.totalFeedbacks = d.total_feedbacks || 0;
          this.stats.totalSessions = d.total_sessions || 0;
          this.$nextTick(() => this.renderCharts(d));
        }
      });
    },
    fetchSessions() {
      Api.feedback.getSessions({ page: 1, size: 20 }, ({ data }) => {
        if (data && data.code === 0) this.sessions = (data.data && data.data.records) || [];
      });
    },
    openSessionDialog() { this.sessionForm = { name: '', elderly_name: '', device_id: '' }; this.sessionDialogVisible = true; },
    createSession() {
      Api.feedback.createSession(this.sessionForm, ({ data }) => {
        if (data && data.code === 0) { this.$message.success('会话已创建'); this.sessionDialogVisible = false; this.fetchSessions(); }
      });
    },
    endSession(row) {
      Api.feedback.createSession({ id: row.id, status: 'ended' }, ({ data }) => {
        if (data && data.code === 0) { this.$message.success('已结束'); this.fetchSessions(); }
      });
    },
    renderCharts(d) {
      if (this.$refs.ratingTrend) {
        if (!this.ratingTrend) this.ratingTrend = echarts.init(this.$refs.ratingTrend);
        const labels = (d.rating_trend_labels || []).slice(-20);
        const vals = (d.rating_trend_values || []).slice(-20);
        this.ratingTrend.setOption({
          tooltip: { trigger: 'axis' },
          grid: { left: 45, right: 15, top: 10, bottom: 25 },
          xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
          yAxis: { type: 'value', min: 0, max: 5, name: '分' },
          series: [{ type: 'line', smooth: true, data: vals, itemStyle: { color: '#FF7A59' }, areaStyle: { opacity: 0.15 } }]
        });
      }
      if (this.$refs.accuracyPie) {
        if (!this.accuracyPie) this.accuracyPie = echarts.init(this.$refs.accuracyPie);
        const acc = d.emotion_accuracy ? Math.round(Number(d.emotion_accuracy) * 100) : 0;
        this.accuracyPie.setOption({
          tooltip: { trigger: 'item' },
          series: [{
            type: 'pie', radius: ['50%', '75%'],
            data: [
              { value: acc, name: '准确', itemStyle: { color: '#10B981' } },
              { value: 100 - acc, name: '不准确', itemStyle: { color: '#ff5e5e' } }
            ],
            label: { formatter: '{b}: {c}%' }
          }]
        });
      }
    }
  }
}
</script>

<style scoped>
.emotion-page { min-height: 100vh; display: flex; flex-direction: column; background: linear-gradient(145deg, #fff2ec, #fff8f5); }
.page-main { padding: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #3d4566; }
.page-sub { color: #818cae; margin: 6px 0 18px; }
.stat-row { margin-bottom: 16px; }
.stat-card { background: #fff; border-radius: 14px; padding: 18px 16px; text-align: center; box-shadow: 0 4px 16px rgba(255, 122, 89, 0.08); }
.stat-num { font-size: 28px; font-weight: 700; color: #FF7A59; }
.stat-lbl { color: #818cae; margin-top: 4px; font-size: 13px; }
.mb-12 { margin-bottom: 12px; }
.pager { margin-top: 10px; text-align: right; }
.chart-card { border-radius: 14px; border: none; }
.panel-title { font-weight: 600; color: #3d4566; margin-bottom: 8px; }
.chart-box { width: 100%; height: 280px; }
</style>
