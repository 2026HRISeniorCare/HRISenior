package resona.modules.model.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import resona.common.dao.BaseDao;
import resona.modules.model.entity.ModelConfigEntity;

@Mapper
public interface ModelConfigDao extends BaseDao<ModelConfigEntity> {

    /**
     * get model_code list
     */
    List<String> getModelCodeList(@Param("modelType") String modelType, @Param("modelName") String modelName);
}
