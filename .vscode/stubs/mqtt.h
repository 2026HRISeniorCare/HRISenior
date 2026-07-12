// IntelliSense stub — xiaozhi-esp32 MQTT component
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string>
#include <functional>
#include <memory>

#ifdef __cplusplus

// xiaozhi-esp32 Mqtt class (minimal stub for mqtt_protocol.h)
class Mqtt {
public:
    using OnMessageCallback = std::function<void(const std::string& topic, const std::string& payload)>;

    Mqtt() = default;
    ~Mqtt() = default;

    bool Connect(const char* broker_url, int port, const char* client_id,
                 const char* username, const char* password);
    void Disconnect();
    bool Publish(const std::string& topic, const std::string& payload);
    bool Subscribe(const std::string& topic);
    void SetOnMessage(OnMessageCallback callback);
    bool IsConnected() const;
};

// ESP-IDF MQTT C types
extern "C" {
#endif

typedef struct esp_mqtt_client *esp_mqtt_client_handle_t;

typedef struct {
    const char *broker_url;
    const char *username;
    const char *password;
    const char *client_id;
    int port;
    int keepalive;
    int reconnect_timeout_ms;
} esp_mqtt_client_config_t;

#ifdef __cplusplus
}
#endif
