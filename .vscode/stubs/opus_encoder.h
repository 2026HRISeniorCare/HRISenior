// IntelliSense stub — real header from espressif/opus component
#pragma once
#include <vector>
#include <cstdint>
class OpusEncoderWrapper {
public:
    OpusEncoderWrapper(int sample_rate, int channels, int frame_duration_ms);
    bool Encode(std::vector<int16_t>&& pcm, std::vector<uint8_t>& payload);
    void SetComplexity(int complexity);
    int sample_rate() const;
};