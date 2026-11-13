<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">D-S 融合算法仿真器</div>
      <div class="page-sub">演示视觉(表情)和语音(声学)两个证据源如何通过 Dempster-Shafer 理论融合出最终情绪判断</div>

      <el-row :gutter="20">
        <!-- 左侧控制区 -->
        <el-col :span="8">
          <el-card class="ctrl-card" shadow="never">
            <div class="card-title">视觉证据(表情识别)</div>
            <div v-for="emo in emotions" :key="'v-'+emo.key" class="slider-row">
              <span class="emo-label">{{ emo.emoji }} {{ emo.label }}</span>
              <el-slider v-model="visionBPA[emo.key]" :min="0" :max="1" :step="0.01" show-input size="small" />
            </div>
            <div class="bpa-sum">Σ vision = {{ visionSum.toFixed(2) }} (需 ≤ 1.0)</div>

            <el-divider />

            <div class="card-title">语音证据(声学特征)</div>
            <div v-for="emo in emotions" :key="'a-'+emo.key" class="slider-row">
              <span class="emo-label">{{ emo.emoji }} {{ emo.label }}</span>
              <el-slider v-model="audioBPA[emo.key]" :min="0" :max="1" :step="0.01" show-input size="small" />
            </div>
            <div class="bpa-sum">Σ audio = {{ audioSum.toFixed(2) }} (需 ≤ 1.0)</div>

            <el-divider />

            <div class="card-title">仿真参数</div>
            <div class="slider-row">
              <span class="emo-label">冲突阈值</span>
              <el-slider v-model="kThreshold" :min="0.5" :max="0.99" :step="0.01" show-input size="small" />
            </div>
            <div class="slider-row">
              <span class="emo-label">蒙特卡洛噪声 σ</span>
              <el-slider v-model="noiseSigma" :min="0" :max="0.3" :step="0.01" show-input size="small" />
            </div>

            <div class="btn-row">
              <el-button type="primary" @click="loadRealData" :loading="loadingReal">📡 加载真实数据</el-button>
              <el-button @click="runMonteCarlo" :loading="mcRunning">🎲 蒙特卡洛 5000</el-button>
              <el-button @click="resetSliders">↺ 重置</el-button>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧结果区 -->
        <el-col :span="16">
          <el-card class="result-card" shadow="never">
            <div class="card-title">融合结果对比</div>
            <div ref="barChart" class="result-chart"></div>
          </el-card>

          <el-row :gutter="16" class="mt-16">
            <el-col :span="12">
              <el-card class="result-card" shadow="never">
                <div class="card-title">冲突因子 K</div>
                <div class="k-display" :class="{ 'k-high': fusedK > 0.85 }">K = {{ fusedK.toFixed(4) }}</div>
                <div class="k-hint" v-if="fusedK > 0.85">⚠ 视音矛盾，可能老人"强颜欢笑"</div>
                <div class="k-hint" v-else>视音一致性较好</div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="result-card" shadow="never" v-if="mcResult">
                <div class="card-title">蒙特卡洛结果(N=5000)</div>
                <div class="stat-row-inline">
                  <div class="mc-stat"><span>融合准确率</span><b>{{ (mcResult.fusionAcc * 100).toFixed(1) }}%</b></div>
                  <div class="mc-stat"><span>视觉单独</span><b>{{ (mcResult.visionAcc * 100).toFixed(1) }}%</b></div>
                  <div class="mc-stat"><span>语音单独</span><b>{{ (mcResult.audioAcc * 100).toFixed(1) }}%</b></div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-col>
      </el-row>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';
import * as echarts from 'echarts';

// ---- 纯 JS D-S 融合核心(从 ds_simulator.html 移植) ----
function normalizeBPA(bpa) {
  const total = Object.values(bpa).reduce((s, v) => s + v, 0);
  if (total === 0) return { ...bpa };
  const r = {};
  Object.keys(bpa).forEach(k => { r[k] = bpa[k] / total; });
  return r;
}

