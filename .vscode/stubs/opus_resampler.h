// IntelliSense stub — real header from espressif/opus component
#pragma once
#include <cstdint>
#include <vector>

class OpusResampler {
public:
    void Configure(int input_rate, int output_rate);
    int GetOutputSamples(int input_samples) const;
    void Process(const int16_t* input, int input_samples, int16_t* output);
};
