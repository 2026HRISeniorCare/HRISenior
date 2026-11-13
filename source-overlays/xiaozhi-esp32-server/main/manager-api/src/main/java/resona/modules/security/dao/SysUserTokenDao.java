package resona.modules.security.dao;

import java.util.Date;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import resona.common.dao.BaseDao;
import resona.modules.security.entity.SysUserTokenEntity;

/**
 * 系统用户Token
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Mapper
public interface SysUserTokenDao extends BaseDao<SysUserTokenEntity> {

    SysUserTokenEntity getByToken(String token);

    SysUserTokenEntity getByUserId(Long userId);

    void logout(@Param("userId") Long userId, @Param("expireDate") Date expireDate);
}
