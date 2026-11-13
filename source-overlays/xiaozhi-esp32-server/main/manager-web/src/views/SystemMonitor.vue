<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">系统运行监控</div>
      <div class="page-sub">实时查看 Python 服务运行状态、设备连接数、各模块处理延迟</div>

      <!-- 仪表盘卡片 -->
      <el-row :gutter="16" class="gauge-row">
        <el-col :span="6">
          <div class="gauge-card" :class="gaugeClass(stats.onlineDevices, 5, 20)">
            <div class="gauge-num">{{ stats.onlineDevices }}</div>
            <div class="gauge-lbl">在线设备</div>
            <div class="gauge-sub">共 {{ stats.totalConnections || '--' }} WebSocket 连接</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="gauge-card" :class="latencyClass(stats.llmP95)">
            <div class="gauge-num">{{ stats.llmP95 || '--' }}<span v-if="stats.llmP95">ms</span></div>
            <div class="gauge-lbl">LLM 延迟 P95</div>
            <div class="gauge-sub">P50: {{ stats.llmP50 || '--' }}ms | P99: {{ stats.llmP99 || '--' }}ms</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="gauge-card" :class="stats.memPct > 80 ? 'danger' : (stats.memPct > 60 ? 'warn' : '')">
            <div class="gauge-num">{{ stats.memPct || '--' }}<span v-if="stats.memPct">%</span></div>
            <div class="gauge-lbl">内存占用</div>
            <div class="gauge-sub">CPU: {{ stats.cpuPct || '--' }}%</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="gauge-card" :class="stats.errorRate > 5 ? 'danger' : (stats.errorRate > 1 ? 'warn' : '')">
            <div class="gauge-num">{{ stats.errorRate || '0' }}<span>%</span></div>
            <div class="gauge-lbl">错误率(最近 5 分钟)</div>
            <div class="gauge-sub">总请求: {{ stats.totalRequests || '--' }}</div>
          </div>
        </el-col>
      </el-row>

      <!-- 延迟趋势图 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">LLM 调用延迟趋势(最近 60 秒)</div>
            <div ref="latencyChart" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">ASR / TTS 处理耗时</div>
            <div ref="asrTtsChart" class="chart-box"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 消息吞吐 + 错误日志 -->
      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">消息吞吐量(条/秒)</div>
            <div ref="throughputChart" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">最近错误日志</div>
            <el-table :data="errorLogs" size="small" max-height="240" stripe>
              <el-table-column label="时间" width="90">
                <template slot-scope="scope">{{ scope.row.time || '--' }}</template>
              </el-table-column>
              <el-table-column label="模块" width="70" prop="module" />
              <el-table-column label="错误信息" min-width="200" prop="msg" show-overflow-tooltip />
            </el-table>
            <div v-if="errorLogs.length === 0" class="no-error">暂无错误 👍</div>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

