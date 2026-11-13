<template>
  <div class="emotion-page">
    <HeaderBar />
    <el-main class="page-main">
      <div class="page-title">情绪预警规则配置</div>
      <div class="page-sub">调整 D-S 融合冲突阈值、数据过期时间、自定义预警规则，配置可推送到在线设备</div>

      <el-row :gutter="20">
        <!-- 全局配置 -->
        <el-col :span="12">
          <el-card class="conf-card" shadow="never">
            <div class="card-title">全局阈值配置</div>
            <div class="conf-item">
              <div class="conf-label">冲突因子 K 阈值</div>
              <div class="conf-desc">当融合冲突因子超过该值时判定为"高冲突"，触发情绪预警</div>
              <el-slider v-model="config.k_threshold" :min="0.5" :max="0.99" :step="0.01" show-input />
            </div>
            <el-divider />
            <div class="conf-item">
              <div class="conf-label">视觉数据过期时间(ms)</div>
              <div class="conf-desc">超过该时间未收到表情数据，视觉可信度降为零</div>
              <el-slider v-model="config.vision_stale_ms" :min="500" :max="10000" :step="100" show-input />
            </div>
            <el-divider />
            <div class="conf-item">
              <div class="conf-label">音频数据过期时间(ms)</div>
              <div class="conf-desc">超过该时间未收到语音情绪数据，音频可信度降为零</div>
              <el-slider v-model="config.audio_stale_ms" :min="500" :max="10000" :step="100" show-input />
            </div>
            <div class="btn-row">
              <el-button type="primary" @click="saveConfig" :loading="savingConfig">💾 保存配置</el-button>
              <el-button type="warning" @click="pushToDevices" :loading="pushing">📡 推送到在线设备</el-button>
            </div>
          </el-card>
        </el-col>

        <!-- 规则列表 -->
        <el-col :span="12">
          <el-card class="conf-card" shadow="never">
            <div class="card-header">
              <span class="card-title">自定义预警规则</span>
              <el-button type="primary" size="mini" icon="el-icon-plus" circle @click="openRuleDialog()" />
            </div>
            <div v-if="rules.length === 0" class="empty-rules">暂无自定义规则，点击 + 添加</div>
            <div v-for="(rule, idx) in rules" :key="idx" class="rule-item">
              <div class="rule-top">
                <span class="rule-name">{{ rule.name }}</span>
                <el-switch v-model="rule.enabled" active-color="#FF7A59" @change="toggleRule(rule)" />
              </div>
              <div class="rule-cond">条件: {{ rule.condition_text }}</div>
              <div class="rule-action">动作: {{ rule.action_text }}</div>
              <el-button type="text" size="mini" style="color:#ff5e5e" @click="deleteRule(rule)">删除</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 新增/编辑规则弹窗 -->
      <el-dialog title="预警规则" :visible.sync="ruleDialogVisible" width="440px">
        <el-form label-width="80px">
          <el-form-item label="规则名称"><el-input v-model="ruleForm.name" placeholder="如：悲伤高冲突预警" /></el-form-item>
          <el-form-item label="触发条件">
            <el-row :gutter="8">
              <el-col :span="10">
                <el-select v-model="ruleForm.condition_field">
                  <el-option label="冲突因子K" value="conflict" />
                  <el-option label="主导情绪" value="dominant" />
                </el-select>
              </el-col>
              <el-col :span="6">
                <el-select v-model="ruleForm.condition_op">
                  <el-option label=">" value="gt" />
                  <el-option label=">=" value="gte" />
                  <el-option label="=" value="eq" />
                  <el-option label="<" value="lt" />
                </el-select>
              </el-col>
              <el-col :span="8">
                <el-input-number v-if="ruleForm.condition_field === 'conflict'" v-model="ruleForm.condition_value" :min="0" :max="1" :step="0.01" size="small" />
                <el-select v-else v-model="ruleForm.condition_value" size="small">
                  <el-option label="快乐" value="happy" />
                  <el-option label="悲伤" value="sad" />
                  <el-option label="平静" value="neutral" />
                  <el-option label="生气" value="anger" />
                </el-select>
              </el-col>
            </el-row>
          </el-form-item>
          <el-form-item label="执行动作">
            <el-select v-model="ruleForm.action">
              <el-option label="标记高优先级预警" value="mark_high_priority" />
              <el-option label="通知紧急联系人" value="notify_contacts" />
              <el-option label="记录安全事件" value="log_safety_event" />
            </el-select>
          </el-form-item>
        </el-form>
        <span slot="footer">
          <el-button @click="ruleDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveRule">保存</el-button>
        </span>
      </el-dialog>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'AlertRules',
  components: { HeaderBar },
  data() {
    return {
      config: {
        k_threshold: 0.85,
        vision_stale_ms: 3000,
        audio_stale_ms: 3000
      },
      rules: [],
      savingConfig: false,
      pushing: false,
      ruleDialogVisible: false,
      ruleForm: { id: '', name: '', condition_field: 'conflict', condition_op: 'gt', condition_value: 0.9, action: 'mark_high_priority', enabled: true }
    }
  },
  mounted() {
    this.fetchConfig();
    this.fetchRules();
  },
  methods: {
    fetchConfig() {
      Api.alert.getAlertConfig(({ data }) => {
        if (data && data.code === 0 && data.data) {
          this.config = { ...this.config, ...data.data };
        }
      });
    },
    fetchRules() {
      Api.alert.getAlertRules(({ data }) => {
        if (data && data.code === 0) this.rules = (data.data && data.data.rules) || [];
      });
    },
    saveConfig() {
      this.savingConfig = true;
      Api.alert.updateAlertConfig(this.config, ({ data }) => {
        if (data && data.code === 0) this.$message.success('配置已保存');
        else this.$message.error('保存失败');
        this.savingConfig = false;
      });
    },
    pushToDevices() {
      this.pushing = true;
      Api.alert.pushConfigToDevices(({ data }) => {
        if (data && data.code === 0) this.$message.success('配置已推送到在线设备');
        else this.$message.error('推送失败');
        this.pushing = false;
      });
    },
    openRuleDialog(row) {
      this.ruleForm = row ? { ...row } : { id: '', name: '', condition_field: 'conflict', condition_op: 'gt', condition_value: 0.9, action: 'mark_high_priority', enabled: true };
      this.ruleDialogVisible = true;
    },
    saveRule() {
      const conditionText = this.ruleForm.condition_field === 'conflict'
        ? `冲突因子K ${this.ruleForm.condition_op === 'gt' ? '>' : this.ruleForm.condition_op === 'gte' ? '>=' : '='} ${this.ruleForm.condition_value}`
        : `主导情绪 ${this.ruleForm.condition_op === 'eq' ? '=' : ''} ${this.ruleForm.condition_value}`;
      const actionMap = { mark_high_priority: '标记高优先级预警', notify_contacts: '通知紧急联系人', log_safety_event: '记录安全事件' };
      const payload = {
        ...this.ruleForm,
        condition_text: conditionText,
        action_text: actionMap[this.ruleForm.action] || this.ruleForm.action
      };
      Api.alert.createAlertRule(payload, ({ data }) => {
        if (data && data.code === 0) { this.$message.success('规则已保存'); this.ruleDialogVisible = false; this.fetchRules(); }
      });
    },
    toggleRule(rule) {
      Api.alert.createAlertRule({ id: rule.id, enabled: rule.enabled }, ({ data }) => {
        if (data && data.code !== 0) { rule.enabled = !rule.enabled; this.$message.error('更新失败'); }
      });
    },
    deleteRule(rule) {
      this.$confirm('删除该规则？', '提示', { type: 'warning' }).then(() => {
        Api.alert.deleteAlertRule(rule.id, ({ data }) => {
          if (data && data.code === 0) { this.$message.success('已删除'); this.fetchRules(); }
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
.conf-card { border-radius: 14px; border: none; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-title { font-weight: 600; color: #3d4566; }
.conf-item { margin: 8px 0; }
.conf-label { font-weight: 600; color: #3d4566; font-size: 14px; }
.conf-desc { color: #818cae; font-size: 12px; margin: 2px 0 6px; }
.btn-row { display: flex; gap: 8px; margin-top: 14px; }
.rule-item { padding: 12px; border-radius: 10px; background: #fdf7f4; margin-bottom: 8px; }
.rule-top { display: flex; justify-content: space-between; align-items: center; }
.rule-name { font-weight: 600; color: #3d4566; }
.rule-cond { font-size: 13px; color: #818cae; margin-top: 4px; }
.rule-action { font-size: 13px; color: #FF7A59; margin-top: 2px; }
.empty-rules { text-align: center; color: #818cae; padding: 30px 0; }
</style>
