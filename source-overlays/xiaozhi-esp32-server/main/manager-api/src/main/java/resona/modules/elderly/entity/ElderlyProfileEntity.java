package resona.modules.elderly.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("elderly_profile")
@Schema(description = "老人健康档案")
public class ElderlyProfileEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "姓名")
    private String name;

    @Schema(description = "年龄")
    private Integer age;

    @Schema(description = "性别")
    private String gender;

    @Schema(description = "紧急联系人姓名")
    private String emergencyContact;

    @Schema(description = "紧急联系电话")
    private String emergencyPhone;

    @Schema(description = "病史标签JSON数组")
    private String medicalTags;

    @Schema(description = "关联设备ID")
    private String deviceId;
}
