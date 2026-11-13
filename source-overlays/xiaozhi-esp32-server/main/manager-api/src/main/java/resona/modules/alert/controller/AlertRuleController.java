package resona.modules.alert.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import resona.common.utils.Result;

@Tag(name = "预警规则管理")
@AllArgsConstructor
@RestController
@RequestMapping("/emotion/alert")
public class AlertRuleController {

    @GetMapping("/rules")
    @Operation(summary = "获取预警规则列表")
    public Result<Map<String, Object>> getRules() {
        // 返回: { rules: [...] }
        return new Result<>();
    }

    @PostMapping("/rules")
    @Operation(summary = "新增/更新预警规则")
    public Result<Void> saveRule(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @DeleteMapping("/rules/{id}")
    @Operation(summary = "删除预警规则")
    public Result<Void> deleteRule(@PathVariable String id) {
        return new Result<>();
    }
}