function dsCombine(vision, audio) {
  const keys = Object.keys(vision);
  let k = 0;
  const combined = {};
  keys.forEach(key => {
    let sum = 0;
    keys.forEach(other => {
      if (other !== key) sum += vision[key] * audio[other];
    });
    k += sum;
    combined[key] = vision[key] * audio[key];
  });
  if (k >= 1 - 1e-9) {
    // 全冲突，退回平均
    const r = {};
    keys.forEach(key => { r[key] = (vision[key] + audio[key]) / 2; });
    return { result: r, k: 0.9999 };
  }
  const result = {};
  keys.forEach(key => { result[key] = combined[key] / (1 - k); });
  return { result, k };
}

export default {
  name: 'DSSimulator',
  components: { HeaderBar },
  data() {
    return {
      emotions: [
        { key: 'happy', label: '快乐', emoji: '😊', color: '#FF7A59' },
        { key: 'sad', label: '悲伤', emoji: '😢', color: '#6f9cff' },
        { key: 'neutral', label: '平静', emoji: '😌', color: '#9aa5c4' },
        { key: 'anger', label: '生气', emoji: '😠', color: '#ff5e5e' }
      ],
      visionBPA: { happy: 0.3, sad: 0.1, neutral: 0.4, anger: 0.1 },
      audioBPA: { happy: 0.2, sad: 0.5, neutral: 0.2, anger: 0.05 },
      kThreshold: 0.85,
      noiseSigma: 0.05,
      barChart: null,
      fusedResult: null,
      fusedK: 0,
      loadingReal: false,
      mcRunning: false,
      mcResult: null
    }
  },
  computed: {
    visionSum() { return Object.values(this.visionBPA).reduce((s, v) => s + v, 0); },
    audioSum() { return Object.values(this.audioBPA).reduce((s, v) => s + v, 0); }
  },
  mounted() { this.runFusion(); },
  beforeDestroy() { if (this.barChart) this.barChart.dispose(); },
  watch: {
    visionBPA: { deep: true, handler() { this.runFusion(); } },
    audioBPA: { deep: true, handler() { this.runFusion(); } }
  },
  methods: {
    runFusion() {
      const vNorm = normalizeBPA(this.visionBPA);
      const aNorm = normalizeBPA(this.audioBPA);
      const { result, k } = dsCombine(vNorm, aNorm);
      this.fusedResult = result;
      this.fusedK = k;
      this.$nextTick(this.renderChart);
    },
    renderChart() {
      if (!this.$refs.barChart) return;
      if (!this.barChart) this.barChart = echarts.init(this.$refs.barChart);
      const labels = this.emotions.map(e => e.label);
      const vData = this.emotions.map(e => (this.visionBPA[e.key] * 100).toFixed(1));
      const aData = this.emotions.map(e => (this.audioBPA[e.key] * 100).toFixed(1));
      const fData = this.emotions.map(e => this.fusedResult ? (this.fusedResult[e.key] * 100).toFixed(1) : 0);
      this.barChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['视觉单独', '语音单独', 'D-S融合后'], top: 0 },
        grid: { left: 45, right: 15, top: 35, bottom: 20 },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value', max: 100, name: '%' },
        series: [
          { name: '视觉单独', type: 'bar', data: vData, itemStyle: { color: '#f59e0b', borderRadius: [4,4,0,0] } },
          { name: '语音单独', type: 'bar', data: aData, itemStyle: { color: '#6f9cff', borderRadius: [4,4,0,0] } },
          { name: 'D-S融合后', type: 'bar', data: fData, itemStyle: { color: '#FF7A59', borderRadius: [4,4,0,0] } }
        ]
      });
    },
    resetSliders() {
      this.visionBPA = { happy: 0.3, sad: 0.1, neutral: 0.4, anger: 0.1 };
      this.audioBPA = { happy: 0.2, sad: 0.5, neutral: 0.2, anger: 0.05 };
      this.mcResult = null;
    },
    loadRealData() {
      this.loadingReal = true;
      Api.emotion.getCurrentEmotion(({ data }) => {
        if (data && data.code === 0 && data.data) {
          const devices = data.data.devices || [];
          if (devices.length > 0 && devices[0].belief && devices[0].belief.length >= 4) {
            const belief = devices[0].belief;
            this.emotions.forEach((e, i) => {
              this.visionBPA[e.key] = belief[i] || 0;
              this.audioBPA[e.key] = Math.max(0, (belief[i] || 0) + (Math.random() - 0.5) * 0.2);
            });
            this.$message.success(`已加载设备 ${devices[0].device_id} 的真实数据`);
          } else {
            this.$message.warning('当前无在线设备或设备未上报情绪数据');
          }
        }
        this.loadingReal = false;
      });
    },
    runMonteCarlo() {
      this.mcRunning = true;
      const params = {
        vision_bpa: this.visionBPA,
        audio_bpa: this.audioBPA,
        noise_sigma: this.noiseSigma,
        trials: 5000
      };
      Api.emotion.runSimulation(params, ({ data }) => {
        if (data && data.code === 0) {
          this.mcResult = data.data || {};
          this.$message.success('蒙特卡洛仿真完成');
        } else {
          // 降级：纯前端计算
          this.mcResult = this.localMonteCarlo();
          this.$message.info('后端仿真不可用，已使用前端本地计算');
        }
        this.mcRunning = false;
      });
    },
    localMonteCarlo() {
      const N = 5000;
      let visionWins = 0, audioWins = 0, fusionWins = 0;
      const groundTruth = 'sad';
      for (let i = 0; i < N; i++) {
        const v = {}, a = {};
        this.emotions.forEach(e => {
          v[e.key] = Math.max(0, Math.min(1, this.visionBPA[e.key] + (Math.random() - 0.5) * 2 * this.noiseSigma));
          a[e.key] = Math.max(0, Math.min(1, this.audioBPA[e.key] + (Math.random() - 0.5) * 2 * this.noiseSigma));
        });
        const vNorm = normalizeBPA(v), aNorm = normalizeBPA(a);
        const { result } = dsCombine(vNorm, aNorm);
        const vTop = Object.keys(vNorm).sort((x, y) => vNorm[y] - vNorm[x])[0];
        const aTop = Object.keys(aNorm).sort((x, y) => aNorm[y] - aNorm[x])[0];
        const fTop = Object.keys(result).sort((x, y) => result[y] - result[x])[0];
        if (vTop === groundTruth) visionWins++;
        if (aTop === groundTruth) audioWins++;
        if (fTop === groundTruth) fusionWins++;
      }
      return {
        fusionAcc: fusionWins / N,
        visionAcc: visionWins / N,
        audioAcc: audioWins / N,
        improvement: ((fusionWins / N - Math.max(visionWins / N, audioWins / N)) * 100).toFixed(1)
      };
    }
  }
}
</script>

