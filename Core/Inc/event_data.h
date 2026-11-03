//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_DATA_H
#define CLEARAIR_EVENT_DATA_H
#include <stdint.h>

// Keep this POD (plain-old-data) so it can be copied through an RTOS queue safely.
struct DataBME680 {
    int8_t temperature;             //  Temperature in C - BME680 with BSEC2
    uint8_t humidity;               // Humidity in % - BME680 with BSEC2
    uint16_t indoorAirQualityIndex; // Indoor Air Quality (IAQ) index - BME680 with BSEC2
};

enum ButtonPressedTypes : uint8_t {
    BUTTON_INVALID = 0,
    //
    BUTTON_UP        = 1,
    BUTTON_DOWN      = 2,
    BUTTON_LEFT      = 3,
    BUTTON_RIGHT     = 4,
    // JUST ONE
    MAX_BUTTON_PRESSED
};

struct DataUiValue {
    uint32_t value;
};

struct DataParticle {
    float mc_2p5;
    float mc_10p0;
    float tps; // typical_particle_size;
};

struct DataCO1NO2 {
    float co1;
    float no2;
};

#endif //CLEARAIR_EVENT_DATA_H
