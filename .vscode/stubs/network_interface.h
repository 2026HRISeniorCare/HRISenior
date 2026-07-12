// IntelliSense stub — real header from xiaozhi-esp32 component
#pragma once
#include <string>
class NetworkInterface {
public:
    virtual ~NetworkInterface() = default;
    virtual bool IsConnected() = 0;
};