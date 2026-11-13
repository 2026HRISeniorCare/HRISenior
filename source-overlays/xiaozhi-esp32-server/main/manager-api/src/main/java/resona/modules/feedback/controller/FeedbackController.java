package resona.modules.feedback.controller;

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

@Tag(name = "用户反馈管理")
@AllArgsConstructor
@RestController
@RequestMapping("/feedback")
public class FeedbackController {

    @GetMapping("/list")
    @Operation(summary = "反馈列表")
    public Result<Map<String, Object>> listFeedback(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        return new Result<>();
    }

    @PostMapping
    @Operation(summary = "提交反馈")
    public Result<Void> submitFeedback(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @GetMapping("/stats")
    @Operation(summary = "反馈统计(评分趋势/准确率)")
    public Result<Map<String, Object>> getStats() {
        return new Result<>();
    }

    @GetMapping("/sessions")
    @Operation(summary = "试用会话列表")
    public Result<Map<String, Object>> listSessions(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return new Result<>();
    }

    @PostMapping("/sessions")
    @Operation(summary = "创建/更新试用会话")
    public Result<Void> saveSession(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }
}
