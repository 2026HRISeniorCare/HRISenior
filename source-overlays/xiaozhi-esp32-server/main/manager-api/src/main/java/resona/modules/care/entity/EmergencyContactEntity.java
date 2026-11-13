package resona.modules.care.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("emergency_contact")
@Schema(description = "紧急联系人")
public class EmergencyContactEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "联系人姓名")
    private String name;

    @Schema(description = "联系电话")
    private String phone;

    @Schema(description = "与老人关系")
    private String relation;

    @Schema(description = "关联老人姓名")
    private String elderlyName;
}
