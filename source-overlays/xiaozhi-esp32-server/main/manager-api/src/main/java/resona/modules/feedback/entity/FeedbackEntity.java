package resona.modules.feedback.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("user_feedback")
@Schema(description = "用户试用反馈")
public class FeedbackEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    @Schema(description = "试用会话ID")
    private String sessionId;

    @Schema(description = "老人姓名")
    private String elderlyName;

    @Schema(description = "评分 1-5")
    private Integer rating;

    @Schema(description = "文字评价")
    private String comment;

    @Schema(description = "情绪判断是否准确")
    private Boolean emotionAccurate;

    @Schema(description = "创建时间")
    private Date createdAt;
}
