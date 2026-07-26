//
// Created by uv on 21/07/2026.
//

#ifndef CLEARAIR_EVENT_DATA_H
#define CLEARAIR_EVENT_DATA_H
#include <stdint.h>

typedef enum __attribute__((packed)){
        IAQ,
        TEMPERATURE,
        HUMIDITY,
        PRESSURE,
        CO2_EQUIVALENT,
        VOC_EQUIVALENT,
        RAW_GAS,
    } SensorSignal;


    // Keep this POD (plain-old-data) so it can be copied through an RTOS queue safely.
    struct DataBME680 {
        SensorSignal signal;
        float value;
        uint8_t accuracy; // BSEC accuracy 0-3, or 0xFF if n/a
    };


#endif //CLEARAIR_EVENT_DATA_H
