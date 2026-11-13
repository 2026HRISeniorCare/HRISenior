package resona.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import org.apache.ibatis.annotations.Select;
import resona.common.dao.BaseDao;
import resona.modules.agent.entity.AgentEntity;
import resona.modules.agent.vo.AgentInfoVO;

@Mapper
public interface AgentDao extends BaseDao<AgentEntity> {
    /**
     * 获取智能体的设备数量
     * 
     * @param agentId 智能体ID
     * @return 设备数量
     */
    Integer getDeviceCountByAgentId(@Param("agentId") String agentId);

    /**
     * 根据设备MAC地址查询对应设备的默认智能体信息
     *
     * @param macAddress 设备MAC地址
     * @return 默认智能体信息
     */
    @Select(" SELECT a.* FROM ai_device d " +
            " LEFT JOIN ai_agent a ON d.agent_id = a.id " +
            " WHERE d.mac_address = #{macAddress} " +
            " ORDER BY d.id DESC LIMIT 1")
    AgentEntity getDefaultAgentByMacAddress(@Param("macAddress") String macAddress);

    /**
     * 根据id查询agent信息，包括插件信息
     *
     * @param agentId 智能体ID
     */
    AgentInfoVO selectAgentInfoById(@Param("agentId") String agentId);
}
