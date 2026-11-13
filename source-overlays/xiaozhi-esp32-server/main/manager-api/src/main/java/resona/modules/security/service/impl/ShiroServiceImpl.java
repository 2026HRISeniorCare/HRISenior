package resona.modules.security.service.impl;

import org.springframework.stereotype.Service;

import lombok.AllArgsConstructor;
import resona.modules.security.dao.SysUserTokenDao;
import resona.modules.security.entity.SysUserTokenEntity;
import resona.modules.security.service.ShiroService;
import resona.modules.sys.dao.SysUserDao;
import resona.modules.sys.entity.SysUserEntity;

@AllArgsConstructor
@Service
public class ShiroServiceImpl implements ShiroService {
    private final SysUserDao sysUserDao;
    private final SysUserTokenDao sysUserTokenDao;

    @Override
    public SysUserTokenEntity getByToken(String token) {
        return sysUserTokenDao.getByToken(token);
    }

    @Override
    public SysUserEntity getUser(Long userId) {
        return sysUserDao.selectById(userId);
    }
}