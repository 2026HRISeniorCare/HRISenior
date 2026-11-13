package resona.modules.config.init;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.DependsOn;

import jakarta.annotation.PostConstruct;
import resona.common.constant.Constant;
import resona.common.redis.RedisKeys;
import resona.common.redis.RedisUtils;
import resona.modules.config.service.ConfigService;
import resona.modules.sys.service.SysParamsService;

@Configuration
@DependsOn("liquibase")
public class SystemInitConfig {

    @Autowired
    private SysParamsService sysParamsService;

    @Autowired
    private ConfigService configService;

    @Autowired
    private RedisUtils redisUtils;

    @PostConstruct
    public void init() {
        // 检查版本号
        String redisVersion = (String) redisUtils.get(RedisKeys.getVersionKey());
        if (!Constant.VERSION.equals(redisVersion)) {
            // 如果版本不一致，清空Redis
            redisUtils.emptyAll();
            // 存储新版本号
            redisUtils.set(RedisKeys.getVersionKey(), Constant.VERSION);
        }

        sysParamsService.initServerSecret();
        configService.getConfig(false);
    }
}