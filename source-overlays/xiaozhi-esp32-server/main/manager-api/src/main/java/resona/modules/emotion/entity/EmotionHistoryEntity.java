package resona.modules.emotion.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("emotion_history")
@Schema(description = "情绪历史记录")
public class EmotionHistoryEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "设备ID")
    private String deviceId;

    @Schema(description = "记录时间")
    private Date timestamp;

    @Schema(description = "主导情绪: happy/sad/neutral/anger")
    private String dominant;

    @Schema(description = "主导情绪置信度 0-1")
    private Double score;

    @Schema(description = "四种情绪belief值JSON数组: [happy,sad,neutral,anger]")
    private String beliefJson;

    @Schema(description = "D-S冲突因子K")
    private Double conflict;

    @Schema(description = "是否高冲突")
    private Boolean highConflict;

    @Schema(description = "环境信噪比 dB")
    private Double snr;

    @Schema(description = "环境亮度 lux")
    private Double lux;

    @Schema(description = "视觉可信度 0-1")
    private Double visionReliability;

    @Schema(description = "音频可信度 0-1")
    private Double audioReliability;
}
