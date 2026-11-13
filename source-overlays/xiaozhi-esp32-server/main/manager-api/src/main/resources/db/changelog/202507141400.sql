-- ============================================================
-- 智岁灵犀 网页功能增强 — 新增数据表
-- 包含: 情绪历史、语料库、关怀提醒、紧急联系人、
--       家属联系记录、安全预警、用户反馈、老人档案、预警规则
-- ============================================================

-- 1. 情绪历史记录表
CREATE TABLE IF NOT EXISTS `emotion_history` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `device_id` VARCHAR(100) DEFAULT NULL COMMENT '设备ID',
    `timestamp` DATETIME DEFAULT NULL COMMENT '记录时间',
    `dominant` VARCHAR(20) DEFAULT NULL COMMENT '主导情绪: happy/sad/neutral/anger',
    `score` DOUBLE DEFAULT NULL COMMENT '主导情绪置信度 0-1',
    `belief_json` TEXT DEFAULT NULL COMMENT '四种情绪belief值JSON: [happy,sad,neutral,anger]',
    `conflict` DOUBLE DEFAULT NULL COMMENT 'D-S冲突因子K',
    `high_conflict` TINYINT(1) DEFAULT 0 COMMENT '是否高冲突',
    `snr` DOUBLE DEFAULT NULL COMMENT '环境信噪比 dB',
    `lux` DOUBLE DEFAULT NULL COMMENT '环境亮度 lux',
    `vision_reliability` DOUBLE DEFAULT NULL COMMENT '视觉可信度 0-1',
    `audio_reliability` DOUBLE DEFAULT NULL COMMENT '音频可信度 0-1',
    PRIMARY KEY (`id`),
    INDEX `idx_device_time` (`device_id`, `timestamp`),
    INDEX `idx_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情绪历史记录';

-- 2. 语料库对话表
CREATE TABLE IF NOT EXISTS `corpus_dialog` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `device_id` VARCHAR(100) DEFAULT NULL COMMENT '设备ID',
    `user_text` TEXT DEFAULT NULL COMMENT '用户说的话',
    `bot_text` TEXT DEFAULT NULL COMMENT '机器人回复',
    `emotion_label` VARCHAR(20) DEFAULT NULL COMMENT '情绪标签: happy/sad/neutral/anger',
    `intent_label` VARCHAR(20) DEFAULT NULL COMMENT '意图类别: chat/emotional/emergency',
    `quality_score` INT DEFAULT NULL COMMENT '回复质量评分 1-5',
    `notes` VARCHAR(500) DEFAULT NULL COMMENT '备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_device` (`device_id`),
    INDEX `idx_emotion` (`emotion_label`),
    INDEX `idx_intent` (`intent_label`),
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='语料库对话记录';

-- 3. 关怀提醒表
CREATE TABLE IF NOT EXISTS `care_reminder` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `type` VARCHAR(20) DEFAULT NULL COMMENT '提醒类型: medication/checkup/birthday/custom',
    `schedule_time` DATETIME DEFAULT NULL COMMENT '提醒时间',
    `repeat_type` VARCHAR(10) DEFAULT 'once' COMMENT '重复: once/daily/weekly',
    `elderly_name` VARCHAR(50) DEFAULT NULL COMMENT '关联老人姓名',
    `note` VARCHAR(500) DEFAULT NULL COMMENT '备注',
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/sent/confirmed',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_schedule` (`schedule_time`),
    INDEX `idx_elderly` (`elderly_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关怀提醒';

-- 4. 紧急联系人表
CREATE TABLE IF NOT EXISTS `emergency_contact` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '联系人姓名',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
    `relation` VARCHAR(20) DEFAULT NULL COMMENT '与老人关系',
    `elderly_name` VARCHAR(50) DEFAULT NULL COMMENT '关联老人姓名',
    PRIMARY KEY (`id`),
    INDEX `idx_elderly` (`elderly_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='紧急联系人';

-- 5. 家属联系记录表
CREATE TABLE IF NOT EXISTS `family_contact_log` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `time` DATETIME DEFAULT NULL COMMENT '联系时间',
    `method` VARCHAR(20) DEFAULT NULL COMMENT '联系方式: phone/wechat/visit',
    `summary` VARCHAR(500) DEFAULT NULL COMMENT '沟通摘要',
    `elderly_name` VARCHAR(50) DEFAULT NULL COMMENT '关联老人姓名',
    PRIMARY KEY (`id`),
    INDEX `idx_time` (`time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='家属联系记录';

-- 6. 安全预警事件表
CREATE TABLE IF NOT EXISTS `safety_alert` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `level` VARCHAR(20) DEFAULT NULL COMMENT '预警级别: attention/warning/danger',
    `device_id` VARCHAR(100) DEFAULT NULL COMMENT '设备ID',
    `elderly_name` VARCHAR(50) DEFAULT NULL COMMENT '老人姓名',
    `trigger_text` TEXT DEFAULT NULL COMMENT '触发预警语句',
    `handle_status` VARCHAR(20) DEFAULT 'pending' COMMENT '处理状态: pending/contacted/resolved',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_level` (`level`),
    INDEX `idx_status` (`handle_status`),
    INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='安全预警事件';

-- 7. 用户试用反馈表
CREATE TABLE IF NOT EXISTS `user_feedback` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `session_id` VARCHAR(36) DEFAULT NULL COMMENT '试用会话ID',
    `elderly_name` VARCHAR(50) DEFAULT NULL COMMENT '老人姓名',
    `rating` INT DEFAULT NULL COMMENT '评分 1-5',
    `comment` VARCHAR(1000) DEFAULT NULL COMMENT '文字评价',
    `emotion_accurate` TINYINT(1) DEFAULT NULL COMMENT '情绪判断是否准确',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_session` (`session_id`),
    INDEX `idx_rating` (`rating`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户试用反馈';

-- 8. 老人健康档案表
CREATE TABLE IF NOT EXISTS `elderly_profile` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '姓名',
    `age` INT DEFAULT NULL COMMENT '年龄',
    `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别',
    `emergency_contact` VARCHAR(50) DEFAULT NULL COMMENT '紧急联系人姓名',
    `emergency_phone` VARCHAR(20) DEFAULT NULL COMMENT '紧急联系电话',
    `medical_tags` VARCHAR(500) DEFAULT NULL COMMENT '病史标签JSON数组',
    `device_id` VARCHAR(100) DEFAULT NULL COMMENT '关联设备ID',
    PRIMARY KEY (`id`),
    INDEX `idx_device` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='老人健康档案';

-- 9. 情绪预警规则表
CREATE TABLE IF NOT EXISTS `alert_rule` (
    `id` VARCHAR(36) NOT NULL COMMENT '主键',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '规则名称',
    `condition_field` VARCHAR(20) DEFAULT NULL COMMENT '条件字段: conflict/dominant',
    `condition_op` VARCHAR(10) DEFAULT NULL COMMENT '操作符: gt/gte/eq/lt',
    `condition_value` VARCHAR(50) DEFAULT NULL COMMENT '条件值',
    `condition_text` VARCHAR(200) DEFAULT NULL COMMENT '条件描述文本',
    `action` VARCHAR(30) DEFAULT NULL COMMENT '执行动作: mark_high_priority/notify_contacts/log_safety_event',
    `action_text` VARCHAR(100) DEFAULT NULL COMMENT '动作描述文本',
    `enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情绪预警规则';
