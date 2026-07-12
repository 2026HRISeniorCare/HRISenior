// IntelliSense stub — real header from xiaozhi-esp32 component
#pragma once
#include <string>
#include <functional>
#include <cstdint>
class WebSocket {
public:
    virtual ~WebSocket() = default;
    virtual bool IsConnected() = 0;
    virtual bool Send(const uint8_t* data, size_t len, bool binary) = 0;
};