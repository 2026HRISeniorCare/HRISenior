<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">情绪历史查询</div>
      <div class="page-sub">回看指定设备和时间段内的情绪变化趋势，支持按小时/天/周聚合</div>

      <!-- 筛选栏 -->
      <el-card class="filter-card" shadow="never">
        <el-row :gutter="16" align="middle">
          <el-col :span="5">
            <el-select v-model="deviceId" placeholder="选择设备" clearable filterable>
              <el-option v-for="d in deviceList" :key="d" :label="d" :value="d" />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="yyyy-MM-dd"
            />
          </el-col>
          <el-col :span="3">
            <el-select v-model="aggregate" placeholder="粒度">
              <el-option label="按小时" value="hour" />
              <el-option label="按天" value="day" />
              <el-option label="按周" value="week" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="doQuery" :loading="loading">查询</el-button>
            <el-button @click="exportCSV" :disabled="!records.length">导出 CSV</el-button>
          </el-col>
        </el-row>
      </el-card>

      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stat-row" v-if="stats">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ stats.total }}</div>
            <div class="stat-lbl">总记录数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ stats.dominantTop }}</div>
            <div class="stat-lbl">最多情绪</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ stats.avgK }}</div>
            <div class="stat-lbl">平均冲突因子 K</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num" :class="{ 'danger': stats.highConflictCount > 0 }">{{ stats.highConflictCount }}</div>
            <div class="stat-lbl">高冲突次数</div>
          </div>
        </el-col>
      </el-row>

      <!-- 趋势图 -->
      <el-card class="chart-card" shadow="never" v-if="trendData">
        <div class="panel-title">情绪变化趋势</div>
        <div ref="trendChart" class="trend-chart"></div>
      </el-card>

      <!-- 分布饼图 + 热力图 -->
      <el-row :gutter="16" v-if="trendData">
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">情绪分布</div>
            <div ref="pieChart" class="pie-chart"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card" shadow="never">
            <div class="panel-title">情绪热力图(时段 × 情绪)</div>
            <div ref="heatChart" class="pie-chart"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 原始记录表 -->
      <el-card class="table-card" shadow="never" v-if="records.length > 0">
        <div class="panel-title">原始记录</div>
        <el-table :data="pagedRecords" stripe>
          <el-table-column label="时间" width="180">
            <template slot-scope="scope">{{ scope.row.timestamp || '--' }}</template>
          </el-table-column>
          <el-table-column label="主导情绪" width="100">
            <template slot-scope="scope">
              <el-tag :color="emotionColor(scope.row.dominant)" effect="dark" size="small">
                {{ cnLabel(scope.row.dominant) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="90">
            <template slot-scope="scope">{{ pct(scope.row.score) }}%</template>
          </el-table-column>
          <el-table-column label="冲突因子 K" width="110">
            <template slot-scope="scope">
              <span :class="{ 'k-danger': (scope.row.conflict || 0) > 0.85 }">
                {{ (scope.row.conflict || 0).toFixed(3) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="SNR(dB)" width="80">
            <template slot-scope="scope">{{ scope.row.snr != null ? scope.row.snr.toFixed(1) : '--' }}</template>
          </el-table-column>
          <el-table-column label="Lux" width="80">
            <template slot-scope="scope">{{ scope.row.lux != null ? scope.row.lux.toFixed(0) : '--' }}</template>
          </el-table-column>
          <el-table-column label="高冲突" width="80">
            <template slot-scope="scope">
              <span v-if="scope.row.high_conflict" class="conflict-tag">⚠</span>
              <span v-else>--</span>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="pager"
          background
          layout="prev, pager, next"
          :total="records.length"
          :page-size="pageSize"
          :current-page.sync="currentPage"
        />
      </el-card>

      <!-- 空状态 -->
      <div v-if="!loading && records.length === 0 && queried" class="empty-tip">
        所选时间范围内暂无情绪数据，请调整筛选条件后重试
      </div>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

export default {
  name: 'EmotionHistory',
  components: { HeaderBar },
  data() {
    return {
      deviceId: '',
      deviceList: [],
      dateRange: [],
      aggregate: 'day',
      loading: false,
      queried: false,
      records: [],
      stats: null,
      trendData: null,
      currentPage: 1,
      pageSize: 10,
      trendChart: null,
      pieChart: null,
      heatChart: null,
      emotionMeta: [
        { key: 'happy', label: '快乐', emoji: '😊', color: '#FF7A59' },
        { key: 'sad', label: '悲伤', emoji: '😢', color: '#6f9cff' },
        { key: 'neutral', label: '平静', emoji: '😌', color: '#9aa5c4' },
        { key: 'anger', label: '生气', emoji: '😠', color: '#ff5e5e' }
      ]
    }
  },
  computed: {
    pagedRecords() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.records.slice(start, start + this.pageSize);
    }
  },
  mounted() {
    // 初始化日期范围(最近7天)
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 7);
    this.dateRange = [
      start.toISOString().slice(0, 10),
      end.toISOString().slice(0, 10)
    ];
    // 先获取在线设备列表作为下拉选项
    this.loadDeviceList();
  },
  beforeDestroy() {
    if (this.trendChart) this.trendChart.dispose();
    if (this.pieChart) this.pieChart.dispose();
    if (this.heatChart) this.heatChart.dispose();
  },
  methods: {
    loadDeviceList() {
      Api.emotion.getCurrentEmotion(({ data }) => {
        if (data && data.code === 0) {
          const devices = (data.data && data.data.devices) || [];
          this.deviceList = devices.map(d => d.device_id);
        }
      });
    },
    cnLabel(k) {
      const m = { happy: '快乐', sad: '悲伤', neutral: '平静', anger: '生气' };
      return m[k] || '未知';
    },
    emotionColor(k) {
      const m = { happy: '#FF7A59', sad: '#6f9cff', neutral: '#9aa5c4', anger: '#ff5e5e' };
      return m[k] || '#999';
    },
    pct(v) { return Math.round((v || 0) * 100); },
    doQuery() {
      this.loading = true;
      this.queried = true;
      const params = {
        aggregate: this.aggregate,
        start: this.dateRange ? this.dateRange[0] : '',
        end: this.dateRange ? this.dateRange[1] : ''
      };
      if (this.deviceId) params.device_id = this.deviceId;

      // 查历史明细
      Api.emotion.getEmotionHistory(params, ({ data }) => {
        if (data && data.code === 0) {
          this.records = (data.data && data.data.records) || [];
          this.trendData = (data.data && data.data.trend) || null;
          this.stats = {
            total: (data.data && data.data.total) || this.records.length,
            dominantTop: this.cnLabel((data.data && data.data.dominantTop) || '--'),
            avgK: ((data.data && data.data.avgK) || 0).toFixed(3),
            highConflictCount: (data.data && data.data.highConflictCount) || 0
          };
          this.currentPage = 1;
          this.$nextTick(() => {
            this.renderTrendChart();
            this.renderPieChart();
            this.renderHeatChart();
          });
        }
        this.loading = false;
      });
    },
    exportCSV() {
      if (this.records.length === 0) return;
      const header = '时间,设备ID,主导情绪,置信度,快乐%,悲伤%,平静%,生气%,冲突K,高冲突,SNR,Lux';
      const rows = this.records.map(r => {
        const b = r.belief || [];
        return [
          r.timestamp || '', r.device_id || this.deviceId, this.cnLabel(r.dominant),
          this.pct(r.score), b[0] || 0, b[1] || 0, b[2] || 0, b[3] || 0,
          (r.conflict || 0).toFixed(3), r.high_conflict ? '是' : '否',
          r.snr != null ? r.snr.toFixed(1) : '', r.lux != null ? r.lux.toFixed(0) : ''
        ].join(',');
      });
      const csv = header + '\n' + rows.join('\n');
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `emotion_history_${this.dateRange[0]}_${this.dateRange[1]}.csv`;
      link.click();
    },
    renderTrendChart() {
      if (!this.$refs.trendChart) return;
      if (!this.trendChart) this.trendChart = echarts.init(this.$refs.trendChart);
      if (!this.trendData) return;
      const t = this.trendData;
      this.trendChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['快乐', '悲伤', '平静', '生气'], top: 0 },
        grid: { left: 50, right: 20, top: 35, bottom: 30 },
        xAxis: { type: 'category', data: t.labels || [], axisLabel: { rotate: 30 } },
        yAxis: { type: 'value', max: 100, name: '%' },
        dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
        series: [
          { name: '快乐', type: 'line', smooth: true, data: t.happy || [], itemStyle: { color: '#FF7A59' } },
          { name: '悲伤', type: 'line', smooth: true, data: t.sad || [], itemStyle: { color: '#6f9cff' } },
          { name: '平静', type: 'line', smooth: true, data: t.neutral || [], itemStyle: { color: '#9aa5c4' } },
          { name: '生气', type: 'line', smooth: true, data: t.anger || [], itemStyle: { color: '#ff5e5e' } }
        ]
      });
    },
    renderPieChart() {
      if (!this.$refs.pieChart) return;
      if (!this.pieChart) this.pieChart = echarts.init(this.$refs.pieChart);
      const counts = { happy: 0, sad: 0, neutral: 0, anger: 0 };
      this.records.forEach(r => { if (counts[r.dominant] !== undefined) counts[r.dominant]++; });
      this.pieChart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        series: [{
          type: 'pie', radius: ['35%', '65%'],
          data: [
            { value: counts.happy, name: '快乐', itemStyle: { color: '#FF7A59' } },
            { value: counts.sad, name: '悲伤', itemStyle: { color: '#6f9cff' } },
            { value: counts.neutral, name: '平静', itemStyle: { color: '#9aa5c4' } },
            { value: counts.anger, name: '生气', itemStyle: { color: '#ff5e5e' } }
          ]
        }]
      });
    },
    renderHeatChart() {
      if (!this.$refs.heatChart) return;
      if (!this.heatChart) this.heatChart = echarts.init(this.$refs.heatChart);
      // 按小时聚合各情绪出现次数
      const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0') + ':00');
      const emotions = ['happy', 'sad', 'neutral', 'anger'];
      const labels = ['快乐', '悲伤', '平静', '生气'];
      const matrix = Array.from({ length: 24 }, () => [0, 0, 0, 0]);
      this.records.forEach(r => {
        if (!r.timestamp) return;
        const h = new Date(r.timestamp).getHours();
        if (h >= 0 && h < 24) {
          const idx = emotions.indexOf(r.dominant);
          if (idx >= 0) matrix[h][idx]++;
        }
      });
      const heatData = [];
      for (let h = 0; h < 24; h++) {
        for (let e = 0; e < 4; e++) {
          heatData.push([e, h, matrix[h][e] || 0]);
        }
      }
      this.heatChart.setOption({
        tooltip: { position: 'top' },
        grid: { left: 80, right: 20, top: 10, bottom: 30 },
        xAxis: { type: 'category', data: labels, splitArea: { show: true } },
        yAxis: { type: 'category', data: hours, splitArea: { show: true } },
        visualMap: { min: 0, max: Math.max(1, ...heatData.map(d => d[2])), calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#fdf7f4', '#ffe0d0', '#FF7A59', '#e04e2f'] } },
        series: [{ type: 'heatmap', data: heatData, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } } }]
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
.filter-card { border-radius: 14px; border: none; margin-bottom: 16px; }
.stat-row { margin-bottom: 16px; }
.stat-card {
  background: #fff; border-radius: 14px; padding: 18px 16px; text-align: center;
  box-shadow: 0 4px 16px rgba(255, 122, 89, 0.08);
}
.stat-num { font-size: 28px; font-weight: 700; color: #FF7A59; }
.stat-num.danger { color: #ff5e5e; }
.stat-lbl { color: #818cae; margin-top: 4px; font-size: 13px; }
.chart-card { border-radius: 14px; border: none; margin-bottom: 16px; }
.panel-title { font-weight: 600; color: #3d4566; margin-bottom: 12px; }
.trend-chart { width: 100%; height: 320px; }
.pie-chart { width: 100%; height: 280px; }
.table-card { border-radius: 14px; border: none; }
.pager { margin-top: 14px; text-align: right; }
.k-danger { color: #ff5e5e; font-weight: 700; }
.conflict-tag { color: #ff5e5e; font-size: 18px; }
.empty-tip {
  background: #fff; border-radius: 12px; padding: 40px; text-align: center;
  color: #818cae;
}
</style>
