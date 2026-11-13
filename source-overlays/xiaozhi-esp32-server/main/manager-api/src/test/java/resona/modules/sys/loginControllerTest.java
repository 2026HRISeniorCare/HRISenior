package resona.modules.sys;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import lombok.extern.slf4j.Slf4j;
import resona.modules.security.controller.LoginController;
import resona.modules.security.dto.LoginDTO;
import resona.modules.security.dto.SmsVerificationDTO;
import resona.modules.sys.dto.RetrievePasswordDTO;

@Slf4j
@SpringBootTest
@ActiveProfiles("dev")
class loginControllerTest {

    @Autowired
    LoginController loginController;

    @Test
    public void testRegister() {
        LoginDTO loginDTO = new LoginDTO();
        loginDTO.setUsername("手机号码");
        loginDTO.setPassword("密码");
        loginDTO.setCaptcha("123456");
        loginController.register(loginDTO);
    }

    @Test
    public void testSmsVerification() {
        try {
            SmsVerificationDTO smsVerificationDTO = new SmsVerificationDTO();
            smsVerificationDTO.setPhone("手机号码");
            smsVerificationDTO.setCaptchaId("123456");
            smsVerificationDTO.setCaptcha("123456");
            loginController.smsVerification(smsVerificationDTO);
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }
    }

    @Test
    public void testRetrievePassword() {
        try {
            RetrievePasswordDTO retrievePasswordDTO = new RetrievePasswordDTO();
            retrievePasswordDTO.setCode("123456");
            retrievePasswordDTO.setPhone("手机号码");
            retrievePasswordDTO.setPassword("密码");
            loginController.retrievePassword(retrievePasswordDTO);
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }

    }

}