export default {
  name: 'SystemMonitor',
  components: { HeaderBar },
  data() {
    return {
      stats: {
        onlineDevices: '--',
        totalConnections: '--',
        llmP50: '--',
        llmP95: '--',
        llmP99: '--',
        memPct: '--',
        cpuPct: '--',
        errorRate: '0',
        totalRequests: '--'
      },
      errorLogs: [],
      latencyHistory: { time: [], p50: [], p95: [], p99: [] },
      asrTtsHistory: { time: [], asr: [], tts: [] },
      throughputHistory: { time: [], msgs: [] },
      timer: null,
      latencyChart: null,
      asrTtsChart: null,
      throughputChart: null
    }
  },
  mounted() {
    this.poll();
    this.timer = setInterval(this.poll, 3000);
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer);
    if (this.latencyChart) this.latencyChart.dispose();
    if (this.asrTtsChart) this.asrTtsChart.dispose();
    if (this.throughputChart) this.throughputChart.dispose();
  },
  methods: {
    poll() {
      Api.emotion.getMonitorStats(({ data }) => {
        if (data && data.code === 0) {
          const d = data.data || {};
          this.stats.onlineDevices = d.online_devices != null ? d.online_devices : '--';
          this.stats.totalConnections = d.total_connections != null ? d.total_connections : '--';
          this.stats.llmP50 = d.llm_p50_ms;
          this.stats.llmP95 = d.llm_p95_ms;
          this.stats.llmP99 = d.llm_p99_ms;
          this.stats.memPct = d.mem_pct;
          this.stats.cpuPct = d.cpu_pct;
          this.stats.errorRate = d.error_rate != null ? d.error_rate : 0;
          this.stats.totalRequests = d.total_requests != null ? d.total_requests : '--';
          this.errorLogs = d.recent_errors || [];

          // 更新历史数据
          const now = new Date().toLocaleTimeString();
          const maxLen = 60;
          const push = (arr, val, max) => { arr.push(val); if (arr.length > max) arr.shift(); };
          push(this.latencyHistory.time, now, maxLen);
          push(this.latencyHistory.p50, d.llm_p50_ms || 0, maxLen);
          push(this.latencyHistory.p95, d.llm_p95_ms || 0, maxLen);
          push(this.latencyHistory.p99, d.llm_p99_ms || 0, maxLen);
          push(this.asrTtsHistory.time, now, maxLen);
          push(this.asrTtsHistory.asr, d.asr_avg_ms || 0, maxLen);
          push(this.asrTtsHistory.tts, d.tts_avg_ms || 0, maxLen);
          push(this.throughputHistory.time, now, maxLen);
          push(this.throughputHistory.msgs, d.messages_per_sec || 0, maxLen);

          this.$nextTick(() => {
            this.renderLatencyChart();
            this.renderAsrTtsChart();
            this.renderThroughputChart();
          });
        }
      });
    },
    gaugeClass(val, warnTh, dangerTh) {
      if (val === '--') return '';
      if (val < warnTh) return 'danger';
      if (val < dangerTh) return 'warn';
      return '';
    },
    latencyClass(val) {
      if (val === '--' || val == null) return '';
      if (val > 3000) return 'danger';
      if (val > 1500) return 'warn';
      return '';
    },
    renderLatencyChart() {
      if (!this.$refs.latencyChart) return;
      if (!this.latencyChart) this.latencyChart = echarts.init(this.$refs.latencyChart);
      const h = this.latencyHistory;
      this.latencyChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['P50', 'P95', 'P99'], top: 0 },
        grid: { left: 55, right: 20, top: 30, bottom: 25 },
        xAxis: { type: 'category', data: h.time, axisLabel: { show: false } },
        yAxis: { type: 'value', name: 'ms' },
        series: [
          { name: 'P50', type: 'line', smooth: true, data: h.p50, itemStyle: { color: '#10B981' }, lineStyle: { width: 1 } },
          { name: 'P95', type: 'line', smooth: true, data: h.p95, itemStyle: { color: '#F59E0B' }, lineStyle: { width: 1 } },
          { name: 'P99', type: 'line', smooth: true, data: h.p99, itemStyle: { color: '#ff5e5e' }, lineStyle: { width: 1 } }
        ]
      });
    },
    renderAsrTtsChart() {
      if (!this.$refs.asrTtsChart) return;
      if (!this.asrTtsChart) this.asrTtsChart = echarts.init(this.$refs.asrTtsChart);
      const h = this.asrTtsHistory;
      this.asrTtsChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['ASR耗时', 'TTS耗时'], top: 0 },
        grid: { left: 55, right: 20, top: 30, bottom: 25 },
        xAxis: { type: 'category', data: h.time, axisLabel: { show: false } },
        yAxis: { type: 'value', name: 'ms' },
        series: [
          { name: 'ASR耗时', type: 'line', smooth: true, data: h.asr, itemStyle: { color: '#6f9cff' }, areaStyle: { opacity: 0.1 }, lineStyle: { width: 1 } },
          { name: 'TTS耗时', type: 'line', smooth: true, data: h.tts, itemStyle: { color: '#FF7A59' }, areaStyle: { opacity: 0.1 }, lineStyle: { width: 1 } }
        ]
      });
    },
    renderThroughputChart() {
      if (!this.$refs.throughputChart) return;
      if (!this.throughputChart) this.throughputChart = echarts.init(this.$refs.throughputChart);
      const h = this.throughputHistory;
      this.throughputChart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 55, right: 20, top: 15, bottom: 25 },
        xAxis: { type: 'category', data: h.time, axisLabel: { show: false } },
        yAxis: { type: 'value', name: '条/秒' },
        series: [{
          name: '消息吞吐', type: 'bar', data: h.msgs,
          itemStyle: { color: '#FF7A59', borderRadius: [4, 4, 0, 0] }
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
.gauge-row { margin-bottom: 16px; }
.gauge-card {
  background: #fff; border-radius: 14px; padding: 18px 16px; text-align: center;
  box-shadow: 0 4px 16px rgba(255, 122, 89, 0.08);
  border-left: 4px solid #10B981;
}
.gauge-card.warn { border-left-color: #F59E0B; }
.gauge-card.danger { border-left-color: #ff5e5e; }
.gauge-num { font-size: 32px; font-weight: 700; color: #3d4566; }
.gauge-lbl { color: #3d4566; font-weight: 600; margin-top: 4px; }
.gauge-sub { color: #818cae; font-size: 12px; margin-top: 2px; }
.chart-card { border-radius: 14px; border: none; }
.panel-title { font-weight: 600; color: #3d4566; margin-bottom: 10px; }
.chart-box { width: 100%; height: 260px; }
.no-error { text-align: center; color: #10B981; padding: 30px; font-size: 16px; }
</style>
