package resona.modules.sys.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;

import resona.common.dao.BaseDao;
import resona.modules.sys.entity.SysDictDataEntity;
import resona.modules.sys.vo.SysDictDataItem;

/**
 * 字典数据
 */
@Mapper
public interface SysDictDataDao extends BaseDao<SysDictDataEntity> {

    List<SysDictDataItem> getDictDataByType(String dictType);

    /**
     * 根据字典类型ID获取字典类型编码
     * 
     * @param dictTypeId 字典类型ID
     * @return 字典类型编码
     */
    String getTypeByTypeId(Long dictTypeId);
}
