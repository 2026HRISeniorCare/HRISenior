package resona.modules.care.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("care_reminder")
@Schema(description = "关怀提醒(用药/复诊/生日等)")
public class CareReminderEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "提醒类型: medication/checkup/birthday/custom")
    private String type;

    @Schema(description = "提醒时间")
    private Date scheduleTime;

    @Schema(description = "重复类型: once/daily/weekly")
    private String repeatType;

    @Schema(description = "关联老人姓名")
    private String elderlyName;

    @Schema(description = "备注")
    private String note;

    @Schema(description = "状态: pending/sent/confirmed")
    private String status;

    @Schema(description = "创建时间")
    private Date createdAt;
}
