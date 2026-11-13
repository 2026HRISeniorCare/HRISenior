package resona.modules.security.controller;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import lombok.AllArgsConstructor;
import resona.common.constant.Constant;
import resona.common.exception.ErrorCode;
import resona.common.exception.RenException;
import resona.common.page.TokenDTO;
import resona.common.user.UserDetail;
import resona.common.utils.Result;
import resona.common.validator.AssertUtils;
import resona.common.validator.ValidatorUtils;
import resona.modules.security.dto.LoginDTO;
import resona.modules.security.dto.SmsVerificationDTO;
import resona.modules.security.password.PasswordUtils;
import resona.modules.security.service.CaptchaService;
import resona.modules.security.service.SysUserTokenService;
import resona.modules.security.user.SecurityUser;
import resona.modules.sys.dto.PasswordDTO;
import resona.modules.sys.dto.RetrievePasswordDTO;
import resona.modules.sys.dto.SysUserDTO;
import resona.modules.sys.service.SysDictDataService;
import resona.modules.sys.service.SysParamsService;
import resona.modules.sys.service.SysUserService;
import resona.modules.sys.vo.SysDictDataItem;

/**
 * 登录控制层
 */
@AllArgsConstructor
@RestController
@RequestMapping("/user")
@Tag(name = "登录管理")
public class LoginController {
    private final SysUserService sysUserService;
    private final SysUserTokenService sysUserTokenService;
    private final CaptchaService captchaService;
    private final SysParamsService sysParamsService;
    private final SysDictDataService sysDictDataService;

    @GetMapping("/captcha")
    @Operation(summary = "验证码")
    public void captcha(HttpServletResponse response, String uuid) throws IOException {
        // uuid不能为空
        AssertUtils.isBlank(uuid, ErrorCode.IDENTIFIER_NOT_NULL);
        // 生成验证码
        captchaService.create(response, uuid);
    }

    @PostMapping("/smsVerification")
    @Operation(summary = "短信验证码")
    public Result<Void> smsVerification(@RequestBody SmsVerificationDTO dto) {
        // 验证图形验证码
        boolean validate = captchaService.validate(dto.getCaptchaId(), dto.getCaptcha(), true);
        if (!validate) {
            throw new RenException("图形验证码错误");
        }
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        if (!isMobileRegister) {
            throw new RenException("没有开启手机注册，没法使用短信验证码功能");
        }
        // 发送短信验证码
        captchaService.sendSMSValidateCode(dto.getPhone());
        return new Result<>();
    }

    @PostMapping("/login")
    @Operation(summary = "登录")
    public Result<TokenDTO> login(@RequestBody LoginDTO login) {
        // 验证是否正确输入验证码（临时跳过用于开发调试）
        // boolean validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha(), true);
        // if (!validate) {
        //     throw new RenException("图形验证码错误，请重新获取");
        // }
        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        // 判断用户是否存在
        if (userDTO == null) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        // 判断密码是否正确，不一样则进入if
        if (!PasswordUtils.matches(login.getPassword(), userDTO.getPassword())) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        return sysUserTokenService.createToken(userDTO.getId());
    }

    @PostMapping("/register")
    @Operation(summary = "注册")
    public Result<Void> register(@RequestBody LoginDTO login) {
        if (!sysUserService.getAllowUserRegister()) {
            throw new RenException("当前不允许普通用户注册");
        }
        // 是否开启手机注册
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        boolean validate;
        if (isMobileRegister) {
            // 验证用户是否是手机号码
            boolean validPhone = ValidatorUtils.isValidPhone(login.getUsername());
            if (!validPhone) {
                throw new RenException("用户名不是手机号码，请重新输入");
            }
            // 验证短信验证码是否正常
            validate = captchaService.validateSMSValidateCode(login.getUsername(), login.getMobileCaptcha(), false);
            if (!validate) {
                throw new RenException("手机验证码错误，请重新获取");
            }
        } else {
            // 验证码校验已跳过(开发调试)
            // validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha(), true);
            // if (!validate) {
            //     throw new RenException("图形验证码错误，请重新获取");
            // }
        }

        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        if (userDTO != null) {
            throw new RenException("此手机号码已经注册过");
        }
        userDTO = new SysUserDTO();
        userDTO.setUsername(login.getUsername());
        userDTO.setPassword(login.getPassword());
        sysUserService.save(userDTO);
        return new Result<>();
    }

