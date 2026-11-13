<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">语料库管理</div>
      <div class="page-sub">收集和管理老年对话语料，标注情绪与意图，导出训练集用于 LoRA 微调</div>

      <!-- 统计行 -->
      <el-row :gutter="16" class="stat-row" v-if="corpusStats">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ corpusStats.total }}</div>
            <div class="stat-lbl">总语料数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ corpusStats.labeled }}</div>
            <div class="stat-lbl">已标注</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ corpusStats.emergencyCount || 0 }}</div>
            <div class="stat-lbl">紧急求助对话</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-num">{{ corpusStats.labeledPct || 0 }}%</div>
            <div class="stat-lbl">标注完成率</div>
          </div>
        </el-col>
      </el-row>

      <!-- 操作栏 -->
      <el-card class="filter-card" shadow="never">
        <el-row :gutter="12" align="middle">
          <el-col :span="4">
            <el-input v-model="searchText" placeholder="搜索对话关键词" clearable @clear="fetchList" />
          </el-col>
          <el-col :span="3">
            <el-select v-model="emotionFilter" placeholder="情绪筛选" clearable>
              <el-option label="快乐" value="happy" />
              <el-option label="悲伤" value="sad" />
              <el-option label="平静" value="neutral" />
              <el-option label="生气" value="anger" />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="intentFilter" placeholder="意图筛选" clearable>
              <el-option label="日常聊天" value="chat" />
              <el-option label="情绪波动" value="emotional" />
              <el-option label="紧急求助" value="emergency" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-date-picker v-model="dateFilter" type="daterange" range-separator="至"
              start-placeholder="开始" end-placeholder="结束" value-format="yyyy-MM-dd" size="small" />
          </el-col>
          <el-col :span="6">
            <el-button type="primary" @click="fetchList" :loading="loading">搜索</el-button>
            <el-button @click="showImportDialog = true">批量导入</el-button>
            <el-button @click="exportSelected" :disabled="selectedRows.length === 0">导出选中({{ selectedRows.length }})</el-button>
          </el-col>
        </el-row>
      </el-card>

      <!-- 语料表格 -->
      <el-card class="table-card" shadow="never">
        <el-table :data="pagedData" stripe @selection-change="onSelectionChange" ref="tableRef">
          <el-table-column type="selection" width="45" />
          <el-table-column label="时间" width="160">
            <template slot-scope="scope">{{ scope.row.created_at || '--' }}</template>
          </el-table-column>
          <el-table-column label="设备" width="120" prop="device_id" />
          <el-table-column label="老人说" min-width="200" prop="user_text" show-overflow-tooltip />
          <el-table-column label="机器人回复" min-width="200" prop="bot_text" show-overflow-tooltip />
          <el-table-column label="情绪标签" width="100">
            <template slot-scope="scope">
              <el-tag v-if="scope.row.emotion_label" :color="emotionColor(scope.row.emotion_label)" effect="dark" size="small">
                {{ cnLabel(scope.row.emotion_label) }}
              </el-tag>
              <span v-else class="unlabeled">未标注</span>
            </template>
          </el-table-column>
          <el-table-column label="意图" width="90">
            <template slot-scope="scope">
              <span v-if="scope.row.intent_label === 'emergency'" class="emergency-tag">🚨紧急</span>
              <span v-else-if="scope.row.intent_label === 'emotional'">😢情绪</span>
              <span v-else-if="scope.row.intent_label === 'chat'">💬日常</span>
              <span v-else class="unlabeled">--</span>
            </template>
          </el-table-column>
          <el-table-column label="质量" width="70">
            <template slot-scope="scope">
              <el-rate v-if="scope.row.quality_score" :value="scope.row.quality_score" disabled show-score text-color="#FF7A59" />
              <span v-else class="unlabeled">--</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template slot-scope="scope">
              <el-button type="text" size="small" @click="openAnnotate(scope.row)">标注</el-button>
              <el-button type="text" size="small" style="color:#ff5e5e" @click="deleteRow(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination class="pager" background layout="prev, pager, next" :total="total" :page-size="pageSize"
          :current-page.sync="currentPage" @current-change="fetchList" />
      </el-card>

      <!-- 标注弹窗 -->
      <el-dialog title="语料标注" :visible.sync="annotateVisible" width="520px">
        <el-form label-width="80px" v-if="annotateItem">
          <el-form-item label="老人说"><div class="dialog-text">{{ annotateItem.user_text }}</div></el-form-item>
          <el-form-item label="机器人回"><div class="dialog-text">{{ annotateItem.bot_text }}</div></el-form-item>
          <el-form-item label="情绪标签">
            <el-radio-group v-model="annotateForm.emotion_label">
              <el-radio-button label="happy">😊 快乐</el-radio-button>
              <el-radio-button label="sad">😢 悲伤</el-radio-button>
              <el-radio-button label="neutral">😌 平静</el-radio-button>
              <el-radio-button label="anger">😠 生气</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="意图类别">
            <el-select v-model="annotateForm.intent_label" placeholder="选择意图">
              <el-option label="日常聊天" value="chat" />
              <el-option label="情绪波动" value="emotional" />
              <el-option label="紧急求助" value="emergency" />
            </el-select>
          </el-form-item>
          <el-form-item label="回复质量">
            <el-rate v-model="annotateForm.quality_score" show-score text-color="#FF7A59" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="annotateForm.notes" type="textarea" rows="2" placeholder="标注备注(可选)" />
          </el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="annotateVisible = false">取消</el-button>
          <el-button type="primary" @click="doAnnotate" :loading="annotateLoading">保存标注</el-button>
        </span>
      </el-dialog>

      <!-- 批量导入弹窗 -->
      <el-dialog title="批量导入语料" :visible.sync="showImportDialog" width="480px">
        <el-upload drag action="" :auto-upload="false" :on-change="handleFileSelect" accept=".json,.csv,.jsonl">
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">将 JSON/CSV/JSONL 文件拖到此处，或<em>点击上传</em></div>
          <div class="el-upload__tip" slot="tip">JSON 格式: [{ "user_text":"...", "bot_text":"...", "device_id":"..." }, ...]</div>
        </el-upload>
        <span slot="footer">
          <el-button @click="showImportDialog = false">取消</el-button>
          <el-button type="primary" @click="doImport" :loading="importLoading" :disabled="!importFile">确认导入</el-button>
        </span>
      </el-dialog>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'CorpusManagement',
  components: { HeaderBar },
  data() {
    return {
      searchText: '',
      emotionFilter: '',
      intentFilter: '',
      dateFilter: null,
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      selectedRows: [],
      corpusStats: null,
      // 标注弹窗
      annotateVisible: false,
      annotateItem: null,
      annotateForm: { emotion_label: '', intent_label: '', quality_score: 0, notes: '' },
      annotateLoading: false,
      // 导入弹窗
      showImportDialog: false,
      importFile: null,
      importLoading: false
    }
  },
  computed: {
    pagedData() { return this.list; }
  },
  mounted() {
    this.fetchList();
    this.fetchStats();
  },
  methods: {
    cnLabel(k) {
      const m = { happy: '快乐', sad: '悲伤', neutral: '平静', anger: '生气' };
      return m[k] || '未知';
    },
    emotionColor(k) {
      const m = { happy: '#FF7A59', sad: '#6f9cff', neutral: '#9aa5c4', anger: '#ff5e5e' };
      return m[k] || '#999';
    },
    fetchList() {
      this.loading = true;
      const params = {
        page: this.currentPage,
        size: this.pageSize,
        search: this.searchText || '',
        emotion: this.emotionFilter || '',
        intent: this.intentFilter || '',
        date_from: this.dateFilter ? this.dateFilter[0] : '',
        date_to: this.dateFilter ? this.dateFilter[1] : ''
      };
      Api.corpus.getCorpusList(params, ({ data }) => {
        if (data && data.code === 0) {
          this.list = (data.data && data.data.records) || [];
          this.total = (data.data && data.data.total) || 0;
        }
        this.loading = false;
      });
    },
    fetchStats() {
      Api.corpus.getCorpusStats(({ data }) => {
        if (data && data.code === 0) {
          this.corpusStats = data.data || {};
        }
      });
    },
    onSelectionChange(rows) { this.selectedRows = rows; },
    openAnnotate(row) {
      this.annotateItem = row;
      this.annotateForm = {
        emotion_label: row.emotion_label || '',
        intent_label: row.intent_label || '',
        quality_score: row.quality_score || 0,
        notes: ''
      };
      this.annotateVisible = true;
    },
    doAnnotate() {
      this.annotateLoading = true;
      Api.corpus.annotateDialog(this.annotateItem.id, this.annotateForm, ({ data }) => {
        if (data && data.code === 0) {
          this.$message.success('标注保存成功');
          this.annotateVisible = false;
          this.fetchList();
          this.fetchStats();
        } else {
          this.$message.error((data && data.msg) || '标注失败');
        }
        this.annotateLoading = false;
      });
    },
    deleteRow(row) {
      this.$confirm('确定删除该语料吗？', '提示', { type: 'warning' }).then(() => {
        Api.corpus.deleteCorpus(row.id, ({ data }) => {
          if (data && data.code === 0) {
            this.$message.success('删除成功');
            this.fetchList();
            this.fetchStats();
          }
        });
      }).catch(() => {});
    },
    exportSelected() {
      const ids = this.selectedRows.map(r => r.id).join(',');
      // 用 GET 导出(浏览器直接下载)
      const base = process.env.VUE_APP_API_BASE_URL || '';
      const url = `${base}/resona/corpus/dialogs/export?ids=${ids}&format=jsonl`;
      window.open(url, '_blank');
      this.$message.success('导出请求已发送');
    },
    handleFileSelect(file) {
      this.importFile = file.raw;
    },
    doImport() {
      if (!this.importFile) return;
      this.importLoading = true;
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const text = e.target.result;
          const ext = this.importFile.name.split('.').pop().toLowerCase();
          let dialogs = [];
          if (ext === 'jsonl') {
            dialogs = text.split('\n').filter(line => line.trim()).map(line => JSON.parse(line));
          } else if (ext === 'csv') {
            const lines = text.split('\n');
            const headers = lines[0].split(',');
            dialogs = lines.slice(1).filter(l => l.trim()).map(l => {
              const vals = l.split(',');
              const obj = {};
              headers.forEach((h, i) => { obj[h.trim()] = (vals[i] || '').trim(); });
              return obj;
            });
          } else {
            dialogs = JSON.parse(text);
            if (!Array.isArray(dialogs)) dialogs = [dialogs];
          }
          // 调批量导入 API(复用批量标注接口或专用导入接口)
          Api.corpus.batchLabel({ dialogs: dialogs }, ({ data }) => {
            if (data && data.code === 0) {
              this.$message.success(`成功导入 ${dialogs.length} 条语料`);
              this.showImportDialog = false;
              this.importFile = null;
              this.fetchList();
              this.fetchStats();
            } else {
              this.$message.error((data && data.msg) || '导入失败');
            }
            this.importLoading = false;
          });
        } catch (err) {
          console.error('文件解析失败:', err);
          this.$message.error('文件格式不正确，请检查后重试');
          this.importLoading = false;
        }
      };
      reader.readAsText(this.importFile);
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
.stat-row { margin-bottom: 16px; }
.stat-card {
  background: #fff; border-radius: 14px; padding: 18px 16px; text-align: center;
  box-shadow: 0 4px 16px rgba(255, 122, 89, 0.08);
}
.stat-num { font-size: 28px; font-weight: 700; color: #FF7A59; }
.stat-lbl { color: #818cae; margin-top: 4px; font-size: 13px; }
.filter-card { border-radius: 14px; border: none; margin-bottom: 16px; }
.table-card { border-radius: 14px; border: none; }
.pager { margin-top: 14px; text-align: right; }
.unlabeled { color: #b0b8cc; font-size: 12px; }
.emergency-tag { color: #ff5e5e; font-weight: 700; }
.dialog-text {
  background: #fdf7f4; padding: 10px 14px; border-radius: 8px; color: #3d4566;
  max-height: 100px; overflow-y: auto;
}
</style>
