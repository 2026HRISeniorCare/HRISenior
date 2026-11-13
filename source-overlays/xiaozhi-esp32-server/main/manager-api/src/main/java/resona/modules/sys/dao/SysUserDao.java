package resona.modules.sys.dao;

import org.apache.ibatis.annotations.Mapper;

import resona.common.dao.BaseDao;
import resona.modules.sys.entity.SysUserEntity;

/**
 * 系统用户
 */
@Mapper
public interface SysUserDao extends BaseDao<SysUserEntity> {

}