// IntelliSense stub — real header from espressif/opus component
#pragma once
#include <vector>
#include <cstdint>
class OpusDecoderWrapper {
public:
    OpusDecoderWrapper(int sample_rate, int channels, int frame_duration_ms);
    bool Decode(std::vector<uint8_t>&& payload, std::vector<int16_t>& pcm);
    int sample_rate() const;
    int duration_ms() const;
    void ResetState();
};