package resona.modules.care.controller;

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

@Tag(name = "关怀提醒·家属联系·安全预警")
@AllArgsConstructor
@RestController
@RequestMapping("/care")
public class CareController {

    // ===== 用药提醒 =====
    @GetMapping("/reminders")
    @Operation(summary = "提醒列表")
    public Result<Map<String, Object>> listReminders(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String type) {
        return new Result<>();
    }

    @PostMapping("/reminders")
    @Operation(summary = "新增提醒")
    public Result<Void> createReminder(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @PutMapping("/reminders/{id}")
    @Operation(summary = "编辑提醒")
    public Result<Void> updateReminder(@PathVariable String id, @RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @DeleteMapping("/reminders/{id}")
    @Operation(summary = "删除提醒")
    public Result<Void> deleteReminder(@PathVariable String id) {
        return new Result<>();
    }

    @GetMapping("/reminder-logs")
    @Operation(summary = "提醒发送日志")
    public Result<Map<String, Object>> getReminderLogs(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        return new Result<>();
    }

    // ===== 家属联系 =====
    @GetMapping("/emergency-contacts")
    @Operation(summary = "紧急联系人列表")
    public Result<Map<String, Object>> getEmergencyContacts(
            @RequestParam(required = false) String elderlyId) {
        return new Result<>();
    }

    @PostMapping("/emergency-contacts")
    @Operation(summary = "新增/编辑紧急联系人")
    public Result<Void> saveEmergencyContact(@RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @GetMapping("/contact-logs")
    @Operation(summary = "联系记录")
    public Result<Map<String, Object>> getContactLogs(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "15") Integer size) {
        return new Result<>();
    }

    // ===== 安全预警 =====
    @GetMapping("/safety-alerts")
    @Operation(summary = "安全预警事件列表")
    public Result<Map<String, Object>> getSafetyAlerts(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        return new Result<>();
    }

    @PutMapping("/safety-alerts/{id}")
    @Operation(summary = "更新安全事件处理状态")
    public Result<Void> updateSafetyAlert(@PathVariable String id, @RequestBody Map<String, Object> body) {
        return new Result<>();
    }

    @GetMapping("/safety-status")
    @Operation(summary = "获取当前安全状态(供HealthOverview指示器)")
    public Result<Map<String, Object>> getSafetyStatus() {
        // 返回: { level: "normal"|"attention"|"warning"|"danger" }
        return new Result<>();
    }
}
