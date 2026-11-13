<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <section class="dashboard-hero">
        <div>
          <div class="page-title">情绪融合监护大盘</div>
          <div class="page-sub">汇聚语音、视觉与 D-S 融合结果，辅助识别老人交互中的情绪波动与冲突信号。</div>
        </div>
        <div class="hero-stats">
          <div class="stat-chip">
            <span class="stat-value">{{ devices.length }}</span>
            <span class="stat-label">在线设备</span>
          </div>
          <div class="stat-chip">
            <span class="stat-value">2s</span>
            <span class="stat-label">刷新周期</span>
          </div>
          <div class="stat-chip">
            <span class="stat-value">A/V</span>
            <span class="stat-label">多模态输入</span>
          </div>
        </div>
      </section>

      <div v-if="devices.length === 0" class="empty-tip">
        <div class="empty-title">等待设备上报</div>
        <div class="empty-copy">暂无在线设备上报情绪数据。请确认 ESP32-S3 与 MaixCam Pro 已完成联调，并开始一次语音或视觉交互。</div>
      </div>

      <div v-for="dev in devices" :key="dev.device_id" class="device-block">
        <div class="device-head">
          <div>
            <span class="dev-id">设备 {{ dev.device_id }}</span>
            <span class="dev-caption">实时融合流</span>
          </div>
          <span v-if="dev.high_conflict" class="conflict-badge">高冲突 · 疑似掩饰负面情绪</span>
        </div>

        <div class="emotion-cards">
          <div v-for="(item, idx) in emotionMeta" :key="idx" class="emo-card"
            :class="{ 'emo-active': dev.dominant === item.key }">
            <div class="emo-token" :style="{ color: item.color }">{{ item.token }}</div>
            <div class="emo-name">{{ item.label }}</div>
            <div class="emo-bar-bg">
              <div class="emo-bar" :style="{ width: beliefPct(dev, idx) + '%', background: item.color }"></div>
            </div>
            <div class="emo-pct">{{ beliefPct(dev, idx) }}%</div>
          </div>
        </div>

        <div class="metric-row">
          <div class="metric">
            <div class="metric-label">主导情绪</div>
            <div class="metric-value">{{ cnLabel(dev.dominant) }}（{{ pct(dev.score) }}%）</div>
          </div>
          <div class="metric">
            <div class="metric-label">D-S 冲突因子 K</div>
            <div class="metric-value">{{ (dev.conflict || 0).toFixed(3) }}</div>
          </div>
        </div>

        <div :ref="'chart_' + dev.device_id" class="trend-chart"></div>
      </div>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

