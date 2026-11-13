package resona.modules.alert.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("alert_rule")
@Schema(description = "情绪预警自定义规则")
public class AlertRuleEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "规则名称")
    private String name;

    @Schema(description = "条件字段: conflict/dominant")
    private String conditionField;

    @Schema(description = "条件操作符: gt/gte/eq/lt")
    private String conditionOp;

    @Schema(description = "条件值")
    private String conditionValue;

    @Schema(description = "条件描述文本")
    private String conditionText;

    @Schema(description = "执行动作: mark_high_priority/notify_contacts/log_safety_event")
    private String action;

    @Schema(description = "动作描述文本")
    private String actionText;

    @Schema(description = "是否启用")
    private Boolean enabled;
}
