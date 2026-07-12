// IntelliSense stub — xiaozhi-esp32 UDP protocol header
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string>
#include <functional>

#ifdef __cplusplus

// xiaozhi-esp32 Udp class
class Udp {
public:
    Udp() = default;
    ~Udp() = default;

    bool Connect(const char* host, int port);
    void Disconnect();
    bool Send(const uint8_t* data, size_t len);
    int Receive(uint8_t* buf, size_t buf_len, int timeout_ms);
    bool IsConnected() const;
};

extern "C" {
#endif

typedef struct udp *udp_handle_t;

#ifdef __cplusplus
}
#endif
