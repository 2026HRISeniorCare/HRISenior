// IntelliSense stub — real header from xiaozhi-esp32 component
#pragma once
#include <string>
#include <functional>
class Http {
public:
    virtual ~Http() = default;
    virtual bool Connect(const std::string& url) = 0;
};