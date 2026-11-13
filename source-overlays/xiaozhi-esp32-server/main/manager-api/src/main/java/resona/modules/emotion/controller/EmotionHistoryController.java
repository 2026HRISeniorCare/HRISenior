package resona.modules.emotion.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import resona.common.utils.Result;

@Tag(name = "情绪历史管理")
@AllArgsConstructor
@RestController
@RequestMapping("/emotion")
public class EmotionHistoryController {

    @PostMapping("/history")
    @Operation(summary = "写入情绪历史记录(Python侧调用)")
    public Result<Void> saveHistory(@RequestBody Map<String, Object> body) {
        // 由Python connection.py异步调用,将实时情绪写入MySQL
        // TODO: 注入 EmotionHistoryService 实现完整CRUD
        // emotionHistoryService.save(body);
        return new Result<>();
    }

    @GetMapping("/history")
    @Operation(summary = "查询情绪历史(分页+筛选+聚合)")
    public Result<Map<String, Object>> getHistory(
            @RequestParam(required = false) String deviceId,
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            @RequestParam(defaultValue = "day") String aggregate,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        // TODO: 注入 EmotionHistoryService 实现查询
        return new Result<>();
    }

    @GetMapping("/stats")
    @Operation(summary = "情绪统计(按天/周/月聚合)")
    public Result<Map<String, Object>> getStats(
            @RequestParam(required = false) String deviceId,
            @RequestParam(required = false) String start,
            @RequestParam(required = false) String end,
            @RequestParam(defaultValue = "day") String aggregate) {
        // TODO: 注入 EmotionHistoryService 实现聚合统计
        return new Result<>();
    }
}
