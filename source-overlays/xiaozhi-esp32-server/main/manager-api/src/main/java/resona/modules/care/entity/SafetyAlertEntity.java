package resona.modules.care.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("safety_alert")
@Schema(description = "安全预警事件(轻生/自伤/极端情绪)")
public class SafetyAlertEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "预警级别: attention/warning/danger")
    private String level;

    @Schema(description = "设备ID")
    private String deviceId;

    @Schema(description = "老人姓名")
    private String elderlyName;

    @Schema(description = "触发预警的用户语句")
    private String triggerText;

    @Schema(description = "处理状态: pending/contacted/resolved")
    private String handleStatus;

    @Schema(description = "创建时间")
    private Date createdAt;
}
