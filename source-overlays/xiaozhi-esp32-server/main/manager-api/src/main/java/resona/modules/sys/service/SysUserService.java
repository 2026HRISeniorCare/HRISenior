package resona.modules.sys.service;

import resona.common.page.PageData;
import resona.common.service.BaseService;
import resona.modules.sys.dto.AdminPageUserDTO;
import resona.modules.sys.dto.PasswordDTO;
import resona.modules.sys.dto.SysUserDTO;
import resona.modules.sys.entity.SysUserEntity;
import resona.modules.sys.vo.AdminPageUserVO;

/**
 * 系统用户
 */
public interface SysUserService extends BaseService<SysUserEntity> {

    SysUserDTO getByUsername(String username);

    SysUserDTO getByUserId(Long userId);

    void save(SysUserDTO dto);

    /**
     * 删除指定用户，且有关联的数据设备和智能体
     * 
     * @param ids
     */
    void deleteById(Long ids);

    /**
     * 验证是否允许修改密码更改
     * 
     * @param userId      用户id
     * @param passwordDTO 验证密码的参数
     */
    void changePassword(Long userId, PasswordDTO passwordDTO);

    /**
     * 直接修改密码，不需要验证
     * 
     * @param userId   用户id
     * @param password 密码
     */
    void changePasswordDirectly(Long userId, String password);

    /**
     * 重置密码
     * 
     * @param userId 用户id
     * @return 随机生成符合规范的密码
     */
    String resetPassword(Long userId);

    /**
     * 管理员分页用户信息
     * 
     * @param dto 分页查找参数
     * @return 用户列表分页数据
     */
    PageData<AdminPageUserVO> page(AdminPageUserDTO dto);

    /**
     * 批量修改用户状态
     * 
     * @param status  用户状态
     * @param userIds 用户ID数组
     */
    void changeStatus(Integer status, String[] userIds);

    /**
     * 获取是否允许用户注册
     *
     * @return 是否允许用户注册
     */
    boolean getAllowUserRegister();

    /**
     * 更新用户头像
     * @param userId 用户ID
     * @param headUrl 头像URL
     */
    void updateAvatar(Long userId, String headUrl);
}
