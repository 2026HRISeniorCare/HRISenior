package resona.modules.corpus.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import resona.common.utils.Result;

@Tag(name = "语料库管理")
@AllArgsConstructor
@RestController
@RequestMapping("/corpus")
public class CorpusController {

    @GetMapping("/dialogs")
    @Operation(summary = "语料列表(分页+筛选)")
    public Result<Map<String, Object>> listDialogs(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String emotion,
            @RequestParam(required = false) String intent,
            @RequestParam(required = false) String dateFrom,
            @RequestParam(required = false) String dateTo) {
        // TODO: 注入 CorpusService 实现
        return new Result<>();
    }

    @GetMapping("/dialogs/{id}")
    @Operation(summary = "语料详情")
    public Result<Map<String, Object>> getDialog(@PathVariable String id) {
        return new Result<>();
    }

    @PostMapping("/dialogs/{id}/annotate")
    @Operation(summary = "人工标注")
    public Result<Void> annotateDialog(@PathVariable String id, @RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @PostMapping("/dialogs/batch-label")
    @Operation(summary = "批量标注/导入")
    public Result<Void> batchLabel(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @GetMapping("/dialogs/export")
    @Operation(summary = "导出训练集JSONL")
    public Result<String> exportDialogs(
            @RequestParam(required = false) String ids,
            @RequestParam(defaultValue = "jsonl") String format) {
        // TODO: 返回JSONL文本或文件下载链接
        return new Result<>();
    }

    @DeleteMapping("/dialogs/{id}")
    @Operation(summary = "删除语料")
    public Result<Void> deleteDialog(@PathVariable String id) {
        return new Result<>();
    }

    @GetMapping("/stats")
    @Operation(summary = "语料统计")
    public Result<Map<String, Object>> getStats() {
        // TODO: 返回 total, labeled, labeledPct, emergencyCount
        return new Result<>();
    }
}