<style scoped>
.emotion-page { min-height: 100vh; display: flex; flex-direction: column; background: linear-gradient(145deg, #fff2ec, #fff8f5); }
.page-main { padding: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #3d4566; }
.page-sub { color: #818cae; margin: 6px 0 18px; }
.ctrl-card, .result-card { border-radius: 14px; border: none; margin-bottom: 12px; }
.card-title { font-weight: 600; color: #3d4566; margin-bottom: 10px; }
.slider-row { margin-bottom: 6px; display: flex; align-items: center; gap: 8px; }
.emo-label { min-width: 65px; font-size: 13px; color: #3d4566; }
.bpa-sum { font-size: 12px; color: #818cae; text-align: right; margin-top: 4px; }
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.result-chart { width: 100%; height: 320px; }
.mt-16 { margin-top: 16px; }
.k-display { font-size: 32px; font-weight: 700; color: #10B981; text-align: center; padding: 16px; }
.k-display.k-high { color: #ff5e5e; }
.k-hint { text-align: center; color: #818cae; font-size: 13px; }
.stat-row-inline { display: flex; gap: 16px; justify-content: center; padding: 10px 0; }
.mc-stat { text-align: center; }
.mc-stat span { display: block; font-size: 12px; color: #818cae; }
.mc-stat b { display: block; font-size: 22px; color: #FF7A59; }
</style>
