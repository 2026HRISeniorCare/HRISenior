package resona.modules.sys.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import resona.common.constant.Constant;
import resona.common.page.PageData;
import resona.common.utils.Result;
import resona.common.validator.ValidatorUtils;
import resona.modules.device.dto.DevicePageUserDTO;
import resona.modules.device.service.DeviceService;
import resona.modules.device.vo.UserShowDeviceListVO;
import resona.modules.sys.dto.AdminPageUserDTO;
import resona.modules.sys.service.SysUserService;
import resona.modules.sys.vo.AdminPageUserVO;

/**
 * 管理员控制层
 *
 * @author zjy
 * @since 2025-3-25
 */
@AllArgsConstructor
@RestController
@RequestMapping("/admin")
@Tag(name = "管理员管理")
public class AdminController {
    private final SysUserService sysUserService;

    private final DeviceService deviceService;

    @GetMapping("/users")
    @Operation(summary = "分页查找用户")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = "mobile", description = "用户手机号码", required = false),
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
    })
    public Result<PageData<AdminPageUserVO>> pageUser(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        AdminPageUserDTO dto = new AdminPageUserDTO();
        dto.setMobile((String) params.get("mobile"));
        dto.setLimit((String) params.get(Constant.LIMIT));
        dto.setPage((String) params.get(Constant.PAGE));
        ValidatorUtils.validateEntity(dto);
        PageData<AdminPageUserVO> page = sysUserService.page(dto);
        return new Result<PageData<AdminPageUserVO>>().ok(page);
    }

    @PutMapping("/users/{id}")
    @Operation(summary = "重置密码")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<String> update(
            @PathVariable Long id) {
        String password = sysUserService.resetPassword(id);
        return new Result<String>().ok(password);
    }

    @DeleteMapping("/users/{id}")
    @Operation(summary = "用户删除")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@PathVariable Long id) {
        sysUserService.deleteById(id);
        return new Result<>();
    }

    @PutMapping("/users/changeStatus/{status}")
    @Operation(summary = "批量修改用户状态")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameter(name = "status", description = "用户状态", required = true)
    public Result<Void> changeStatus(@PathVariable Integer status, @RequestBody String[] userIds) {
        sysUserService.changeStatus(status, userIds);
        return new Result<Void>();
    }

    @GetMapping("/device/all")
    @Operation(summary = "分页查找设备")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = "keywords", description = "设备关键词", required = false),
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
    })
    public Result<PageData<UserShowDeviceListVO>> pageDevice(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        DevicePageUserDTO dto = new DevicePageUserDTO();
        dto.setKeywords((String) params.get("keywords"));
        dto.setLimit((String) params.get(Constant.LIMIT));
        dto.setPage((String) params.get(Constant.PAGE));
        ValidatorUtils.validateEntity(dto);
        PageData<UserShowDeviceListVO> page = deviceService.page(dto);
        return new Result<PageData<UserShowDeviceListVO>>().ok(page);
    }
}