export default {
  name: 'EmotionDashboard',
  components: { HeaderBar },
  data() {
    return {
      devices: [],
      timer: null,
      charts: {},        // device_id -> echarts instance
      history: {},       // device_id -> { time:[], series:{happy:[],...} }
      emotionMeta: [
        { key: 'happy', label: '快乐', token: 'H', color: '#FF7A59' },
        { key: 'sad', label: '悲伤', token: 'S', color: '#6f9cff' },
        { key: 'neutral', label: '平静', token: 'N', color: '#9aa5c4' },
        { key: 'anger', label: '生气', token: 'A', color: '#ff5e5e' }
      ]
    }
  },
  mounted() {
    this.poll();
    this.timer = setInterval(this.poll, 2000);
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer);
    Object.values(this.charts).forEach(c => c && c.dispose());
  },
  methods: {
    beliefPct(dev, idx) {
      const b = dev.belief;
      if (!Array.isArray(b) || b.length <= idx) return 0;
      return Math.round((b[idx] || 0) * 100);
    },
    pct(v) { return Math.round((v || 0) * 100); },
    cnLabel(k) {
      const m = { happy: '快乐', sad: '悲伤', neutral: '平静', anger: '生气' };
      return m[k] || '未知';
    },
    poll() {
      Api.emotion.getCurrentEmotion(({ data }) => {
        if (data && data.code === 0) {
          this.devices = (data.data && data.data.devices) || [];
          this.$nextTick(this.updateCharts);
        }
      });
    },
    updateCharts() {
      const now = new Date().toLocaleTimeString();
      this.devices.forEach(dev => {
        const id = dev.device_id;
        if (!this.history[id]) {
          this.history[id] = { time: [], happy: [], sad: [], neutral: [], anger: [] };
        }
        const h = this.history[id];
        h.time.push(now);
        ['happy', 'sad', 'neutral', 'anger'].forEach((k, i) => {
          h[k].push(this.beliefPct(dev, i));
        });
        // 仅保留最近 30 个点
        if (h.time.length > 30) {
          h.time.shift();
          ['happy', 'sad', 'neutral', 'anger'].forEach(k => h[k].shift());
        }
        const el = this.$refs['chart_' + id];
        const dom = Array.isArray(el) ? el[0] : el;
        if (!dom) return;
        if (!this.charts[id]) {
          this.charts[id] = echarts.init(dom);
        }
        this.charts[id].setOption({
          color: ['#FF7A59', '#6f9cff', '#9aa5c4', '#ff5e5e'],
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(39, 48, 79, 0.94)',
            borderWidth: 0,
            textStyle: { color: '#fff' }
          },
          legend: {
            data: ['快乐', '悲伤', '平静', '生气'],
            top: 0,
            textStyle: { color: '#626b86' }
          },
          grid: { left: 42, right: 24, top: 38, bottom: 34 },
          xAxis: {
            type: 'category',
            data: h.time,
            axisLine: { lineStyle: { color: '#dbe1ef' } },
            axisLabel: { color: '#8a93ad' }
          },
          yAxis: {
            type: 'value',
            max: 100,
            name: '%',
            splitLine: { lineStyle: { color: '#edf1f8' } },
            axisLabel: { color: '#8a93ad' }
          },
          series: [
            { name: '快乐', type: 'line', smooth: true, data: h.happy, showSymbol: false, lineStyle: { width: 3 } },
            { name: '悲伤', type: 'line', smooth: true, data: h.sad, showSymbol: false, lineStyle: { width: 3 } },
            { name: '平静', type: 'line', smooth: true, data: h.neutral, showSymbol: false, lineStyle: { width: 3 } },
            { name: '生气', type: 'line', smooth: true, data: h.anger, showSymbol: false, lineStyle: { width: 3 } }
          ]
        });
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
  background:
    radial-gradient(circle at 12% 4%, rgba(255, 122, 89, 0.14), transparent 28%),
    radial-gradient(circle at 88% 8%, rgba(111, 156, 255, 0.16), transparent 30%),
    linear-gradient(145deg, #fff7f1, #f7fbff 62%, #fffaf5);
}
.page-main {
  padding: 24px;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
.dashboard-hero {
  display: flex;
  justify-content: space-between;
  gap: 22px;
  align-items: stretch;
  margin-bottom: 22px;
  padding: 28px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow: 0 20px 46px rgba(74, 91, 132, 0.12);
}
.page-title {
  font-size: clamp(28px, 3vw, 46px);
  line-height: 1.08;
  font-weight: 800;
  color: #27304f;
  letter-spacing: -0.04em;
}
.page-sub {
  max-width: 640px;
  color: #6f7894;
  margin: 12px 0 0;
  line-height: 1.8;
}
.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(100px, 1fr));
  gap: 10px;
  min-width: 360px;
}
.stat-chip {
  border-radius: 20px;
  background: linear-gradient(180deg, #fff7f1, #f2f6ff);
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-value {
  color: #ff6f4c;
  font-size: 30px;
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  color: #7d879f;
  margin-top: 10px;
  font-size: 12px;
}
.empty-tip {
  background: rgba(255, 255, 255, 0.82);
  border-radius: 24px;
  padding: 46px;
  text-align: center;
  color: #818cae;
  border: 1px dashed rgba(255, 122, 89, 0.34);
}
.empty-title {
  color: #27304f;
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 10px;
}
.empty-copy {
  max-width: 620px;
  margin: 0 auto;
  line-height: 1.8;
}
.device-block {
  background: rgba(255, 255, 255, 0.86);
  border-radius: 26px;
  padding: 22px;
  margin-bottom: 18px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow: 0 18px 40px rgba(74, 91, 132, 0.1);
}
.device-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.dev-id { font-weight: 800; color: #27304f; font-size: 18px; }
.dev-caption {
  display: block;
  color: #8a93ad;
  font-size: 12px;
  margin-top: 4px;
}
.conflict-badge {
  background: #fff0ea;
  color: #e6513f;
  padding: 7px 13px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}
.emotion-cards { display: flex; gap: 16px; flex-wrap: wrap; }
.emo-card {
  flex: 1;
  min-width: 140px;
  background: linear-gradient(180deg, #fbfcff, #fff8f4);
  border-radius: 20px;
  padding: 18px;
  text-align: left;
  border: 1px solid #edf1f8;
  transition: transform 0.28s ease, border-color 0.28s ease, box-shadow 0.28s ease;
}
.emo-card:hover {
  transform: translateY(-2px);
}
.emo-active {
  border-color: rgba(255, 122, 89, 0.45);
  background: #fff2ec;
  box-shadow: 0 16px 30px rgba(255, 122, 89, 0.16);
}
.emo-token {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(74, 91, 132, 0.1);
}
.emo-name { color: #3d4566; font-weight: 700; margin: 12px 0 8px; }
.emo-bar-bg { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }
.emo-bar { height: 100%; border-radius: 4px; }
.emo-pct { margin-top: 6px; color: #818cae; font-size: 13px; }
.metric-row { display: flex; gap: 14px; margin: 18px 0; flex-wrap: wrap; }
.metric {
  min-width: 180px;
  padding: 14px 16px;
  border-radius: 18px;
  background: #f7f9ff;
}
.metric-label { color: #818cae; font-size: 13px; }
.metric-value { color: #27304f; font-size: 20px; font-weight: 800; margin-top: 6px; font-variant-numeric: tabular-nums; }
.trend-chart { width: 100%; height: 260px; }

@media (max-width: 900px) {
  .dashboard-hero {
    flex-direction: column;
  }
  .hero-stats {
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .page-main {
    padding: 12px;
  }
  .dashboard-hero {
    padding: 22px;
    border-radius: 22px;
  }
  .hero-stats {
    grid-template-columns: 1fr;
  }
  .device-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
