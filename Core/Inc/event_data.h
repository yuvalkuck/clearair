//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_DATA_H
#define CLEARAIR_EVENT_DATA_H
#include <cstdint>

#ifdef __cplusplus
namespace Message { namespace Data {
    enum class SensorSignal : uint8_t {
        IAQ,
        TEMPERATURE,
        HUMIDITY,
        PRESSURE,
        CO2_EQUIVALENT,
        VOC_EQUIVALENT,
        RAW_GAS,
    };

    extern "C" {
#endif
    // Keep this POD (plain-old-data) so it can be copied through an RTOS queue safely.
    struct BME680D {
        uint8_t signal;
        float value;
        uint8_t accuracy; // BSEC accuracy 0-3, or 0xFF if n/a
    };
#ifdef __cplusplus
    }
}}
#endif


#endif //CLEARAIR_EVENT_DATA_H
