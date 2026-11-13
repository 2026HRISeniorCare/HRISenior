<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">健康概览面板</div>
      <div class="page-sub">安安陪伴下的老人整体状态概览</div>

      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-num">{{ onlineCount }}</div>
          <div class="stat-lbl">在线设备</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ alertCount }}</div>
          <div class="stat-lbl">情绪预警(累计)</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ dominantCn }}</div>
          <div class="stat-lbl">当前主导情绪</div>
        </div>
      </div>

      <div class="panel-row">
        <el-card class="panel" shadow="never">
          <div class="panel-title">情绪分布(在线设备实时)</div>
          <div ref="pie" class="pie-chart"></div>
        </el-card>

        <el-card class="panel" shadow="never">
          <div class="panel-title">关怀提醒</div>
          <ul class="care-list">
            <li v-for="(tip, i) in careTips" :key="i">
              <span class="dot"></span>{{ tip }}
            </li>
          </ul>
        </el-card>
      </div>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

export default {
  name: 'HealthOverview',
  components: { HeaderBar },
  data() {
    return {
      onlineCount: 0,
      alertCount: 0,
      dominantCn: '--',
      pie: null,
      timer: null
    }
  },
  computed: {
    careTips() {
      const tips = ['安安会持续陪伴老人聊天,缓解孤独感。'];
      if (this.dominantCn === '悲伤') tips.push('检测到情绪偏低,建议家人多陪伴或致电问候。');
      if (this.alertCount > 0) tips.push('存在情绪冲突预警,请前往「情绪预警」查看详情。');
      if (this.onlineCount === 0) tips.push('当前无在线设备,请确认设备联网。');
      return tips;
    }
  },
  mounted() {
    this.poll();
    this.timer = setInterval(this.poll, 3000);
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer);
    if (this.pie) this.pie.dispose();
  },
  methods: {
    cnLabel(k) {
      const m = { happy: '快乐', sad: '悲伤', neutral: '平静', anger: '生气' };
      return m[k] || '未知';
    },
    poll() {
      Api.emotion.getCurrentEmotion(({ data }) => {
        if (data && data.code === 0) {
          const devices = (data.data && data.data.devices) || [];
          this.onlineCount = (data.data && data.data.online) || 0;
          // 聚合各情绪计数(以每台设备主导情绪计)
          const counts = { happy: 0, sad: 0, neutral: 0, anger: 0 };
          devices.forEach(d => { if (counts[d.dominant] !== undefined) counts[d.dominant]++; });
          const top = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
          this.dominantCn = devices.length ? this.cnLabel(top) : '--';
          this.$nextTick(() => this.renderPie(counts));
        }
      });
      Api.emotion.getEmotionAlerts(({ data }) => {
        if (data && data.code === 0) this.alertCount = (data.data || []).length;
      });
    },
    renderPie(counts) {
      if (!this.$refs.pie) return;
      if (!this.pie) this.pie = echarts.init(this.$refs.pie);
      this.pie.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        series: [{
          type: 'pie', radius: ['40%', '68%'],
          data: [
            { value: counts.happy, name: '快乐', itemStyle: { color: '#FF7A59' } },
            { value: counts.sad, name: '悲伤', itemStyle: { color: '#6f9cff' } },
            { value: counts.neutral, name: '平静', itemStyle: { color: '#9aa5c4' } },
            { value: counts.anger, name: '生气', itemStyle: { color: '#ff5e5e' } }
          ]
        }]
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
.stat-row { display: flex; gap: 20px; margin-bottom: 20px; }
.stat-card {
  flex: 1; background: #fff; border-radius: 14px; padding: 24px; text-align: center;
  box-shadow: 0 4px 16px rgba(255, 122, 89, 0.08);
}
.stat-num { font-size: 32px; font-weight: 700; color: #FF7A59; }
.stat-lbl { color: #818cae; margin-top: 8px; }
.panel-row { display: flex; gap: 20px; }
.panel { flex: 1; border-radius: 14px; border: none; }
.panel-title { font-weight: 600; color: #3d4566; margin-bottom: 12px; }
.pie-chart { width: 100%; height: 300px; }
.care-list { list-style: none; padding: 0; margin: 0; }
.care-list li { display: flex; align-items: center; padding: 10px 0; color: #3d4566; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #FF7A59; margin-right: 10px; }
.mock-note { color: #b0b8cc; font-size: 12px; margin-top: 14px; }
</style>
