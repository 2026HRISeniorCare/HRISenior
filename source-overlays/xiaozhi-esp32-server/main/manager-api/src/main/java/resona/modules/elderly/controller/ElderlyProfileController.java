package resona.modules.elderly.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import resona.common.utils.Result;

@Tag(name = "老人健康档案")
@AllArgsConstructor
@RestController
@RequestMapping("/elderly")
public class ElderlyProfileController {

    @GetMapping("/profiles")
    @Operation(summary = "老人列表")
    public Result<Map<String, Object>> listProfiles(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "50") Integer size) {
        return new Result<>();
    }

    @GetMapping("/profiles/{id}")
    @Operation(summary = "老人详情(含情绪摘要、设备、提醒)")
    public Result<Map<String, Object>> getProfile(@PathVariable String id) {
        return new Result<>();
    }

    @PostMapping("/profiles")
    @Operation(summary = "新增老人档案")
    public Result<Void> createProfile(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @PutMapping("/profiles/{id}")
    @Operation(summary = "编辑老人档案")
    public Result<Void> updateProfile(@PathVariable String id, @RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @DeleteMapping("/profiles/{id}")
    @Operation(summary = "删除老人档案")
    public Result<Void> deleteProfile(@PathVariable String id) {
        return new Result<>();
    }
}