    @GetMapping("/info")
    @Operation(summary = "用户信息获取")
    public Result<UserDetail> info() {
        UserDetail user = SecurityUser.getUser();
        // 补齐头像URL
        SysUserDTO sysUser = sysUserService.getByUserId(user.getId());
        if (sysUser != null) {
            user.setHeadUrl(sysUser.getHeadUrl());
        }
        Result<UserDetail> result = new Result<>();
        result.setData(user);
        return result;
    }

    @PostMapping("/avatar")
    @Operation(summary = "上传头像")
    public Result<String> uploadAvatar(@RequestParam("file") MultipartFile file) {
        // 校验文件类型
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || !originalFilename.matches("(?i).*\\.(jpg|jpeg|png|gif|webp)$")) {
            throw new RenException("只支持 jpg/png/gif/webp 图片格式");
        }
        if (file.getSize() > 5 * 1024 * 1024) {
            throw new RenException("图片大小不能超过5MB");
        }
        try {
            String uploadDir = "uploadfile/avatar";
            Path uploadPath = Paths.get(uploadDir);
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }
            // 文件名:用户ID_时间戳_原始名
            UserDetail user = SecurityUser.getUser();
            String ext = originalFilename.substring(originalFilename.lastIndexOf("."));
            String fileName = user.getId() + "_" + System.currentTimeMillis() + ext;
            Path filePath = uploadPath.resolve(fileName);
            Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);
            String headUrl = "/" + uploadDir + "/" + fileName;
            // 更新数据库
            sysUserService.updateAvatar(user.getId(), headUrl);
            return new Result<String>().ok(headUrl);
        } catch (IOException e) {
            throw new RenException("头像上传失败: " + e.getMessage());
        }
    }

    @PutMapping("/change-password")
    @Operation(summary = "修改用户密码")
    public Result<?> changePassword(@RequestBody PasswordDTO passwordDTO) {
        // 判断非空
        ValidatorUtils.validateEntity(passwordDTO);
        Long userId = SecurityUser.getUserId();
        sysUserTokenService.changePassword(userId, passwordDTO);
        return new Result<>();
    }

    @PutMapping("/retrieve-password")
    @Operation(summary = "找回密码")
    public Result<?> retrievePassword(@RequestBody RetrievePasswordDTO dto) {
        // 是否开启手机注册
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        if (!isMobileRegister) {
            throw new RenException("没有开启手机注册，没法使用找回密码功能");
        }
        // 判断非空
        ValidatorUtils.validateEntity(dto);
        // 验证用户是否是手机号码
        boolean validPhone = ValidatorUtils.isValidPhone(dto.getPhone());
        if (!validPhone) {
            throw new RenException("输入的手机号码格式不正确");
        }

        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(dto.getPhone());
        if (userDTO == null) {
            throw new RenException("输入的手机号码未注册");
        }
        // 验证短信验证码是否正常
        boolean validate = captchaService.validateSMSValidateCode(dto.getPhone(), dto.getCode(), false);
        // 判断是否通过验证
        if (!validate) {
            throw new RenException("输入的手机验证码错误");
        }

        sysUserService.changePasswordDirectly(userDTO.getId(), dto.getPassword());
        return new Result<>();
    }

    @GetMapping("/pub-config")
    @Operation(summary = "公共配置")
    public Result<Map<String, Object>> pubConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("enableMobileRegister", sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class));
        config.put("version", Constant.VERSION);
        config.put("year", "©" + Calendar.getInstance().get(Calendar.YEAR));
        config.put("allowUserRegister", sysUserService.getAllowUserRegister());
        List<SysDictDataItem> list = sysDictDataService.getDictDataByType(Constant.DictType.MOBILE_AREA.getValue());
        config.put("mobileAreaList", list);
        config.put("beianIcpNum", sysParamsService.getValue(Constant.SysBaseParam.BEIAN_ICP_NUM.getValue(), true));
        config.put("beianGaNum", sysParamsService.getValue(Constant.SysBaseParam.BEIAN_GA_NUM.getValue(), true));
        config.put("name", sysParamsService.getValue(Constant.SysBaseParam.SERVER_NAME.getValue(), true));

        return new Result<Map<String, Object>>().ok(config);
    }
}