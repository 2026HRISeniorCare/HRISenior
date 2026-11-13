package resona.modules.corpus.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("corpus_dialog")
@Schema(description = "语料库对话记录")
public class CorpusEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "设备ID")
    private String deviceId;

    @Schema(description = "用户说的话")
    private String userText;

    @Schema(description = "机器人回复")
    private String botText;

    @Schema(description = "情绪标签: happy/sad/neutral/anger")
    private String emotionLabel;

    @Schema(description = "意图类别: chat/emotional/emergency")
    private String intentLabel;

    @Schema(description = "回复质量评分 1-5")
    private Integer qualityScore;

    @Schema(description = "备注")
    private String notes;

    @Schema(description = "创建时间")
    private Date createdAt;
}
