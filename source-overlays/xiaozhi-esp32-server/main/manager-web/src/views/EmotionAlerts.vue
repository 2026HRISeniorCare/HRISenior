<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">情绪预警记录</div>
      <div class="page-sub">
        记录语音与表情情绪出现明显冲突（疑似掩饰负面情绪）的时刻，供家属 / 医护关注
      </div>

      <el-card class="table-card" shadow="never">
        <el-table :data="pagedAlerts" style="width: 100%" empty-text="暂无预警记录">
          <el-table-column label="时间" width="200">
            <template slot-scope="scope">{{ fmtTime(scope.row.ts) }}</template>
          </el-table-column>
          <el-table-column prop="device_id" label="设备" width="220" />
          <el-table-column label="主导情绪" width="140">
            <template slot-scope="scope">
              <el-tag type="danger" effect="light">{{ cnLabel(scope.row.dominant) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="冲突因子 K" width="140">
            <template slot-scope="scope">{{ (scope.row.conflict || 0).toFixed(3) }}</template>
          </el-table-column>
          <el-table-column prop="stt_text" label="对话内容" />
        </el-table>

        <div class="pager">
          <el-pagination background layout="prev, pager, next" :total="alerts.length" :page-size="pageSize"
            :current-page.sync="currentPage" />
        </div>
      </el-card>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'EmotionAlerts',
  components: { HeaderBar },
  data() {
    return {
      alerts: [],
      currentPage: 1,
      pageSize: 10,
      timer: null
    }
  },
  computed: {
    pagedAlerts() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.alerts.slice(start, start + this.pageSize);
    }
  },
  mounted() {
    this.fetch();
    this.timer = setInterval(this.fetch, 5000);
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer);
  },
  methods: {
    fetch() {
      Api.emotion.getEmotionAlerts(({ data }) => {
        if (data && data.code === 0) {
          this.alerts = data.data || [];
        }
      });
    },
    cnLabel(k) {
      const m = { happy: '快乐', sad: '悲伤', neutral: '平静', anger: '生气' };
      return m[k] || '未知';
    },
    fmtTime(ts) {
      if (!ts) return '--';
      // ts 为设备上报的毫秒时间戳(设备上电计时),这里直接展示原值+相对说明
      return typeof ts === 'number' ? ('设备时刻 ' + ts + ' ms') : String(ts);
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
.table-card { border-radius: 14px; border: none; }
.pager { margin-top: 16px; text-align: right; }
</style>
